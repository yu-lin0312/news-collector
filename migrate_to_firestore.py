"""
Migration script to upload local SQLite news data to Firestore.
Run this locally to populate Firestore with your existing data.
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta

# Force SQLite mode for reading local data
os.environ['USE_FIRESTORE'] = 'False'

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Now import database_firestore directly to write to Firestore
import database_firestore as firestore_db

def migrate_news():
    """Migrate news from local SQLite to Firestore."""
    # Read from local SQLite
    conn = sqlite3.connect('news.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get recent news (last 3 days)
    today = datetime.now()
    three_days_ago = (today - timedelta(days=3)).strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT * FROM news 
        WHERE published_at >= ?
        ORDER BY published_at DESC
    ''', (three_days_ago,))
    
    rows = cursor.fetchall()
    conn.close()
    
    print(f"Found {len(rows)} news items from the last 3 days")
    
    # Write to Firestore
    success_count = 0
    skip_count = 0
    
    for row in rows:
        # Check if already exists in Firestore
        if firestore_db.url_exists(row['url']):
            print(f"Skipping (already exists): {row['title'][:50]}...")
            skip_count += 1
            continue
        
        # Add to Firestore
        result = firestore_db.add_news(
            title=row['title'],
            url=row['url'],
            source=row['source'],
            category=row['category'],
            published_at=row['published_at'],
            summary=row['summary'],
            image_url=row['image_url'],
            ai_rundown=row['ai_rundown'] if 'ai_rundown' in row.keys() else None,
            ai_details=row['ai_details'] if 'ai_details' in row.keys() else None,
            ai_impact=row['ai_impact'] if 'ai_impact' in row.keys() else None,
            discussion_url=row['discussion_url'] if 'discussion_url' in row.keys() else None
        )
        
        if result:
            print(f"Migrated: {row['title'][:50]}...")
            success_count += 1
        else:
            print(f"Failed to migrate: {row['title'][:50]}...")
    
    print(f"\nMigration complete!")
    print(f"Migrated: {success_count}")
    print(f"Skipped: {skip_count}")
    print(f"Total: {len(rows)}")

if __name__ == "__main__":
    migrate_news()
