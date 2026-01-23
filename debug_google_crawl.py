from crawler import NewsCrawler
import json

def debug_crawl():
    crawler = NewsCrawler()
    # Find Google News (AI) source
    google_source = next((s for s in crawler.sources if s['name'] == "Google News (AI)"), None)
    
    if google_source:
        print(f"Debugging crawl for: {google_source['name']}")
        crawler.crawl_source(google_source)
    else:
        print("Google News (AI) source not found in sources.json")
    
    crawler.close()

if __name__ == "__main__":
    debug_crawl()
