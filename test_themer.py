#!/usr/bin/env python3
"""
Test script for Step 2: Theme Extraction & Classification
Tests PII filtering and theme classification.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)


def test_pii_filter():
    """Test PII filtering module."""
    print("="*60)
    print("TEST 1: PII Filter")
    print("="*60)
    
    from src.pii_filter import filter_pii, detect_pii
    
    test_cases = [
        ("Contact me at john@email.com", True),
        ("Call +91-9876543210 for help", True),
        ("Great app, love it!", False),
        ("My PAN ABCDE1234F not updating", True),
        ("Visit www.example.com", True),
    ]
    
    passed = 0
    for text, should_have_pii in test_cases:
        cleaned = filter_pii(text)
        detected = detect_pii(text)
        has_pii = len(detected) > 0
        
        status = "✓" if has_pii == should_have_pii else "✗"
        print(f"{status} '{text[:40]}...' -> PII detected: {has_pii}")
        
        if has_pii == should_have_pii:
            passed += 1
    
    print(f"\nPII Filter: {passed}/{len(test_cases)} tests passed")
    return passed == len(test_cases)


def test_theme_classification():
    """Test theme classification with a small sample."""
    print("\n" + "="*60)
    print("TEST 2: Theme Classification (Sample)")
    print("="*60)
    
    from src.themer import classify_reviews_batch, discover_themes
    from src.pii_filter import batch_filter_pii
    
    # Sample reviews
    sample_reviews = [
        "App keeps crashing whenever I open the stocks section. Very frustrating!",
        "The UI is beautiful and easy to navigate. Love the dark mode!",
        "Stock prices are not updating in real-time. Delayed by several minutes.",
        "KYC verification took forever. Support was unhelpful.",
        "Best trading app! Smooth experience and great customer service.",
    ]
    
    # Filter PII
    cleaned = batch_filter_pii(sample_reviews)
    
    # First discover themes from samples
    print("Discovering themes from sample...")
    discovered_themes = discover_themes(cleaned, max_themes=5, sample_size=5)
    print(f"Discovered {len(discovered_themes)} themes")
    
    # Classify using discovered themes
    print(f"Classifying {len(cleaned)} sample reviews...")
    results = classify_reviews_batch(cleaned, themes=discovered_themes, batch_size=10)
    
    print("\nClassification Results:")
    for i, result in enumerate(results):
        print(f"  [{i+1}] Theme: {result.get('theme', 'N/A')}, "
              f"Sentiment: {result.get('sentiment', 'N/A')}, "
              f"Confidence: {result.get('confidence', 'N/A')}")
    
    # Verify all reviews got classified
    all_classified = len(results) == len(sample_reviews)
    # Themes should be from discovered themes (or close matches)
    has_themes = all(r.get('theme') for r in results)
    
    print(f"\n✓ All reviews classified: {all_classified}")
    print(f"✓ Themes assigned: {has_themes}")
    print(f"✓ Discovered themes: {list(discovered_themes.keys())}")
    
    return all_classified and has_themes


def test_full_pipeline():
    """Test the full theme extraction pipeline with DB."""
    print("\n" + "="*60)
    print("TEST 3: Full Pipeline (Limited Sample)")
    print("="*60)
    
    from src.config import Config
    
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        print("Skipping: Supabase not configured")
        return True
    
    if not Config.GEMINI_API_KEY:
        print("Skipping: Gemini API key not configured")
        return True
    
    # Load a small sample from DB
    from supabase import create_client
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    result = supabase.table('reviews').select('*').limit(30).execute()
    
    if not result.data:
        print("No reviews in database")
        return False
    
    import pandas as pd
    df = pd.DataFrame(result.data)
    df['text'] = df['content']
    
    print(f"Testing with {len(df)} reviews from database...")
    
    # Run theme extraction (without updating DB for test)
    from src.themer import extract_themes_from_reviews, get_theme_summary
    
    df, discovered_themes = extract_themes_from_reviews(df)
    summary = get_theme_summary(df, discovered_themes)
    
    # Verify results
    has_themes = 'theme' in df.columns and df['theme'].notna().all()
    has_sentiment = 'sentiment_label' in df.columns and df['sentiment_label'].notna().all()
    themes_limited = len(df['theme'].unique()) <= 6  # 5 themes + possible "Unknown"
    
    print(f"\n✓ Themes assigned: {has_themes}")
    print(f"✓ Sentiments assigned: {has_sentiment}")
    print(f"✓ Theme count ≤5: {themes_limited} ({len(df['theme'].unique())} unique)")
    print(f"✓ Summary generated: {len(summary.get('themes', []))} themes in summary")
    
    return has_themes and has_sentiment and themes_limited


def main():
    print("\n" + "="*60)
    print("STEP 2 TEST: Theme Extraction & Classification")
    print("="*60)
    
    results = []
    
    # Test 1: PII Filter
    results.append(("PII Filter", test_pii_filter()))
    
    # Test 2: Theme Classification
    results.append(("Theme Classification", test_theme_classification()))
    
    # Test 3: Full Pipeline
    results.append(("Full Pipeline", test_full_pipeline()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ SOME TESTS FAILED")
    print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

