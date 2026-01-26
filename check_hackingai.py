import database
from datetime import datetime, timedelta

def check_hackingai():
    print("Checking HackingAI data in database...")
    
    # Get all news and filter for HackingAI
    # Note: database.get_news returns a list of dictionaries
    # We'll fetch a reasonable amount, e.g., last 7 days if the DB supports it, 
    # or just get all and filter in python if get_news doesn't support source filtering directly.
    # Looking at crawler.py, it imports database. Let's see what database.py offers.
    # Assuming database.get_news(limit=...) or similar.
    
    try:
        # Try to get recent news
        news_items = database.get_all_news()
        
        hacking_ai_items = [n for n in news_items if 'hacking' in str(n['source']).lower()]
        
        print(f"Found {len(hacking_ai_items)} HackingAI items in the last {len(news_items)} news entries.")
        
        if hacking_ai_items:
            print("\nMost recent 5 items:")
            for item in hacking_ai_items[:5]:
                print(f"- [{item['published_at']}] {item['title']} ({item['source']})")
        else:
            print("No HackingAI items found recently.")
            
    except Exception as e:
        print(f"Error querying database: {e}")

if __name__ == "__main__":
    check_hackingai()
