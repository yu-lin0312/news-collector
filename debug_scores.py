import rule_based_top10
import database
from datetime import datetime

def analyze_scores():
    database.init_db()
    # 獲取最近 7 天的新聞
    news = rule_based_top10.get_recent_news()
    
    scored_news = []
    for n in news:
        score = rule_based_top10.calculate_score(n)
        scored_news.append({
            'title': n.get('title', 'No Title'),
            'source': n.get('source', 'Unknown'),
            'score': score,
            'date': n.get('published_at', 'Unknown')
        })
    
    # 按分數排序
    scored_news.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "="*50)
    print(f"{'Rank':<5} | {'Score':<6} | {'Source':<20} | {'Title'}")
    print("-" * 80)
    
    for i, n in enumerate(scored_news[:20]):
        title = n['title'][:60] + "..." if len(n['title']) > 60 else n['title']
        source = n['source'][:20]
        print(f"{i+1:<5} | {n['score']:<6} | {source:<20} | {title}")
    print("="*50 + "\n")

if __name__ == "__main__":
    analyze_scores()
