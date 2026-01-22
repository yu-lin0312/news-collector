import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from datetime import datetime
import os
import json

# Initialize Firebase app
cred = None
db = None

def get_db():
    global db
    if db is None:
        try:
            # Check for local file first
            key_path = "serviceAccountKey.json"
            if os.path.exists(key_path):
                cred = credentials.Certificate(key_path)
            else:
                # Try to get from environment variable (useful for Cloud Run/Streamlit Cloud)
                service_account_json = os.environ.get('FIREBASE_CREDENTIALS') or os.environ.get('FIREBASE_SERVICE_ACCOUNT')
                if service_account_json:
                    try:
                        service_account_info = json.loads(service_account_json)
                        cred = credentials.Certificate(service_account_info)
                    except json.JSONDecodeError:
                        print("Error: FIREBASE_CREDENTIALS env var is not valid JSON.")
                        return None
                else:
                    print("Warning: No Firebase credentials found (serviceAccountKey.json or FIREBASE_CREDENTIALS env var).")
                    return None
            
            try:
                firebase_admin.get_app()
            except ValueError:
                firebase_admin.initialize_app(cred)
            
            db = firestore.client()
        except Exception as e:
            print(f"Error initializing Firestore: {e}")
            return None
    return db

def init_db():
    # Firestore doesn't need explicit table creation
    pass

def url_exists(url):
    db = get_db()
    if not db: return False
    
    try:
        # Query for document with this url
        docs = db.collection('news').where('url', '==', url).limit(1).stream()
        for _ in docs:
            return True
        return False
    except Exception as e:
        print(f"Error checking url in Firestore: {e}")
        return False

def add_news(title, url, source, category, published_at, summary, image_url, ai_rundown=None, ai_details=None, ai_impact=None, discussion_url=None):
    db = get_db()
    if not db: return False
    
    try:
        data = {
            'title': title,
            'url': url,
            'source': source,
            'category': category,
            'published_at': published_at,
            'summary': summary,
            'image_url': image_url,
            'created_at': datetime.now(),
            'ai_rundown': ai_rundown,
            'ai_details': ai_details,
            'ai_impact': ai_impact,
            'discussion_url': discussion_url
        }
        # Add a new document with auto-generated ID
        db.collection('news').add(data)
        return True
    except Exception as e:
        print(f"Error adding news to Firestore: {e}")
        return False

def update_ai_analysis(url, rundown, details, impact):
    db = get_db()
    if not db: return False
    
    try:
        # First find the document
        docs = db.collection('news').where('url', '==', url).limit(1).stream()
        doc_ref = None
        for doc in docs:
            doc_ref = doc.reference
            break
            
        if doc_ref:
            doc_ref.update({
                'ai_rundown': rundown,
                'ai_details': details,
                'ai_impact': impact
            })
            return True
        return False
    except Exception as e:
        print(f"Error updating AI analysis in Firestore: {e}")
        return False

def get_all_news():
    db = get_db()
    if not db: return []
    
    try:
        print("Firestore: Fetching all news (limit 100)...")
        # Order by published_at DESC
        docs = db.collection('news').order_by('published_at', direction=firestore.Query.DESCENDING).limit(100).stream()
        
        news_list = []
        for doc in docs:
            news_data = doc.to_dict()
            news_list.append(news_data)
            
        print(f"Firestore: Fetched {len(news_list)} items.")
        if len(news_list) > 0:
            print(f"Firestore: First item date: {news_list[0].get('published_at')}")
            
        return news_list
    except Exception as e:
        print(f"Error fetching news from Firestore: {e}")
        return []

def get_today_news_count():
    db = get_db()
    if not db: return 0
    
    try:
        today_str = datetime.now().strftime('%Y-%m-%d')
        # Firestore doesn't support "starts with" natively easily without range queries
        # We'll use a range query for the day
        start_of_day = f"{today_str} 00:00:00"
        end_of_day = f"{today_str} 23:59:59"
        
        # Note: This assumes published_at is stored as a string in the same format.
        # If it's a timestamp object, this needs adjustment.
        # Based on existing code, it seems to be a string.
        
        docs = db.collection('news')\
            .where('published_at', '>=', start_of_day)\
            .where('published_at', '<=', end_of_day)\
            .stream()
            
        count = sum(1 for _ in docs)
        return count
    except Exception as e:
        print(f"Error counting today's news in Firestore: {e}")
        return 0

def cleanup_old_news(days=30):
    db = get_db()
    if not db: return 0
    
    try:
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        print(f"Cleaning up news older than {cutoff_str}...")
        
        # Query for old documents
        docs = db.collection('news').where('published_at', '<', cutoff_str).stream()
        
        count = 0
        batch = db.batch()
        batch_size = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            batch_size += 1
            count += 1
            
            if batch_size >= 400:
                batch.commit()
                batch = db.batch()
                batch_size = 0
        
        if batch_size > 0:
            batch.commit()
            
        return count
    except Exception as e:
        print(f"Error cleaning up Firestore: {e}")
        return 0

# --- Briefing Storage (JSON Blob) ---

def save_briefing(date_str, data_dict):
    """Saves the full generated briefing JSON to Firestore."""
    db = get_db()
    if not db: return False
    
    try:
        # Use a separate collection for briefings
        # Document ID = date_str (e.g., "2026-01-22") to ensure uniqueness and easy lookup
        doc_ref = db.collection('briefings').document(date_str)
        doc_ref.set(data_dict)
        print(f"Briefing for {date_str} saved to Firestore.")
        return True
    except Exception as e:
        print(f"Error saving briefing to Firestore: {e}")
        return False

def get_briefing(date_str):
    """Retrieves the briefing JSON for a specific date."""
    db = get_db()
    if not db: return None
    
    try:
        doc_ref = db.collection('briefings').document(date_str)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    except Exception as e:
        print(f"Error retrieving briefing from Firestore: {e}")
        return None

def list_briefings():
    """Lists all available briefing dates (document IDs)."""
    db = get_db()
    if not db: return []
    
    try:
        # Get all document IDs from briefings collection
        docs = db.collection('briefings').stream()
        dates = [doc.id for doc in docs]
        # Sort descending
        dates.sort(reverse=True)
        return dates
    except Exception as e:
        print(f"Error listing briefings from Firestore: {e}")
        return []

