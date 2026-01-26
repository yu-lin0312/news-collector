import database
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import os

def check_db_sources():
    print("Checking all sources in database...")
    try:
        news_items = database.get_all_news()
        sources = set()
        for item in news_items:
            sources.add(item['source'])
            
        print(f"Found {len(news_items)} total items.")
        print("Unique sources found:")
        for s in sorted(sources):
            count = sum(1 for i in news_items if i['source'] == s)
            print(f"- {s}: {count} items")
            
    except Exception as e:
        print(f"Error checking sources: {e}")

from crawler import NewsCrawler

def debug_google_news():
    print("\n" + "="*50)
    print("Debugging Google News (AI) with REAL Crawler...")
    
    crawler = NewsCrawler()
    source = {
        "name": "Google News (AI)",
        "url": "https://news.google.com/rss/search?q=artificial+intelligence&hl=zh-TW&gl=TW&ceid=TW:zh-hant",
        "type": "static",
        "category": "全球 AI 趨勢",
        "selectors": {
          "container": "item",
          "title": "title",
          "link": "link",
          "link_attr": "TEXT",
          "date": "pubDate",
          "summary": "description",
          "image": ""
        }
    }
    
    try:
        crawler.crawl_source(source)
    except Exception as e:
        print(f"Crawler error: {e}")
    finally:
        crawler.close()

if __name__ == "__main__":
    # check_db_sources()
    debug_google_news()
