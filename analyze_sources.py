import database
from datetime import datetime, timedelta
import sys

# Force UTF-8 for Windows console
sys.stdout.reconfigure(encoding='utf-8')

def analyze_distribution():
    print("Analyzing News Distribution for Today...")
    
    # Get news from last 24 hours
    today = datetime.now()
    limit_date = today - timedelta(days=1)
    
    conn = database.get_connection()
    c = conn.cursor()
    
    # Count by source
    c.execute("""
        SELECT source, COUNT(*) as count 
        FROM news 
        WHERE created_at >= ? 
        GROUP BY source 
        ORDER BY count DESC
    """, (limit_date.strftime('%Y-%m-%d %H:%M:%S'),))
    
    rows = c.fetchall()
    
    print(f"\nTotal Sources Found: {len(rows)}")
    print("-" * 30)
    print(f"{'Source':<30} | {'Count':<5}")
    print("-" * 30)
    
    google_count = 0
    hacking_count = 0
    
    for row in rows:
        source = row['source']
        count = row['count']
        print(f"{source[:30]:<30} | {count:<5}")
        
        if 'Google News' in source:
            google_count += count
            
    # Check HackingAI specifically by discussion_url
    c.execute("""
        SELECT COUNT(*) 
        FROM news 
        WHERE created_at >= ? AND discussion_url IS NOT NULL AND discussion_url != ''
    """, (limit_date.strftime('%Y-%m-%d %H:%M:%S'),))
    
    hacking_count = c.fetchone()[0]
    
    print("-" * 30)
    print(f"Google News Total: {google_count}")
    print(f"HackingAI (via discussion_url): {hacking_count}")
    
    conn.close()

if __name__ == "__main__":
    analyze_distribution()
