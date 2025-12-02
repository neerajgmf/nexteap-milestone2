import sys
import os
sys.path.append(os.getcwd())

from src.scraper import fetch_google_play_reviews, fetch_app_store_reviews
import pandas as pd

def debug_scrapers():
    print("--- Debugging Scrapers ---")

    # 1. Google Play
    print("\n1. Testing Google Play Scraper...")
    try:
        gp_df = fetch_google_play_reviews()
        print(f"   Success! Fetched {len(gp_df)} reviews.")
        if not gp_df.empty:
            print("   Latest 5 Google Play Reviews:")
            pd.set_option('display.max_colwidth', None)
            print(gp_df[['date', 'rating', 'text']].head(5))
    except Exception as e:
        print(f"   Failed: {e}")

    # 2. App Store
    print("\n2. Testing App Store Scraper...")
    try:
        as_df = fetch_app_store_reviews()
        print(f"   Success! Fetched {len(as_df)} reviews.")
        if not as_df.empty:
            print("   Latest 5 App Store Reviews:")
            pd.set_option('display.max_colwidth', None)
            print(as_df[['date', 'rating', 'text']].head(5))
    except Exception as e:
        print(f"   Failed: {e}")

if __name__ == "__main__":
    debug_scrapers()
