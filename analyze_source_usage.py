"""
Analyze which sources from sources.json appear in the generated briefings.
This script will help identify sources that are crawled but never used.
"""
import json
import glob
from collections import Counter

# Load sources.json
with open('sources.json', 'r', encoding='utf-8') as f:
    sources = json.load(f)

all_source_names = set(s['name'] for s in sources)
print(f"Total configured sources: {len(all_source_names)}")
print("-" * 50)

# Analyze all briefing files
briefing_files = glob.glob("top10_*.json")
briefing_files = [f for f in briefing_files if 'cache' not in f]

source_usage = Counter()
total_items = 0

for file in briefing_files:
    with open(file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        top10 = data.get('top10', [])
        for item in top10:
            if item:
                source = item.get('source', 'Unknown')
                source_usage[source] += 1
                total_items += 1

print(f"Analyzed {len(briefing_files)} briefing files, {total_items} total items")
print("-" * 50)

# Find sources that are used
used_sources = set(source_usage.keys())
# Find sources that are configured but never appear
unused_sources = all_source_names - used_sources

print(f"\n=== SOURCES THAT APPEAR IN BRIEFINGS ({len(used_sources)}) ===")
for source, count in source_usage.most_common():
    print(f"  {source}: {count} times")

print(f"\n=== SOURCES THAT ARE CRAWLED BUT NEVER USED ({len(unused_sources)}) ===")
for source in sorted(unused_sources):
    # Find the source config
    config = next((s for s in sources if s['name'] == source), None)
    category = config.get('category', 'Unknown') if config else 'Unknown'
    print(f"  - {source} (Category: {category})")
