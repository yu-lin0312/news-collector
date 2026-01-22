import json
import os
from datetime import datetime
import deep_analyzer
import google.generativeai as genai

# Load existing data
filename = "top10_2026-01-16.json"
if not os.path.exists(filename):
    print(f"Error: {filename} not found.")
    exit()

with open(filename, 'r', encoding='utf-8') as f:
    data = json.load(f)

top10_list = data.get('top10', [])
print(f"Loaded {len(top10_list)} items from {filename}")

if not top10_list:
    print("No items to summarize.")
    exit()

# Generate Summary
print("Generating Daily Briefing Summary...")
# Ensure API Key is set (it should be in env from run_command)
if not os.environ.get("GOOGLE_API_KEY"):
    print("Error: GOOGLE_API_KEY not set.")
    exit()

# Force use of a working model for this specific task if needed, 
# but deep_analyzer.generate_daily_summary already has logic.
# Let's just call it.
daily_summary = deep_analyzer.generate_daily_summary(top10_list)

if daily_summary:
    print("Summary generated successfully!")
    print(json.dumps(daily_summary, indent=2, ensure_ascii=False))
    
    # Update data
    data['daily_briefing'] = daily_summary
    
    # Save back
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Updated {filename} with daily briefing summary.")
else:
    print("Failed to generate summary.")
