import database
import sys

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def check_google_urls():
    print("Checking URLs of items that were likely Google News...")
    
    conn = database.get_connection()
    c = conn.cursor()
    
    # Check items that have 'news.google.com' in URL
    c.execute("SELECT count(*), source FROM news WHERE url LIKE '%news.google.com%' GROUP BY source LIMIT 20")
    rows = c.fetchall()
    
    print("Counts by source for items with 'news.google.com' in URL:")
    for row in rows:
        print(f"Count: {row[0]}, Source: {row[1]}")
        
    conn.close()

if __name__ == "__main__":
    check_google_urls()
