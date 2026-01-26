import os
os.environ['USE_FIRESTORE'] = 'True'

from crawler import NewsCrawler
import json

# Load sources
with open('sources.json', 'r', encoding='utf-8') as f:
    sources = json.load(f)

# Find HackingAI source
hackingai_source = next((s for s in sources if s['name'] == 'HackingAI'), None)

if not hackingai_source:
    print("ERROR: HackingAI not found in sources.json")
else:
    print(f"Found HackingAI source: {hackingai_source}")
    print("\nTesting HackingAI crawl to Firestore...")
    
    crawler = NewsCrawler()
    try:
        crawler.crawl_hackingai(hackingai_source)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        crawler.close()
