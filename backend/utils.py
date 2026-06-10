"""
Utility helpers used across the backend.
Handles text normalization, hashing, and diff generation.
"""

import hashlib
import re
import difflib
from typing import Optional


def normalize_text(text: str) -> str:
    """
    Normalize raw scraped text to reduce false positives from
    trivial HTML/whitespace changes.

    Steps:
    - Collapse all whitespace to single spaces
    - Strip leading/trailing whitespace
    - Remove common noise patterns (timestamps, session IDs, etc.)
    - Lowercase for comparison
    """
    if not text:
        return ""

    # Collapse all whitespace (newlines, tabs, multiple spaces)
    cleaned = re.sub(r"\s+", " ", text)

    # Strip surrounding whitespace
    cleaned = cleaned.strip()

    # Remove patterns that change every request but carry no pricing info:
    # e.g. ISO timestamps like 2024-01-15T12:34:56
    cleaned = re.sub(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?", "", cleaned)

    # Remove cache-busting tokens (hex strings 32+ chars long)
    cleaned = re.sub(r"\b[a-f0-9]{32,}\b", "", cleaned)

    return cleaned.lower()


def hash_content(text: str) -> str:
    """
    Return the SHA-256 hex digest of the normalized text.
    Used to quickly detect whether content has changed.
    """
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def has_changed(old_hash: str, new_hash: str) -> bool:
    """Return True if the two hashes differ (i.e. content changed)."""
    return old_hash != new_hash


def build_diff_summary(old_text: str, new_text: str, max_lines: int = 30) -> str:
    """
    Generate a human-readable unified diff between old and new content.
    Limits output to max_lines for readability in Telegram messages.
    """
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile="previous",
        tofile="current",
        lineterm="",
        n=2,  # context lines
    ))

    if not diff:
        return "No text difference found (hash mismatch may be due to structure)."

    # Trim to max_lines to avoid Telegram message size limits
    trimmed = diff[:max_lines]
    summary = "\n".join(trimmed)
    if len(diff) > max_lines:
        summary += f"\n... ({len(diff) - max_lines} more lines)"

    return summary


def extract_price_mentions(text: str) -> list[str]:
    """
    Simple regex to pull out price-like strings from text.
    Used to enrich change summaries.
    Examples: $20/month, $0.002/1K tokens, Free, €10
    """
    # Match price and optional suffix like /mo, /month, per user, etc.
    pattern = r"(?:free|(?:₹|\$|€|£)\s*[\d,]+(?:\.\d+)?(?:(?:\s*/\s*|\s+per\s+)(?:month|mo|year|yr|user|seat))?|\b[\d,]+(?:\.\d+)?\s*INR(?:(?:\s*/\s*|\s+per\s+)(?:month|mo|year|yr|user|seat))?)"
    matches = re.findall(pattern, text, re.IGNORECASE)
    # Deduplicate while preserving order and converting to INR
    seen = set()
    unique = []
    for m in matches:
        inr_val = convert_to_inr(m)
        key = inr_val.lower()
        if key not in seen:
            seen.add(key)
            unique.append(inr_val)
    return unique


import urllib.request
import json

_cached_rate = None

def get_exchange_rate() -> float:
    """Fetch the latest USD to INR exchange rate, caching the result in memory."""
    global _cached_rate
    if _cached_rate is not None:
        return _cached_rate
    
    try:
        req = urllib.request.Request(
            "https://api.frankfurter.app/latest?from=USD&to=INR",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.loads(response.read().decode())
            _cached_rate = float(data["rates"]["INR"])
            return _cached_rate
    except Exception as e:
        print(f"Failed to fetch exchange rate: {e}")
        return 83.5 # Fallback

def convert_to_inr(price_str: str) -> str:
    """
    Converts a price string (like '$20/mo', '20', or '₹ 1,950 INR / महीना') to a standardized INR format.
    Uses a dynamic exchange rate fetched from an API.
    """
    rate = get_exchange_rate()
    if not price_str or price_str.lower() in ("free", "see website", "multiple", "not found"):
        return price_str

    # Normalize suffix if present
    suffix = ""
    suffix_match = re.search(r"(?:\s*/\s*|\s+per\s+)(month|mo|year|yr|user|seat)", price_str, re.IGNORECASE)
    if suffix_match:
        s = suffix_match.group(1).lower()
        if s in ("month", "mo"):
            suffix = "/mo"
        elif s in ("year", "yr"):
            suffix = "/yr"
        elif s in ("user", "seat"):
            suffix = "/user"
        else:
            suffix = f"/{s}"

    # Find the numeric portion
    match = re.search(r"[\d,]+(?:\.\d+)?", price_str)
    if not match:
        return price_str
    
    val_str = match.group(0).replace(",", "")
    
    try:
        val = float(val_str)
        # If the string already indicates INR, don't multiply
        if "₹" in price_str or "inr" in price_str.lower() or "rs" in price_str.lower():
            inr_val = int(val) if val.is_integer() else val
        else:
            inr_val = int(val * rate) if val.is_integer() else round(val * rate, 2)
        
        return f"₹{inr_val:,.0f}{suffix}"
    except ValueError:
        return price_str

from dataclasses import dataclass, asdict
from typing import List, Dict, Any

@dataclass
class PricingPlan:
    name: str = "Unpublished"
    usd_price_str: str = "Not found"
    price: str = "Not found"
    billing_cycle: str = "Unpublished"
    features: str = "Unpublished"

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

async def fetch_html_with_retry(url: str, tool_name: str, retries: int = 2) -> Optional[str]:
    """Fetch HTML with standard headers and retry logic for bot protection."""
    import asyncio
    # pyrefly: ignore [missing-import]
    from playwright.async_api import async_playwright
    import logging
    logger = logging.getLogger(__name__)
    
    for attempt in range(retries):
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=BROWSER_HEADERS["User-Agent"],
                    viewport={"width": 1920, "height": 1080}
                )
                page = await context.new_page()
                await page.set_extra_http_headers({"Accept-Language": BROWSER_HEADERS["Accept-Language"]})
                await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,media}", lambda r: r.abort())
                
                response = await page.goto(url, timeout=30000, wait_until="domcontentloaded")
                
                if response and response.status in [403, 429]:
                    logger.warning(f"[{tool_name}] Blocked or rate limited (Status {response.status})")
                    await browser.close()
                    await asyncio.sleep(2)
                    continue

                try:
                    await page.wait_for_selector("main, article, section, #__next, .price", timeout=10_000)
                except Exception:
                    pass
                
                html = await page.content()
                await browser.close()
                return html
        except Exception as e:
            logger.warning(f"[{tool_name}] Request failed: {e}")
            await asyncio.sleep(2)
    return None

