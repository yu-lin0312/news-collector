import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import time

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def get_playwright_manager():
    # Mock manager for standalone script
    class Manager:
        def get_page(self):
            self.p = sync_playwright().start()
            self.browser = self.p.chromium.launch(headless=True)
            return self.browser.new_page()
        def close(self):
            self.browser.close()
            self.p.stop()
    return Manager()

def fetch_article_content(url):
    print(f"Fetching: {url}")
    
    # 1. Try requests first
    try:
        print("Trying Requests...")
        response = requests.get(url, headers=HEADERS, timeout=10, verify=False, allow_redirects=True)
        print(f"Requests Status: {response.status_code}")
        print(f"Final URL: {response.url}")
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text = soup.get_text(separator='\n', strip=True)
            print(f"Requests Content Length: {len(text)}")
            if len(text) > 500:
                return text, "Success (Requests)"
            else:
                print("Content too short (Requests)")
    except Exception as e:
        print(f"Requests Error: {e}")

    # 2. Fallback to Playwright
    print("Trying Playwright...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=30000)
                
                # Wait for redirect if it's google news
                if "news.google.com" in url:
                    print("Waiting for Google News redirect...")
                    page.wait_for_timeout(5000)
                
                content = page.content()
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator='\n', strip=True)
                print(f"Playwright Content Length: {len(text)}")
                
                if len(text) > 500:
                    return text, "Success (Playwright)"
                else:
                    return None, "Content too short (Playwright)"
            finally:
                browser.close()
    except Exception as e:
        return None, f"Playwright Error: {e}"

def test_fetch():
    urls = [
        "https://news.google.com/rss/articles/CBMijgFBVV95cUxPTFUtVlgyZUpSeXlTT3drVE1WYjFWMGhad0V5ZkZ3bFJjZTdFWWVodVpLUEFxT18teUc4ME9YamJacjYxdGs1RU1QODhZdVctZ05RZFNJQUNjRVlkM3JzWEJRcGJjWm5lWUkyVFFsS0RiVXZTUjkzX21sSnNPUkJhdHhnVWV2Wk5EVVhuLTV3?oc=5",
        "https://www.inside.com.tw/article/40548-baidu-ernie-assistant-reaches-200m-users"
    ]
    
    for url in urls:
        print("\n" + "-"*50)
        content, status = fetch_article_content(url)
        print(f"Result: {status}")
        if content:
            print(f"Preview: {content[:200]}...")
        print("-"*50)

if __name__ == "__main__":
    test_fetch()
