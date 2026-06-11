import asyncio
from bs4 import BeautifulSoup
import sys
sys.path.append('.')
from scrapers.claude_scraper import URL, EXPECTED_TIERS, ANCHORS
from utils import fetch_html_with_retry

async def main():
    html = await fetch_html_with_retry(URL, "Claude")
    soup = BeautifulSoup(html, "html.parser")
    
    import copy
    import re
    from utils import extract_pricing_plans
    
    soup_copy = copy.copy(soup)
    for tag in soup_copy(["script", "style", "nav", "footer", "noscript"]):
        tag.decompose()
        
    tier_nodes = {}
    for tier_name in EXPECTED_TIERS:
        elements = []
        anchor_text = ANCHORS.get(tier_name)
        if anchor_text:
            elements = soup_copy.find_all(string=re.compile(re.escape(anchor_text), re.IGNORECASE))
            elements = [el.parent for el in elements if el.parent]
        if not elements:
            elements = soup_copy.find_all(lambda t: t.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'span']
                                     and t.string and tier_name.lower() == t.string.strip().lower())
        if elements:
            target_node = min(elements, key=lambda tag: len(tag.get_text(strip=True)))
            tier_nodes[tier_name] = target_node

    all_heading_nodes = list(tier_nodes.values())
    
    def is_ancestor(ancestor, node):
        curr = node.parent
        while curr:
            if curr == ancestor:
                return True
            curr = curr.parent
        return False

    for tier_name in EXPECTED_TIERS:
        target_node = tier_nodes.get(tier_name)
        if not target_node:
            continue
        card = target_node
        for _ in range(8):
            parent = card.parent
            if not parent or parent.name in ['body', 'html', 'main', 'section']:
                break
            if any(other != target_node and is_ancestor(parent, other) for other in all_heading_nodes):
                break
            card = parent
            
        print(f"\n--- {tier_name} Card Text ---")
        print(repr(card.get_text(separator=" ", strip=True)))

if __name__ == "__main__":
    asyncio.run(main())
