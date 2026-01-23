import rule_based_top10
import database_firestore as fs
from datetime import datetime

def analyze_firestore_scores():
    db = fs.get_db()
    if not db:
        print("Failed to connect to Firestore.")
        return

    today_str = "2026-01-23"
    print(f"Analyzing news for {today_str} in Firestore...")
    
    # Get news from today using string range that covers ISO format
    docs = db.collection('news').where('published_at', '>=', today_str).where('published_at', '<=', f"{today_str}T23:59:59").stream()
    
    news_list = []
    for doc in docs:
        news_list.append(doc.to_dict())
    
    if not news_list:
        print("No news found for today in Firestore.")
        return

    scored_news = []
    for n in news_list:
        score = rule_based_top10.calculate_score(n)
        scored_news.append({
            'title': n.get('title', 'No Title'),
            'source': n.get('source', 'Unknown'),
            'score': score,
            'date': n.get('published_at', 'Unknown'),
            'url': n.get('url') or n.get('link')
        })
    
    # Sort by score
    scored_news.sort(key=lambda x: x['score'], reverse=True)
    
    targets = [
        "Apple plans to make Siri an AI chatbot",
        "Notion working on custom MCPs",
        "Altman Meets Mideast Investors",
        "Pass@k is Mostly Bunk",
        "Claude's new constitution",
        "Meta's new AI team",
        "Apple vs. the AI Hype Cycle",
        "OpenAI's former sales leader"
    ]
    
    output_lines = []
    output_lines.append("\n" + "="*120)
    output_lines.append(f"{'Rank':<5} | {'Score':<6} | {'Source':<15} | {'Category':<10} | {'Title':<35} | {'URL'}")
    output_lines.append("-" * 120)

    for i, n in enumerate(scored_news[:1]):
        print(f"DEBUG: Keys in document: {list(n.keys())}")
        
    for i, n in enumerate(scored_news[:30]):
        is_target = any(t.lower() in n['title'].lower() for t in targets)
        prefix = ">> " if is_target else "   "
        
        # Calculate components for debugging
        source_weight = rule_based_top10.SOURCE_WEIGHTS.get(n['source'], 5)
        if 'discussion_url' in n and n['discussion_url']:
            source_weight = 9
            
        try:
            pub_date = datetime.fromisoformat(n['date'])
            now = datetime.now(pub_date.tzinfo)
            days_diff = (now - pub_date).days
            date_bonus = 0
            if days_diff <= 0: date_bonus = 10
            elif days_diff <= 1: date_bonus = 4
        except:
            date_bonus = 0
            
        # Recalculate category using the new logic
        sources_config = [] # Mock config, fallback logic doesn't need it for these sources
        category = rule_based_top10.categorize_news(n, sources_config)[:10]
        
        title = n['title'][:30] + "..." if len(n['title']) > 30 else n['title']
        source = n['source'][:15]
        url = n.get('url', '')
        output_lines.append(f"{prefix}{i+1:<3} | {n['score']:<6} | {source:<15} | {category:<10} | {title:<35} | {url}")
    output_lines.append("="*120 + "\n")
    
    with open('debug_output_urls_utf8.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    print("Output written to debug_output_urls_utf8.txt")

if __name__ == "__main__":
    analyze_firestore_scores()
