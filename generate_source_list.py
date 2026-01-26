import database
import sys

# Force UTF-8 for Windows console and file output
sys.stdout.reconfigure(encoding='utf-8')

def generate_source_list():
    try:
        conn = database.get_connection()
        c = conn.cursor()
        
        # Get all unique sources
        c.execute("SELECT DISTINCT source FROM news ORDER BY source COLLATE NOCASE")
        rows = c.fetchall()
        
        sources = [row['source'] for row in rows if row['source']]
        
        output_file = 'all_news_sources.md'
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"# 新聞採集器 - 完整媒體來源清單 ({len(sources)} 個)\n\n")
            f.write("此清單包含直接抓取的來源，以及透過 Google News 和 HackingAI 聚合器發現的原始媒體。\n\n")
            
            # Group by first character for better readability
            current_group = ""
            for source in sources:
                first_char = source[0].upper() if source else "?"
                if first_char != current_group:
                    current_group = first_char
                    f.write(f"\n## {current_group}\n")
                f.write(f"- {source}\n")
        
        print(f"成功產生清單：{output_file}，共 {len(sources)} 個來源。")
        conn.close()
    except Exception as e:
        print(f"產生清單時發生錯誤: {e}")

if __name__ == "__main__":
    generate_source_list()
