import os
import json
import database
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime, timedelta
import time
import random
from playwright.sync_api import sync_playwright
import urllib3
from dotenv import load_dotenv
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# Timezone helper
TAIPEI_TZ = ZoneInfo("Asia/Taipei")

def get_taiwan_now():
    """Get current time in Taiwan timezone."""
    return datetime.now(TAIPEI_TZ)

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- Patch for Streamlit/Windows I/O Error ---
import builtins
def safe_print(*args, **kwargs):
    try:
        builtins.print(*args, **kwargs)
    except ValueError:
        pass # Ignore "I/O operation on closed file"
    except OSError:
        pass

print = safe_print
# ---------------------------------------------

def log_debug(msg):
    with open("debug_log.txt", "a", encoding="utf-8") as f:
        f.write(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")

# Configuration
CACHE_FILE = 'top10_cache.json'

def get_api_key():
    """Dynamically load API Key from env or .env file"""
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key and os.path.exists('.env'):
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('GOOGLE_API_KEY='):
                        api_key = line.strip().split('=')[1]
                        break
        except:
            pass
    return api_key

# Browser headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


class PlaywrightManager:
    """Singleton manager for shared Playwright browser instance."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._playwright = None
            cls._instance._browser = None
            cls._instance._context = None
        return cls._instance
    
    def _ensure_browser(self):
        """Lazily initialize shared Playwright browser and context."""
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._context = self._browser.new_context(
                user_agent=HEADERS['User-Agent'],
                ignore_https_errors=True
            )
        return self._context
    
    def get_page(self):
        """Get a new page from shared context."""
        context = self._ensure_browser()
        return context.new_page()
    
    def close(self):
        """Cleanup Playwright resources."""
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None


# Global Playwright manager instance
_playwright_manager = None

def get_playwright_manager():
    """Get or create the global Playwright manager."""
    global _playwright_manager
    if _playwright_manager is None:
        _playwright_manager = PlaywrightManager()
    return _playwright_manager

def cleanup_playwright():
    """Cleanup global Playwright resources."""
    global _playwright_manager
    if _playwright_manager:
        _playwright_manager.close()
        _playwright_manager = None


def fetch_article_content(url, source, discussion_url=None):
    """
    Fetches the full content of an article and its OG image.
    Returns: (text_content, status_message, image_url)
    """
    print(f"Fetching content for: {url}")
    log_debug(f"Fetching content for: {url} (Source: {source})")
    image_url = None

    # --- Reddit First Strategy for HackingAI ---
    if discussion_url and 'hackingai' in source.lower():
        log_debug(f"HackingAI item detected. Trying Reddit first: {discussion_url}")
        try:
            from crawler import NewsCrawler
            crawler = NewsCrawler()
            # Use specific selector for Reddit post content
            html = crawler.fetch_with_browser(discussion_url, wait_selector='shreddit-post')
            crawler.close()
            
            if html:
                soup = BeautifulSoup(html, 'html.parser')
                # Try to find the main post content
                # Reddit's structure varies, but often in shreddit-post or div with specific classes
                content_div = soup.select_one('shreddit-post')
                if content_div:
                     # Extract text from the post content
                     text = content_div.get_text(strip=True)
                     if len(text) > 100:
                         log_debug(f"Successfully fetched Reddit content ({len(text)} chars)")
                         return f"[Reddit Discussion Content]\n{text}", "Success (Reddit)", None
                
                # Fallback to general text extraction if specific selector fails
                text = soup.get_text(strip=True)
                if len(text) > 500:
                     return f"[Reddit Page Content]\n{text[:5000]}", "Success (Reddit General)", None
                     
            log_debug("Reddit fetch failed or content too short. Falling back to original URL.")
        except Exception as e:
            log_debug(f"Error fetching Reddit content: {e}")

    try:
        # 1. Try requests first (faster)
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove clutter
            for tag in soup(["script", "style", "nav", "footer", "header", "aside", "iframe", "noscript"]):
                tag.decompose()
                
            # Try to find main article content
            article = soup.find('article')
            if not article:
                # Fallback to common content classes
                for cls in ['content', 'post-content', 'entry-content', 'article-body', 'story-body']:
                    article = soup.find(class_=cls)
                    if article: break
            
            if not article:
                article = soup # Fallback to body
                
            text = article.get_text(separator='\n', strip=True)
            
            # Try to find OG image
            if not image_url:
                og_image = soup.find('meta', property='og:image')
                if og_image:
                    image_url = og_image.get('content')
                else:
                    twitter_image = soup.find('meta', name='twitter:image')
                    if twitter_image:
                        image_url = twitter_image.get('content')

            if len(text) > 500:
                return text, "Success (Requests)", image_url
                
        # 2. Fallback to Playwright (for dynamic content)
        print("Requests failed or content too short, trying Playwright...")
        manager = get_playwright_manager()
        page = manager.get_page()
        try:
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
            
            # Wait a bit for JS to load
            try:
                page.wait_for_selector('article, .content, p', timeout=5000)
            except TimeoutError:
                pass
                
            content = page.content()
        finally:
            page.close()
            
        soup = BeautifulSoup(content, 'html.parser')
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
            
        text = soup.get_text(separator='\n', strip=True)
        
        # Try to find OG image in Playwright content
        if not image_url:
            og_image = soup.find('meta', property='og:image')
            if og_image:
                image_url = og_image.get('content')
        
        if len(text) > 500:
            return text, "Success (Playwright)", image_url
        else:
            return None, "Content too short even with Playwright", image_url
                
    except Exception as e:
        return None, f"Error: {str(e)}", None

def analyze_article_with_gemini(title, content, source):
    """
    Uses Gemini to generate UX writing for a single article.
    """
    api_key = get_api_key()
    if not api_key:
        error_msg = "CRITICAL: No API Key found. Cannot proceed with AI analysis."
        print(error_msg)
        raise ValueError(error_msg)
        # return None

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')

    prompt = f"""
    你是一位專業的科技新聞編輯，擅長 UX Writing。請閱讀以下新聞內容，並為「每日 AI 簡報」撰寫分析文案。
    
    【新聞資訊】
    標題：{title}
    來源：{source}
    內容摘要：
    {content[:3000]}... (下略)

    【撰寫要求】
    請生成以下欄位的內容（繁體中文）：
    
    1. **ai_rundown (重點摘要)**：
       - 類似 The Rundown AI 的風格。
       - 用一句話破題，接著用 2-3 句話清楚說明發生了什麼事。
       - 語氣專業、簡潔、有力。
       - 字數控制在 50 字以內。

    【輸出格式】
    請直接回覆 JSON 格式，不要有 markdown 標記：
    {{
        "ai_rundown": "..."
    }}
    """
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            text = response.text
            
            # Clean up json
            try:
                # Find the first { and last }
                start_idx = text.find('{')
                end_idx = text.rfind('}')
                
                if start_idx != -1 and end_idx != -1:
                    text = text[start_idx:end_idx+1]
            except:
                pass
            
            try:
                return json.loads(text)
            except json.JSONDecodeError as je:
                print(f"JSON Decode Error: {je}")
                log_debug(f"JSON Decode Error for {title}: {je}")
                log_debug(f"Raw Text: {text}")
                print(f"Raw Text was: {text[:500]}...") # Log first 500 chars
                # Continue to retry loop
                
        except Exception as e:
            print(f"Gemini analysis failed (Attempt {attempt+1}): {e}")
            log_debug(f"Gemini analysis failed (Attempt {attempt+1}): {e}")
            if "429" in str(e) or "ResourceExhausted" in str(e):
                wait_time = (attempt + 1) * 20 # Increase wait time
                print(f"Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                # If it's not a rate limit, maybe just wait a bit and retry once
                time.sleep(5)
                
    return None

def generate_daily_summary(top10_list):
    """
    Generates a high-level summary for the entire briefing card.
    """
    api_key = get_api_key()
    if not api_key or not top10_list:
        return None
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    # Prepare input
    news_text = ""
    for i, item in enumerate(top10_list):
        news_text += f"{i+1}. {item['title']} (Category: {item.get('top10_category')})\n"
        
    prompt = f"""
    你是一位 AI 新聞主編。請根據以下今日 Top 5 新聞列表，為首頁的「每日簡報卡片」撰寫文案。
    
    【今日新聞列表】
    {news_text}
    
    【撰寫要求】
    請生成 JSON 格式，包含以下兩個欄位 (繁體中文)：
    
    1. **title_summary (標題總結)**：
       - 綜合今日最重要的 1-2 個大事件，寫成一個吸睛的標題。
       - 例如：「歐盟祭出 AI 新禁令，台積電 2nm 傳新進展」
       - 字數限制：25 字以內。
       
    2. **key_takeaways (重點速覽)**：
       - 用一句話概括今日重點，提到 2-3 個關鍵字或公司。
       - 例如：「涵蓋 Grok 監管爭議、MIT 2026 十大技術預測及 AI 醫療新應用。」
       - 字數限制：40 字以內。
       
    【輸出格式】
    {{
        "title_summary": "...",
        "key_takeaways": "..."
    }}
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        return json.loads(text)
    except Exception as e:
        print(f"Daily summary generation failed: {e}")
        return None

def select_top_stories_with_ai(candidates):
    """
    Uses Gemini to select the top 10 most impactful stories from a larger pool.
    """
    api_key = get_api_key()
    if not api_key or not candidates:
        return candidates[:10] # Fallback
        
    print(f"🤖 AI Editor is selecting top stories from {len(candidates)} candidates...")
    
    genai.configure(api_key=api_key)
    # Use 3 Flash for selection to save quota
    model = genai.GenerativeModel('gemini-3-flash-preview')
    
    # Prepare candidate list for AI
    candidates_text = ""
    for i, item in enumerate(candidates):
        candidates_text += f"ID: {i}\n標題: {item['title']}\n來源: {item['source']}\n摘要: {item.get('summary', '')[:100]}...\n\n"
        
    prompt = f"""
    你是一位擁有 20 年經驗的科技新聞總編輯。請從以下 {len(candidates)} 則新聞候選名單中，挑選出 **今天最具影響力、最值得讀者關注的 20 則新聞**。

    【候選新聞列表】
    {candidates_text}

    【挑選標準】
    1. **影響力 (Impact)**：優先選擇對產業有重大影響、顛覆性技術或大公司的重要動態。
    2. **分類平衡 (Category Balance)**：請檢視候選名單中的不同分類 (Category)，每個分類若有高品質新聞，應至少入選 1 則。我們希望讀者能看到多元的觀點。
    3. **多樣性 (Diversity)**：避免單一公司 (如 OpenAI) 或單一主題洗版，確保涵蓋模型、硬體、應用、政策等多個面向。
    4. **時效性 (Timeliness)**：優先選擇最新的重大突破。
    5. **排除雜訊**：剔除過於冷門的技術細節、純粹的股價波動或重複的報導。

    【輸出格式】
    請直接回覆一個 JSON 陣列，只包含被選中新聞的 "ID" (整數)，按重要性排序 (第 1 名最重要)：
    [ID1, ID2, ID3, ..., ID20]
    
    例如：[5, 12, 0, 8, 1, 3, 7, 9, 2, 4, ...]
    """
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
            
        selected_ids = json.loads(text)
        
        # Filter and reorder candidates based on AI selection
        selected_candidates = []
        for idx in selected_ids:
            if 0 <= idx < len(candidates):
                selected_candidates.append(candidates[idx])
                
        print(f"🤖 AI Editor selected {len(selected_candidates)} stories.")
        return selected_candidates
        
    except Exception as e:
        print(f"AI Selection failed: {e}")
        return candidates[:20] # Fallback

def generate_deep_top10(target_date=None):
    if target_date is None:
        target_date = get_taiwan_now()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d').replace(tzinfo=TAIPEI_TZ)

    print(f"Starting Deep Analysis for {target_date.strftime('%Y-%m-%d')}...")
    
    # 1. Get Candidates (Top 30 from Rule-Based)
    import rule_based_top10
    
    database.init_db()
    all_news = rule_based_top10.get_recent_news() # This gets last 7 days
    
    # Filter for target date window
    limit_date = target_date - timedelta(days=1)
    limit_date = limit_date.replace(hour=0, minute=0, second=0)
    
    print(f"DEBUG: Target Date: {target_date}, Limit Date: {limit_date}")
    print(f"DEBUG: Total news items: {len(all_news)}")
    
    candidates = []
    for item in all_news:
        try:
            pub_date = datetime.strptime(item['published_at'], '%Y-%m-%d')
            # print(f"DEBUG: Checking {item['published_at']} vs {limit_date} - {target_date}")
            if limit_date <= pub_date <= target_date:
                candidates.append(item)
        except:
            continue
            
    # Score them
    if not candidates:
        print(f"WARNING: No news found for date range {limit_date} to {target_date}")
        # We might want to raise an error here too if strict mode is on, but for now just log loudly
        print("CRITICAL: Candidate list is empty! Analysis will produce nothing.")

    sources_config = rule_based_top10.load_sources_config()
    for item in candidates:
        item['score'] = rule_based_top10.calculate_score(item)
        item['top10_category'] = rule_based_top10.categorize_news(item, sources_config)
        
    # Sort by score
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    # --- DIVERSITY ENFORCEMENT ---
    # Group by category
    category_buckets = {}
    for item in candidates:
        cat = item.get('top10_category', 'Uncategorized')
        if cat not in category_buckets:
            category_buckets[cat] = []
        category_buckets[cat].append(item)
        
    diversity_pool = []
    seen_urls = set()
    
    # 1. Guaranteed Entry: Top 3 from each category
    for cat, items in category_buckets.items():
        # items are already sorted by score
        top_picks = items[:3]
        for item in top_picks:
            if item['url'] not in seen_urls:
                diversity_pool.append(item)
                seen_urls.add(item['url'])
    
    # --- SPECIAL ENFORCEMENT ---
    # 1. Ensure at least 5 HackingAI items (via discussion_url)
    hacking_ai_items = [item for item in candidates if item.get('discussion_url') and item['url'] not in seen_urls]
    for item in hacking_ai_items[:5]:
        diversity_pool.append(item)
        seen_urls.add(item['url'])
        
    # 2. Fill the rest up to 50, but CAP Google News
    remaining_slots = 50 - len(diversity_pool)
    google_news_count = sum(1 for item in diversity_pool if 'news.google.com' in item['url'])
    MAX_GOOGLE_NEWS = 4
    
    if remaining_slots > 0:
        for item in candidates: # candidates is already sorted by score
            if item['url'] not in seen_urls:
                # Check Google News Cap
                is_google_news = 'news.google.com' in item['url']
                
                if is_google_news:
                    if google_news_count >= MAX_GOOGLE_NEWS:
                        continue
                    google_news_count += 1
                    
                diversity_pool.append(item)
                seen_urls.add(item['url'])
                if len(diversity_pool) >= 50:
                    break
                    
    # If still not enough (because of strict caps), fill with anything
    if len(diversity_pool) < 20:
        for item in candidates:
            if len(diversity_pool) >= 50: break
            if item['url'] in seen_urls: continue
            diversity_pool.append(item)
            seen_urls.add(item['url'])

    candidates = diversity_pool
    # Re-sort pool by score for AI
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"Found {len(candidates)} candidates (Diversity Enforced). Sending to AI Editor...")
    
    # --- AI EDITOR SELECTION ---
    final_candidates = select_top_stories_with_ai(candidates)
    
    final_top10 = []
    processed_count = 0
    
    # 2. Process Candidates until we have 10 good ones
    for item in final_candidates:
        if len(final_top10) >= 10:
            break
            
        print(f"Processing candidate {processed_count+1}/{len(final_candidates)}: {item['title']}")
        log_debug(f"Processing candidate {processed_count+1}: {item['title']}")
        
        # Fetch Content
        content, status, fetched_image = fetch_article_content(item['url'], item['source'], item.get('discussion_url'))
        
        # Backfill image if missing
        if not item.get('image_url') and fetched_image:
            print(f"  -> Found missing image: {fetched_image[:50]}...")
            item['image_url'] = fetched_image
            # Update DB with new image
            conn = None
            try:
                conn = database.get_connection()
                c = conn.cursor()
                c.execute("UPDATE news SET image_url = ? WHERE url = ?", (fetched_image, item['url']))
                conn.commit()
            except Exception as e:
                print(f"  -> Failed to update image in DB: {e}")
            finally:
                if conn:
                    conn.close()
        
        if not content:
            print(f"  -> Fetch failed: {status}")
            log_debug(f"  -> Fetch failed: {status}")
            
            # Fallback to RSS summary if available
            if item.get('summary'):
                print("  -> Falling back to RSS summary...")
                log_debug("  -> Falling back to RSS summary...")
                content = item['summary']
                # Append a note to content so AI knows it's a summary
                content += "\n\n(Note: Full article content could not be fetched. Analyze based on this summary.)"
            else:
                processed_count += 1
                continue
            
        # Analyze with AI
        print("  -> Analyzing with Gemini...")
        log_debug("  -> Analyzing with Gemini...")
        analysis = analyze_article_with_gemini(item['title'], content, item['source'])
        
        if analysis:
            item['ai_rundown'] = analysis.get('ai_rundown')
            # Removed details and impact as per user request
            item['ai_details'] = None
            item['ai_impact'] = None
            if 'ai_bullets' in item:
                del item['ai_bullets']
            
            # Save to DB
            database.update_ai_analysis(
                item['url'], 
                item['ai_rundown'], 
                None, # details
                None  # impact
            )
            
            final_top10.append(item)
            print(f"  -> Added to Top 10 ✅ (Total: {len(final_top10)})")
            
            # INCREMENTAL SAVE
            # Add rank
            current_top10 = []
            for i, t_item in enumerate(final_top10):
                t_item_copy = t_item.copy()
                t_item_copy['rank'] = i + 1
                current_top10.append(t_item_copy)
                
            result = {
                "date": target_date.strftime('%Y-%m-%d'),
                "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "top10": current_top10,
                "news_count": len(candidates),
                "analysis_stats": {"processed": processed_count + 1, "accepted": len(final_top10)},
                "method": "deep-ai-analysis"
            }
            
            filename = f"top10_{target_date.strftime('%Y-%m-%d')}.json"
            # Save to DB (Firestore or Local File via abstraction)
            database.save_briefing(target_date.strftime('%Y-%m-%d'), result)
            print(f"  -> Saved progress to DB ({filename})")
            
        else:
            print("  -> AI Analysis failed, skipping.")
            log_debug("  -> AI Analysis failed, skipping.")
            
        processed_count += 1
        time.sleep(1) # Paid tier: faster processing
        
    # 3. Generate Daily Summary (The Cherry on Top)
    print("Generating Daily Briefing Summary...")
    daily_summary = generate_daily_summary(final_top10)
    
    # 4. Final Save
    # Add rank
    for i, item in enumerate(final_top10):
        item['rank'] = i + 1
        
    filename = f"top10_{target_date.strftime('%Y-%m-%d')}.json"
    
    # SAFETY CHECK: Don't overwrite existing good file with empty data
    if not final_top10:
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                if existing_data.get('top10') and len(existing_data['top10']) > 0:
                    print(f"⚠️ WARNING: Generated list is empty, but {filename} already has data.")
                    print("⚠️ Aborting save to prevent overwriting valid briefing.")
                    return existing_data
            except Exception as e:
                print(f"Error checking existing file: {e}")
    
    result = {
        "date": target_date.strftime('%Y-%m-%d'),
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "top10": final_top10,
        "daily_briefing": daily_summary, # New field
        "news_count": len(candidates),
        "analysis_stats": {"processed": processed_count, "accepted": len(final_top10)},
        "method": "deep-ai-analysis"
    }
    
    # Save to DB (Firestore or Local File via abstraction)
    database.save_briefing(target_date.strftime('%Y-%m-%d'), result)
    
    # Cleanup Playwright resources
    cleanup_playwright()
        
    print(f"Saved Deep Analysis Top 10 to {filename}")
    return result


if __name__ == "__main__":
    # Test run
    if not get_api_key():
        print("Please set GOOGLE_API_KEY environment variable to test.")
    else:
        generate_deep_top10()
