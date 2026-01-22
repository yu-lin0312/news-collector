import os
import json
import database
import google.generativeai as genai
from datetime import datetime, timedelta
import time

# Configuration
CACHE_FILE = 'top10_cache.json'
SERVICE_ACCOUNT_FILE = 'serviceAccountKey.json' # Not used by genai directly, but good to know context
# We need an API Key for Gemini. 
# Assuming the user has set GOOGLE_API_KEY env var or we need to ask for it.
# However, the user provided a serviceAccountKey.json which is for Firebase.
# For Gemini, we usually need an API key. 
# Let's check if there is an existing way they use Gemini.
# I see `analyze_html.py` and `analyze_policy_sources.py` in the file list. 
# Let me check `analyze_html.py` to see how they use LLMs.

def get_todays_news():
    """Fetch news from the database published within the last 24 hours."""
    # Since we don't have a direct "get_news_by_date" in database.py, we fetch all and filter.
    # Or we can add a method to database.py. For now, let's fetch all and filter in python to avoid DB schema changes if possible,
    # but `get_all_news` might be heavy. 
    # Let's look at `database.py` again. It has `get_all_news`.
    
    all_news = database.get_all_news()
    if not all_news:
        return []

    # Convert to dict if needed
    news_list = []
    if hasattr(all_news[0], 'keys'):
        news_list = [dict(row) for row in all_news]
    else:
        news_list = all_news

    # Filter for "today" (let's say last 24 hours or same calendar day)
    # The user request said "Today's Top 10". 
    # Let's use 24 hours window for better coverage, or just today's date.
    # Given news might be crawled from different timezones, 24h is safer.
    
    # Filter for "today" and "yesterday" to ensure we have enough coverage
    # especially if running early in the morning
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    
    today_str = today.strftime('%Y-%m-%d')
    yesterday_str = yesterday.strftime('%Y-%m-%d')
    
    todays_news = []
    
    for item in news_list:
        try:
            pub_date_str = item['published_at']
            # Check if date matches today or yesterday
            if pub_date_str == today_str or pub_date_str == yesterday_str:
                todays_news.append(item)
                
        except Exception as e:
            print(f"Error parsing date for {item.get('title')}: {e}")
            
    print(f"Found {len(todays_news)} items for {today_str} and {yesterday_str}")
    return todays_news

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading cache: {e}")
    return None

def save_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving cache: {e}")

