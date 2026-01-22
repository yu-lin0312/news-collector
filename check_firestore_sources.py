"""檢查 Firestore 雲端資料庫中的新聞來源"""

from database_firestore import get_db
from collections import Counter

print("=== Firestore 雲端新聞來源統計 ===\n")

db = get_db()
if not db:
    print("無法連線到 Firestore")
    exit(1)

# 查詢所有新聞
docs = db.collection('news').stream()

sources = []
for doc in docs:
    data = doc.to_dict()
    source = data.get('source', 'Unknown')
    sources.append(source)

# 統計來源
source_counts = Counter(sources)

print(f"總新聞數量: {len(sources)}")
print(f"來源種類數: {len(source_counts)}\n")

print("各來源新聞數量：")
for source, count in source_counts.most_common():
    print(f"  {source}: {count}")
