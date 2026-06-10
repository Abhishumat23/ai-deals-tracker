import sqlite3
from bs4 import BeautifulSoup
import re

conn = sqlite3.connect('data/deals.db')
c = conn.cursor()
c.execute("SELECT raw_content FROM snapshots WHERE tool_name = 'Claude' ORDER BY id DESC LIMIT 1")
html = c.fetchone()[0]

soup = BeautifulSoup(html, "html.parser")
for t in ["Free", "Pro", "Max", "Team"]:
    nodes = soup.find_all(string=re.compile(r'\b' + t + r'\b', re.IGNORECASE))
    print(f"\n--- {t} ---")
    for n in nodes[:3]:
        parent = n.parent
        if parent:
            print(f"Parent: <{parent.name} class='{parent.get('class', '')}'> {n.strip()} </{parent.name}>")
            if parent.parent:
                print(f"Grandparent class: {parent.parent.get('class', '')}")

