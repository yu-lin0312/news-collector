import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables before importing modules that depend on them
load_dotenv()

import database
import time
import urllib3
import json
import re
from playwright.sync_api import sync_playwright
import sys
import io
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

# Timezone helper
TAIPEI_TZ = ZoneInfo("Asia/Taipei")

# Force UTF-8 encoding for stdout/stderr on Windows to prevent UnicodeEncodeError
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class NewsCrawler:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.db = database
        self.sources = self.load_sources()
        # Shared Playwright resources
        self._playwright = None
        self._browser = None
        self._context = None
        
        # Auto-install Playwright browsers if needed (for Streamlit Cloud)
        self._check_playwright_install()

    def _check_playwright_install(self):
        """Ensure Playwright browsers are installed."""
        import subprocess
        import sys
        try:
            # Check if we can launch a browser (cheap check)
            # Or just check if the folder exists. 
            # Better: just try to run 'playwright install chromium' if it fails to launch.
            # But we don't want to run it every time.
            # Let's rely on the fact that if _ensure_browser fails, we might need it.
            # Actually, Streamlit Cloud is ephemeral, so we might need to install it on startup.
            # But 'packages.txt' installs system deps, not the python browser binaries.
            # We need to run `playwright install chromium`
            
            # Check a marker file or similar? No, filesystem is ephemeral.
            # Just run it. It returns quickly if already installed.
            print("Checking Playwright browsers...")
            subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
            print("Playwright browsers checked.")
        except Exception as e:
            print(f"ERROR: Failed to install Playwright browsers: {e}")
            print(f"ERROR TYPE: {type(e).__name__}")
            import traceback
            traceback.print_exc()
            print("WARNING: Continuing without Playwright browser check...")

    def _ensure_browser(self):
        """Lazily initialize shared Playwright browser and context."""
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            self._context = self._browser.new_context(
                user_agent=self.headers['User-Agent'],
                viewport={'width': 1920, 'height': 1080},
                ignore_https_errors=True
            )
            self._context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return self._context

    def _get_page(self):
        """Get a new page from shared context."""
        context = self._ensure_browser()
        return context.new_page()

    def close(self):
        """Cleanup Playwright resources."""
        if self._context:
            self._context.close()
            self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

    def load_sources(self):
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'sources.json')
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading sources.json: {e}")
            return []

    def fetch_page(self, url):
        try:
            # Use a session for better persistence
            session = requests.Session()
            response = session.get(url, headers=self.headers, timeout=15, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {repr(e)}")
            return None

    def fetch_with_browser(self, url, wait_selector=None):
        """Fetch page content using shared Playwright browser."""
        print(f"Fetching with Playwright: {url}")
        try:
            page = self._get_page()
            page.goto(url, wait_until='domcontentloaded', timeout=45000)
            
            # Wait for content to load
            # If wait_selector is provided, use it. Otherwise use a default set.
            selector = wait_selector if wait_selector else 'article, .item, .view-mode-teaser, .post_list_item'
            
            try:
                print(f"  Waiting for selector: {selector}")
                page.wait_for_selector(selector, timeout=30000)
            except Exception as e:
                print(f"  Timeout or error waiting for content ({selector}), trying to parse anyway...")
            
            content = page.content()
            page.close()
            return content
        except Exception as e:
            print(f"Playwright error: {e}")
            return None

    # --- Date Normalization Helpers ---
    def _today(self):
        """Return today's date as YYYY-MM-DD in Taipei Time."""
        return datetime.now(TAIPEI_TZ).strftime('%Y-%m-%d')

    def _try_regex_extraction(self, date_str):
        """Try to extract date using regex patterns."""
        patterns = [
            (r'(\d{4}-\d{1,2}-\d{1,2})', '%Y-%m-%d'),    # YYYY-MM-DD
            (r'(\d{4}/\d{1,2}/\d{1,2})', '%Y/%m/%d'),    # YYYY/MM/DD
            (r'(\d{1,2}/\d{1,2}/\d{4})', '%m/%d/%Y'),    # MM/DD/YYYY
            (r'(\d{4})年(\d{1,2})月(\d{1,2})日', '%Y-%m-%d'),  # YYYY年MM月DD日
        ]
        for pattern, fmt in patterns:
            match = re.search(pattern, date_str)
            if match:
                try:
                    return datetime.strptime(match.group(1), fmt).strftime('%Y-%m-%d')
                except ValueError:
                    continue
        return None

    def _try_common_formats(self, date_str):
        """Try common date formats."""
        formats = [
            '%Y-%m-%d',        # 2025-12-31
            '%Y/%m/%d',        # 2025/12/31
            '%m/%d/%Y',        # 12/31/2025
            '%b %d, %Y',       # Dec 31, 2025
            '%B %d, %Y',       # December 31, 2025
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Handle "Thursday 18 Dec 2025" - remove weekday prefix
        clean_date = re.sub(r'^[A-Za-z]+,?\s+', '', date_str)
        for fmt in ['%d %b %Y', '%d %B %Y']:
            try:
                return datetime.strptime(clean_date, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # Handle "December 16" (assume current year)
        try:
            dt = datetime.strptime(date_str, '%B %d')
            return dt.replace(year=datetime.now(TAIPEI_TZ).year).strftime('%Y-%m-%d')
        except ValueError:
            pass
        
        return None

    def _try_relative_time(self, date_str):
        """Handle relative time expressions like '2 hours ago' or '3天前'."""
        try:
            lower = date_str.lower()
            if 'ago' in lower:
                parts = lower.split()
                num = int(parts[0])
                unit = parts[1]
                if 'hour' in unit or 'min' in unit:
                    return self._today()
                elif 'day' in unit:
                    return (datetime.now(TAIPEI_TZ) - timedelta(days=num)).strftime('%Y-%m-%d')
            
            if '小時前' in date_str or '分鐘前' in date_str:
                return self._today()
            if '天前' in date_str:
                num = int(date_str.replace('天前', '').strip())
                return (datetime.now(TAIPEI_TZ) - timedelta(days=num)).strftime('%Y-%m-%d')
        except Exception:
            pass
        return None

    def normalize_date(self, date_str):
        """Parse various date formats and return YYYY-MM-DD."""
        if not date_str:
            return self._today()
        
        date_str = date_str.strip()
        
        # Try strategies in order
        return (
            self._try_regex_extraction(date_str) or
            self._try_common_formats(date_str) or
            self._try_relative_time(date_str) or
            self._today()
        )

    def extract_text(self, element, selector):
        if not element or not selector:
            return ""
            
        # Special selector for self text
        if selector == "SELF":
            return element.get_text(strip=True)
            
        # Handle multiple selectors separated by comma
        for sel in selector.split(','):
            sel = sel.strip()
            found = element.select_one(sel)
            if found:
                text = found.text.strip()
                # Special handling for RSS link tag which might be parsed as void element
                if not text and found.name == 'link' and found.next_sibling:
                    text = str(found.next_sibling).strip()
                return text
        return ""

    def extract_attr(self, element, selector, attr):
        if not element or not selector:
            return ""
        
        if selector == "SELF":
            return element.get(attr, "")
            
        for sel in selector.split(','):
            sel = sel.strip()
            found = element.select_one(sel)
            if found:
                return found.get(attr, "")
        return ""

    def extract_image(self, element, selector):
        if not element or not selector:
            return ""
        
        # Special handling for Inside (style attribute)
        if 'post_list_item_img' in selector:
            found = element.select_one(selector)
            if found and 'style' in found.attrs:
                style = found['style']
                if "url('" in style:
                    return style.split("url('")[1].split("')")[0]
                elif 'url("' in style:
                    return style.split('url("')[1].split('")')[0]
            return ""

        # Try to find a valid image among all matches
        candidates = element.select(selector)
        for img in candidates:
            # Try data-src first
            url = img.get('data-src')
            if not url:
                url = img.get('src')
            
            if not url:
                continue
                
            # Validation
            url_lower = url.lower()
            if any(x in url_lower for x in ['placeholder', 'icon', 'share', 'btn', 'button', 'logo', 'avatar', 'pixel', 'gif']):
                continue
                
            # Skip small images (heuristic)
            if 'width' in img.attrs and img['width'].isdigit() and int(img['width']) < 100:
                continue
                
            return url
            
        return ""

    def get_nested_value(self, data, path):
        """Helper to get value from nested dictionary using dot notation"""
        try:
            if not path or path == "SELF":
                return data
                
            keys = path.split('.')
            value = data
            for key in keys:
                if isinstance(value, list):
                    try:
                        key = int(key)
                        value = value[key]
                    except (ValueError, IndexError):
                        return None
                else:
                    if not isinstance(value, dict):
                        return None
                    value = value.get(key, None)
                
                if value is None:
                    return None
            
            return value
        except Exception:
            return None

    def crawl_json_api(self, source):
        name = source['name']
        url = source['url']
        mapping = source.get('json_mapping', {})
        category = source.get('category', 'Uncategorized')
        
        print(f"Crawling {name} (JSON API)...")
        
        try:
            response = requests.get(url, headers=self.headers, verify=False, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            items = data
            # If items are nested
            if mapping.get('items') and mapping['items'] != 'SELF':
                items = self.get_nested_value(data, mapping['items'])
                
            if not isinstance(items, list):
                print(f"Expected list of items, got {type(items)}")
                return

            print(f"Found {len(items)} items on {name}")
            
            count = 0
            for item in items:
                try:
                    # Extract fields using mapping
                    title = self.get_nested_value(item, mapping['title'])
                    if not title: continue
                    
                    link = self.get_nested_value(item, mapping['link'])
                    if not link: continue
                    
                    if self.db.url_exists(link):
                        continue
                        
                    raw_date = self.get_nested_value(item, mapping['date'])
                    published_at = self.normalize_date(raw_date)
                    
                    # Summary might be HTML, strip it
                    raw_summary = self.get_nested_value(item, mapping['summary'])
                    summary = BeautifulSoup(raw_summary, 'html.parser').get_text(strip=True) if raw_summary else ""
                    
                    # Skip image extraction (not used in UI)
                    image_url = ""
                    
                    print(f"Adding: {title} ({category})")
                    self.db.add_news(title, link, name, category, published_at, summary, image_url)
                    count += 1
                    
                except Exception as e:
                    print(f"Error parsing {name} item: {e}")
                    
            print(f"{name}: Added {count} new items.")
            
        except Exception as e:
            print(f"Error crawling {name}: {e}")


    def crawl_tldr_api(self, source):
        """
        Crawl TLDR Tech API/Page using shared Playwright browser.
        """
        name = source['name']
        print(f"Crawling TLDR API: {source['url']}")
        news_items = []
        
        try:
            page = self._get_page()
            page.goto(source['url'])
            
            # Wait for content to load
            try:
                page.wait_for_selector('article.mt-3', timeout=10000)
            except TimeoutError:
                print("Timeout waiting for articles")
                
            content = page.content()
            page.close()
                
            soup = BeautifulSoup(content, 'html.parser')
            articles = soup.select('article.mt-3')
            print(f"Found {len(articles)} articles")
            
            for article in articles:
                try:
                    title_elem = article.select_one('a.font-bold h3')
                    link_elem = article.select_one('a.font-bold')
                    summary_elem = article.select_one('div.newsletter-html')
                    
                    if title_elem and link_elem:
                        title = title_elem.get_text(strip=True)
                        link = link_elem.get('href')
                        summary = summary_elem.get_text(strip=True) if summary_elem else ""
                        
                        # Filter out sponsors
                        if "(Sponsor)" in title:
                            continue
                            
                        # Clean up title (remove read time)
                        if "(" in title and "read)" in title:
                            title = title.rsplit("(", 1)[0].strip()
                        
                        # Try to extract date from original URL
                        published_at = self._try_extract_date_from_url(link)
                        
                        news_items.append({
                            'source': source['name'],
                            'title': title,
                            'url': link,
                            'summary': summary,
                            'published_at': published_at
                        })
                        print(f"Parsed item: {title} (Date: {published_at})")
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
            
            print(f"{name}: Added {len(news_items)} new items.")
            for item in news_items:
                 self.db.add_news(item['title'], item['url'], item['source'], 'Tech', item['published_at'], item['summary'], "")
                    
        except Exception as e:
            print(f"Error crawling TLDR: {e}")
            
        return news_items
    
    def _extract_date_from_html(self, html, url=""):
        """Extract date from HTML content using BeautifulSoup."""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 1. Look for <time> tag
            time_tag = soup.find('time')
            if time_tag:
                datetime_attr = time_tag.get('datetime')
                if datetime_attr:
                    return self.normalize_date(datetime_attr)
                text = time_tag.get_text(strip=True)
                if text:
                    return self.normalize_date(text)
            
            # 2. Look for meta tags
            meta_published = soup.find('meta', property='article:published_time')
            if meta_published:
                return self.normalize_date(meta_published.get('content'))
            
            meta_date = soup.find('meta', attrs={'name': 'date'})
            if meta_date:
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
                        normalized = self.normalize_date(date_text)
                        if normalized and normalized <= self._today():
                            return normalized
        except Exception as e:
            print(f"Error parsing HTML for date ({url}): {e}")
        return None

    def _try_extract_date_from_url(self, url):
        """
        Try to extract publication date from the original article URL.
        Falls back to Playwright if requests fails.
        """
        print(f"  Extracting date from: {url}")
        
        # 1. Try fast requests first
        try:
            response = requests.get(url, headers=self.headers, timeout=10, verify=False)
            if response.status_code == 200:
                date = self._extract_date_from_html(response.text, url)
                if date and date != self._today():
                    return date
                print(f"    -> Requests returned no date or today's date. Trying Playwright...")
            else:
                print(f"    -> Requests failed ({response.status_code}). Trying Playwright...")
        except Exception as e:
            print(f"    -> Requests error: {e}. Trying Playwright...")

        # 2. Fallback to Playwright
        try:
            html = self.fetch_with_browser(url)
            if html:
                date = self._extract_date_from_html(html, url)
                if date:
                    return date
        except Exception as e:
            print(f"    -> Playwright date extraction error: {e}")
        
        # Fallback to current date
        print("    -> Could not extract date, using today.")
        return self._today()


    def crawl_hackingai(self, source):
        """
        Crawl HackingAI.app
        """
        name = source['name']
        print(f"Crawling {name}...")
        
        # HackingAI loads content dynamically, use Playwright
        # No specific selector needed as it hydrates, but we can wait for .post-title
        html = self.fetch_with_browser(source['url'], wait_selector='.post-title')
        
        if not html:
            print(f"Failed to fetch {name}")
            return

        soup = BeautifulSoup(html, 'html.parser')
        
        # Select all post items (they are in .mb-3 containers)
        # Structure:
        # <div class="mb-3">
        #   <div class="fw-bold" ...>Category</div>
        #   <a class="post-title ..." href="REDDIT_URL">Title</a>
        #   <div class="meta">
        #      DATE ...
        #      <a class="source-link" href="SOURCE_URL">Source</a>
        #   </div>
        # </div>
        
        items = soup.select('div.mb-3')
        print(f"Found {len(items)} items on {name}")
        
        count = 0
        for item in items:
            try:
                # Extract Title & Reddit Link
                title_elem = item.select_one('a.post-title')
                if not title_elem: continue
                
                title = title_elem.get_text(strip=True)
                discussion_url = title_elem.get('href') # This is the Reddit link
                
                # Extract Original Source Link
                source_link_elem = item.select_one('a.source-link')
                if not source_link_elem: continue
                
                source_url = source_link_elem.get('href')
                source_name = source_link_elem.get_text(strip=True)
                
                # Extract Category
                cat_elem = item.select_one('div.fw-bold')
                category = cat_elem.get_text(strip=True) if cat_elem else "全球 AI 趨勢"

                meta_elem = item.select_one('div.meta')
                raw_date = ""
                if meta_elem:
                    # Text is like "2026-01-21 22:07:41 EST ·"
                    raw_date = meta_elem.get_text(strip=True).split('·')[0].strip()
                
                published_at = self.normalize_date(raw_date)
                
                # --- News vs Discussion Logic ---
                is_news = False
                
                # 1. Check if source is image/reddit
                lower_source = source_url.lower()
                is_image = any(x in lower_source for x in ['i.redd.it', 'imgur.com', '.jpg', '.png', '.gif'])
                is_reddit = 'reddit.com' in lower_source
                
                if discussion_url != source_url and not is_image and not is_reddit:
                    is_news = True
                
                # Filter: Only keep News items as per user request
                # Filter: Only keep News items as per user request
                if not is_news:
                    # print(f"Skipping discussion/image: {title}")
                    continue
                    
                # Check if exists
                if self.db.url_exists(source_url):
                    print(f"  -> Skipping existing URL: {source_url}")
                    continue
                    
                print(f"Adding (HackingAI): {title} ({source_name}) | Date: {published_at}")
                # Add to DB with discussion_url
                success = self.db.add_news(title, source_url, source_name, category, published_at, "", "", discussion_url=discussion_url)
                if success:
                    count += 1
                else:
                    print(f"  -> Failed to add to DB: {title}")
                
            except Exception as e:
                print(f"Error parsing HackingAI item: {e}")
                
        print(f"{name}: Added {count} new items.")

    def crawl_source(self, source):
        name = source['name']
        method = source.get('type', 'static')
        
        # Skip link-only sources (blocked by WAF/Cloudflare)
        if source.get('link_only'):
            print(f"Skipping {name} (link-only)")
            return
        
        if method == 'json_api':
            self.crawl_json_api(source)
            return

        if method == 'tldr_api':
            self.crawl_tldr_api(source)
            return

        if method == 'hackingai':
            self.crawl_hackingai(source)
            return

        url = source['url']
        
        print(f"Crawling {name}...")
        
        if method == 'dynamic':
            # Use the container selector as the wait_selector for better reliability
            wait_sel = None
            if 'selectors' in source and 'container' in source['selectors']:
                wait_sel = source['selectors']['container'].split(',')[0].strip()
            html = self.fetch_with_browser(url, wait_selector=wait_sel)
        else:
            html = self.fetch_page(url)
            
        if not html:
            print(f"Failed to fetch {name}")
            return

        # Detect RSS/XML
        is_rss = 'rss' in url.lower() or 'feed' in url.lower() or 'xml' in url.lower()
        parser = 'xml' if is_rss else 'html.parser'
        soup = BeautifulSoup(html, parser)
        
        # Handle JSON Embedded
        if source.get('json_embedded'):
            print(f"Extracting embedded JSON for {name}...")
            script = soup.find('script', id='__NEXT_DATA__')
            
            data = None
            if script:
                try:
                    data = json.loads(script.text)
                except Exception as e:
                    print(f"Error parsing __NEXT_DATA__ for {name}: {e}")
            
            # Try Inertia.js
            if not data:
                app_div = soup.find('div', id='app')
                if app_div and app_div.get('data-page'):
                    try:
                        data = json.loads(app_div.get('data-page'))
                    except Exception as e:
                        print(f"Error parsing Inertia.js data for {name}: {e}")
            
            # Try other JSON scripts
            if not data:
                scripts = soup.find_all('script', type='application/json')
                for s in scripts:
                    try:
                        data = json.loads(s.text)
                        break
                    except:
                        continue
            
            if data:
                try:
                    items = self.get_nested_value(data, source.get('json_path', ''))
                    if not isinstance(items, list):
                        print(f"Expected list of items in JSON, got {type(items)}")
                        return
                    
                    print(f"Found {len(items)} items in embedded JSON for {name}")
                    mapping = source.get('json_mapping', {})
                    count = 0
                    for item in items:
                        try:
                            title = str(self.get_nested_value(item, mapping.get('title', '')) or "")
                            if not title: continue
                            
                            link = str(self.get_nested_value(item, mapping.get('link', '')) or "")
                            if not link: continue
                            
                            # Handle relative links
                            if not link.startswith('http'):
                                if name == 'Wevolver':
                                    link = f"https://www.wevolver.com/article/{link}"
                                elif name == 'AI Policy Tracker':
                                    link = f"https://aipolicytracker.org/news/{link}"
                                else:
                                    base_url = '/'.join(url.split('/')[:3])
                                    if link.startswith('/'):
                                        link = base_url + link
                                    else:
                                        link = base_url + '/' + link

                            if self.db.url_exists(link):
                                continue
                            
                            raw_date = str(self.get_nested_value(item, mapping.get('date', '')) or "")
                            published_at = self.normalize_date(raw_date)
                            
                            
                            summary = str(self.get_nested_value(item, mapping.get('summary', '')) or "")
                            
                            # Skip image extraction (not used in UI)
                            image_url = ""
                            
                            category = source.get('category', 'Uncategorized')
                            print(f"Adding (JSON): {title} ({category})")
                            self.db.add_news(title, link, name, category, published_at, summary, image_url)
                            count += 1
                        except Exception as e:
                            print(f"Error parsing {name} JSON item: {e}")
                    
                    print(f"{name}: Added {count} new items.")
                    return
                except Exception as e:
                    print(f"Error extracting data from JSON for {name}: {e}")

        # Fallback to CSS selectors
        selectors = source.get('selectors', {})
        if not selectors or 'container' not in selectors:
            print(f"No selectors found for {name}")
            return

        # Handle multiple container selectors
        items = []
        for sel in selectors['container'].split(','):
            sel = sel.strip()
            found_items = soup.select(sel)
            if found_items:
                items = found_items
                break
        
        print(f"Found {len(items)} items on {name}")
        
        count = 0
        for item in items:
            try:
                # Extract Title
                title = self.extract_text(item, selectors['title'])
                if not title: 
                    print(f"  -> Skip: No title found")
                    continue
                
                # Extract Link
                link_attr = selectors.get('link_attr', 'href')
                if link_attr == 'TEXT':
                    link = self.extract_text(item, selectors['link'])
                else:
                    link = self.extract_attr(item, selectors['link'], link_attr)
                
                if not link: 
                    print(f"  -> Skip: No link found for '{title}'")
                    continue
                
                # Handle relative links
                if not link.startswith('http'):
                    base_url = '/'.join(url.split('/')[:3]) # https://example.com
                    if link.startswith('/'):
                        link = base_url + link
                    else:
                        # Handle cases like BusinessNext where base might be needed
                        if 'bnext.com.tw' in url:
                            link = "https://www.bnext.com.tw" + link
                        else:
                            link = base_url + '/' + link

                if self.db.url_exists(link):
                    # print(f"  -> Skip: URL exists: {link}")
                    continue
                
                # Extract Date
                raw_date = ""
                if selectors.get('date'):
                    # Special handling for BusinessNext nested span
                    if name == 'BusinessNext':
                        meta_div = item.select_one(selectors['date'].split('span')[0]) # Get parent
                        if meta_div:
                            spans = meta_div.select('span')
                            if spans:
                                raw_date = spans[-1].text.strip()
                    else:
                        raw_date = self.extract_text(item, selectors['date'])
                
                published_at = self.normalize_date(raw_date)
                
                # Extract Summary
                summary = self.extract_text(item, selectors['summary'])
                
                # Special handling for Google News source extraction
                real_source_name = name
                # 處理所有 Google News 變體 (AI, Gemini AI, ChatGPT, 人工智慧等)
                if "Google News" in name or "google news" in name.lower():
                    try:
                        # For RSS, source is often in a specific tag or part of title/description
                        # In Google News RSS, it's often at the end of the title: "Title - Source"
                        if " - " in title:
                            parts = title.rsplit(" - ", 1)
                            if len(parts) > 1:
                                real_source_name = parts[1].strip()
                                title = parts[0].strip() # Clean title
                        
                        # Fallback to description font tag if title split fails or to be sure
                        description_elem = item.select_one('description')
                        if description_elem:
                            desc_html = description_elem.get_text()
                            desc_soup = BeautifulSoup(desc_html, 'html.parser')
                            font_elem = desc_soup.find('font', color='#6f6f6f')
                            if font_elem:
                                real_source_name = font_elem.get_text(strip=True)
                    except Exception as e:
                        print(f"Error extracting Google News source: {e}")


                # Skip image extraction (not used in UI)
                image_url = ""
                
                # Get Category
                category = source.get('category', 'Uncategorized')
                
                print(f"Adding: {title} ({real_source_name}) | Date: {published_at}")
                self.db.add_news(title, link, real_source_name, category, published_at, summary, image_url)
                count += 1
                
            except Exception as e:
                print(f"Error parsing {name} item: {repr(e)}")
        
        print(f"{name}: Added {count} new items.")

    def run(self):
        database.init_db()
        print(f"Starting crawl for {len(self.sources)} sources...")
        
        try:
            for source in self.sources:
                try:
                    self.crawl_source(source)
                except Exception as e:
                    print(f"Error crawling {source['name']}: {repr(e)}")
        finally:
            self.close()  # Ensure Playwright resources are cleaned up
        
        print("Crawl finished.")

if __name__ == "__main__":
    import sys
    import traceback
    
    try:
        crawler = NewsCrawler()
        crawler.run()
    except Exception as e:
        print(f"CRITICAL CRAWLER ERROR: {e}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
