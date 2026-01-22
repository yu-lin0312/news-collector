"""檢查 Firestore 雲端資料庫中的 briefing 資料"""

from database_firestore import get_briefing, list_briefings
import json

print("=== Firestore 雲端資料庫查詢 ===\n")

# 列出所有可用的 briefing 日期
print("可用的 Briefing 日期：")
dates = list_briefings()
for d in dates:
    print(f"  - {d}")

print()

# 查詢 2026-01-22 的資料
date_str = "2026-01-22"
print(f"查詢 {date_str} 的 Briefing：")
data = get_briefing(date_str)

if data:
    news_count = len(data.get("top10", []))
    print(f"  ✓ 資料存在")
    print(f"  新聞數量: {news_count}")
    print(f"  生成時間: {data.get('generated_at', 'N/A')}")
    print()
    print("  新聞標題：")
    for i, news in enumerate(data.get("top10", []), 1):
        title = news.get("title", "N/A")[:50]
        print(f"    {i}. {title}...")
else:
    print("  ✗ 無資料")
