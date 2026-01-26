import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

def check_specific_news():
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    url = "https://blog.google/products-and-platforms/products/search/personal-intelligence-ai-mode-search/?utm_source=tldrai"
    
    print(f"查詢 URL: {url}")
    print("=" * 80)
    
    try:
        docs = db.collection('news').where('url', '==', url).limit(1).stream()
        
        found = False
        for doc in docs:
            found = True
            data = doc.to_dict()
            print(f"標題: {data.get('title')}")
            print(f"來源: {data.get('source')}")
            print(f"分類: {data.get('category')}")
            print(f"發布日期 (published_at): {data.get('published_at')}")
            print(f"建立時間 (created_at): {data.get('created_at')}")
            print(f"摘要: {data.get('summary', 'N/A')[:100]}...")
            
        if not found:
            print("❌ 在 Firestore 中找不到這則新聞")
            
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")

if __name__ == "__main__":
    check_specific_news()
