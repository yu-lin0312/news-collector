import database_firestore as fs
from firebase_admin import firestore

def list_latest_news():
    db = fs.get_db()
    if not db:
        print("Failed to connect to Firestore.")
        return

    print("Fetching latest 20 news items from Firestore...")
    docs = db.collection('news').order_by('published_at', direction=firestore.Query.DESCENDING).limit(20).stream()
    
    print("\n" + "="*80)
    print(f"{'Date':<20} | {'Source':<20} | {'Title'}")
    print("-" * 80)
    
    for doc in docs:
        d = doc.to_dict()
        title = d.get('title', 'No Title')[:50]
        source = d.get('source', 'Unknown')[:20]
        date = d.get('published_at', 'Unknown')
        print(f"{str(date):<20} | {source:<20} | {title}")
    print("="*80 + "\n")

if __name__ == "__main__":
    list_latest_news()
