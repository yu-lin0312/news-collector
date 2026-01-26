import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

def check_briefing_dates():
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    today_str = '2026-01-26'
    print(f"檢查簡報日期: {today_str}")
    print("=" * 80)
    
    doc_ref = db.collection('briefings').document(today_str)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        top10 = data.get('top10', [])
        print(f"找到 {len(top10)} 則新聞\n")
        
        for i, item in enumerate(top10, 1):
            title = item.get('title', 'No Title')
            published_at = item.get('published_at', 'N/A')
            source = item.get('source', 'Unknown')
            
            print(f"{i}. 日期: {published_at}")
            print(f"   來源: {source}")
            print(f"   標題: {title[:60]}...")
            print()
    else:
        print(f"找不到 {today_str} 的簡報")

if __name__ == "__main__":
    check_briefing_dates()
