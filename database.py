import sqlite3
import os
import json
from datetime import datetime

# Check environment variable to decide which DB to use
# Default to SQLite if not set
USE_FIRESTORE = os.environ.get('USE_FIRESTORE', 'False').lower() == 'true'

if USE_FIRESTORE:
    try:
        import database_firestore as backend
        print("Using Firestore database")
    except ImportError:
        print("Error importing database_firestore, falling back to SQLite")
        USE_FIRESTORE = False

if not USE_FIRESTORE:
    print("Using SQLite database")
    DB_NAME = "news.db"

    def get_connection():
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db():
        conn = get_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                source TEXT,
                category TEXT,
                published_at DATETIME,
                summary TEXT,
                image_url TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Check if category column exists, if not add it (migration)
        c.execute("PRAGMA table_info(news)")
        columns = [info[1] for info in c.fetchall()]
        
        if 'category' not in columns:
            print("Migrating database: adding category column")
            c.execute("ALTER TABLE news ADD COLUMN category TEXT")

        # AI Analysis columns migration
        if 'ai_rundown' not in columns:
            print("Migrating database: adding ai_rundown column")
            c.execute("ALTER TABLE news ADD COLUMN ai_rundown TEXT")
            
        if 'ai_details' not in columns:
            print("Migrating database: adding ai_details column")
            c.execute("ALTER TABLE news ADD COLUMN ai_details TEXT")
            
        if 'ai_impact' not in columns:
            print("Migrating database: adding ai_impact column")
            c.execute("ALTER TABLE news ADD COLUMN ai_impact TEXT")

        if 'ai_bullets' not in columns:
            print("Migrating database: adding ai_bullets column")
            c.execute("ALTER TABLE news ADD COLUMN ai_bullets TEXT")

        if 'discussion_url' not in columns:
            print("Migrating database: adding discussion_url column")
            c.execute("ALTER TABLE news ADD COLUMN discussion_url TEXT")
            
        conn.commit()
        conn.close()

    def url_exists(url):
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT 1 FROM news WHERE url = ?', (url,))
        exists = c.fetchone() is not None
        conn.close()
        return exists

    def add_news(title, url, source, category, published_at, summary, image_url, ai_rundown=None, ai_details=None, ai_impact=None, discussion_url=None):
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO news (title, url, source, category, published_at, summary, image_url, ai_rundown, ai_details, ai_impact, discussion_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (title, url, source, category, published_at, summary, image_url, ai_rundown, ai_details, ai_impact, discussion_url))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def cleanup_old_news(days=30):
        conn = get_connection()
        c = conn.cursor()
        try:
            from datetime import datetime, timedelta
            cutoff_date = datetime.now() - timedelta(days=days)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            
            c.execute('DELETE FROM news WHERE published_at < ?', (cutoff_str,))
            deleted_count = c.rowcount
            conn.commit()
            return deleted_count
        except Exception as e:
            print(f"Error cleaning up old news: {e}")
            return 0
        finally:
            conn.close()

    def get_all_news():
        # Initialize DB if it doesn't exist
        if not os.path.exists(DB_NAME):
            init_db()
            
        conn = get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM news ORDER BY published_at DESC, created_at DESC')
        rows = c.fetchall()
        conn.close()
        return rows

    def get_today_news_count():
        """Count news items published today"""
        conn = get_connection()
        c = conn.cursor()
        today_str = datetime.now().strftime('%Y-%m-%d')
        # Check for both full datetime and date string
        c.execute("SELECT COUNT(*) FROM news WHERE published_at LIKE ? OR published_at = ?", (f"{today_str}%", today_str))
        count = c.fetchone()[0]
        conn.close()
        return count

    def update_ai_analysis(url, rundown, details, impact):
        conn = get_connection()
        c = conn.cursor()
        try:
            c.execute('''
                UPDATE news 
                SET ai_rundown = ?, ai_details = ?, ai_impact = ?
                WHERE url = ?
            ''', (rundown, details, impact, url))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating AI analysis: {e}")
            return False
        finally:
            conn.close()
            
    # --- Briefing Storage (Local JSON File Fallback) ---
    def save_briefing(date_str, data_dict):
        filename = f"top10_{date_str}.json"
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2)
            print(f"Briefing saved to local file: {filename}")
            return True
        except Exception as e:
            print(f"Error saving local briefing: {e}")
            return False

    def get_briefing(date_str):
        filename = f"top10_{date_str}.json"
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error reading local briefing: {e}")
                return None
        return None

else:
    # Proxy calls to the firestore backend
    def init_db():
        return backend.init_db()

    def url_exists(url):
        return backend.url_exists(url)

    def add_news(title, url, source, category, published_at, summary, image_url, ai_rundown=None, ai_details=None, ai_impact=None, discussion_url=None):
        return backend.add_news(title, url, source, category, published_at, summary, image_url, ai_rundown, ai_details, ai_impact, discussion_url)

    def cleanup_old_news(days=30):
        return backend.cleanup_old_news(days)

    def get_all_news():
        return backend.get_all_news()
        
    def get_today_news_count():
        return backend.get_today_news_count()
        
    def update_ai_analysis(url, rundown, details, impact):
        return backend.update_ai_analysis(url, rundown, details, impact)
        
    def save_briefing(date_str, data_dict):
        return backend.save_briefing(date_str, data_dict)
        
    def get_briefing(date_str):
        return backend.get_briefing(date_str)

    def list_briefings():
        return backend.list_briefings()
