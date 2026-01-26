import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
from playwright.sync_api import sync_playwright

# Mock the crawler's date extraction logic for testing
class DateTester:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        }

    def _today(self):
        return datetime.now().strftime('%Y-%m-%d')

    def normalize_date(self, date_str):
        # Simplified version of crawler.normalize_date for testing
        if not date_str: return None
        print(f"    [Normalize] Trying to normalize: '{date_str}'")
        try:
            # Try basic parsing
            from dateutil import parser
            dt = parser.parse(date_str, fuzzy=True)
            return dt.strftime('%Y-%m-%d')
        except:
            return None

    def _try_extract_date_from_url(self, url):
        print(f"  Testing URL: {url}")
        try:
            # Fetch the original article
            print("    [Requests] Fetching...")
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            print(f"    [Requests] Status: {response.status_code}")
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 1. Look for <time> tag
                time_tag = soup.find('time')
                if time_tag:
                    datetime_attr = time_tag.get('datetime')
                    if datetime_attr:
                        print(f"    [Success] Found <time datetime='{datetime_attr}'>")
                        return self.normalize_date(datetime_attr)
                    text = time_tag.get_text(strip=True)
                    if text:
                        print(f"    [Success] Found <time>{text}</time>")
                        return self.normalize_date(text)
                
                # 2. Look for meta tags
                meta_published = soup.find('meta', property='article:published_time')
                if meta_published:
                    print(f"    [Success] Found meta article:published_time='{meta_published.get('content')}'")
                    return self.normalize_date(meta_published.get('content'))
                
                meta_date = soup.find('meta', attrs={'name': 'date'})
                if meta_date:
                    print(f"    [Success] Found meta date='{meta_date.get('content')}'")
                    return self.normalize_date(meta_date.get('content'))
                
                # 3. Look for common date classes
                date_selectors = [
                    '.published-date', '.post-date', '.entry-date', 
                    '.article-date', '[class*="date"]', '[class*="time"]'
                ]
                for selector in date_selectors:
                    date_elem = soup.select_one(selector)
                    if date_elem:
                        date_text = date_elem.get_text(strip=True)
                        if date_text:
                            print(f"    [Success] Found selector '{selector}': '{date_text}'")
                            return self.normalize_date(date_text)
            else:
                print("    [Fail] Non-200 status code")

        except Exception as e:
            print(f"    [Error] {e}")
        
        print("    [Fail] Could not extract date, falling back to None")
        return None

def run_test():
    tester = DateTester()
    
    # Hardcoded list of typical AI news URLs to test date extraction
    links = [
        "https://www.anthropic.com/news/claude-3-5-sonnet",
        "https://openai.com/index/sora/",
        "https://techcrunch.com/2024/02/15/openai-launches-sora-a-text-to-video-generation-model/",
        "https://www.theverge.com/2024/2/15/24074151/openai-sora-text-to-video-ai-model",
        "https://simonwillison.net/2024/Feb/15/sora/"
    ]

    print(f"Testing {len(links)} hardcoded links...")
    
    for link in links:
        print("-" * 50)
        date = tester._try_extract_date_from_url(link)
        print(f"Result: {date}")

if __name__ == "__main__":
    run_test()
