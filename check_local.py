import sqlite3
import glob
import os

print("--- Local SQLite Check ---")
if os.path.exists('news.db'):
    conn = sqlite3.connect('news.db')
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM news WHERE published_at LIKE "2026-01-24%"')
    count = c.fetchone()[0]
    print(f"News items for 2026-01-24: {count}")
    conn.close()
else:
    print("news.db not found")

print("\n--- Local Briefing Files ---")
files = glob.glob("top10_*.json")
for f in sorted(files, reverse=True):
    print(f"- {f}")
