from crawler import NewsCrawler
import sys
import io

# Force UTF-8
# Force UTF-8 removed

def test_reddit():
    crawler = NewsCrawler()
    url = "https://www.reddit.com/r/robotics/comments/1qjj2em/will_there_be_a_need_for_those_with_a_cs/"
    print(f"Fetching {url}...")
    html = crawler.fetch_with_browser(url)
    
    if html:
        print("Successfully fetched Reddit page.")
        with open("reddit_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Saved to reddit_dump.html")
    else:
        print("Failed to fetch Reddit page.")
    
    crawler.close()

if __name__ == "__main__":
    test_reddit()
