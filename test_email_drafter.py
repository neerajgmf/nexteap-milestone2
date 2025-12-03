#!/usr/bin/env python3
"""
Test script for Step 4: Email Drafting
Tests email generation and Resend integration.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv(override=True)


def test_email_subject_generation():
    """Test email subject generation."""
    print("="*60)
    print("TEST 1: Email Subject Generation")
    print("="*60)
    
    from src.email_drafter import generate_email_subject
    
    # Test data
    summary = {
        'period_end': '2025-12-03T14:00:00+00:00',
        'reviews_with_issues': 63,
        'top_themes': [
            {'name': 'Customer Support Issues', 'count': 19},
            {'name': 'App Compatibility', 'count': 17},
        ]
    }
    
    subject = generate_email_subject(summary)
    print(f"  Generated: {subject}")
    
    # Verify
    assert 'IND MONEY' in subject, "Should include product name"
    assert '63' in subject, "Should include issue count"
    assert 'Customer Support' in subject, "Should include top theme"
    
    print("✓ Subject generation passed")
    return True


def test_plain_text_email():
    """Test plain text email generation."""
    print("\n" + "="*60)
    print("TEST 2: Plain Text Email Generation")
    print("="*60)
    
    from src.email_drafter import generate_plain_text_email
    
    summary = {
        'period_start': '2025-11-01T00:00:00+00:00',
        'period_end': '2025-12-03T14:00:00+00:00',
        'total_reviews': 550,
        'reviews_with_issues': 63,
        'top_themes': [
            {'name': 'Customer Support Issues', 'count': 19, 'percentage': 3.5, 'avg_rating': 1.9},
            {'name': 'App Compatibility', 'count': 17, 'percentage': 3.1, 'avg_rating': 2.3},
        ],
        'actions': [
            {
                'title': 'Improve Customer Support',
                'description': 'Add live chat support.',
                'priority': 'high',
                'addresses_theme': 'Customer Support Issues'
            }
        ]
    }
    
    text = generate_plain_text_email(summary)
    print(f"  Generated {len(text)} chars")
    print(f"  Preview:\n{text[:300]}...")
    
    # Verify
    assert 'WEEKLY PULSE' in text, "Should include header"
    assert 'Customer Support Issues' in text, "Should include themes"
    assert 'Improve Customer Support' in text, "Should include actions"
    
    print("\n✓ Plain text email passed")
    return True


def test_html_email():
    """Test HTML email generation."""
    print("\n" + "="*60)
    print("TEST 3: HTML Email Generation")
    print("="*60)
    
    from src.email_drafter import generate_html_email
    
    summary = {
        'period_start': '2025-11-01T00:00:00+00:00',
        'period_end': '2025-12-03T14:00:00+00:00',
        'total_reviews': 550,
        'reviews_with_issues': 63,
        'top_themes': [
            {'name': 'Customer Support Issues', 'count': 19, 'percentage': 3.5, 'avg_rating': 1.9, 'sentiments': {'negative': 16}},
        ],
        'actions': [
            {
                'title': 'Improve Customer Support',
                'description': 'Add live chat support.',
                'priority': 'high',
                'effort': 'medium',
                'addresses_theme': 'Customer Support Issues'
            }
        ]
    }
    
    html = generate_html_email(summary)
    print(f"  Generated {len(html)} chars")
    
    # Verify
    assert '<!DOCTYPE html>' in html, "Should be valid HTML"
    assert 'IND MONEY' in html, "Should include product name"
    assert 'Customer Support Issues' in html, "Should include themes"
    assert 'inline' in html.lower() or 'style=' in html, "Should have inline styles"
    
    print("✓ HTML email passed")
    return True


def test_full_draft_pipeline():
    """Test the full email drafting pipeline."""
    print("\n" + "="*60)
    print("TEST 4: Full Draft Pipeline")
    print("="*60)
    
    from src.config import Config
    
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        print("Skipping: Supabase not configured")
        return True
    
    # Generate pulse summary first
    from src.note_generator import generate_weekly_pulse
    from src.email_drafter import draft_and_send_pulse_email, save_email_draft
    
    print("Generating pulse data...")
    _, _, summary = generate_weekly_pulse(weeks=12)
    
    if not summary:
        print("No pulse data available")
        return False
    
    # Draft email (don't send)
    subject, html_body, text_body, result = draft_and_send_pulse_email(
        summary=summary,
        send=False  # Don't actually send
    )
    
    # Save drafts
    files = save_email_draft(subject, html_body, text_body)
    
    # Verify
    has_subject = len(subject) > 20
    has_html = len(html_body) > 500
    has_text = len(text_body) > 200
    files_saved = os.path.exists(files['html']) and os.path.exists(files['text'])
    
    print(f"\n✓ Subject generated: {has_subject}")
    print(f"✓ HTML body generated: {has_html} ({len(html_body)} chars)")
    print(f"✓ Text body generated: {has_text} ({len(text_body)} chars)")
    print(f"✓ Files saved: {files_saved}")
    print(f"  - {files['html']}")
    print(f"  - {files['text']}")
    
    return has_subject and has_html and has_text and files_saved


def test_resend_config():
    """Test Resend API configuration."""
    print("\n" + "="*60)
    print("TEST 5: Resend Configuration")
    print("="*60)
    
    from src.config import Config
    
    has_api_key = bool(Config.RESEND_API_KEY)
    has_sender = bool(Config.SENDER_EMAIL)
    has_recipient = bool(Config.RECIPIENT_EMAIL)
    
    print(f"  RESEND_API_KEY: {'✓ Set' if has_api_key else '✗ Not set'}")
    print(f"  SENDER_EMAIL: {'✓ ' + Config.SENDER_EMAIL if has_sender else '✗ Not set'}")
    print(f"  RECIPIENT_EMAIL: {'✓ ' + Config.RECIPIENT_EMAIL if has_recipient else '✗ Not set'}")
    
    if has_api_key:
        print("\n✓ Resend is configured (ready to send)")
    else:
        print("\n⚠ Resend not configured - emails will be drafted but not sent")
        print("  To enable sending, add to .env:")
        print("    RESEND_API_KEY=re_xxxx")
        print("    RECIPIENT_EMAIL=your@email.com")
    
    return True  # Config check always passes


def main():
    print("\n" + "="*60)
    print("STEP 4 TEST: Email Drafting")
    print("="*60)
    
    results = []
    
    # Test 1: Subject Generation
    results.append(("Subject Generation", test_email_subject_generation()))
    
    # Test 2: Plain Text Email
    results.append(("Plain Text Email", test_plain_text_email()))
    
    # Test 3: HTML Email
    results.append(("HTML Email", test_html_email()))
    
    # Test 4: Full Pipeline
    results.append(("Full Pipeline", test_full_draft_pipeline()))
    
    # Test 5: Resend Config
    results.append(("Resend Config", test_resend_config()))
    
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

