import database
from urllib.parse import urlparse
import sys

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def fix_hackingai_sources():
    print("Fixing HackingAI Source Names in Database...")
    
    conn = database.get_connection()
    c = conn.cursor()
    
    # Get all HackingAI items (identified by having a discussion_url)
    c.execute("SELECT id, title, url FROM news WHERE discussion_url IS NOT NULL AND discussion_url != ''")
    rows = c.fetchall()
    
    print(f"Found {len(rows)} items to check.")
    
    updated_count = 0
    
    for row in rows:
        news_id = row['id']
        title = row['title']
        source_url = row['url']
        
        if not source_url:
            continue
            
        try:
            # Extract domain from source_url
            domain = urlparse(source_url).netloc
            # Remove www.
            if domain.startswith('www.'):
                domain = domain[4:]
            
            real_source = domain
            
            if real_source:
                # Update the record
                c.execute("UPDATE news SET source = ? WHERE id = ?", (real_source, news_id))
                updated_count += 1
                print(f"Updated ID {news_id}: {title[:30]}... -> {real_source}")
                    
        except Exception as e:
            print(f"Error processing ID {news_id}: {e}")
            
    conn.commit()
    conn.close()
    
    print("-" * 30)
    print(f"Total Updated: {updated_count}")

if __name__ == "__main__":
    fix_hackingai_sources()
