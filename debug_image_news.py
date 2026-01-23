import rule_based_top10
import database
from datetime import datetime

def analyze_specific_news():
    database.init_db()
    news_list = database.get_all_news()
    
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
    print(f"{'Source':<20} | {'Score':<6} | {'Title'}")
    print("-" * 80)
    
    found_count = 0
    for item in news_list:
        # Convert sqlite3.Row to dict
        item_dict = dict(item)
        title = item_dict.get('title', '')
        if any(t.lower() in title.lower() for t in targets):
            score = rule_based_top10.calculate_score(item_dict)
            short_title = title[:50] + "..." if len(title) > 50 else title
            print(f"{item_dict.get('source', 'Unknown'):<20} | {score:<6} | {short_title}")
            found_count += 1
            
    if found_count == 0:
        print("No matching news items found in database.")
    print("="*80 + "\n")

if __name__ == "__main__":
    analyze_specific_news()
