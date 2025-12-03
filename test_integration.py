#!/usr/bin/env python3
"""
INTEGRATION TEST: Full End-to-End Pipeline
Tests the complete workflow from review ingestion to email drafting.

Pipeline:
  Step 1: Scraper → Fetch reviews from stores, save to DB
  Step 2: Themer → Discover themes, classify reviews
  Step 3: Note Generator → Generate weekly pulse
  Step 4: Email Drafter → Create and optionally send email
"""

import os
import sys
import time
from datetime import datetime, timezone
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)


def print_header(title: str, char: str = "="):
    """Print formatted section header."""
    width = 70
    print(f"\n{char * width}")
    print(f"  {title}")
    print(f"{char * width}")


def print_step(step_num: int, title: str):
    """Print step header."""
    print(f"\n{'─' * 70}")
    print(f"  STEP {step_num}: {title}")
    print(f"{'─' * 70}")


def check_configuration():
    """Verify all required configuration is present."""
    print_header("CONFIGURATION CHECK")
    
    from src.config import Config
    
    checks = {
        "Supabase URL": bool(Config.SUPABASE_URL),
        "Supabase Key": bool(Config.SUPABASE_KEY),
        "LLM Provider": Config.get_llm_provider() != "none",
        "OpenRouter Key": bool(Config.OPENROUTER_API_KEY),
        "Product Name": bool(Config.PRODUCT_NAME),
        "Google Play ID": bool(Config.GOOGLE_PLAY_ID),
        "App Store ID": bool(Config.APP_STORE_ID),
    }
    
    optional = {
        "Resend API Key": bool(Config.RESEND_API_KEY),
        "Recipient Email": bool(Config.RECIPIENT_EMAIL),
    }
    
    all_required_pass = True
    
    print("\n  Required:")
    for name, status in checks.items():
        symbol = "✓" if status else "✗"
        print(f"    {symbol} {name}")
        if not status:
            all_required_pass = False
    
    print("\n  Optional (for email):")
    for name, status in optional.items():
        symbol = "✓" if status else "○"
        print(f"    {symbol} {name}")
    
    print(f"\n  LLM Provider: {Config.get_llm_provider()}")
    if Config.OPENROUTER_API_KEY:
        print(f"  OpenRouter Model: {Config.OPENROUTER_MODEL}")
    
    return all_required_pass


def load_reviews_from_db(weeks: int = 12):
    """Load reviews from Supabase database."""
    from datetime import timedelta
    from supabase import create_client
    from src.config import Config
    
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).isoformat()
    result = supabase.table('reviews').select('*').gte('date', cutoff).execute()
    
    if not result.data:
        return pd.DataFrame()
    
    df = pd.DataFrame(result.data)
    df['text'] = df['content']  # Normalize column name
    return df


def test_step1_data_ingestion():
    """Test Step 1: Review Data Ingestion."""
    print_step(1, "DATA INGESTION")
    
    from src.scraper import get_recent_reviews
    from src.config import Config
    
    start_time = time.time()
    
    # Check if we have data in DB
    print("\n  Checking existing data in database...")
    existing_reviews = load_reviews_from_db(weeks=12)
    
    if existing_reviews.empty or len(existing_reviews) < 100:
        print(f"  Found {len(existing_reviews)} reviews, fetching more...")
        # Fetch fresh data
        reviews_df = get_recent_reviews(
            weeks=12,
            save_to_db=True,
            save_to_csv=False
        )
        print(f"  Fetched and saved {len(reviews_df)} reviews")
    else:
        reviews_df = existing_reviews
        print(f"  Using existing {len(reviews_df)} reviews from database")
    
    elapsed = time.time() - start_time
    
    # Verify data quality
    if not reviews_df.empty:
        # Convert date column if needed
        if reviews_df['date'].dtype == 'object':
            reviews_df['date'] = pd.to_datetime(reviews_df['date'])
        date_range = f"{reviews_df['date'].min().date()} to {reviews_df['date'].max().date()}"
    else:
        date_range = "N/A"
        
    metrics = {
        "Total Reviews": len(reviews_df),
        "Sources": reviews_df['source'].nunique() if not reviews_df.empty else 0,
        "Date Range": date_range,
        "Avg Rating": round(reviews_df['rating'].mean(), 2) if not reviews_df.empty else "N/A",
    }
    
    print(f"\n  Data Metrics:")
    for name, value in metrics.items():
        print(f"    • {name}: {value}")
    
    print(f"\n  ⏱ Completed in {elapsed:.2f}s")
    
    success = len(reviews_df) >= 50
    print(f"\n  {'✓ PASSED' if success else '✗ FAILED'}: Data Ingestion")
    
    return success, reviews_df


