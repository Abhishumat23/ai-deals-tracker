import sqlite3
import re

def get_context(text, word):
    idx = text.lower().find(word.lower())
    if idx != -1:
        return text[max(0, idx-50):idx+150]
    return "NOT FOUND"

conn = sqlite3.connect('/Users/abhishumat/Downloads/ai-deals-tracker/backend/data/deals.db')
cursor = conn.cursor()
cursor.execute("SELECT tool_name, raw_content FROM snapshots GROUP BY tool_name HAVING id = MAX(id);")
for row in cursor.fetchall():
    name = row[0]
    text = row[1]
    print(f"--- {name} ---")
    if name == 'OpenAI':
        print("Go:", get_context(text, " go "))
        print("Plus:", get_context(text, " plus "))
        print("Pro:", get_context(text, " pro "))
    if name == 'Perplexity':
        print("Pro:", get_context(text, " pro "))
    if name == 'Gemini':
        print("Google AI Plus 1:", get_context(text, "google ai plus 1"))

