import rule_based_top10
import database_firestore as fs
from datetime import datetime

def analyze_image_news_scores():
    db = fs.get_db()
    if not db:
        print("Failed to connect to Firestore.")
        return

    today_str = "2026-01-23"
    docs = db.collection('news').where('published_at', '>=', today_str).where('published_at', '<=', f"{today_str}T23:59:59").stream()
    
    scored_news = []
    for doc in docs:
        d = doc.to_dict()
        score = rule_based_top10.calculate_score(d)
        scored_news.append({
            'title': d.get('title'),
            'source': d.get('source'),
            'score': score
        })
    
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
    
    print("\n" + "="*80)
    print(f"{'Rank':<5} | {'Score':<6} | {'Source':<20} | {'Title'}")
    print("-" * 80)
    
    for i, n in enumerate(scored_news):
        title = n['title']
        if any(t.lower() in title.lower() for t in targets):
            print(f"{i+1:<5} | {n['score']:<6} | {n['source']:<20} | {title[:50]}...")
    print("="*80 + "\n")

if __name__ == "__main__":
    analyze_image_news_scores()