def test_step2_theme_classification(reviews_df):
    """Test Step 2: Theme Discovery & Classification."""
    print_step(2, "THEME CLASSIFICATION")
    
    from src.themer import run_theme_extraction
    from src.config import Config
    
    start_time = time.time()
    
    # Check if reviews are already classified
    print("\n  Checking for classified reviews...")
    classified_df = load_reviews_from_db(weeks=12)
    
    classified_count = classified_df['theme'].notna().sum() if not classified_df.empty and 'theme' in classified_df.columns else 0
    
    if classified_count < len(reviews_df) * 0.5:
        print(f"  Only {classified_count}/{len(reviews_df)} classified, running classification...")
        # Run theme extraction (returns tuple of DataFrame, summary)
        classified_df, theme_summary = run_theme_extraction(weeks=12)
    else:
        print(f"  Using existing classification: {classified_count} reviews")
    
    elapsed = time.time() - start_time
    
    # Analyze themes
    if not classified_df.empty and 'theme' in classified_df.columns:
        theme_counts = classified_df['theme'].value_counts()
        
        print(f"\n  Theme Distribution:")
        for theme, count in theme_counts.head(6).items():
            pct = round(count / len(classified_df) * 100, 1)
            print(f"    • {theme}: {count} ({pct}%)")
        
        # Calculate actionable issues (excluding No Issue)
        issue_count = classified_df[~classified_df['theme'].isin(['No Issue', 'Unknown'])].shape[0]
        issue_pct = round(issue_count / len(classified_df) * 100, 1)
        print(f"\n  Actionable Issues: {issue_count} ({issue_pct}%)")
    
    print(f"\n  ⏱ Completed in {elapsed:.2f}s")
    
    success = not classified_df.empty and 'theme' in classified_df.columns
    print(f"\n  {'✓ PASSED' if success else '✗ FAILED'}: Theme Classification")
    
    return success, classified_df


def test_step3_note_generation(classified_df):
    """Test Step 3: Weekly Pulse Generation."""
    print_step(3, "NOTE GENERATION")
    
    from src.note_generator import generate_weekly_pulse
    
    start_time = time.time()
    
    print("\n  Generating weekly pulse...")
    md_content, html_content, summary = generate_weekly_pulse(weeks=12)
    
    elapsed = time.time() - start_time
    
    if summary:
        print(f"\n  Pulse Summary:")
        print(f"    • Total Reviews: {summary.get('total_reviews', 0)}")
        print(f"    • Reviews with Issues: {summary.get('reviews_with_issues', 0)}")
        print(f"    • Top Themes: {len(summary.get('top_themes', []))}")
        print(f"    • Action Items: {len(summary.get('actions', []))}")
        
        # Show top themes
        if summary.get('top_themes'):
            print(f"\n  Top Issues:")
            for i, theme in enumerate(summary['top_themes'], 1):
                print(f"    {i}. {theme['name']} ({theme['count']} mentions)")
        
        # Show actions
        if summary.get('actions'):
            print(f"\n  Recommended Actions:")
            for i, action in enumerate(summary['actions'], 1):
                priority = action.get('priority', 'medium').upper()
                print(f"    {i}. [{priority}] {action['title'][:50]}...")
        
        # Show generated files
        if summary.get('files'):
            print(f"\n  Generated Files:")
            for fmt, path in summary['files'].items():
                print(f"    • {fmt.upper()}: {path}")
    
    print(f"\n  ⏱ Completed in {elapsed:.2f}s")
    
    success = summary is not None and len(summary.get('top_themes', [])) > 0
    print(f"\n  {'✓ PASSED' if success else '✗ FAILED'}: Note Generation")
    
    return success, summary


