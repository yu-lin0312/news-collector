import json

with open('top10_2026-01-26.json', encoding='utf-8') as f:
    data = json.load(f)
    
for i, item in enumerate(data.get('top10', []), 1):
    date = item.get('published_at', 'N/A')
    if 'T' in str(date):
        date = str(date).split('T')[0]
    print(f"{i}. {date}")
