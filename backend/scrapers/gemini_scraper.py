"""
Scraper for https://gemini.google/subscriptions/
Extracts Gemini Advanced pricing strictly using dynamic DOM extraction.
"""

import asyncio
import json
import logging
import re
from typing import Optional
from bs4 import BeautifulSoup
import sys
sys.path.append('.')

from utils import fetch_html_with_retry, extract_pricing_plans, convert_to_inr

logger = logging.getLogger(__name__)

TOOL_NAME = "Gemini"
URL = "https://gemini.google/subscriptions/"
EXPECTED_TIERS = ["Free", "Google AI Plus", "Business", "Enterprise"]

ANCHORS = {
    "Free": "Gemini",
    "Google AI Plus": "Gemini Advanced",
    "Business": "Gemini for Google Workspace",
    "Enterprise": "Gemini Enterprise"
}

async def scrape() -> Optional[dict]:
    """Main scrape entrypoint."""
    html = await fetch_html_with_retry(URL, TOOL_NAME)
    if not html:
        return None
        
    soup = BeautifulSoup(html, "html.parser")
    
    # Extract raw text for legacy global price match (if needed)
    main_text = soup.get_text(separator=" ", strip=True)
    prices_raw = re.findall(r"(?:₹|\$)\s*[\d,]+(?:\.\d+)?(?:/\w+)?|[\d,]+(?:\.\d+)?\s*INR(?:/\w+)?", main_text)
    inr_prices = [convert_to_inr(p) for p in list(dict.fromkeys(prices_raw))]

    tiers = extract_pricing_plans(soup, EXPECTED_TIERS, ANCHORS)

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
