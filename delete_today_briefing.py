import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

def delete_briefing():
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    
    date_str = '2026-01-26'
    print(f"正在刪除 {date_str} 的簡報...")
    
    try:
        # Delete the briefing document
        doc_ref = db.collection('briefings').document(date_str)
        doc_ref.delete()
        print(f"✅ 已成功刪除 {date_str} 的簡報")
        print("您現在可以重新生成了")
    except Exception as e:
        print(f"❌ 刪除失敗: {e}")

if __name__ == "__main__":
    delete_briefing()
