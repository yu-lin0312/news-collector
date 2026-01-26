import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime

def check_today_count():
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    today_str = '2026-01-26'
    print(f"檢查 {today_str} 的新聞數量...")
    
    # Query for today's news
    start_of_day = f"{today_str} 00:00:00"
    end_of_day = f"{today_str} 23:59:59"
    
    try:
        docs = db.collection('news')\
            .where('published_at', '>=', start_of_day)\
            .where('published_at', '<=', end_of_day)\
            .stream()
        
        count = sum(1 for _ in docs)
        print(f"✅ 找到 {count} 則今天的新聞")
        
        # Also check with ISO format
        docs2 = db.collection('news').where('published_at', '>=', today_str).where('published_at', '<', '2026-01-27').stream()
        count2 = sum(1 for _ in docs2)
        print(f"✅ (ISO 格式查詢) 找到 {count2} 則今天的新聞")
        
    except Exception as e:
        print(f"❌ 查詢失敗: {e}")

if __name__ == "__main__":
    check_today_count()
