import database
from crawler import NewsCrawler
import json
import os
import sys
import io

# Force UTF-8
# Force UTF-8 removed

def verify():
    print("1. Initializing Database (Migration Check)...")
    database.init_db()
    print("Database initialized.")
    
    print("\n2. Testing HackingAI Crawler...")
    crawler = NewsCrawler()
    
    # Find HackingAI source
    hackingai_source = None
    for src in crawler.sources:
        if src['name'] == 'HackingAI':
            hackingai_source = src
            break
            
    if not hackingai_source:
        print("Error: HackingAI source not found in sources.json")
        return

    # Run crawler for this source
    crawler.crawl_hackingai(hackingai_source)
    crawler.close()
    
    print("\n3. Verifying Database Records...")
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT title, url, discussion_url FROM news WHERE source='HackingAI' ORDER BY created_at DESC LIMIT 5")
    rows = c.fetchall()
    
    if not rows:
        print("No HackingAI items found in DB.")
    else:
        for row in rows:
            print(f"Title: {row['title']}")
            print(f"URL: {row['url']}")
            print(f"Reddit: {row['discussion_url']}")
            print("-" * 20)
            
    conn.close()

if __name__ == "__main__":
    verify()
