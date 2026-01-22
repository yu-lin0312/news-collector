import database
import sys

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def check_hackingai_sources():
    print("Checking HackingAI Source Names in Database...")
    
    conn = database.get_connection()
    c = conn.cursor()
    
    # Get recent HackingAI items (identified by having a discussion_url)
    c.execute("""
        SELECT id, title, source, discussion_url, created_at 
        FROM news 
        WHERE discussion_url IS NOT NULL AND discussion_url != ''
        ORDER BY created_at DESC
        LIMIT 20
    """)
    rows = c.fetchall()
    
    print(f"Found {len(rows)} recent HackingAI items.")
    print("-" * 60)
    print(f"{'ID':<5} | {'Source':<20} | {'Title':<30}")
    print("-" * 60)
    
    for row in rows:
        print(f"{row['id']:<5} | {row['source']:<20} | {row['title'][:30]}...")
        
    conn.close()

if __name__ == "__main__":
    check_hackingai_sources()
