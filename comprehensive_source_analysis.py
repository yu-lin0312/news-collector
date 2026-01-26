import database
import json
from collections import Counter
import sys

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def get_all_stats():
    conn = database.get_connection()
    c = conn.cursor()
    
    # 1. Get all news items
    c.execute("SELECT source, discussion_url, url FROM news")
    rows = c.fetchall()
    
    # Load configured sources for comparison
    try:
        with open('sources.json', 'r', encoding='utf-8') as f:
            config_sources = json.load(f)
            config_names = {s['name'] for s in config_sources}
    except:
        config_names = set()

    stats = Counter()
    hacking_ai_sources = Counter()
    google_news_sources = Counter()
    direct_sources = Counter()
    
    for row in rows:
        source = row['source']
        disc_url = row['discussion_url']
        url = row['url']
        
        stats[source] += 1
        
        # Logic to identify HackingAI (usually has a discussion_url from reddit)
        if disc_url and 'reddit.com' in disc_url:
            hacking_ai_sources[source] += 1
        # Logic to identify Google News (if not in config_names and not hacking ai)
        # Actually, Google News items are often renamed to the publisher.
        # We can check if the source is one of the "Direct" ones in our config.
        elif source in config_names:
            direct_sources[source] += 1
        else:
            # If it's not a direct config source and not HackingAI, it's likely from Google News
            google_news_sources[source] += 1

    print(f"=== 總體統計 ===")
    print(f"資料庫總新聞數: {len(rows)}")
    print(f"不重複來源總數: {len(stats)}")
    print("\n=== 來源分類統計 ===")
    print(f"1. 直接抓取的來源 (Configured): {sum(direct_sources.values())} 則")
    print(f"2. 透過 HackingAI 發現的來源: {sum(hacking_ai_sources.values())} 則")
    print(f"3. 透過 Google News 發現的來源: {sum(google_news_sources.values())} 則")
    
    print("\n=== HackingAI 帶來的原始媒體 (前 10 名) ===")
    for s, count in hacking_ai_sources.most_common(10):
        print(f"  - {s}: {count}")
        
    print("\n=== Google News 帶來的原始媒體 (前 10 名) ===")
    for s, count in google_news_sources.most_common(10):
        print(f"  - {s}: {count}")

    print("\n=== 直接抓取的媒體 (前 10 名) ===")
    for s, count in direct_sources.most_common(10):
        print(f"  - {s}: {count}")

    conn.close()

if __name__ == "__main__":
    get_all_stats()
