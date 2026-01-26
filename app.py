import streamlit as st
import os
import json
from dotenv import load_dotenv

# Inject Streamlit secrets into environment variables for subprocesses and main app
def load_secrets_to_env():
    """
    Load secrets from streamlit.secrets into os.environ so that subprocesses
    (like crawler.py and deep_analyzer.py) and the main app can access them.
    """
    def get_secret(key):
        if key in st.secrets:
            return st.secrets[key]
        elif "general" in st.secrets and key in st.secrets["general"]:
            return st.secrets["general"][key]
        return None
    
    # 1. GOOGLE_API_KEY
    api_key = get_secret("GOOGLE_API_KEY")
    if api_key:
        os.environ["GOOGLE_API_KEY"] = api_key

    # 2. FIREBASE_CREDENTIALS
    creds = get_secret("FIREBASE_CREDENTIALS")
    if creds:
        if isinstance(creds, dict):
            os.environ["FIREBASE_CREDENTIALS"] = json.dumps(dict(creds))
        else:
            os.environ["FIREBASE_CREDENTIALS"] = str(creds)

    # 3. USE_FIRESTORE
    use_firestore = get_secret("USE_FIRESTORE")
    if use_firestore:
        os.environ["USE_FIRESTORE"] = use_firestore

load_secrets_to_env()

# Load .env file (Local overrides)
# This must run AFTER load_secrets_to_env to allow local .env to override cloud secrets
load_dotenv(override=True)

import database
import pandas as pd
from datetime import datetime, timedelta
import time


# Page config
st.set_page_config(
    page_title="AI News Radar",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed"  # Hide sidebar by default
)

# Load CSS
def load_css():
    css_path = os.path.join('assets', 'style.css')
    if os.path.exists(css_path):
        with open(css_path, encoding='utf-8') as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()

