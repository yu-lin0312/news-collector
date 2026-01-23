import sqlite3
from datetime import datetime

def check_today_news():
    conn = sqlite3.connect('news.db')
    conn.row_factory = sqlite3.Row
    today_str = '2026-01-23'
    rows = conn.execute('SELECT title, source, published_at FROM news WHERE published_at >= ?', (today_str,)).fetchall()
    
    print(f"Found {len(rows)} news for today")
    for r in rows:
        print(f"{r['published_at']} | {r['source']:<20} | {r['title']}")
    
    conn.close()

if __name__ == "__main__":
    check_today_news()
