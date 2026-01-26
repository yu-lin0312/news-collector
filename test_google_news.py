import requests
from playwright.sync_api import sync_playwright

url = "https://news.google.com/rss/search?q=artificial+intelligence&hl=zh-TW&gl=TW&ceid=TW:zh-hant"
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

def test_requests():
    print(f"Testing requests for {url}...")
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print(f"Content length: {len(response.text)}")
            print(f"Start of content: {response.text[:200]}")
        else:
            print("Failed to fetch via requests.")
    except Exception as e:
        print(f"Requests error: {e}")

def test_playwright():
    print(f"\nTesting Playwright for {url}...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            response = page.goto(url)
            print(f"Status: {response.status()}")
            content = page.content()
            print(f"Content length: {len(content)}")
            print(f"Start of content: {content[:200]}")
        except Exception as e:
            print(f"Playwright error: {e}")
        browser.close()

if __name__ == "__main__":
    test_requests()
    test_playwright()
