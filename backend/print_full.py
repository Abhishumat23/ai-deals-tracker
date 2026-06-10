import sqlite3

conn = sqlite3.connect('/Users/abhishumat/Downloads/ai-deals-tracker/backend/data/deals.db')
cursor = conn.cursor()
cursor.execute("SELECT tool_name, raw_content FROM snapshots GROUP BY tool_name HAVING id = MAX(id);")
for row in cursor.fetchall():
    print(f"=== {row[0]} ===")
    print(row[1][:4000]) # First 4000 chars should have pricing
    print("\n")
