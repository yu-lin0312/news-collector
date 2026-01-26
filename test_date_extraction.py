"""
Test the new date extraction function with the Google Blog URL
"""
import sys
sys.path.insert(0, '.')

from crawler import NewsCrawler

def test_date_extraction():
    crawler = NewsCrawler()
    
    # Test with the Google Blog URL that was showing wrong date
    test_url = "https://blog.google/products-and-platforms/products/search/personal-intelligence-ai-mode-search/"
    
    print(f"Testing date extraction from: {test_url}")
    print("=" * 80)
    
    extracted_date = crawler._try_extract_date_from_url(test_url)
    
    print(f"\nExtracted date: {extracted_date}")
    print(f"Expected: 2026-01-22 (or similar)")
    
    if extracted_date and '2026-01-22' in extracted_date:
        print("\n✅ SUCCESS: Correctly extracted the real publication date!")
    elif extracted_date and '2026-01-26' in extracted_date:
        print("\n❌ FAILED: Still using current date instead of article date")
    else:
        print(f"\n⚠️  UNCERTAIN: Got date {extracted_date}, please verify manually")
    
    crawler.close()

if __name__ == "__main__":
    test_date_extraction()
