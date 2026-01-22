import database
from bs4 import BeautifulSoup
import sys

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def fix_google_sources():
    print("Fixing Google News Source Names in Database...")
    
    conn = database.get_connection()
    c = conn.cursor()
    
    # Get all Google News items
    c.execute("SELECT id, title, summary FROM news WHERE source = 'Google News (AI)'")
    rows = c.fetchall()
    
    print(f"Found {len(rows)} items to check.")
    
    updated_count = 0
    
    for row in rows:
        news_id = row['id']
        title = row['title']
        summary = row['summary']
        
        if not summary:
            continue
            
        try:
            # Parse the summary HTML to find the source
            # Format: <a ...>Title</a>&nbsp;&nbsp;<font color="#6f6f6f">Source Name</font>
            soup = BeautifulSoup(summary, 'html.parser')
            font_elem = soup.find('font', color='#6f6f6f')
            
            if font_elem:
                real_source = font_elem.get_text(strip=True)
                
                if real_source and real_source != "Google News (AI)":
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
    fix_google_sources()
