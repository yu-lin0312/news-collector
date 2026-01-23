import os
import json
import database
from datetime import datetime, timedelta

# Source weights (1-10, higher = more authoritative)
SOURCE_WEIGHTS = {
    # Policy sources
    'Whitehouse': 10,
    'NIST': 9,
    'GOV.UK': 8,
    'CISA': 8,
    'Euractiv': 7,
    'Futurium': 7,
    'AI Policy Tracker': 8,
    'White & Case': 7,
    
    # Academic/Technology sources
    'Nature': 10,
    'Nature NPJ Digital Med': 9,
    'IEEE Spectrum': 9,
    'Turing Institute': 8,
    'PNAS': 9,
    'RAND': 8,
    'Wevolver': 7,
    
    # Tech News sources
    'TechCrunch': 9,
    'TechCrunch AI': 9,
    'VentureBeat': 8,
    'TechNews': 7,
    # 台灣中文來源 (提高權重，使用實際來源名稱)
    'iThome': 10,
    'INSIDE': 10,
    '數位時代': 10,
    'TechOrange': 9,
    'TechOrange 科技報橘': 10,  # 實際名稱
    'BusinessNext': 8,
    'Meet': 7,
    'Techbang': 7,
    '經濟日報 AI': 9,
    '聯合報科技': 9,
    # Google News 帶回來的中文來源
    'CMoney投資網誌': 9,
    'CMoney': 9,
    '科技島': 10,
    'news.cnyes.com': 8,
    '聯合新聞網': 10,
    'TechNews 科技新報': 10,
    '工商時報': 9,
    '中央社 CNA': 10,
    '經濟日報': 9,
    '奇摩新聞': 8,
    '蕃新聞': 7,
    '網管人': 8,
    '台視全球資訊網': 8,
    'Techritual Hong Kong': 7,
    # 其他英文來源
    'AI News': 7,
    'Computer Weekly': 7,
    'Washington Examiner': 6,
    'IT Brief NZ': 6,
    
    # Business sources
    'Sequoia Cap': 8,
    'Christian Kromme': 6,
    'Campaign Archive': 5,
    
    # Community/Aggregators
    'HackingAI': 9,
    'TLDR Tech AI': 8,
}

# Keyword weights for scoring
KEYWORD_WEIGHTS = {
    # Policy keywords
    'regulation': 3, 'law': 3, 'government': 3, 'policy': 3,
    'ban': 3, 'compliance': 2, 'legislation': 3, 'executive order': 3,
    '法規': 3, '政策': 3, '監管': 3, '法律': 3,
    
    # Technology keywords
    'breakthrough': 3, 'research': 3, 'algorithm': 3, 'model': 2,
    'paper': 2, 'study': 2, 'discovery': 3, 'innovation': 2,
    '研究': 3, '突破': 3, '演算法': 3, '創新': 2,
    
    # Industry keywords
    'launch': 2, 'release': 2, 'product': 2, 'deploy': 2,
    'adopt': 2, 'implementation': 2, 'rollout': 2,
    '發布': 2, '推出': 2, '部署': 2, '應用': 2,
    
    # Business keywords
    'funding': 2, 'investment': 2, 'acquisition': 2, 'ipo': 3,
    'revenue': 2, 'partnership': 2, 'merger': 2,
    '融資': 2, '投資': 2, '併購': 2, '收購': 2,
    
    # Risk keywords
    'security': 3, 'breach': 3, 'bias': 3, 'risk': 3,
    'concern': 2, 'threat': 3, 'vulnerability': 3, 'attack': 3,
    '風險': 3, '資安': 3, '威脅': 3, '漏洞': 3,
}

