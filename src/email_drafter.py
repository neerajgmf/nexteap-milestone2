"""
Email Drafter Module
Generates and sends weekly pulse emails using Resend API.

Components:
1. Email Generator - Creates subject and body from pulse data
2. HTML Formatter - Styled HTML email for rich clients
3. Plain Text Formatter - Fallback for text-only clients
4. Resend Integration - Email delivery via Resend API
"""

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import html

from .config import Config


def generate_email_subject(summary: Dict) -> str:
    """
    Generate an email subject line from pulse summary.
    
    Args:
        summary: Pulse summary dict with themes and stats
        
    Returns:
        Email subject string
    """
    period_end = datetime.fromisoformat(summary.get('period_end', datetime.now(timezone.utc).isoformat()))
    week_str = period_end.strftime("%b %d")
    
    # Get top theme for subject
    top_themes = summary.get('top_themes', [])
    if top_themes:
        top_theme = top_themes[0]['name']
        issues_count = summary.get('reviews_with_issues', 0)
        return f"📊 {Config.PRODUCT_NAME} Weekly Pulse ({week_str}) - {issues_count} Issues Found: {top_theme}"
    else:
        return f"📊 {Config.PRODUCT_NAME} Weekly Pulse ({week_str}) - No Critical Issues"


def generate_plain_text_email(summary: Dict) -> str:
    """
    Generate plain text email body from pulse summary.
    
    Args:
        summary: Pulse summary dict
        
    Returns:
        Plain text email body
    """
    period_start = datetime.fromisoformat(summary.get('period_start', '')).strftime("%B %d")
    period_end = datetime.fromisoformat(summary.get('period_end', '')).strftime("%B %d, %Y")
    
    lines = [
        f"{Config.PRODUCT_NAME} WEEKLY PULSE",
        "=" * 40,
        "",
        f"Period: {period_start} - {period_end}",
        f"Total Reviews: {summary.get('total_reviews', 0)}",
        f"Reviews with Issues: {summary.get('reviews_with_issues', 0)} ({round(summary.get('reviews_with_issues', 0) / max(summary.get('total_reviews', 1), 1) * 100, 1)}%)",
        "",
        "-" * 40,
        "TOP ISSUES",
        "-" * 40,
        "",
    ]
    
    # Add themes
    for i, theme in enumerate(summary.get('top_themes', []), 1):
        lines.append(f"{i}. {theme['name']}")
        lines.append(f"   {theme['count']} mentions ({theme['percentage']}%) | Avg Rating: {theme.get('avg_rating', 'N/A')}/5")
        lines.append("")
    
    # Add actions
    actions = summary.get('actions', [])
    if actions:
        lines.extend([
            "-" * 40,
            "RECOMMENDED ACTIONS",
            "-" * 40,
            "",
        ])
        
        for i, action in enumerate(actions, 1):
            priority = action.get('priority', 'medium').upper()
            lines.append(f"{i}. [{priority}] {action['title']}")
            lines.append(f"   {action['description']}")
            lines.append(f"   Addresses: {action.get('addresses_theme', 'N/A')}")
            lines.append("")
    
    lines.extend([
        "-" * 40,
        f"Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "AI Review Analyzer",
    ])
    
    return "\n".join(lines)


