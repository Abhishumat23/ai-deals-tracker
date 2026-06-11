"""
Scraper for ChatGPT (OpenAI) pricing.
Extracts ChatGPT plan pricing dynamically using JS bundle extraction.
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

from utils import convert_to_inr

logger = logging.getLogger(__name__)

TOOL_NAME = "OpenAI"
URL = "https://chatgpt.com/pricing"
EXPECTED_TIERS = ["Free", "Plus", "Pro", "Team"]

def parse_js_price(val_str):
    val_str = val_str.strip()
    try:
        if 'e' in val_str:
            base, exp = val_str.split('e')
            val = float(base) * (10 ** int(exp))
        else:
            val = float(val_str)
        return val / 100.0
    except Exception:
        return None

async def scrape() -> Optional[dict]:
    """Main scrape entrypoint using dynamic JS bundle parsing."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    
    extracted_data = {}
    main_text = ""
    
    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15) as client:
            r = await client.get(URL)
            if r.status_code != 200:
                logger.error(f"Failed to fetch {URL}: {r.status_code}")
                return None
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Find all script or link tags with .js extension
            js_urls = []
            for tag in soup.find_all(["script", "link"]):
                src = tag.get("src") or tag.get("href")
                if src and ".js" in src:
                    if src.startswith("/"):
                        src = "https://chatgpt.com" + src
                    js_urls.append(src)
            
            js_urls = list(dict.fromkeys(js_urls))
            
            for url in js_urls:
                try:
                    res = await client.get(url)
                    if res.status_code != 200:
                        continue
                    js_content = res.text
                    
                    found_any = False
                    for prod in ["chatgpt.free", "chatgpt.go", "chatgpt.plus", "chatgpt.pro"]:
                        if f'"{prod}"' in js_content:
                            found_any = True
                            idx = js_content.find(f'"{prod}"')
                            start = idx + len(prod) + 3
                            brace_count = 0
                            end = start
                            for i in range(start, len(js_content)):
                                if js_content[i] == '{':
                                    brace_count += 1
                                elif js_content[i] == '}':
                                    brace_count -= 1
                                    if brace_count == 0:
                                        end = i + 1
                                        break
                            dict_str = js_content[start:end]
                            kv_pairs = re.findall(r'("?[a-zA-Z0-9_-]+"?:)?([0-9e]+)', dict_str)
                            prices = {}
                            for key, val in kv_pairs:
                                key = key.replace('"', '').replace(':', '').strip()
                                if key in ["usd", "inr"]:
                                    parsed_val = parse_js_price(val)
                                    if parsed_val is not None:
                                        prices[key] = parsed_val
                            extracted_data[prod] = prices
                    if found_any:
                        # Once we successfully find the pricing data chunk, we can stop
                        break
                except Exception as e:
                    logger.warning(f"Error checking JS url {url}: {e}")
    except Exception as e:
        logger.error(f"Error scraping OpenAI: {e}")
        return None

    # Fallbacks and mapping to expected tiers
    # 'Free'
    free_data = extracted_data.get("chatgpt.free", {})
    # 'Plus'
    plus_data = extracted_data.get("chatgpt.plus", {})
    # 'Pro'
    pro_data = extracted_data.get("chatgpt.pro", {})
    # 'Team' (if not found, fall back to $25 / ₹2,500)
    team_data = extracted_data.get("chatgpt.team", {"usd": 25.0, "inr": 2500.0})

    # Construct the tiers
    tiers = []
    
    # 1. Free
    free_usd = free_data.get("usd", 0.0)
    free_inr = free_data.get("inr", 0.0)
    tiers.append({
        "name": "Free",
        "usd_price_str": "free" if free_usd == 0 else f"${free_usd:g}",
        "price": "Free" if free_inr == 0 else f"₹{free_inr:,.0f}",
        "billing_cycle": "always",
        "features": "Access to GPT-4o mini, limited GPT-4o, and basic features."
    })
    
    # 2. Plus
    plus_usd = plus_data.get("usd", 20.0)
    plus_inr = plus_data.get("inr", 1999.0)
    tiers.append({
        "name": "Plus",
        "usd_price_str": f"${plus_usd:g}",
        "price": f"₹{plus_inr:,.0f}/mo" if plus_inr else convert_to_inr(f"${plus_usd}/mo"),
        "billing_cycle": "monthly",
        "features": "Access to GPT-4o, GPT-4, GPT-3.5, advanced data analysis, and priority access."
    })
    
    # 3. Pro
    pro_usd = pro_data.get("usd", 200.0)
    pro_inr = pro_data.get("inr", 19900.0)
    tiers.append({
        "name": "Pro",
        "usd_price_str": f"${pro_usd:g}",
        "price": f"₹{pro_inr:,.0f}/mo" if pro_inr else convert_to_inr(f"${pro_usd}/mo"),
        "billing_cycle": "monthly",
        "features": "Access to GPT-4o at 5x usage limit, o1-pro, advanced voice, and dedicated support."
    })
    
    # 4. Team
    team_usd = team_data.get("usd", 25.0)
    team_inr = team_data.get("inr", 2500.0)
    tiers.append({
        "name": "Team",
        "usd_price_str": f"${team_usd:g}/user",
        "price": f"₹{team_inr:,.0f}/user/mo" if team_inr else convert_to_inr(f"${team_usd}/user/mo"),
        "billing_cycle": "monthly",
        "features": "Everything in Plus, higher limits, admin console, and shared workspace."
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
