import os
import json
from dotenv import load_dotenv

# Load environment variables before importing modules that depend on them
load_dotenv()

import database
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
from datetime import datetime, timedelta
import time
import random
from playwright.sync_api import sync_playwright
import urllib3
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
    
    def _check_playwright_install(self):
        """Ensure Playwright browsers are installed."""
        import subprocess
        import sys
        try:
            # Check if we can launch a browser (cheap check)
            # Just run install command, it returns quickly if already installed
            print("Checking Playwright browsers in Deep Analyzer...")
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            print("Playwright browsers checked.")
        except Exception as e:
            print(f"Warning: Failed to install Playwright browsers: {e}")

    def _ensure_browser(self):
        """Lazily initialize shared Playwright browser and context."""
        if self._browser is None:
            self._check_playwright_install()
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
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

def resolve_original_source(item):
    """
    If source is an aggregator, try to resolve the real source from URL.
    """
    aggregator_names = ['TLDR Tech AI', 'HackingAI']
    
    # Check if it's an aggregator
    is_aggregator = False
    for agg in aggregator_names:
        if agg.lower() in item['source'].lower():
            is_aggregator = True
            break
            
    if is_aggregator:
        try:
            from urllib.parse import urlparse
            domain = urlparse(item['url']).netloc
            # Remove www.
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Extract main name
            parts = domain.split('.')
            if len(parts) >= 2:
                name = parts[0]
                # Special cases
                if 'github' in name: return 'GitHub'
                if 'arxiv' in name: return 'Arxiv'
                if 'youtube' in name: return 'YouTube'
                if 'bloomberg' in name: return 'Bloomberg'
                if 'techcrunch' in name: return 'TechCrunch'
                if 'wsj' in name: return 'WSJ'
                if 'nytimes' in name: return 'NYTimes'
                if 'reuters' in name: return 'Reuters'
                
                # Default: Capitalize first letter
                return name.title()
        except:
            pass
    return item['source']


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
            
            # Special handling for Google News redirects
            if "news.google.com" in url:
                print("Waiting for Google News redirect...")
                page.wait_for_timeout(5000)
            
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

    # 定義 7 種新聞分類
    CATEGORY_DEFINITIONS = """
    - Breaking: 突發重大事件、重要人事異動、產品重大更新（如 GPT-5 發布、CEO 辭職）
    - Tools: 新工具、App、網站、實用功能發布（如 ChatGPT 新功能、Perplexity 更新）
    - Business: 融資、投資、併購、財報、商業合作（如 OpenAI 融資、Google 收購）
    - Creative: AI 繪圖、影片生成、設計工具（如 Sora、Midjourney、Runway）
    - Research: 學術論文、技術突破、新架構（如 Arxiv 論文、MIT 研究）
    - Rules: 政府法規、政策、補助方案（如 歐盟 AI Act、台灣補助）
    - Risk: 資安漏洞、AI 偏見、倫理爭議、安全威脅（如 AI 攻擊、隱私問題）
    """
    
    prompt = f"""
    你是一位專業的科技新聞編輯，擅長 UX Writing。請閱讀以下新聞內容，並為「每日 AI 簡報」撰寫分析文案。
    
    【新聞資訊】
    標題：{title}
    來源：{source}
    內容摘要：
    {content[:3000]}... (下略)

    【撰寫要求】
    請生成以下欄位的內容：
    
    1. **ai_rundown (重點摘要，繁體中文)**：
       - 類似 The Rundown AI 的風格。
       - 用一句話破題，接著用 2-3 句話清楚說明發生了什麼事。
       - 語氣專業、簡潔、有力。
       - 字數控制在 50 字以內。

    2. **category (新聞分類，英文)**：
       - 根據新聞內容，從以下 7 種分類中選擇最適合的一種：
       {CATEGORY_DEFINITIONS}
       - 只需回傳分類名稱（Breaking/Tools/Business/Creative/Research/Rules/Risk）

    【輸出格式】
    請直接回覆 JSON 格式，不要有 markdown 標記：
    {{
        "ai_rundown": "...",
        "category": "..."
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
    
    # Trust rule_based_top10's filtering and scoring (which already handles recency bonus)
    # We just take the top candidates directly to avoid double-filtering issues with timezones
    print(f"DEBUG: Trusting rule_based_top10 results. Total items: {len(all_news)}")
    
    # Define limit_date for logging purposes (matching rule_based_top10 logic)
    limit_date = target_date - timedelta(days=7)
    
    candidates = []
    for item in all_news:
        # Basic validation
        if not (item and item.get('title') and item.get('url')):
            continue
            
        # Strict Date Check (Redundancy)
        try:
            pub_date_str = item['published_at']
            if 'T' in pub_date_str:
                pub_date = datetime.fromisoformat(pub_date_str)
            else:
                pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
                
            if pub_date.tzinfo is not None:
                pub_date = pub_date.replace(tzinfo=None)
                
            # If older than limit_date (5 days), skip
            if pub_date < limit_date:
                # print(f"Skipping old news: {item['title']} ({pub_date_str})")
                continue
                
            candidates.append(item)
        except:
            # If date parse fails, keep it but it might get low score
            candidates.append(item)
            
    # Score them
    if not candidates:
        print(f"WARNING: No news found for date range {limit_date} to {target_date}")
        # We might want to raise an error here too if strict mode is on, but for now just log loudly
        print("CRITICAL: Candidate list is empty! Analysis will produce nothing.")

    sources_config = rule_based_top10.load_sources_config()
    for item in candidates:
        # Resolve original source for aggregators (TLDR, HackingAI, etc.)
        item['source'] = resolve_original_source(item)
        
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
    source_counts = {} # Track items per source for capping
    MAX_PER_SOURCE = 3
    
    # 1. Guaranteed Entry: Top 3 from each category
    from difflib import SequenceMatcher
    
    def is_duplicate(item, pool):
        """Check if item is duplicate based on URL or Title similarity"""
        for existing in pool:
            # URL check
            if item['url'] == existing['url']:
                return True
            
            # Title similarity check
            ratio = SequenceMatcher(None, item['title'].lower(), existing['title'].lower()).ratio()
            if ratio > 0.85: # 85% similarity threshold
                print(f"DEBUG: Duplicate detected by title: '{item['title']}' vs '{existing['title']}' ({ratio:.2f})")
                return True
        return False

    for cat, items in category_buckets.items():
        # items are already sorted by score
        top_picks = items[:3]
        for item in top_picks:
            if not is_duplicate(item, diversity_pool):
                # Check source cap
                source = item.get('source', 'Unknown')
                if source_counts.get(source, 0) >= MAX_PER_SOURCE:
                    continue
                    
                diversity_pool.append(item)
                seen_urls.add(item['url'])
                source_counts[source] = source_counts.get(source, 0) + 1
    
    # --- SPECIAL ENFORCEMENT ---
    # 1. Ensure at least 5 HackingAI items (via discussion_url)
    # HackingAI is special, we might want to allow more from it if it's the aggregator itself,
    # but since we resolved sources, these might now be 'GitHub', 'Arxiv', etc.
    # So we filter by discussion_url presence which indicates HackingAI origin.
    hacking_ai_items = [item for item in candidates if item.get('discussion_url') and not is_duplicate(item, diversity_pool)]
    for item in hacking_ai_items[:5]:
        # Check source cap (even for HackingAI derived items, we want diversity)
        # But maybe relax it slightly or treat them as distinct? 
        # Let's enforce cap to ensure we don't get 5 Arxiv papers if HackingAI posted 5 Arxiv papers.
        source = item.get('source', 'Unknown')
        if source_counts.get(source, 0) >= MAX_PER_SOURCE:
            continue
            
        diversity_pool.append(item)
        seen_urls.add(item['url'])
        source_counts[source] = source_counts.get(source, 0) + 1
        
    # 2. Fill the rest up to 50, but CAP Google News
    remaining_slots = 50 - len(diversity_pool)
    google_news_count = sum(1 for item in diversity_pool if 'news.google.com' in item['url'])
    MAX_GOOGLE_NEWS = 4
    
    if remaining_slots > 0:
        for item in candidates: # candidates is already sorted by score
            if item['url'] not in seen_urls:
                # Check Google News Cap (Legacy logic, but source_counts handles it generally now)
                is_google_news = 'news.google.com' in item['url']
                
                if is_google_news:
                    if google_news_count >= MAX_GOOGLE_NEWS:
                        continue
                    google_news_count += 1
                
                # General Source Cap
                source = item.get('source', 'Unknown')
                if source_counts.get(source, 0) >= MAX_PER_SOURCE:
                    continue
                    
                diversity_pool.append(item)
                seen_urls.add(item['url'])
                source_counts[source] = source_counts.get(source, 0) + 1
                if len(diversity_pool) >= 50:
                    break
                    
    # If still not enough (because of strict caps), fill with anything
    if len(diversity_pool) < 20:
        for item in candidates:
            if len(diversity_pool) >= 50: break
            if item['url'] in seen_urls: continue
            
            # Still enforce cap in fallback? Maybe relax if desperate.
            # Let's enforce strict diversity.
            source = item.get('source', 'Unknown')
            if source_counts.get(source, 0) >= MAX_PER_SOURCE:
                continue
                
            diversity_pool.append(item)
            seen_urls.add(item['url'])
            source_counts[source] = source_counts.get(source, 0) + 1

    candidates = diversity_pool
    # Re-sort pool by score for AI
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
    print(f"Found {len(candidates)} candidates (Diversity Enforced). Sending to AI Editor...")
    
    # --- AI EDITOR SELECTION ---
    final_candidates = select_top_stories_with_ai(candidates)
    
    # 定義 7 種新聞分類
    ALL_CATEGORIES = ['Breaking', 'Tools', 'Business', 'Creative', 'Research', 'Rules', 'Risk']
    
    processed_articles = []  # 改用新變數名稱，收集所有成功處理的文章
    processed_count = 0
    
    # 2. Process Candidates until we have 12 good ones (減少處理數量以提升效能)
    for item in final_candidates:
        if len(processed_articles) >= 12:
            break
            
        print(f"Processing candidate {processed_count+1}/{len(final_candidates)}: {item['title']}")
        log_debug(f"Processing candidate {processed_count+1}: {item['title']}")
        
        # Fetch Content
        content, status, fetched_image = fetch_article_content(item['url'], item['source'], item.get('discussion_url'))
        
        # Backfill image if missing (DISABLED for speed)
        # if not item.get('image_url') and fetched_image:
        #     print(f"  -> Found missing image: {fetched_image[:50]}...")
        #     item['image_url'] = fetched_image
        #     # Update DB with new image
        #     try:
        #         database.update_news_image(item['url'], fetched_image)
        #     except Exception as e:
        #         print(f"  -> Failed to update image in DB: {e}")
        
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
            item['ai_category'] = analysis.get('category', 'Breaking')  # 新增分類欄位
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
            
            processed_articles.append(item)
            print(f"  -> Added to pool ✅ (Total: {len(processed_articles)})")
            
            # INCREMENTAL SAVE
            # Add rank
            current_top10 = []
            for i, t_item in enumerate(processed_articles):
                t_item_copy = t_item.copy()
                t_item_copy['rank'] = i + 1
                current_top10.append(t_item_copy)
                
            result = {
                "date": target_date.strftime('%Y-%m-%d'),
                "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "top10": current_top10,
                "news_count": len(candidates),
                "analysis_stats": {"processed": processed_count + 1, "accepted": len(processed_articles)},
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
        # Removed time.sleep(0.5) for faster processing
        
    # 3. 分類平衡選擇：確保每個分類至少有 1 則，然後按 score 排序
    print("\n🎯 Applying category balance with score-based ranking...")
    
    # 按分類分組
    category_buckets = {cat: [] for cat in ALL_CATEGORIES}
    for item in processed_articles:
        cat = item.get('ai_category', 'Breaking')
        if cat in category_buckets:
            category_buckets[cat].append(item)
        else:
            category_buckets['Breaking'].append(item)  # 未知分類歸入 Breaking
    
    # 在每個分類內按 score 排序
    for cat in category_buckets:
        category_buckets[cat].sort(key=lambda x: x.get('score', 0), reverse=True)
    
    # 列印每個分類的數量
    for cat, items in category_buckets.items():
        print(f"  {cat}: {len(items)} items")
    
    # 選擇邏輯：每個分類至少 1 則（選該分類中 score 最高的）
    final_top10 = []
    used_urls = set()
    
    # 第一輪：每個分類各選 1 則（按 score 最高）
    for cat in ALL_CATEGORIES:
        items = category_buckets[cat]
        if items and len(final_top10) < 10:
            # 選該分類中 score 最高的一則
            for item in items:
                if item['url'] not in used_urls:
                    final_top10.append(item)
                    used_urls.add(item['url'])
                    print(f"  ✓ Selected [{cat}] (score: {item.get('score', 0):.1f}): {item['title'][:40]}...")
                    break
    
    # 第二輪：用剩餘名額補齊（按 score 排序）
    remaining_items = [item for item in processed_articles if item['url'] not in used_urls]
    remaining_items.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    for item in remaining_items:
        if len(final_top10) >= 10:
            break
        final_top10.append(item)
        used_urls.add(item['url'])
        print(f"  + Filled with [{item.get('ai_category', 'Unknown')}] (score: {item.get('score', 0):.1f}): {item['title'][:40]}...")
    
    # 最終按 score 排序
    final_top10.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    print(f"\n📋 Final Top 10 selected and sorted by score ({len(final_top10)} items)")
    
    # 4. Generate Daily Summary (The Cherry on Top)
    print("Generating Daily Briefing Summary...")
    daily_summary = generate_daily_summary(final_top10)
    
    # 5. Final Save
    # Add rank
    for i, item in enumerate(final_top10):
        item['rank'] = i + 1
        
    filename = f"top10_{target_date.strftime('%Y-%m-%d')}.json"
    
    # SAFETY CHECK: Don't overwrite existing good data with empty data
    # Check BOTH local file AND Firestore
    if not final_top10:
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Check Firestore first (for cloud deployments)
        try:
            existing_briefing = database.get_briefing(date_str)
            if existing_briefing and existing_briefing.get('top10') and len(existing_briefing['top10']) > 0:
                print(f"⚠️ WARNING: Generated list is empty, but Firestore already has {len(existing_briefing['top10'])} items for {date_str}.")
                print("⚠️ Aborting save to prevent overwriting valid briefing.")
                # Cleanup Playwright before returning
                cleanup_playwright()
                return existing_briefing
        except Exception as e:
            print(f"Error checking Firestore: {e}")
        
        # Also check local file (for local development)
        if os.path.exists(filename):
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
                if existing_data.get('top10') and len(existing_data['top10']) > 0:
                    print(f"⚠️ WARNING: Generated list is empty, but {filename} already has data.")
                    print("⚠️ Aborting save to prevent overwriting valid briefing.")
                    # Cleanup Playwright before returning
                    cleanup_playwright()
                    return existing_data
            except Exception as e:
                print(f"Error checking existing file: {e}")
    
    result = {
        "date": target_date.strftime('%Y-%m-%d'),
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "top10": final_top10,
        "daily_briefing": daily_summary, # New field
        "news_count": len(candidates),
        "analysis_stats": {"processed": processed_count, "accepted": len(processed_articles), "final_selected": len(final_top10)},
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
