import rule_based_top10
import database
import json
from datetime import datetime

def generate_historical_data():
    database.init_db()
    
    # 1. Generate for Today (Jan 16) - Real Data
    print("Generating for Jan 16...")
    rule_based_top10.generate_rule_based_top10('2026-01-16')
    
    # 2. Generate for Yesterday (Jan 15) - Mock Data (since DB is empty for 15th)
    print("Generating for Jan 15 (Mock)...")
    
    # Create a mock result structure
    mock_15th = {
        "date": "2026-01-15",
        "generated_at": "2026-01-15 18:00:00",
        "top10": [],
        "news_count": 10,
        "analysis_stats": {"Technology": 10},
        "method": "mock"
    }
    
    # Populate with some mock items
    for i in range(1, 11):
        mock_15th['top10'].append({
            "rank": i,
            "title": f"Historical News Item #{i} from Jan 15",
            "url": "https://example.com",
            "source": "Mock Source",
            "published_at": "2026-01-15 10:00:00",
            "top10_category": "Technology",
            "score": 10 - i,
            "image_url": "https://via.placeholder.com/800x400/333/fff?text=Jan+15+Briefing",
            "ai_rundown": "This is a historical summary for Jan 15.",
            "ai_details": "- Detail 1\n- Detail 2",
            "ai_impact": "Impact analysis for Jan 15."
        })
        
    with open('top10_2026-01-15.json', 'w', encoding='utf-8') as f:
        json.dump(mock_15th, f, ensure_ascii=False, indent=2)
    print("Saved mock Top 10 to top10_2026-01-15.json")

if __name__ == "__main__":
    generate_historical_data()