# Load sources config
def load_sources_config():
    try:
        with open('sources.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading sources.json: {e}")
        return []

sources_config = load_sources_config()

# Build category list for filter buttons
categories = list(set(s.get('category', '其他') for s in sources_config))
categories.sort()

# Check for Firestore errors
if hasattr(database, 'FIRESTORE_IMPORT_ERROR') and database.FIRESTORE_IMPORT_ERROR:
    st.warning(f"⚠️ Firestore 連線失敗，已切換至本地模式 (SQLite)。錯誤訊息: {database.FIRESTORE_IMPORT_ERROR}")
    st.info("請檢查 Secrets 設定中的 FIREBASE_CREDENTIALS 是否正確。")


# ========== HEADER ==========
# st.title("📡 AI News Radar")

# ========== TOP 10 SECTION ==========
import rule_based_top10
import glob

# ========== MINIMALIST SINGLE-LAYER FEED ==========
# Inject CSS with Minimalist design principles
# Find all available briefing files via DB
briefing_dates = database.list_briefings()
# briefing_files = sorted(glob.glob("top10_*.json"), reverse=True)
# # Exclude cache files
# briefing_files = [f for f in briefing_files if 'cache' not in f]

# Check if today's briefing exists
today_str = datetime.now().strftime('%Y-%m-%d')
today_file = f"top10_{today_str}.json"

# Stealth Popover - Looks like a header, but opens control panel on click
with st.popover("📅 每日新聞", help="點擊管理簡報"):
    st.markdown("#### 🛠️ 簡報控制台")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    today_file = f"top10_{today_str}.json"
    
    # Check if we have news for today in DB
    today_news_count = database.get_today_news_count()
    has_news = today_news_count > 0
    
    # Determine default behavior
    if today_str not in briefing_dates:
        if has_news:
            default_skip_crawl = True
            st.caption(f"📊 資料庫已有 {today_news_count} 則今日新聞")
        else:
            default_skip_crawl = False
            st.caption("⚠️ 資料庫尚無今日新聞，將自動爬取")
    else:
        default_skip_crawl = True
        st.caption("✅ 今日簡報已存在，點擊可重新生成")
    
    if st.button("🚀 開始生成", use_container_width=True):
        # Terminal Container
        term_container = st.empty()
        
        def update_terminal(lines, show_cursor=True):
            content_lines = ""
            for line in lines:
                content_lines += f'<div class="terminal-line"><span class="terminal-prompt">➜</span><span>{line}</span></div>'
            
            cursor_html = '<span class="terminal-cursor"></span>' if show_cursor else ''
            
            html = f'''
            <div class="terminal-window">
                <div class="terminal-header">
                    <div class="terminal-dots">
                        <div class="terminal-dot dot-red"></div>
                        <div class="terminal-dot dot-yellow"></div>
                        <div class="terminal-dot dot-green"></div>
                    </div>
                    <span>BRIEFING_GENERATOR_v2.1</span>
                </div>
                <div class="terminal-content">
                    {content_lines}
                    {cursor_html}
                </div>
            </div>
            '''
            term_container.markdown(html, unsafe_allow_html=True)
            time.sleep(0.3)
        
        try:
            logs = []
            logs.append("Initializing system...")
            update_terminal(logs)
            time.sleep(0.5)
            
            logs.append("Authenticating user... [OK]")
            update_terminal(logs)
            
            # Step 1: Crawl (Always force crawl when manually triggered)
            if True: # Always run crawl sequence when button is clicked
                logs.append("Checking environment variables...")
                
                # DEBUG: Check what secrets are actually loaded
                has_key = "GOOGLE_API_KEY" in st.secrets or ("general" in st.secrets and "GOOGLE_API_KEY" in st.secrets["general"])
                if has_key:
                    logs.append("DEBUG: GOOGLE_API_KEY found in st.secrets")
                else:
                    logs.append("DEBUG: GOOGLE_API_KEY NOT found in st.secrets")
                    
                api_key = os.environ.get("GOOGLE_API_KEY")
                if api_key:
                    logs.append(f"API Key found in env: {api_key[:5]}... (masked)")
                else:
                    logs.append("WARNING: GOOGLE_API_KEY not found in env!")
                update_terminal(logs)
                
                logs.append("Starting crawler subsystem...")
                update_terminal(logs)
                
                # Get initial count
                initial_count = database.get_today_news_count()
                logs.append(f"Initial news count: {initial_count}")
                update_terminal(logs)

                logs.append("Targeting global AI news sources...")
                update_terminal(logs)
                
                import subprocess
                import sys
                result = subprocess.run([sys.executable, "crawler.py"], capture_output=True, text=True, encoding='utf-8')
                
                # Show crawler output in logs
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            logs.append(f"CRAWLER: {line[:100]}")  # Truncate long lines
                    update_terminal(logs)
                
                if result.returncode != 0:
                    logs.append(f"ERROR: Crawler failed with code {result.returncode}")
                    logs.append("Aborting sequence.")
                    update_terminal(logs, show_cursor=False)
                    
                    error_msg = result.stderr if result.stderr else result.stdout
                    st.error(f"爬蟲錯誤: {error_msg}")
                    st.stop()
                else:
                    # Wait for Firestore writes to complete (async write latency)
                    logs.append("Waiting for database sync...")
                    update_terminal(logs)
                    time.sleep(2)
                    
                    # Get final count
                    final_count = database.get_today_news_count()
                    new_items = final_count - initial_count
                    
                    logs.append("Crawler finished successfully. [OK]")
                    logs.append(f"Data ingestion complete. New items: {new_items}")
                    update_terminal(logs)
                    
                    if new_items == 0:
                        logs.append("WARNING: No new items found.")
                        update_terminal(logs)
                        st.warning("⚠️ 本次爬蟲未抓取到任何新新聞 (新增數: 0)")
                        with st.expander("❓ 為什麼抓不到新聞？(點擊查看排除方法)"):
                            st.markdown("""
                            **可能原因與解決方法：**
                            1. **資料庫已有最新資料**：今天的新聞可能已經抓過了。
                            2. **網路連線問題**：伺服器可能無法連線到新聞網站。
                            3. **網站阻擋 (WAF)**：新聞來源可能阻擋了爬蟲 (如 Cloudflare)。
                            4. **來源網站未更新**：目標網站今天可能還沒發布新文章。
                            
                            **建議操作：**
                            - 檢查 `debug_log.txt` 查看詳細錯誤。
                            - 稍後再試。
                            """)
                    else:
                        st.success(f"✅ 成功抓取 {new_items} 則新新聞！")
            else:
                logs.append("Database check: Found existing records.")
                logs.append("Skipping crawler sequence. [SKIP]")
                update_terminal(logs)
            
            # Step 2: Analyze & Generate
            logs.append("Initializing AI Core (Deep Analyzer)...")
            update_terminal(logs)
            
            import deep_analyzer
            import rule_based_top10
            import importlib
            importlib.reload(rule_based_top10)
            importlib.reload(deep_analyzer)
            
            logs.append("AI Agent: Analyzing content relevance...")
            update_terminal(logs)
            
            # Capture stdout/stderr from deep_analyzer to show in UI
            import io
            import contextlib
            
            output_capture = io.StringIO()
            result = None
            
            try:
                with contextlib.redirect_stdout(output_capture), contextlib.redirect_stderr(output_capture):
                    result = deep_analyzer.generate_deep_top10()
            except Exception as e:
                output_capture.write(f"\nEXCEPTION in deep_analyzer: {e}")
            
            # Process captured logs
            captured_logs = output_capture.getvalue().split('\n')
            for line in captured_logs:
                if line.strip():
                    logs.append(f"DA: {line}")
            
            update_terminal(logs)
            
            if not result or not result.get('top10'):
                logs.append("CRITICAL: Generation produced 0 items.")
                update_terminal(logs, show_cursor=False)
                st.error("⚠️ 生成結果為空！上方終端機已顯示詳細日誌 (DA: 開頭)。請檢查是否有 'Found 0 candidates' 或其他錯誤訊息。")
                st.stop()
            
            logs.append(f"Success: Generated {len(result['top10'])} items.")
            logs.append("Generating briefing artifacts...")
            update_terminal(logs)
            
            logs.append("Sequence complete. System ready.")
            update_terminal(logs, show_cursor=False)
            
            time.sleep(1)
            st.rerun()
        except Exception as e:
            logs.append(f"CRITICAL ERROR: {str(e)}")
            update_terminal(logs, show_cursor=False)
            st.error(f"發生錯誤: {e}")

if not briefing_dates:
    st.info("尚無每日簡報資料。請先點擊上方「📅 每日新聞」按鈕，再點擊「🚀 開始生成」來產生第一期簡報。")
else:
    
    # Iterate through dates to find the first valid briefing
    found_valid_briefing = False
    file_date = None
    top10_list = []
    
    for date_str in briefing_dates:
        try:
            data = database.get_briefing(date_str)
            if data and data.get('top10'):
                top10_list = [item for item in data.get('top10', []) if item is not None]
                if top10_list: # Ensure list is not empty
                    file_date = date_str
                    found_valid_briefing = True
                    break
        except Exception as e:
            print(f"Error checking briefing for {date_str}: {e}")
            continue
            
    if not found_valid_briefing:
        st.info("尚無可用的每日簡報資料。請先點擊上方「📅 每日新聞」按鈕，再點擊「🚀 開始生成」來產生第一期簡報。")
    else:
        # Check if the displayed news is from today
        today_str = datetime.now().strftime('%Y-%m-%d')
        if file_date != today_str:
            st.warning(f"⚠️ 尚未生成今日 ({today_str}) 的新聞，目前顯示 {file_date} 的內容。")
        
        # Display Date Header
        st.markdown(f"### {file_date} 新聞AI摘要")
        st.markdown("---")
        
        # 5x2 Grid Layout
        html_cards = []
        html_cards.append('<div class="news-grid-responsive">')
        
        for i, item in enumerate(top10_list[:10]): # Ensure max 10
            rank = i + 1
            title = item.get('title', 'No Title')
            source = item.get('source', 'Unknown')
            url = item.get('url', '#')
            rundown = item.get('ai_rundown', '尚無摘要')
            
            # 分類標籤對應的顯示名稱和 CSS class
            CATEGORY_DISPLAY = {
                'Breaking': ('Breaking', 'tag-breaking'),
                'Tools': ('Tools', 'tag-tools'),
                'Business': ('Business', 'tag-business'),
                'Creative': ('Creative', 'tag-creative'),
                'Research': ('Research', 'tag-research'),
                'Rules': ('Rules', 'tag-rules'),
                'Risk': ('Risk', 'tag-risk'),
            }
            
            ai_category = item.get('ai_category', '')
            category_name, category_class = CATEGORY_DISPLAY.get(ai_category, ('', ''))
            
            # 只在有分類時顯示標籤
            category_tag = f'<span class="news-category-tag {category_class}">{category_name}</span>' if category_name else ''
            
            card_html = f'''
<div class="news-card-text-only">
<div class="card-rank">#{rank:02d}</div>
<a href="{url}" target="_blank" class="card-title">{title}</a>
<div class="card-meta">
<span class="news-source">{source}</span>
{category_tag}
</div>
<div class="card-summary">
{rundown}
</div>
</div>
'''
            html_cards.append(card_html)
        
        html_cards.append('</div>')
        
        st.markdown("".join(html_cards), unsafe_allow_html=True)
            



# ========== NEWS FEED SECTION ==========
# ========== NEWS FEED SECTION (HIDDEN) ==========
# st.markdown("---")
# 
# col_feed_title, col_actions = st.columns([3, 1])
# with col_feed_title:
#     st.subheader("📰 完整新聞列表")
# 
# with col_actions:
#     # Use Popover for a cleaner "dropdown menu" feel
#     with st.popover("⚙️ 管理", use_container_width=True):
#         # 1. Update News
#         if st.button("🔄 更新新聞", key="refresh_news", use_container_width=True):
#             with st.spinner("正在爬取最新新聞..."):
#                 import subprocess
#                 import sys
#                 try:
#                     result = subprocess.run(
#                         [sys.executable, "crawler.py"],
#                         capture_output=True,
#                         text=True
#                     )
#                     if result.returncode == 0:
#                         st.success("新聞更新完成！")
#                     else:
#                         st.error("更新失敗")
#                 except Exception as e:
#                     st.error(f"更新失敗: {e}")
#             st.rerun()
#         
#         # 2. Cleanup Old Data
#         if st.button("🧹 清理舊資料 (30天前)", help="刪除 30 天以前的新聞資料", use_container_width=True):
#             with st.spinner("正在清理過期資料..."):
#                 try:
#                     deleted_count = database.cleanup_old_news(30)
#                     if deleted_count > 0:
#                         st.success(f"成功刪除 {deleted_count} 筆過期新聞！")
#                         time.sleep(2) # Show success message for a bit
#                         st.rerun()
#                     else:
#                         st.info("沒有發現超過 30 天的過期新聞。")
#                 except Exception as e:
#                     st.error(f"清理失敗: {e}")
# 
# # Filter buttons
# # Filter buttons
# filter_cols = st.columns(len(categories) + 1) # +1 for "All" button
# 
# with filter_cols[0]:
#     if st.button("全部", use_container_width=True):
#         st.session_state['selected_category'] = 'All'
#         st.session_state['source_filter'] = '全部來源'
# 
# for i, cat in enumerate(categories):
#     with filter_cols[i + 1]:
#         if st.button(cat, use_container_width=True):
#             st.session_state['selected_category'] = cat
#             st.session_state['source_filter'] = '全部來源'
# 
# # Get selected category from session state
# selected_category = st.session_state.get('selected_category', 'All')
# 
# # Source dropdown filter
# col_source, col_search = st.columns([1, 2])
# with col_source:
#     # Filter sources based on selected category
#     if selected_category == 'All':
#         available_sources = sorted(list(set(s['name'] for s in sources_config)))
#     else:
#         available_sources = sorted(list(set(s['name'] for s in sources_config if s.get('category') == selected_category)))
#         
#     selected_source = st.selectbox(
#         "篩選來源",
#         ["全部來源"] + available_sources,
#         key="source_filter"
#     )
# 
# with col_search:
#     # Search bar
#     search_query = st.text_input("🔍 搜尋新聞", placeholder="輸入關鍵字...")
# 
# 
# 
# 
# # Load news data
# news_data = database.get_all_news()
# if news_data:
#     if hasattr(news_data[0], 'keys'):
#         news_data = [dict(row) for row in news_data]
#     df = pd.DataFrame(news_data)
# else:
#     df = pd.DataFrame(columns=['title', 'url', 'source', 'published_at', 'summary', 'image_url', 'category'])
# 
# # Apply filters
# # 1. Category filter
# if selected_category != 'All':
#     # Find sources in this category
#     sources_in_cat = [s['name'] for s in sources_config if s.get('category') == selected_category]
#     df = df[df['source'].isin(sources_in_cat)]
# 
# # 2. Source filter
# if selected_source != "全部來源":
#     df = df[df['source'] == selected_source]
# 
# # 3. Search filter
# if search_query:
#     query = search_query.lower()
#     df = df[
#         df['title'].str.lower().str.contains(query, na=False) | 
#         df['summary'].str.lower().str.contains(query, na=False)
#     ]
# 
# # Pagination Logic
# ITEMS_PER_PAGE = 50
# total_items = len(df)
# total_pages = max(1, (total_items + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
# 
# # Get current page from session state (default to 1)
# if 'page_input' not in st.session_state:
#     st.session_state.page_input = 1
# 
# current_page = st.session_state.page_input
# 
# # Display count
# # Calculate display range
# start_item = (current_page - 1) * ITEMS_PER_PAGE + 1
# end_item = min(current_page * ITEMS_PER_PAGE, total_items)
# 
# # Display count info (top)
# st.markdown(f"<div style='text-align: left; color: #5f6368; font-size: 13px; margin: 5px 0;'>顯示 {total_items} 則新聞 (第 {current_page} / {total_pages} 頁)</div>", unsafe_allow_html=True)
# 
# st.markdown("---") # Separator
# 
# # Slice dataframe for current page
# start_idx = (current_page - 1) * ITEMS_PER_PAGE
# end_idx = start_idx + ITEMS_PER_PAGE
# page_df = df.iloc[start_idx:end_idx]
# 
# # Display news list
# # Helper function for keyword highlighting
# def highlight_keywords(text):
#     import re
#     # Keywords to highlight (Yellow)
#     keywords = [
#         "AI", "OpenAI", "Google", "Microsoft", "Apple", "NVIDIA", "Meta", "Amazon",
#         "LLM", "GPT", "Gemini", "Claude", "Llama",
#         "AGI", "Generative AI", "Machine Learning",
#         "Regulation", "Policy", "Act", "Bill", "Law", "Ban",
#         "Investment", "Funding", "Acquisition", "IPO", "Earnings",
#         "Security", "Privacy", "Risk", "Safety", "Ethics",
#         "China", "US", "EU", "UK", "Taiwan"
#     ]
#     
#     # Negative keywords (Red)
#     negative_keywords = [
#         "Layoff", "Cut", "Fire", "Sue", "Lawsuit", "Fine", "Ban", "Restrict",
#         "Fail", "Error", "Bug", "Vulnerability", "Attack", "Hack", "Breach",
#         "裁員", "訴訟", "罰款", "禁止", "限制", "失敗", "錯誤", "漏洞", "攻擊", "駭客"
#     ]
#     
#     # Extract keywords for separate column
#     extracted_keywords = []
#     
#     # Escape keywords for regex
#     for kw in keywords:
#         pattern = re.compile(re.escape(kw), re.IGNORECASE)
#         if pattern.search(text):
#             extracted_keywords.append(kw)
#             # text = pattern.sub(f"<span class='highlight-keyword'>{kw}</span>", text) # Don't highlight in title
#         
#     for kw in negative_keywords:
#         pattern = re.compile(re.escape(kw), re.IGNORECASE)
#         if pattern.search(text):
#             extracted_keywords.append(kw)
#             # text = pattern.sub(f"<span class='highlight-negative'>{kw}</span>", text) # Don't highlight in title
#         
#     return text, extracted_keywords
# 
# # Display news list - Grid View Layout (Table Only)
# # Build HTML string using a list to avoid indentation issues
# html_parts = []
# html_parts.append("""
# <table class="news-grid-table">
#     <thead>
#         <tr>
#             <th class="col-date">日期</th>
#             <th class="col-source">來源</th>
#             <th class="col-category">分類</th>
#             <th class="col-title">標題</th>
#             <th class="col-keywords">關鍵字</th>
#         </tr>
#     </thead>
#     <tbody>
# """)
# 
# for idx, row in page_df.iterrows():
#     source_cat = next((s.get('category', '') for s in sources_config if s['name'] == row['source']), '其他')
#     
#     cat_map = {
#         '政策與政府': 'dot-policy',
#         '學術與科學': 'dot-tech',
#         '科技與新聞': 'dot-industry',
#         '其他與利基市場': 'dot-business'
#     }
#     dot_class = cat_map.get(source_cat, 'dot-other')
#     
#     # Highlight title and extract keywords
#     title_text, keywords_found = highlight_keywords(row['title'])
#     
#     # Format keywords
#     keywords_html = ""
#     for k in keywords_found:
#         style_class = 'highlight-negative' if k in ["Layoff", "Cut", "Fire", "Sue", "Lawsuit", "Fine", "Ban", "Restrict", "Fail", "Error", "Bug", "Vulnerability", "Attack", "Hack", "Breach", "裁員", "訴訟", "罰款", "禁止", "限制", "失敗", "錯誤", "漏洞", "攻擊", "駭客"] else 'highlight-keyword'
#         keywords_html += f"<span class='{style_class}' style='font-size: 11px; margin-right: 4px; display: inline-block; margin-bottom: 2px;'>{k}</span>"
#     
#     html_parts.append(f"""
#         <tr>
#             <td class="col-date">{row['published_at']}</td>
#             <td class="col-source">
#                 <span class="category-dot {dot_class}"></span>
#                 {row['source']}
#             </td>
#             <td class="col-category">{source_cat}</td>
#             <td class="col-title"><a href="{row['url']}" target="_blank">{title_text}</a></td>
#             <td class="col-keywords">{keywords_html}</td>
#         </tr>
#     """)
# 
# html_parts.append("""
#     </tbody>
# </table>
# """)
# 
# full_html = "".join(html_parts)
# 
# # Clean up indentation for Streamlit HTML rendering
# import re
# full_html = re.sub(r'^\s+', '', full_html, flags=re.MULTILINE)
# 
# st.markdown(full_html, unsafe_allow_html=True)
# 
# # Gmail-Style Pagination Controls
# total_pages = (total_items // ITEMS_PER_PAGE) + (1 if total_items % ITEMS_PER_PAGE > 0 else 0)
# 
# # Calculate display range
# start_item = (current_page - 1) * ITEMS_PER_PAGE + 1
# end_item = min(current_page * ITEMS_PER_PAGE, total_items)
# 
# st.markdown("---") # Separator
# 
# # Bottom pagination controls (centered)
# bot_spacer1, bot_prev, bot_info, bot_next, bot_spacer2 = st.columns([3, 1, 3, 1, 3])
# 
# with bot_prev:
#     if st.button("‹ 上一頁", key="prev_btn", disabled=current_page <= 1, use_container_width=True):
#         st.session_state.page_input = max(1, current_page - 1)
#         st.rerun()
# 
# with bot_info:
#     st.markdown(f"<div style='text-align: center; color: #5f6368; font-size: 14px; padding: 8px 0;'>顯示 {total_items} 則新聞 (第 {current_page} / {total_pages} 頁)</div>", unsafe_allow_html=True)
# 
# with bot_next:
#     if st.button("下一頁 ›", key="next_btn", disabled=current_page >= total_pages, use_container_width=True):
#         st.session_state.page_input = min(total_pages, current_page + 1)
#         st.rerun()
