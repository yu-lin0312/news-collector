"""
快速同步腳本：將本地 JSON 檔案同步到 Firebase Firestore
用途：當本地資料正確但雲端不同步時，快速上傳

使用方式：
    python sync_to_firestore.py                  # 同步今天的資料
    python sync_to_firestore.py 2026-01-22       # 同步指定日期的資料
"""

import json
import sys
from datetime import datetime
from database_firestore import save_briefing, get_db

def sync_briefing(date_str=None):
    """同步指定日期的 briefing 到 Firestore"""
    
    # 預設同步今天
    if date_str is None:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    json_file = f"top10_{date_str}.json"
    
    print(f"正在同步 {json_file} 到 Firestore...")
    
    # 讀取本地 JSON
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"錯誤：找不到檔案 {json_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"錯誤：JSON 解析失敗 - {e}")
        return False
    
    # 確認資料內容
    news_count = len(data.get('top10', []))
    print(f"本地檔案包含 {news_count} 則新聞")
    
    # 檢查 Firestore 連線
    db = get_db()
    if not db:
        print("錯誤：無法連線到 Firestore")
        return False
    
    # 上傳到 Firestore
    success = save_briefing(date_str, data)
    
    if success:
        print(f"✓ 成功同步 {news_count} 則新聞到 Firestore！")
        print(f"  日期：{date_str}")
    else:
        print("✗ 同步失敗")
    
    return success

def main():
    # 從命令列參數取得日期（可選）
    date_str = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = sync_briefing(date_str)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
