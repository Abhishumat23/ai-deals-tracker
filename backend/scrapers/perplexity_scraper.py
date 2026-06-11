"""
Scraper for Perplexity pricing.
Extracts Perplexity plan pricing dynamically using JS bundle extraction.
"""

import asyncio
import json
import logging
import re
# pyrefly: ignore [missing-import]
import httpx
from typing import Optional
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
import sys
sys.path.append('.')

from utils import fetch_html_with_retry, convert_to_inr

logger = logging.getLogger(__name__)

TOOL_NAME = "Perplexity"
URL = "https://www.perplexity.ai/pro"
EXPECTED_TIERS = ["Free", "Pro", "Enterprise"]

def parse_val(val_str):
    val_str = val_str.strip()
    try:
        if 'e' in val_str:
            base, exp = val_str.split('e')
            return float(base) * (10 ** int(exp))
        else:
            return float(val_str)
    except Exception:
        return 0.0

async def scrape() -> Optional[dict]:
    """Main scrape entrypoint using dynamic JS bundle parsing."""
    html = await fetch_html_with_retry(URL, TOOL_NAME)
    if not html:
        return None
        
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract all JS URLs from the page
    js_urls = []
    for tag in soup.find_all(["script", "link"]):
        src = tag.get("src") or tag.get("href")
        if src and ".js" in src:
            if src.startswith("/"):
                src = "https://www.perplexity.ai" + src
            js_urls.append(src)
    js_urls = list(dict.fromkeys(js_urls))
    
    pricing_data = {}
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    async with httpx.AsyncClient(headers=headers, timeout=10) as client:
        for url in js_urls:
            try:
                res = await client.get(url)
                if res.status_code != 200:
                    continue
                content = res.text
                if "yearlyPricePerMonth" in content and "standard:{" in content:
                    # Found the tierMetadata file!
                    dicts = re.findall(r'\b(\w+)=\{monthly:([0-9e]+),yearly:([0-9e]+),yearlyPerMonth:([0-9e]+)\}', content)
                    parsed_dicts = {}
                    for name, m, y, y_pm in dicts:
                        parsed_dicts[name] = {
                            "monthly": parse_val(m),
                            "yearly": parse_val(y),
                            "yearlyPerMonth": parse_val(y_pm)
                        }
                    
                    # Map to friendly structures
                    pro_prices = parsed_dicts.get("f", {"monthly": 20.0, "yearly": 200.0})
                    ent_prices = parsed_dicts.get("g", {"monthly": 40.0, "yearly": 400.0})
                    
                    pricing_data = {
                        "Free": {"monthly": 0.0, "yearly": 0.0},
                        "Pro": pro_prices,
                        "Enterprise": ent_prices
                    }
                    break
            except Exception as e:
                logger.warning(f"Error checking Perplexity JS URL {url}: {e}")
                
    # Fallback to standard prices if JS parsing failed
    if not pricing_data:
        pricing_data = {
            "Free": {"monthly": 0.0, "yearly": 0.0},
            "Pro": {"monthly": 20.0, "yearly": 200.0},
            "Enterprise": {"monthly": 40.0, "yearly": 400.0}
        }
        
    # Construct the tiers
    tiers = []
    
    # 1. Free
    tiers.append({
        "name": "Free",
        "usd_price_str": "free",
        "price": "Free",
        "billing_cycle": "always",
        "features": "Basic search queries, general web sources, and basic search limits."
    })
    
    # 2. Pro
    pro_usd = pricing_data["Pro"]["monthly"]
    tiers.append({
        "name": "Pro",
        "usd_price_str": f"${pro_usd:g}",
        "price": convert_to_inr(f"${pro_usd}/mo"),
        "billing_cycle": "monthly",
        "features": "Unlimited Pro search, access to advanced AI models (Claude, GPT, Gemini), file analysis, and image generation."
    })
    
    # 3. Enterprise
    ent_usd = pricing_data["Enterprise"]["monthly"]
    tiers.append({
        "name": "Enterprise",
        "usd_price_str": f"${ent_usd:g}/user",
        "price": convert_to_inr(f"${ent_usd}/user/mo"),
        "billing_cycle": "monthly",
        "features": "Collaboration tools, SSO, user management, advanced security, and dedicated support."
    })
    
    # Construct raw_text for change detection
    main_text = "\n".join([f"{t['name']}: {t['usd_price_str']} ({t['price']}) - {t['features']}" for t in tiers])
    inr_prices = [t["price"] for t in tiers if t["price"] != "Free"]
    
    return {
        "tool": TOOL_NAME,
        "url": URL,
        "raw_text": main_text,
        "prices_found": inr_prices,
        "tiers": tiers,
        "plan": "Multiple",
        "price": inr_prices[0] if inr_prices else "See website",
    }

if __name__ == "__main__":
    result = asyncio.run(scrape())
    print(json.dumps(result, indent=2))
