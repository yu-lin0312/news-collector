import database
import sys
import io

# Force UTF-8 removed

def check_db():
    print("Checking Database Records...")
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT title, url, discussion_url FROM news WHERE source='HackingAI' ORDER BY created_at DESC LIMIT 5")
    rows = c.fetchall()
    
    if not rows:
        print("No HackingAI items found in DB.")
    else:
        print(f"Found {len(rows)} items:")
        for row in rows:
            print(f"Title: {row['title']}")
            print(f"URL: {row['url']}")
            print(f"Reddit: {row['discussion_url']}")
            print("-" * 20)
            
    conn.close()

if __name__ == "__main__":
    check_db()
