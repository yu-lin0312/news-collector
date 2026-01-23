import database_firestore as fs
import json
from datetime import datetime

def view_briefing():
    db = fs.get_db()
    if not db:
        print("Failed to connect to Firestore.")
        return

    date_str = "2026-01-23"
    print(f"Fetching briefing for {date_str} from Firestore...")
    
    doc_ref = db.collection('briefings').document(date_str)
    doc = doc_ref.get()
    
    if doc.exists:
        data = doc.to_dict()
        # Convert datetime objects to string for JSON serialization
        def default_converter(o):
            if isinstance(o, datetime):
                return o.isoformat()
            return str(o)
            
        output_str = json.dumps(data, indent=2, default=default_converter, ensure_ascii=False)
        print(output_str)
        with open('briefing_23_utf8.json', 'w', encoding='utf-8') as f:
            f.write(output_str)
    else:
        print(f"No briefing found for {date_str}")

if __name__ == "__main__":
    view_briefing()
