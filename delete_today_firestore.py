import os
os.environ['USE_FIRESTORE'] = 'True'

import database_firestore

def delete_today_news():
    """Delete all news from 2026-01-26 in Firestore"""
    print("Connecting to Firestore...")
    
    # Get database connection
    db = database_firestore.get_db()
    
    if not db:
        print("ERROR: Could not connect to Firestore")
        return
    
    target_date = "2026-01-26"
    print(f"Deleting all news from {target_date}...")
    
    try:
        # Query for all news on this date
        # Firestore query for date range
        start_of_day = f"{target_date}"
        end_of_day = f"{target_date}T23:59:59"
        
        # Get all documents for this date
        docs = db.collection('news')\
            .where('published_at', '>=', start_of_day)\
            .where('published_at', '<=', end_of_day)\
            .stream()
        
        # Delete in batches
        batch = db.batch()
        count = 0
        batch_size = 0
        
        for doc in docs:
            batch.delete(doc.reference)
            batch_size += 1
            count += 1
            
            # Commit every 400 items (Firestore limit is 500)
            if batch_size >= 400:
                print(f"Committing batch... ({count} items so far)")
                batch.commit()
                batch = db.batch()
                batch_size = 0
        
        # Commit remaining items
        if batch_size > 0:
            print(f"Committing final batch...")
            batch.commit()
        
        print(f"✅ Successfully deleted {count} news items from {target_date}")
        
        # Also delete today's briefing if it exists
        print(f"\nDeleting briefing for {target_date}...")
        briefing_ref = db.collection('briefings').document(target_date)
        briefing_ref.delete()
        print(f"✅ Briefing deleted")
        
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    confirm = input(f"⚠️  WARNING: This will delete ALL news from 2026-01-26 in Firestore.\nType 'YES' to confirm: ")
    if confirm == 'YES':
        delete_today_news()
    else:
        print("Cancelled.")
