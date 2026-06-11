import asyncio
from bs4 import BeautifulSoup
import sys
sys.path.append('.')
from scrapers.gemini_scraper import URL, EXPECTED_TIERS, ANCHORS
from utils import fetch_html_with_retry

async def main():
    html = await fetch_html_with_retry(URL, "Gemini", wait_selector="div[class*='_cardLogoText_']")
    soup = BeautifulSoup(html, "html.parser")
    
    import copy
    import re
    from utils import _extract_precise_price, convert_to_inr
    
    soup_copy = copy.copy(soup)
    for tag in soup_copy(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
        
    tier_nodes = {}
    
    def score_candidate(tag):
        text_len = len(tag.get_text(strip=True))
        has_btn = False
        curr = tag
        while curr:
            if curr.name in ['button'] or curr.get('role') == 'tab':
                has_btn = True
                break
            classes = curr.get('class', [])
            if isinstance(classes, list):
                if any('tab' in c.lower() for c in classes):
                    has_btn = True
                    break
            elif isinstance(classes, str):
                if 'tab' in classes.lower():
                    has_btn = True
                    break
            curr = curr.parent
        return (has_btn, text_len)

    for tier_name in EXPECTED_TIERS:
        elements = []
        anchor_text = ANCHORS.get(tier_name)
        if anchor_text:
            elements = soup_copy.find_all(string=re.compile(re.escape(anchor_text), re.IGNORECASE))
            elements = [el.parent for el in elements if el.parent]
        if not elements:
            elements = soup_copy.find_all(lambda t: t.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'span']
                                     and t.string and tier_name.lower() == t.string.strip().lower())
        if not elements:
            elements = soup_copy.find_all(string=re.compile(r'\b' + re.escape(tier_name) + r'(?:\b|\d|\*|\s)', re.IGNORECASE))
            elements = [el.parent for el in elements if el.parent and el.parent.name not in ['body', 'html', 'main']]
            
        if elements:
            target_node = min(elements, key=score_candidate)
            tier_nodes[tier_name] = target_node

    all_heading_nodes = list(tier_nodes.values())
    
    def is_ancestor(ancestor, node):
        curr = node.parent
        while curr:
            if curr == ancestor:
                return True
            curr = curr.parent
        return False

    noise_strings = ["Download", "Log in", "Sign up", "Get started", "Contact Sales"]
    
    for tier_name in EXPECTED_TIERS:
        target_node = tier_nodes.get(tier_name)
        if not target_node:
            print(f"[{tier_name}] No target node found")
            continue
            
        card = target_node
        for _ in range(8):
            parent = card.parent
            if not parent or parent.name in ['body', 'html', 'main', 'section']:
                break
            
            engulfed_other = False
            for other_node in all_heading_nodes:
                if other_node != target_node and is_ancestor(parent, other_node):
                    engulfed_other = True
                    break
            
            if engulfed_other:
                break
            card = parent
            
        lis = card.find_all('li')
        features_list = [li.get_text(strip=True) for li in lis if li.get_text(strip=True)]
        
        card_for_price = copy.deepcopy(card)
        for li in card_for_price.find_all('li'):
            li.decompose()
        card_text_for_price = card_for_price.get_text(separator=" ", strip=True)
        card_text_full = card.get_text(separator=" ", strip=True)
        
        for noise in noise_strings:
            card_text_for_price = re.sub(re.escape(noise), "", card_text_for_price, flags=re.IGNORECASE)
            card_text_full = re.sub(re.escape(noise), "", card_text_full, flags=re.IGNORECASE)
            
        usd_price_str = _extract_precise_price(card_text_for_price)
        print(f"\n--- {tier_name} ---")
        print("card_text_for_price:", repr(card_text_for_price))
        print("usd_price_str:", usd_price_str)
        if usd_price_str == "Not found":
            fallback_price = _extract_precise_price(card_text_full)
            print("fallback_price:", fallback_price)

if __name__ == "__main__":
    asyncio.run(main())
