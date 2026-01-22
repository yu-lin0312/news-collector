from playwright.sync_api import sync_playwright
import time
import sys
import io

# Force UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

def fetch_html():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        print("Navigating to HackingAI...")
        page.goto("https://hackingai.app/", wait_until="domcontentloaded")
        time.sleep(5) # Wait for hydration
        html = page.content()
        browser.close()
        return html

try:
    html = fetch_html()
    with open("hackingai_dump.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Successfully saved HTML to hackingai_dump.html")
except Exception as e:
    print(f"Error: {e}")
