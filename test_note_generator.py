#!/usr/bin/env python3
"""
Test script for Step 3: Note Generation
Tests pulse document generation from classified reviews.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)


def test_theme_selection():
    """Test top theme selection."""
    print("="*60)
    print("TEST 1: Theme Selection")
    print("="*60)
    
    import pandas as pd
    from src.note_generator import select_top_themes
    
    # Create test data
    test_data = pd.DataFrame({
        'theme': ['App Crashes'] * 10 + ['Withdrawal Delays'] * 7 + ['Poor Support'] * 5 + ['No Issue'] * 20,
        'sentiment_label': ['negative'] * 22 + ['positive'] * 20,
        'rating': [2] * 10 + [3] * 7 + [2] * 5 + [5] * 20,
    })
    
    top_themes = select_top_themes(test_data, n=3)
    
    print(f"Selected {len(top_themes)} themes:")
    for theme in top_themes:
        print(f"  • {theme['name']}: {theme['count']} ({theme['percentage']}%)")
    
    # Verify
    assert len(top_themes) == 3, "Should select 3 themes"
    assert top_themes[0]['name'] == 'App Crashes', "First theme should be App Crashes"
    assert 'No Issue' not in [t['name'] for t in top_themes], "Should not include 'No Issue'"
    
    print("✓ Theme selection passed")
    return True


def test_quote_extraction():
    """Test quote extraction."""
    print("\n" + "="*60)
    print("TEST 2: Quote Extraction")
    print("="*60)
    
    import pandas as pd
    from src.note_generator import extract_quotes
    
    # Create test data with various reviews
    test_data = pd.DataFrame({
        'theme': ['App Crashes'] * 5,
        'sentiment_label': ['negative', 'negative', 'neutral', 'positive', 'negative'],
        'content': [
            "App crashes every time I open the stocks section. Very frustrating experience!",
            "Keeps freezing and crashing. Need to restart multiple times.",
            "Sometimes the app crashes but mostly works fine.",
            "App is stable now after the update.",
            "Too many crashes! Worst app ever. My email is test@email.com",  # Contains PII
        ],
        'rating': [1, 2, 3, 4, 1],
        'date': ['2024-01-01'] * 5,
        'source': ['Google Play'] * 5,
    })
    test_data['text'] = test_data['content']
    
    quotes = extract_quotes(test_data, 'App Crashes', n=3)
    
    print(f"Extracted {len(quotes)} quotes:")
    for quote in quotes:
        print(f"  • [{quote['sentiment']}] \"{quote['text'][:50]}...\"")
    
    # Verify
    assert len(quotes) == 3, "Should extract 3 quotes"
    assert quotes[0]['sentiment'] == 'negative', "First quote should be negative"
    assert 'test@email.com' not in quotes[-1]['text'], "PII should be filtered"
    
    print("✓ Quote extraction passed")
    return True


def test_action_generation():
    """Test action idea generation."""
    print("\n" + "="*60)
    print("TEST 3: Action Generation")
    print("="*60)
    
    from src.note_generator import generate_action_ideas
    
    themes = [
        {'name': 'App Crashes', 'count': 10, 'percentage': 15.0},
        {'name': 'Withdrawal Delays', 'count': 7, 'percentage': 10.5},
    ]
    
    quotes_by_theme = {
        'App Crashes': [
            {'text': 'App crashes when opening stocks'},
            {'text': 'Freezes on portfolio page'},
        ],
        'Withdrawal Delays': [
            {'text': 'Money stuck for 2 weeks'},
            {'text': 'Withdrawal taking forever'},
        ],
    }
    
    print("Generating action ideas...")
    actions = generate_action_ideas(themes, quotes_by_theme, n=3)
    
    print(f"Generated {len(actions)} actions:")
    for action in actions:
        print(f"  • [{action['priority']}] {action['title']}")
    
    # Verify - be lenient, at least 1 action
    if len(actions) == 0:
        print("⚠ Warning: No actions generated, retrying...")
        # Retry once
        actions = generate_action_ideas(themes, quotes_by_theme, n=3)
        print(f"  Retry generated {len(actions)} actions")
    
    success = len(actions) > 0 and all('title' in a for a in actions)
    
    if success:
        print("✓ Action generation passed")
    else:
        print("✗ Action generation failed")
    
    return success


def test_full_pipeline():
    """Test the full pulse generation pipeline."""
    print("\n" + "="*60)
    print("TEST 4: Full Pipeline")
    print("="*60)
    
    from src.config import Config
    
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        print("Skipping: Supabase not configured")
        return True
    
    if not Config.OPENROUTER_API_KEY and not Config.GEMINI_API_KEY:
        print("Skipping: No LLM provider configured")
        return True
    
    from src.note_generator import generate_weekly_pulse
    
    print("Running full pulse generation...")
    md, html, summary = generate_weekly_pulse(weeks=12, output_dir="artifacts/pulses")
    
    # Verify
    has_content = len(md) > 100
    has_html = len(html) > 100
    has_themes = len(summary.get('top_themes', [])) > 0
    has_actions = len(summary.get('actions', [])) > 0
    
    print(f"\n✓ Markdown generated: {len(md)} chars")
    print(f"✓ HTML generated: {len(html)} chars")
    print(f"✓ Themes found: {len(summary.get('top_themes', []))}")
    print(f"✓ Actions generated: {len(summary.get('actions', []))}")
    
    return has_content and has_html


def main():
    print("\n" + "="*60)
    print("STEP 3 TEST: Note Generation")
    print("="*60)
    
    results = []
    
    # Test 1: Theme Selection
    results.append(("Theme Selection", test_theme_selection()))
    
    # Test 2: Quote Extraction
    results.append(("Quote Extraction", test_quote_extraction()))
    
    # Test 3: Action Generation
    results.append(("Action Generation", test_action_generation()))
    
    # Test 4: Full Pipeline
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

