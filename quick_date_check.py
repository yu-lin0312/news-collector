import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

def check_dates():
    if not firebase_admin._apps:
        cred = credentials.Certificate('serviceAccountKey.json')
        firebase_admin.initialize_app(cred)
    
    db = firestore.client()
    doc = db.collection('briefings').document('2026-01-26').get()
    
    if doc.exists:
        top10 = doc.to_dict().get('top10', [])
        for i, item in enumerate(top10, 1):
            date = item.get('published_at', 'N/A')
            # Extract just the date part
            if 'T' in str(date):
                date = str(date).split('T')[0]
            print(f"{i}. {date}")

if __name__ == "__main__":
    check_dates()
