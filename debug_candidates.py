import rule_based_top10
import database
import json

def check_candidates():
    database.init_db()
    print("Getting Top 12 candidates from rule_based_top10...")
    
    # Mock sources config since we might not load it exactly the same way
    try:
        with open('sources.json', 'r', encoding='utf-8') as f:
            sources_config = json.load(f)
    except:
        sources_config = []

    candidates = rule_based_top10.get_top10_candidates(limit=12)
    
    print("\n" + "="*80)
    print(f"{'Rank':<5} | {'Score':<6} | {'Source':<20} | {'Category':<15} | {'Title'}")
    print("-" * 80)
    
    for i, n in enumerate(candidates):
        title = n['title'][:50] + "..." if len(n['title']) > 50 else n['title']
        source = n['source'][:20]
        # Category might be calculated inside get_top10_candidates or passed through
        # rule_based_top10.py calculates it before returning
        category = n.get('top10_category', 'Unknown')[:15]
        print(f"{i+1:<5} | {n['score']:<6} | {source:<20} | {category:<15} | {title}")
    print("="*80 + "\n")

if __name__ == "__main__":
    check_candidates()
