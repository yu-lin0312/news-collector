import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

def check_news_date():
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    url = "https://blog.google/products-and-platforms/products/search/personal-intelligence-ai-mode-search/?utm_source=tldrai"
    
    try:
        docs = db.collection('news').where('url', '==', url).limit(1).stream()
        
        for doc in docs:
            data = doc.to_dict()
            print(f"published_at: {data.get('published_at')}")
            print(f"created_at: {data.get('created_at')}")
            print(f"source: {data.get('source')}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_news_date()
