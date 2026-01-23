import database_firestore as fs
from firebase_admin import firestore
import re

def is_chinese(text):
    return re.search(r'[\u4e00-\u9fff]', text) is not None

def check_chinese_news():
    db = fs.get_db()
    if not db:
        print("Failed to connect to Firestore.")
        return

    print("Fetching latest 100 news items from Firestore...")
    docs = db.collection('news').order_by('published_at', direction=firestore.Query.DESCENDING).limit(100).stream()
    
    chinese_count = 0
    print("\n" + "="*80)
    print(f"{'Date':<20} | {'Source':<20} | {'Title'}")
    print("-" * 80)
    
    for doc in docs:
        d = doc.to_dict()
        title = d.get('title', 'No Title')
        if is_chinese(title):
            chinese_count += 1
            source = d.get('source', 'Unknown')[:20]
            date = d.get('published_at', 'Unknown')
            print(f"{str(date):<20} | {source:<20} | {title[:50]}")
            
    print("-" * 80)
    print(f"Total Chinese news found in latest 100: {chinese_count}")
    print("="*80 + "\n")

if __name__ == "__main__":
    check_chinese_news()
