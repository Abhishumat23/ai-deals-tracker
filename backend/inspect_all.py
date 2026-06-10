import sqlite3
import re
from bs4 import BeautifulSoup

conn = sqlite3.connect('data/deals.db')
c = conn.cursor()

def dump_tools(tool_name):
    c.execute("SELECT raw_content FROM snapshots WHERE tool_name = ? ORDER BY id DESC LIMIT 1", (tool_name,))
    row = c.fetchone()
    if not row:
        print(f"No data for {tool_name}")
        return
    html = row[0]
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "button", "a"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    
    prices = re.findall(r"(?:\$|₹)\s*[\d,]+(?:\.\d+)?", text)
    print(f"\n================ {tool_name} ================")
    print(f"Prices found: {list(set(prices))}")
    print(text[:3000])

for t in ["OpenAI", "Gemini", "Cursor", "Perplexity"]:
    dump_tools(t)