def analyze_with_gemini(news_items):
    """
    Analyze news items using Gemini API to categorize and score them.
    """
    # Check for API Key
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        # Try to find it in a .env file or similar if not set
        # For now, raise error or return empty
        print("Error: GOOGLE_API_KEY not found in environment variables.")
        return []

    genai.configure(api_key=api_key)
    # Using gemini-2.0-flash as it is available in this environment
    model = genai.GenerativeModel('gemini-2.0-flash')

    # Prepare prompt
    # We might need to batch this if there are too many items.
    # Let's process in batches of 10-20 to avoid token limits.
    
    analyzed_results = []
    
    # Simple batching
    batch_size = 3 # Reduced batch size further for Free Tier
    print(f"Starting analysis of {len(news_items)} items in batches of {batch_size}...")
    
    for i in range(0, len(news_items), batch_size):
        batch = news_items[i:i+batch_size]
        print(f"Processing batch {i//batch_size + 1}...")
        
        prompt = """
        你是一位 AI 產業分析專家。請針對以下新聞進行分析：

        """
        
        for idx, item in enumerate(batch):
            prompt += f"""
            ---
            ID: {idx}
            標題：{item['title']}
            摘要：{item['summary']}
            來源：{item['source']}
            ---
            """
            
        prompt += """
        請依照以下標準對每一則新聞進行分類與評分：

        【類型分類】
        - Policy（政策/法規/治理）：政府法令、監管政策、倫理規範等
        - Technology（技術/研究）：新演算法、研究突破、技術創新等
        - Industry（產業應用）：企業導入、產品發布、市場應用等
        - Business（商業/投資/策略）：融資、併購、商業策略等
        - Risk（風險/資安/社會影響）：資安威脅、倫理爭議、負面影響等

        【影響力評分】1-10 分
        評估標準：
        - 對產業發展方向的影響
        - 對政策制定的啟示
        - 對技術路線的影響
        - 影響範圍（地區性 vs. 全球性）
        - 時效性與重要性

        請以 JSON Array 格式回覆，陣列中每個物件包含：
        - id: 對應輸入的 ID (整數)
        - category: 類型 (Policy/Technology/Industry/Business/Risk)
        - impact_score: 評分 (1-10)
        - reason: 簡短理由 (繁體中文)
        
        範例格式：
        [
            {"id": 0, "category": "Policy", "impact_score": 8, "reason": "歐盟 AI 法案通過，影響深遠"},
            ...
        ]
        """
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                # Parse JSON from response
                text = response.text
                
                # Clean up markdown code blocks if present
                if "```json" in text:
                    text = text.split("```json")[1].split("```")[0]
                elif "```" in text:
                    text = text.split("```")[1].split("```")[0]
                    
                batch_results = json.loads(text)
                
                # Merge results back to news items
                for res in batch_results:
                    original_idx = res.get('id')
                    if original_idx is not None and 0 <= original_idx < len(batch):
                        item = batch[original_idx].copy()
                        item['analysis_category'] = res.get('category')
                        item['impact_score'] = res.get('impact_score')
                        item['reason'] = res.get('reason')
                        analyzed_results.append(item)
                
                print(f"Batch {i//batch_size + 1} success. Got {len(batch_results)} results.")
                time.sleep(5) # Base rate limiting
                break # Success, exit retry loop
                
            except Exception as e:
                print(f"Error analyzing batch {i} (Attempt {attempt+1}/{max_retries}): {e}")
                if "429" in str(e):
                    wait_time = (attempt + 1) * 20 # 20s, 40s, 60s
                    print(f"Rate limit hit. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    # Other errors, maybe skip or retry?
                    time.sleep(5)
                    # If it's not a rate limit, maybe we shouldn't retry indefinitely, but let's try 3 times.
        
    return analyzed_results

def select_top_10(analyzed_news):
    """
    Select Top 10 news based on quotas and scores.
    Quotas:
    - Policy: 2
    - Technology: 2
    - Industry: 3
    - Business: 2
    - Risk: 1
    """
    # Group by category
    grouped = {
        'Policy': [],
        'Technology': [],
        'Industry': [],
        'Business': [],
        'Risk': []
    }
    
    # Sort all by score desc first to handle duplicates or same scores
    # Also handle deduplication here? 
    # Let's do a simple deduplication by title similarity or just assume crawler did some.
    # The crawler has url_exists check, so exact duplicates are gone.
    # But same news from different sources might exist.
    # For now, let's just sort by score.
    
    sorted_news = sorted(analyzed_news, key=lambda x: x.get('impact_score', 0), reverse=True)
    
    # Assign to groups
    for item in sorted_news:
        cat = item.get('analysis_category')
        if cat in grouped:
            grouped[cat].append(item)
        else:
            # Fallback or map other categories
            # If Gemini returns something else, maybe put in Industry or Business?
            # Let's put in Industry as default
            grouped['Industry'].append(item)

    # Quotas
    quotas = {
        'Policy': 2,
        'Technology': 2,
        'Industry': 3,
        'Business': 2,
        'Risk': 1
    }
    
    top_10 = []
    used_ids = set() # To avoid duplicates if we fill from others
    
    # First pass: fill quotas
    for cat, count in quotas.items():
        candidates = grouped[cat]
        # Sort by score again just in case
        candidates.sort(key=lambda x: x.get('impact_score', 0), reverse=True)
        
        selected = candidates[:count]
        top_10.extend(selected)
        for item in selected:
            used_ids.add(item['url']) # Use URL as ID
            
    # Check if we have 10
    if len(top_10) < 10:
        needed = 10 - len(top_10)
        # Get all remaining items from all categories
        remaining = []
        for cat in grouped:
            for item in grouped[cat]:
                if item['url'] not in used_ids:
                    remaining.append(item)
        
        # Sort remaining by score
        remaining.sort(key=lambda x: x.get('impact_score', 0), reverse=True)
        
        # Fill
        top_10.extend(remaining[:needed])
        
    # Final sort by rank (maybe by category order or just score?)
    # User asked for:
    # 輸出格式請只包含：排名（1–10）、新聞標題、來源、類型
    # Usually Top 10 is sorted by importance (score).
    
    top_10.sort(key=lambda x: x.get('impact_score', 0), reverse=True)
    
    # Add rank
    for i, item in enumerate(top_10):
        item['rank'] = i + 1
        
    return top_10

def generate_top_10(force_refresh=False):
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Check cache
    if not force_refresh:
        cache = load_cache()
        if cache and cache.get('date') == today:
            print("Using cached Top 10")
            return cache
            
    print("Generating new Top 10...")
    
    # 1. Get Today's News
    news = get_todays_news()
    print(f"Found {len(news)} news items for today.")
    
    if not news:
        return {"date": today, "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'), "top10": [], "news_count": 0}

    # 2. Analyze
    analyzed = analyze_with_gemini(news)
    print(f"Analyzed {len(analyzed)} items.")
    
    # 3. Select Top 10
    top_10 = select_top_10(analyzed)
    
    # 4. Save Cache
    result = {
        "date": today,
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "top10": top_10,
        "news_count": len(news),
        "analysis_stats": {
            k: len([x for x in analyzed if x.get('analysis_category') == k])
            for k in ['Policy', 'Technology', 'Industry', 'Business', 'Risk']
        }
    }
    
    save_cache(result)
    return result

if __name__ == "__main__":
    # Test run
    print("Testing top_news_analyzer.py...")
    
    # Check DB connection
    try:
        database.init_db()
        print("DB initialized.")
    except Exception as e:
        print(f"DB init failed: {e}")
        
    # Check today's news
    news = get_todays_news()
    print(f"Today's news count: {len(news)}")
    
    if news:
        print("Sample news:", news[0]['title'])
    else:
        print("No news found for today. Please run crawler.py first.")
        
    # Check API Key
    if os.environ.get("GOOGLE_API_KEY"):
        print("GOOGLE_API_KEY is set. Starting full analysis test...")
        try:
            result = generate_top_10(force_refresh=True)
            print("Analysis complete.")
            print(f"Top 10 count: {len(result.get('top10', []))}")
            print(f"Stats: {result.get('analysis_stats')}")
        except Exception as e:
            print(f"Analysis failed: {e}")
    else:
        print("GOOGLE_API_KEY is NOT set.")