def load_sources_config():
    try:
        with open('sources.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading sources.json: {e}")
        return []

def get_recent_news():
    """Get news from the last 7 days"""
    all_news = database.get_all_news()
    if not all_news:
        return []
    
    # Convert to dict if needed
    news_list = []
    if all_news and hasattr(all_news[0], 'keys'):
        news_list = [dict(row) for row in all_news]
    else:
        news_list = all_news
    
    print(f"RB: Total items from DB: {len(news_list)}")
    
    # Filter for recent news (last 7 days)
    today = datetime.now()
    limit_date = today - timedelta(days=7)
    
    recent_news = []
    for item in news_list:
        try:
            pub_date_str = item['published_at']
            # Parse date to compare
            try:
                # Try YYYY-MM-DD
                pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
            except ValueError:
                try:
                    # Try ISO format (YYYY-MM-DDTHH:MM:SS...)
                    # Handle timezone if present, or just ignore it for comparison
                    if 'T' in pub_date_str:
                        pub_date = datetime.fromisoformat(pub_date_str)
                        # Make naive for comparison if needed, or ensure limit_date is aware
                        if pub_date.tzinfo is not None:
                            pub_date = pub_date.replace(tzinfo=None)
                    else:
                        continue
                except ValueError:
                     # print(f"Date parse error for {pub_date_str}")
                     continue
            
            if pub_date >= limit_date:
                recent_news.append(item)
        except Exception as e:
            # If date parsing fails, skip or check if string match (fallback)
            pass
    
    print(f"Found {len(recent_news)} recent news items (last 7 days)")
    return recent_news

def calculate_score(news_item):
    """Calculate score based on source weight, keywords, and recency"""
    score = 0
    
    # 1. Source weight (× 1.5 multiplier)
    source = news_item['source']
    
    # Special handling for HackingAI items (identified by discussion_url)
    if news_item.get('discussion_url'):
        source_weight = 9 # Equivalent to HackingAI weight
    else:
        source_weight = SOURCE_WEIGHTS.get(source, 5)
        
    score += source_weight * 1.5
    
    # 2. Keyword weighting
    text = (news_item.get('title', '') + ' ' + news_item.get('summary', '')).lower()
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in text:
            score += weight
    
    # 3. Recency bonus (今日新聞優先)
    try:
        pub_date_str = news_item['published_at']
        try:
            # Try YYYY-MM-DD first
            pub_date = datetime.strptime(pub_date_str, '%Y-%m-%d')
        except ValueError:
            # Try ISO format (e.g. from Firestore)
            pub_date = datetime.fromisoformat(pub_date_str)
            
        # Compare dates only to avoid timezone issues
        today_date = datetime.now().date()
        pub_date_date = pub_date.date()
        days_diff = (today_date - pub_date_date).days
        
        if days_diff <= 0:  # Today - 大幅加分
            score += 10
        elif days_diff <= 1:  # Yesterday
            score += 4
        elif days_diff <= 3:  # Within 3 days
            score += 2
        elif days_diff <= 7:  # Within 7 days
            score += 1
    except Exception as e:
        # print(f"Date score error: {e}")
        pass
    
    return round(score, 1)

def categorize_news(news_item, sources_config):
    """Categorize news based on source category and keywords"""
    source_name = news_item['source']
    
    # Find source category from config
    source_category = ''
    
    # Special handling for HackingAI items
    if news_item.get('discussion_url'):
        source_category = '全球 AI 趨勢' # Default category for HackingAI
    else:
        # Check config first
        for src in sources_config:
            if src['name'] == source_name:
                source_category = src.get('category', '')
                break
        
        # Fallback for Google News sources (hardcoded categories)
        if not source_category:
            tw_tech_sources = [
                'CMoney投資網誌', 'CMoney', '科技島', 'news.cnyes.com', 
                '聯合新聞網', 'TechNews 科技新報', 'TechOrange 科技報橘',
                '工商時報', '中央社 CNA', '經濟日報', '奇摩新聞', 
                '蕃新聞', '網管人', '台視全球資訊網', 'Techritual Hong Kong'
            ]
            if source_name in tw_tech_sources:
                source_category = '台灣科技新聞'
            elif 'TechCrunch' in source_name:
                source_category = '全球 AI 趨勢'
    
    # Map to Top 10 categories
    text = (news_item.get('title', '') + ' ' + news_item.get('summary', '')).lower()
    
    # Check for Risk keywords first (highest priority)
    risk_keywords = ['security', 'breach', 'bias', 'risk', 'threat', 'vulnerability', 'attack', '風險', '資安', '威脅']
    if any(kw in text for kw in risk_keywords):
        return 'Risk'
    
    # Then check source category
    if '政策' in source_category or '政府' in source_category:
        return 'Policy'
    elif '學術' in source_category or '科學' in source_category:
        return 'Technology'
    elif '科技' in source_category or '新聞' in source_category or '趨勢' in source_category:
        # Further distinguish between Industry and Business
        business_keywords = ['funding', 'investment', 'acquisition', 'ipo', 'revenue', '融資', '投資', '併購']
        if any(kw in text for kw in business_keywords):
            return 'Business'
        return 'Industry'
    else:
        return 'Business'

def generate_rule_based_top10(target_date=None):
    """
    Generate Top 10 news based on rules for a specific date.
    target_date: datetime object or string 'YYYY-MM-DD'. Defaults to today.
    """
    if target_date is None:
        target_date = datetime.now()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, '%Y-%m-%d')
        
    # Ensure we're looking at the end of that day if it's not today
    if target_date.date() < datetime.now().date():
        target_date = target_date.replace(hour=23, minute=59, second=59)

    print(f"Generating Top 10 for date: {target_date.strftime('%Y-%m-%d')}")
    
    # 1. Get recent news (last 24 hours from target_date)
    all_news = database.get_all_news()
    if not all_news:

        return {
            "date": target_date.strftime('%Y-%m-%d'),
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "top10": [],
            "news_count": 0,
            "analysis_stats": {},
            "method": "rule-based"
        }
    
    # Convert to dict if needed
    news_list = []
    if all_news and hasattr(all_news[0], 'keys'):
        news_list = [dict(row) for row in all_news]
    else:
        news_list = all_news
    
    # Filter for news within 24 hours of target_date
    limit_date = target_date - timedelta(days=1)
    
    news = []
    for item in news_list:
        try:
            # Try parsing with time first
            try:
                pub_date = datetime.strptime(item['published_at'], '%Y-%m-%d %H:%M:%S')
            except ValueError:
                # Fallback to date only
                pub_date = datetime.strptime(item['published_at'], '%Y-%m-%d')
                
            # Check if news is within the 24h window ending at target_date
            if limit_date <= pub_date <= target_date:
                news.append(item)
        except Exception as e:
            # print(f"Date parse error: {e}")
            continue
            
    if not news:
        print(f"No news found for {target_date.strftime('%Y-%m-%d')}")
        # Fallback: if no news for specific date, just take latest for demo purposes if it's today
        if target_date.date() == datetime.now().date():
             print("Fallback: Using latest 50 news for today")
             news = news_list[:50]
        else:
             return {
                "date": target_date.strftime('%Y-%m-%d'),
                "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "top10": [],
                "news_count": 0,
                "analysis_stats": {},
                "method": "rule-based"
            }
    
    # 0. Load config
    sources_config = load_sources_config()

    # Filter out None items from news
    news = [item for item in news if item is not None]

    # 2. Score and categorize all news
    for item in news:
        item['score'] = calculate_score(item)
        item['top10_category'] = categorize_news(item, sources_config)
    
    # 3. Group by category
    grouped = {
        'Policy': [],
        'Technology': [],
        'Industry': [],
        'Business': [],
        'Risk': []
    }
    
    for item in news:
        cat = item['top10_category']
        if cat in grouped:
            grouped[cat].append(item)
    
    # Sort each group by score
    for cat in grouped:
        grouped[cat].sort(key=lambda x: x['score'], reverse=True)
    
    # 4. Select by quotas
    quotas = {
        'Policy': 2,
        'Technology': 2,
        'Industry': 3,
        'Business': 2,
        'Risk': 1
    }
    
    top10 = []
    for cat, count in quotas.items():
        selected = grouped[cat][:count]
        top10.extend(selected)
    
    # 5. Fill remaining slots if needed
    if len(top10) < 10:
        remaining = []
        for cat in grouped:
            for item in grouped[cat]:
                if item not in top10:
                    remaining.append(item)
        remaining.sort(key=lambda x: x['score'], reverse=True)
        top10.extend(remaining[:10-len(top10)])
    
    # 6. Final sort by score and add rank
    top10.sort(key=lambda x: x['score'], reverse=True)
    top10 = top10[:10]  # Ensure exactly 10
    
    for i, item in enumerate(top10):
        item['rank'] = i + 1
    
    # 7. Calculate stats
    stats = {k: len(v) for k, v in grouped.items()}
    
    result = {
        "date": target_date.strftime('%Y-%m-%d'),
        "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "top10": top10,
        "news_count": len(news),
        "analysis_stats": stats,
        "method": "rule-based"
    }
    
    # Save to date-specific file
    filename = f"top10_{target_date.strftime('%Y-%m-%d')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Saved Top 10 to {filename}")
    
    return result

if __name__ == "__main__":
    print("Testing rule-based Top 10 generator...")
    database.init_db()
    result = generate_rule_based_top10()
    print(f"Generated {len(result['top10'])} items")
    print(f"Stats: {result['analysis_stats']}")
    if result['top10']:
        print("\nTop 3:")
        for item in result['top10'][:3]:
            print(f"{item['rank']}. {item['title']} - Score: {item['score']}")
