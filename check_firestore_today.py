import os
# Force Firestore usage
os.environ['USE_FIRESTORE'] = 'True'
import database
from datetime import datetime

def check_cloud_news():
    print("Checking Firestore news for 2026-01-26...")
    try:
        # get_all_news in database.py proxies to database_firestore.get_all_news()
        # which fetches the latest 100 items ordered by published_at DESC
        news_items = database.get_all_news()
        
        if not news_items:
            print("No news items found in Firestore.")
            return

        today_str = "2026-01-26"
        today_items = [n for n in news_items if str(n.get('published_at', '')).startswith(today_str)]
        
        print(f"Found {len(today_items)} items published on {today_str} (out of latest 100).")
        
        hacking_ai_today = [n for n in today_items if 'hacking' in str(n.get('source', '')).lower()]
        print(f"HackingAI items on {today_str}: {len(hacking_ai_today)}")
        
        if today_items:
            print("\nTop 10 items for today (1/26):")
            for i, item in enumerate(today_items[:10]):
                print(f"{i+1}. [{item.get('source')}] {item.get('title')} ({item.get('published_at')})")
        
        if hacking_ai_today:
            print("\nHackingAI items for today (1/26):")
            for i, item in enumerate(hacking_ai_today):
                print(f"- {item.get('title')} ({item.get('published_at')})")
        else:
            # Check if there are ANY HackingAI items in the latest 100
            hacking_ai_any = [n for n in news_items if 'hacking' in str(n.get('source', '')).lower()]
            if hacking_ai_any:
                print("\nRecent HackingAI items (not necessarily today):")
                for item in hacking_ai_any[:5]:
                    print(f"- {item.get('title')} ({item.get('published_at')})")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_cloud_news()
