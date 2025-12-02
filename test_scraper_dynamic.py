from src.scraper import get_recent_reviews
import pandas as pd

def test_scraper():
    print("Testing scraper with dynamic arguments...")
    
    # Test with a known app (e.g., WhatsApp on Google Play)
    # WhatsApp ID: com.whatsapp
    
    try:
        print("Fetching WhatsApp reviews...")
        reviews = get_recent_reviews(google_play_id='com.whatsapp', weeks=1)
        
        if not reviews.empty:
            print(f"Success! Fetched {len(reviews)} reviews.")
            print(reviews.head())
        else:
            print("No reviews found (might be expected if timeframe is short or rate limited).")
            
    except Exception as e:
        print(f"Scraper test failed: {e}")

if __name__ == "__main__":
    test_scraper()
