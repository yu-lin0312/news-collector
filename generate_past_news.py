import deep_analyzer
import sys

# Set date to 2026-01-14
target_date = "2026-01-15"

print(f"Triggering generation for {target_date}...")
deep_analyzer.generate_deep_top10(target_date)
print("Done.")