def generate_html_email(summary: Dict) -> str:
    """
    Generate styled HTML email body from pulse summary.
    
    Args:
        summary: Pulse summary dict
        
    Returns:
        HTML email body (inline styles for email compatibility)
    """
    period_start = datetime.fromisoformat(summary.get('period_start', '')).strftime("%B %d")
    period_end = datetime.fromisoformat(summary.get('period_end', '')).strftime("%B %d, %Y")
    
    total_reviews = summary.get('total_reviews', 0)
    reviews_with_issues = summary.get('reviews_with_issues', 0)
    issue_pct = round(reviews_with_issues / max(total_reviews, 1) * 100, 1)
    
    # Build themes HTML
    themes_html = ""
    for i, theme in enumerate(summary.get('top_themes', []), 1):
        stars = "⭐" * int(theme.get('avg_rating', 3))
        sentiment_negative = theme.get('sentiments', {}).get('negative', 0)
        
        themes_html += f"""
        <div style="background: #f8f9fa; border-radius: 8px; padding: 16px; margin-bottom: 16px; border-left: 4px solid {'#dc3545' if sentiment_negative > 10 else '#ffc107'};">
            <h3 style="margin: 0 0 8px 0; color: #212529; font-size: 16px;">
                {i}. {html.escape(theme['name'])}
            </h3>
            <p style="margin: 0; color: #6c757d; font-size: 14px;">
                <strong>{theme['count']} mentions</strong> ({theme['percentage']}% of reviews) 
                | Avg Rating: {stars} ({theme.get('avg_rating', 'N/A')})
            </p>
        </div>
        """
    
    # Build actions HTML
    actions_html = ""
    for i, action in enumerate(summary.get('actions', []), 1):
        priority = action.get('priority', 'medium')
        priority_color = {'high': '#dc3545', 'medium': '#ffc107', 'low': '#28a745'}.get(priority, '#6c757d')
        priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
        effort = action.get('effort', 'medium')
        effort_label = {'quick-win': '⚡ Quick Win', 'medium': '📅 Medium', 'large': '🏗️ Large'}.get(effort, effort)
        
        actions_html += f"""
        <div style="background: #fff; border: 1px solid #dee2e6; border-radius: 8px; padding: 16px; margin-bottom: 16px;">
            <h4 style="margin: 0 0 8px 0; color: #212529; font-size: 15px;">
                {i}. {html.escape(action['title'])}
            </h4>
            <p style="margin: 0 0 8px 0; font-size: 12px;">
                <span style="background: {priority_color}; color: white; padding: 2px 8px; border-radius: 4px; font-weight: bold;">
                    {priority_emoji} {priority.upper()}
                </span>
                <span style="margin-left: 8px; color: #6c757d;">{effort_label}</span>
            </p>
            <p style="margin: 0 0 8px 0; color: #495057; font-size: 14px;">
                {html.escape(action['description'])}
            </p>
            <p style="margin: 0; color: #6c757d; font-size: 12px; font-style: italic;">
                Addresses: {html.escape(action.get('addresses_theme', 'N/A'))}
            </p>
        </div>
        """
    
    # Full HTML email template
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f4f4f4;">
    <div style="max-width: 600px; margin: 0 auto; background: #ffffff;">
        
        <!-- Header -->
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 32px 24px; text-align: center;">
            <h1 style="margin: 0; color: white; font-size: 24px; font-weight: 600;">
                📊 {Config.PRODUCT_NAME} Weekly Pulse
            </h1>
            <p style="margin: 8px 0 0 0; color: rgba(255,255,255,0.9); font-size: 14px;">
                {period_start} - {period_end}
            </p>
        </div>
        
        <!-- Stats Bar -->
        <div style="display: flex; background: #f8f9fa; padding: 16px 24px; border-bottom: 1px solid #dee2e6;">
            <div style="flex: 1; text-align: center;">
                <div style="font-size: 24px; font-weight: bold; color: #212529;">{total_reviews}</div>
                <div style="font-size: 12px; color: #6c757d;">Total Reviews</div>
            </div>
            <div style="flex: 1; text-align: center; border-left: 1px solid #dee2e6;">
                <div style="font-size: 24px; font-weight: bold; color: #dc3545;">{reviews_with_issues}</div>
                <div style="font-size: 12px; color: #6c757d;">With Issues ({issue_pct}%)</div>
            </div>
            <div style="flex: 1; text-align: center; border-left: 1px solid #dee2e6;">
                <div style="font-size: 24px; font-weight: bold; color: #28a745;">{len(summary.get('actions', []))}</div>
                <div style="font-size: 12px; color: #6c757d;">Actions</div>
            </div>
        </div>
        
        <!-- Content -->
        <div style="padding: 24px;">
            
            <!-- Top Issues Section -->
            <h2 style="margin: 0 0 16px 0; color: #212529; font-size: 18px; border-bottom: 2px solid #667eea; padding-bottom: 8px;">
                🔍 Top Issues This Week
            </h2>
            
            {themes_html if themes_html else '<p style="color: #6c757d;">No significant issues found.</p>'}
            
            <!-- Actions Section -->
            <h2 style="margin: 24px 0 16px 0; color: #212529; font-size: 18px; border-bottom: 2px solid #667eea; padding-bottom: 8px;">
                💡 Recommended Actions
            </h2>
            
            {actions_html if actions_html else '<p style="color: #6c757d;">No actions generated.</p>'}
            
        </div>
        
        <!-- Footer -->
        <div style="background: #f8f9fa; padding: 16px 24px; text-align: center; border-top: 1px solid #dee2e6;">
            <p style="margin: 0; color: #6c757d; font-size: 12px;">
                Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by AI Review Analyzer
            </p>
            <p style="margin: 8px 0 0 0; color: #adb5bd; font-size: 11px;">
                This is an automated report. Do not reply to this email.
            </p>
        </div>
        
    </div>
