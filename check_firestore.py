import database_firestore
import json

# Check Jan 24
briefing = database_firestore.get_briefing('2026-01-24')
if briefing:
    top10 = briefing.get('top10', [])
    print(f'Briefing for 2026-01-24: {len(top10)} items')
    if top10:
        print("First item sample:")
        print(json.dumps(top10[0], ensure_ascii=False, indent=2))
else:
    print('No briefing for 2026-01-24')

# List all available dates
dates = database_firestore.list_briefings()
print(f'Available briefing dates: {dates}')