def test_step4_email_drafting(summary):
    """Test Step 4: Email Drafting."""
    print_step(4, "EMAIL DRAFTING")
    
    from src.email_drafter import (
        generate_email_subject,
        generate_html_email,
        generate_plain_text_email,
        save_email_draft
    )
    from src.config import Config
    
    start_time = time.time()
    
    # Generate email content
    print("\n  Generating email content...")
    subject = generate_email_subject(summary)
    html_body = generate_html_email(summary)
    text_body = generate_plain_text_email(summary)
    
    print(f"\n  Email Details:")
    print(f"    • Subject: {subject}")
    print(f"    • HTML Size: {len(html_body):,} chars")
    print(f"    • Text Size: {len(text_body):,} chars")
    
    # Save draft
    files = save_email_draft(subject, html_body, text_body)
    print(f"\n  Draft Saved:")
    print(f"    • HTML: {files['html']}")
    print(f"    • Text: {files['text']}")
    
    # Check Resend configuration
    can_send = bool(Config.RESEND_API_KEY and Config.RECIPIENT_EMAIL)
    print(f"\n  Email Delivery: {'Ready (Resend configured)' if can_send else 'Draft only (Resend not configured)'}")
    
    elapsed = time.time() - start_time
    print(f"\n  ⏱ Completed in {elapsed:.2f}s")
    
    success = len(subject) > 0 and len(html_body) > 100 and len(text_body) > 50
    print(f"\n  {'✓ PASSED' if success else '✗ FAILED'}: Email Drafting")
    
    return success, files


def test_full_cron_simulation():
    """Simulate what the cron job would do."""
    print_step(5, "CRON SIMULATION (Full Pipeline)")
    
    print("\n  Simulating weekly cron execution...")
    
    from src.scraper import get_recent_reviews
    from src.themer import run_theme_extraction
    from src.note_generator import generate_weekly_pulse
    from src.email_drafter import draft_and_send_pulse_email, save_email_draft
    
    total_start = time.time()
    
    # This is what the cron would do:
    # 1. Fetch fresh reviews (incremental)
    # 2. Classify new reviews
    # 3. Generate pulse
    # 4. Send email
    
    print("\n  [Cron Step 1] Checking for new reviews...")
    # In a real cron, we'd only fetch new reviews
    
    print("  [Cron Step 2] Classifying reviews...")
    # Already done in previous step
    
    print("  [Cron Step 3] Generating pulse...")
    md, html, summary = generate_weekly_pulse(weeks=1)  # Just last week for cron
    
    print("  [Cron Step 4] Drafting email...")
    subject, html_body, text_body, result = draft_and_send_pulse_email(
        summary=summary,
        send=False  # Don't actually send in test
    )
    
    total_elapsed = time.time() - total_start
    
    print(f"\n  Total Cron Execution: {total_elapsed:.2f}s")
    
    return True


def main():
    """Run full integration test."""
    print_header("INTEGRATION TEST: AI Review Analyzer", "═")
    print(f"  Started: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    results = []
    total_start = time.time()
    
    # Configuration Check
    config_ok = check_configuration()
    if not config_ok:
        print("\n⚠ Configuration incomplete. Some tests may fail.")
    results.append(("Configuration", config_ok))
    
    # Step 1: Data Ingestion
    step1_ok, reviews_df = test_step1_data_ingestion()
    results.append(("Step 1: Data Ingestion", step1_ok))
    
    if not step1_ok:
        print("\n✗ Cannot continue without data. Aborting.")
        return False
    
    # Step 2: Theme Classification
    step2_ok, classified_df = test_step2_theme_classification(reviews_df)
    results.append(("Step 2: Theme Classification", step2_ok))
    
    if not step2_ok:
        print("\n✗ Cannot continue without classification. Aborting.")
        return False
    
    # Step 3: Note Generation
    step3_ok, summary = test_step3_note_generation(classified_df)
    results.append(("Step 3: Note Generation", step3_ok))
    
    if not step3_ok:
        print("\n⚠ Note generation failed, using minimal summary for email test.")
        summary = {
            'period_start': datetime.now(timezone.utc).isoformat(),
            'period_end': datetime.now(timezone.utc).isoformat(),
            'total_reviews': len(reviews_df),
            'reviews_with_issues': 0,
            'top_themes': [],
            'actions': []
        }
    
    # Step 4: Email Drafting
    step4_ok, files = test_step4_email_drafting(summary)
    results.append(("Step 4: Email Drafting", step4_ok))
    
    # Step 5: Cron Simulation
    step5_ok = test_full_cron_simulation()
    results.append(("Step 5: Cron Simulation", step5_ok))
    
    total_elapsed = time.time() - total_start
    
    # Final Summary
    print_header("INTEGRATION TEST RESULTS", "═")
    
    all_passed = True
    for name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print(f"\n  Total Execution Time: {total_elapsed:.2f}s")
    print(f"  Completed: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    print("\n" + "═" * 70)
    if all_passed:
        print("  ✓ ALL INTEGRATION TESTS PASSED")
        print("    Pipeline is ready for production cron deployment!")
    else:
        print("  ✗ SOME TESTS FAILED")
        print("    Review errors above before deployment.")
    print("═" * 70 + "\n")
    
    return all_passed


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