</body>
</html>
"""
    
    return html_content


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: str,
    from_email: str = None
) -> Dict:
    """
    Send email using Resend API.
    
    Args:
        to_email: Recipient email address
        subject: Email subject
        html_body: HTML email content
        text_body: Plain text fallback
        from_email: Sender email (defaults to config)
        
    Returns:
        Dict with send status and message ID
    """
    if not Config.RESEND_API_KEY:
        return {
            'success': False,
            'error': 'RESEND_API_KEY not configured',
            'message_id': None
        }
    
    import resend
    resend.api_key = Config.RESEND_API_KEY
    
    sender = from_email or Config.SENDER_EMAIL
    
    try:
        response = resend.Emails.send({
            "from": sender,
            "to": [to_email],
            "subject": subject,
            "html": html_body,
            "text": text_body,
        })
        
        return {
            'success': True,
            'message_id': response.get('id'),
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message_id': None
        }


def draft_and_send_pulse_email(
    summary: Dict,
    to_email: str = None,
    send: bool = True
) -> Tuple[str, str, str, Dict]:
    """
    Generate and optionally send the weekly pulse email.
    
    Args:
        summary: Pulse summary dict from note_generator
        to_email: Recipient email (defaults to config)
        send: Whether to actually send the email
        
    Returns:
        Tuple of (subject, html_body, text_body, send_result)
    """
    print("\n" + "="*60)
    print("Drafting Weekly Pulse Email")
    print("="*60)
    
    # Generate email content
    print("\n[1/3] Generating email subject...")
    subject = generate_email_subject(summary)
    print(f"  Subject: {subject}")
    
    print("\n[2/3] Generating email body...")
    html_body = generate_html_email(summary)
    text_body = generate_plain_text_email(summary)
    print(f"  HTML: {len(html_body)} chars")
    print(f"  Text: {len(text_body)} chars")
    
    # Send email
    send_result = {'success': False, 'message_id': None, 'error': 'Not sent (send=False)'}
    
    if send:
        recipient = to_email or Config.RECIPIENT_EMAIL
        if not recipient:
            send_result = {
                'success': False,
                'error': 'No recipient email configured. Set RECIPIENT_EMAIL in .env',
                'message_id': None
            }
            print(f"\n[3/3] ⚠ Cannot send: {send_result['error']}")
        else:
            print(f"\n[3/3] Sending email to {recipient}...")
            send_result = send_email(recipient, subject, html_body, text_body)
            
            if send_result['success']:
                print(f"  ✓ Email sent! Message ID: {send_result['message_id']}")
            else:
                print(f"  ✗ Failed to send: {send_result['error']}")
    else:
        print("\n[3/3] Skipping send (draft mode)")
    
    print("\n" + "="*60)
    print("✓ Email Draft Complete")
    print("="*60)
    
    return subject, html_body, text_body, send_result


def save_email_draft(
    subject: str,
    html_body: str,
    text_body: str,
    output_dir: str = "artifacts/emails"
) -> Dict[str, str]:
    """
    Save email draft to files.
    
    Args:
        subject: Email subject
        html_body: HTML content
        text_body: Plain text content
        output_dir: Output directory
        
    Returns:
        Dict with file paths
    """
    import os
    
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save HTML
    html_path = os.path.join(output_dir, f"email_{timestamp}.html")
    with open(html_path, 'w') as f:
        f.write(html_body)
    
    # Save text
    text_path = os.path.join(output_dir, f"email_{timestamp}.txt")
    with open(text_path, 'w') as f:
        f.write(f"Subject: {subject}\n\n{text_body}")
    
    return {
        'html': html_path,
        'text': text_path,
    }


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Draft and send weekly pulse email")
    parser.add_argument('--send', action='store_true', help="Actually send the email")
    parser.add_argument('--to', type=str, help="Recipient email address")
    parser.add_argument('--weeks', type=int, default=1, help="Weeks of data to analyze")
    args = parser.parse_args()
    
    # Generate pulse first
    from .note_generator import generate_weekly_pulse
    
    print("Generating pulse data...")
    _, _, summary = generate_weekly_pulse(weeks=args.weeks)
    
    if not summary:
        print("Failed to generate pulse. No data available.")
        exit(1)
    
    # Draft and send email
    subject, html_body, text_body, result = draft_and_send_pulse_email(
        summary=summary,
        to_email=args.to,
        send=args.send
    )
    
    # Save draft
    files = save_email_draft(subject, html_body, text_body)
    print(f"\nDrafts saved:")
    print(f"  HTML: {files['html']}")
    print(f"  Text: {files['text']}")

