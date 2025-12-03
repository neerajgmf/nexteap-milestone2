#!/usr/bin/env python3
"""
Test script for Step 1: Review Ingestion
Tests scraper functionality with limited count for quick verification.
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import Config

def test_ingestion():
    print("=" * 60)
    print("STEP 1 TEST: Review Ingestion Pipeline")
    print("=" * 60)
    
    # Check config
    print("\n[1/4] Checking configuration...")
    print(f"  Product: {Config.PRODUCT_NAME}")
    print(f"  Google Play ID: {Config.GOOGLE_PLAY_ID}")
    print(f"  App Store ID: {Config.APP_STORE_ID}")
    print(f"  Weeks to analyze: {Config.WEEKS_TO_ANALYZE}")
    
    # Import scraper
    print("\n[2/4] Importing scraper module...")
    from src.scraper import get_recent_reviews
    print("  ✓ Scraper imported successfully")
    
    # Fetch reviews (limited count for testing)
    print("\n[3/4] Fetching reviews (limited to 50 for test)...")
    reviews = get_recent_reviews(
        weeks=12,
        save_to_db=False,  # Skip DB for initial test
        save_to_csv=True,
        gp_count=50  # Limited for quick test
    )
    
    if reviews.empty:
        print("  ✗ No reviews fetched - check network/API")
        return False
    
    print(f"  ✓ Fetched {len(reviews)} reviews")
    
    # Validate schema
    print("\n[4/4] Validating schema...")
    required_cols = ['text', 'rating', 'date', 'source', 'review_hash']
    missing = [c for c in required_cols if c not in reviews.columns]
    if missing:
        print(f"  ✗ Missing columns: {missing}")
        return False
    
    print(f"  ✓ All required columns present: {required_cols}")
    
    # Show sample
    print("\n" + "=" * 60)
    print("SAMPLE DATA (first 3 rows):")
    print("=" * 60)
    print(reviews[['date', 'source', 'rating', 'text']].head(3).to_string())
    
    # Stats
    print("\n" + "=" * 60)
    print("QUICK STATS:")
    print("=" * 60)
    print(f"  Total reviews: {len(reviews)}")
    print(f"  Date range: {reviews['date'].min()} to {reviews['date'].max()}")
    print(f"  Avg rating: {reviews['rating'].mean():.2f}")
    print(f"  By source:")
    for source in reviews['source'].unique():
        count = len(reviews[reviews['source'] == source])
        print(f"    - {source}: {count}")
    
    # Check CSV was created
    print("\n" + "=" * 60)
    print("CSV OUTPUT:")
    print("=" * 60)
    import os
    csv_dir = os.path.join(os.path.dirname(__file__), 'artifacts', 'reviews')
    if os.path.exists(csv_dir):
        csvs = [f for f in os.listdir(csv_dir) if f.endswith('.csv')]
        if csvs:
            latest = sorted(csvs)[-1]
            print(f"  ✓ CSV created: artifacts/reviews/{latest}")
        else:
            print("  ✗ No CSV files found")
    else:
        print("  ✗ artifacts/reviews/ directory not found")
    
    print("\n" + "=" * 60)
    print("✓ STEP 1 TEST PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_ingestion()
    sys.exit(0 if success else 1)

