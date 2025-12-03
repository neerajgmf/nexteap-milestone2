# Step 4: Email Drafting

## Overview

Step 4 generates and sends weekly pulse emails with formatted content for stakeholders, integrating with Resend API for delivery.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     EMAIL DRAFTING PIPELINE                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Pulse Summary (from Step 3)                                        │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           STEP 1: SUBJECT GENERATION                        │    │
│  │  • Include product name                                     │    │
│  │  • Include date/period                                      │    │
│  │  • Highlight issue count and top theme                      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           STEP 2: EMAIL BODY GENERATION                     │    │
│  │  • HTML version with inline styles                          │    │
│  │  • Plain text fallback                                      │    │
│  │  • Stats bar: total reviews, issues, actions                │    │
│  │  • Top issues section                                       │    │
│  │  • Recommended actions section                              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           STEP 3: DELIVERY (via Resend)                     │    │
│  │  • Send to configured recipient                             │    │
│  │  • Save draft copies locally                                │    │
│  │  • Return delivery status                                   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Output Formats

### Email Subject

```
📊 IND MONEY Weekly Pulse (Dec 03) - 63 Issues Found: Customer Support Issues
```

Components:
- 📊 Emoji indicator
- Product name
- Date period
- Issue count
- Top theme name

### Plain Text Email

```
IND MONEY WEEKLY PULSE
========================================

Period: September 10 - December 03, 2025
Total Reviews: 550
Reviews with Issues: 63 (11.5%)

----------------------------------------
TOP ISSUES
----------------------------------------

1. Customer Support Issues
   19 mentions (3.5%) | Avg Rating: 1.9/5

2. App Compatibility
   17 mentions (3.1%) | Avg Rating: 2.3/5

3. Data/Chart Accuracy
   12 mentions (2.2%) | Avg Rating: 2.7/5

----------------------------------------
RECOMMENDED ACTIONS
----------------------------------------

1. [HIGH] Implement Dedicated Customer Support SLA System
   Establish a tiered support system with guaranteed response times...
   Addresses: Customer Support Issues

...
```

### HTML Email

Styled HTML with:
- Gradient header with product branding
- Stats bar (total reviews, issues, action count)
- Color-coded priority indicators (🔴 HIGH, 🟡 MEDIUM, 🟢 LOW)
- Mobile-responsive layout
- Inline styles for email client compatibility

## Configuration

Add to `.env`:

```bash
# Resend API
RESEND_API_KEY=re_xxxxxxxxxxxx

# Email addresses
SENDER_EMAIL=noreply@yourdomain.com  # Optional, defaults to Resend sandbox
RECIPIENT_EMAIL=team@company.com     # Required for sending
```

### Sender Domain

Resend requires sender domain verification for production:
- **Sandbox**: Use `onboarding@resend.dev` (limited to your account email)
- **Production**: Configure custom domain in Resend dashboard

## Usage

### Draft Only (No Send)

```bash
# Generate draft without sending
python -m src.email_drafter --weeks 12

# Output saved to artifacts/emails/
```

### Draft and Send

```bash
# Send to configured recipient
python -m src.email_drafter --weeks 12 --send

# Send to specific email
python -m src.email_drafter --weeks 1 --send --to team@company.com
```

### Programmatic Usage

```python
from src.note_generator import generate_weekly_pulse
from src.email_drafter import draft_and_send_pulse_email, save_email_draft

# Generate pulse
_, _, summary = generate_weekly_pulse(weeks=1)

# Draft email (don't send)
subject, html, text, result = draft_and_send_pulse_email(
    summary=summary,
    send=False
)

# Or send immediately
subject, html, text, result = draft_and_send_pulse_email(
    summary=summary,
    to_email="team@company.com",
    send=True
)

# Check result
if result['success']:
    print(f"Sent! Message ID: {result['message_id']}")
else:
    print(f"Failed: {result['error']}")
```

## Test Results

```
============================================================
STEP 4 TEST: Email Drafting
============================================================
  ✓ PASS: Subject Generation
  ✓ PASS: Plain Text Email
  ✓ PASS: HTML Email
  ✓ PASS: Full Pipeline
  ✓ PASS: Resend Config

============================================================
✓ ALL TESTS PASSED
============================================================
```

## Files

| File | Purpose |
|------|---------|
| `src/email_drafter.py` | Email generation and sending module |
| `test_email_drafter.py` | Test script |
| `artifacts/emails/` | Saved email drafts |

## Output Files

Email drafts are saved with timestamps:

```
artifacts/emails/
├── email_20251203_203331.html
├── email_20251203_203331.txt
└── ...
```

## Components

### 1. Subject Generator (`generate_email_subject`)

Creates informative email subjects:

```python
subject = generate_email_subject(summary)
# "📊 IND MONEY Weekly Pulse (Dec 03) - 63 Issues Found: Customer Support Issues"
```

### 2. Plain Text Generator (`generate_plain_text_email`)

Creates ASCII-formatted email for text-only clients:

- Fixed-width formatting
- Section dividers
- Priority indicators in brackets `[HIGH]`

### 3. HTML Generator (`generate_html_email`)

Creates styled HTML email:

- **Inline Styles**: All CSS is inlined for email client compatibility
- **Gradient Header**: Visual branding
- **Stats Bar**: Quick metrics overview
- **Priority Colors**: Red/Yellow/Green indicators
- **Responsive**: Mobile-friendly layout

### 4. Resend Integration (`send_email`)

Sends via Resend API:

```python
result = send_email(
    to_email="recipient@example.com",
    subject="Weekly Pulse",
    html_body=html_content,
    text_body=text_content
)
```

## Key Design Decisions

### 1. Dual Format Output

Both HTML and plain text versions are generated:
- **HTML**: Rich formatting for modern email clients
- **Plain Text**: Fallback for accessibility and text-only clients

### 2. Inline CSS

All styles are inlined because:
- Many email clients strip `<style>` tags
- Gmail, Outlook, Yahoo have varying support
- Inline styles have best cross-client compatibility

### 3. Local Draft Storage

All emails are saved locally before sending:
- Audit trail
- Easy review before production sends
- Debugging failed sends

### 4. Graceful Degradation

If Resend isn't configured:
- Email is still drafted and saved
- Error clearly indicates missing configuration
- No crashes or failures

## Next Steps

**Step 5: Cron Automation** will:
1. Create cron job entry point
2. Schedule weekly runs
3. Add logging and error handling
4. Set up monitoring/alerting