def _extract_precise_price(text: str) -> str:
    """Strict regex to pull out floating/integer values and currency symbols."""
    # Match $ or ₹ followed by digits/commas/decimals
    match = re.search(r"(\$|₹)\s*([\d,]+(?:\.\d+)?)", text)
    if not match:
        if re.search(r"\bfree\b", text, re.IGNORECASE):
            return "free"
        return "Not found"
    
    val_str = match.group(2).replace(",", "")
    try:
        val = float(val_str)
        return f"${val:g}"
    except ValueError:
        return "Not found"

def extract_pricing_plans(soup, expected_tiers: list[str], anchors: Dict[str, str] = None) -> List[Dict[str, Any]]:
    """
    Implements the strictly dynamic DOM selector strategy.
    Finds heading elements matching expected tier names, walks up to find the card,
    slices the text from the anchor to avoid bleeding, and extracts price/features.
    """
    noise_strings = ["Download", "Log in", "Sign up", "Get started", "Contact Sales"]
    for tag in soup(["script", "style", "nav", "footer", "button", "a", "noscript"]):
        tag.decompose()
        
    extracted = []
    if anchors is None:
        anchors = {}
        
    for tier_name in expected_tiers:
        plan = PricingPlan(name=tier_name)
        
        try:
            elements = []
            anchor_text = anchors.get(tier_name)
            
            # 1. Try anchor text match first
            if anchor_text:
                elements = soup.find_all(string=re.compile(re.escape(anchor_text), re.IGNORECASE))
                elements = [el.parent for el in elements if el.parent]
                
            # 2. Dynamically search for the tier name in headings/containers
            if not elements:
                elements = soup.find_all(lambda t: t.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'strong', 'span']
                                         and t.string and tier_name.lower() == t.string.strip().lower())
                                         
            # 3. Fallback: Just get any element containing the text
            if not elements:
                elements = soup.find_all(string=re.compile(r'\b' + re.escape(tier_name) + r'\b', re.IGNORECASE))
                elements = [el.parent for el in elements if el.parent and el.parent.name not in ['body', 'html', 'main']]
                
            if elements:
                # Pick the most tightly scoped element
                target_node = min(elements, key=lambda tag: len(tag.get_text(strip=True)))
                
                # Walk up exactly 3 levels to get the column/card container
                # Stop if we hit a known wrapper structure to avoid engulfing other columns
                card = target_node
                for _ in range(3):
                    if card.parent and card.parent.name not in ['body', 'html', 'main', 'section']:
                        card = card.parent
                        
                card_text = card.get_text(separator=" ", strip=True)
                
                # Dynamic String Slicing: Only look for prices near the tier name
                # This prevents picking up a $0 price from a "Free" column that happens to be an ancestor in flat SPAs
                anchor_idx = -1
                if anchor_text:
                    anchor_idx = card_text.lower().find(anchor_text.lower())
                if anchor_idx == -1:
                    anchor_idx = card_text.lower().find(tier_name.lower())
                
                if anchor_idx != -1:
                    # Keep up to 150 characters before the anchor in case the price is placed above the heading
                    start_idx = max(0, anchor_idx - 150)
                    card_text = card_text[start_idx:]
                    
                # Strip dynamic noise
                for noise in noise_strings:
                    card_text = re.sub(re.escape(noise), "", card_text, flags=re.IGNORECASE)
                    
                plan.usd_price_str = _extract_precise_price(card_text)
                
                if plan.usd_price_str != "Not found":
                    plan.price = convert_to_inr(plan.usd_price_str)
                elif "free" in card_text.lower() and tier_name.lower() != "team":
                    plan.price = "Free"
                    
                # Dynamic Billing Extraction
                if re.search(r"/\s*(mo|month)\b", card_text, re.IGNORECASE):
                    plan.billing_cycle = "monthly"
                elif re.search(r"/\s*(yr|year|annually)\b", card_text, re.IGNORECASE):
                    plan.billing_cycle = "annually"
                elif plan.price == "Free" or plan.price == "₹0":
                    plan.billing_cycle = "always"
                    
                # Dynamic Feature Extraction
                lis = card.find_all('li')
                if lis:
                    plan.features = " | ".join([li.get_text(strip=True) for li in lis])
                else:
                    clean_text = re.sub(r'[^A-Za-z0-9\s,\.\-]', '', card_text)
                    # Use up to 150 chars to avoid grabbing the whole page
                    plan.features = clean_text[:150] + "..." if len(clean_text) > 150 else clean_text
                    
        except Exception as e:
            pass # Fails safely to dataclass defaults
            
        extracted.append(asdict(plan))
        
    return extracted

def truncate(text: str, max_chars: int = 500) -> str:
    """Truncate text to max_chars and append ellipsis if needed."""
    if not text or len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "…"
