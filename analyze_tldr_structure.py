from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

def analyze_tldr():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Navigating to TLDR AI...")
        page.goto('https://tldr.tech/ai', wait_until='domcontentloaded')
        
        # Wait for articles to load
        try:
            page.wait_for_selector('article.mt-3', timeout=10000)
        except:
            print("Timeout waiting for articles")
        
        content = page.content()
        browser.close()
        
        # Parse with BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        articles = soup.select('article.mt-3')
        
        print(f"Found {len(articles)} articles\n")
        
        # Analyze first article structure
        if articles:
            first = articles[0]
            print("First article HTML structure:")
            print("=" * 80)
            print(first.prettify()[:2000])
            print("\n" + "=" * 80)
            
            # Look for date-related elements
            print("\nSearching for date elements...")
            date_candidates = first.find_all(['time', 'span', 'div'], class_=lambda x: x and ('date' in x.lower() or 'time' in x.lower()))
            if date_candidates:
                print(f"Found {len(date_candidates)} potential date elements:")
                for elem in date_candidates:
                    print(f"  - {elem.name}.{elem.get('class')}: {elem.get_text(strip=True)}")
            else:
                print("No obvious date elements found")
                
                # Check all text in the article
                print("\nAll text content in first article:")
                print(first.get_text()[:500])

if __name__ == "__main__":
    analyze_tldr()
