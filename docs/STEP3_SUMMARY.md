# Step 3: Note Generation (Weekly Pulse)

## Overview

Step 3 generates a one-page weekly pulse document from classified reviews, including top issues, representative quotes, and AI-generated action recommendations.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NOTE GENERATION PIPELINE                        │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Classified Reviews (DB)                                            │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           STEP 1: THEME SELECTION                           │    │
│  │  • Count issues by theme (excluding "No Issue")             │    │
│  │  • Select top 3 problem themes by frequency                 │    │
│  │  • Calculate stats: count, %, avg rating, sentiment         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           STEP 2: QUOTE EXTRACTION                          │    │
│  │  • Select 3 representative quotes per theme                 │    │
│  │  • Prioritize negative sentiment (most actionable)          │    │
│  │  • Filter PII from quotes                                   │    │
│  │  • Choose medium-length reviews (not too short/long)        │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           STEP 3: ACTION GENERATION                         │    │
│  │  • Send themes + quotes to LLM (Claude Sonnet 4)            │    │
│  │  • Generate 3 specific, actionable recommendations          │    │
│  │  • Include priority (high/medium/low) and effort estimate   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           STEP 4: PULSE ASSEMBLY                            │    │
│  │  • Generate Markdown document                               │    │
│  │  • Generate styled HTML version                             │    │
│  │  • Save to artifacts/pulses/                                │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Output: Weekly Pulse Document

### Sample Output

```markdown
# IND MONEY Weekly Pulse

**Period:** September 10 - December 03, 2025  
**Total Reviews:** 550  
**Reviews with Issues:** 63 (11.5%)

---

## 🔍 Top Issues This Week

### 1. Customer Support Issues
**19 mentions** (3.5% of reviews) | Avg Rating: ⭐ (1.9)

**What users are saying:**
> "Worst service from the support. A stock is getting delisted 
> and they didn't reply even after 10 days of filing an enquiry."

### 2. App Compatibility
**17 mentions** (3.1% of reviews) | Avg Rating: ⭐⭐ (2.3)

### 3. Data/Chart Accuracy
**12 mentions** (2.2% of reviews) | Avg Rating: ⭐⭐ (2.7)

---

## 💡 Recommended Actions

### 1. Implement Live Chat Support Widget
🔴 **HIGH** | 📅 Medium

Deploy an in-app live chat system with dedicated support agents...

### 2. Launch Performance Optimization Sprint
🔴 **HIGH** | 📅 Medium

Conduct comprehensive app performance audit...

### 3. Add NPS Tier 2 and EPF Tracking
🟡 **MEDIUM** | 📅 Medium

Integrate NPS Tier 2 account tracking...
```

## Components

### 1. Theme Selector (`select_top_themes`)

Selects the top N problem themes from classified reviews:

```python
top_themes = select_top_themes(df, n=3)
# Returns:
# [
#   {'name': 'Customer Support Issues', 'count': 19, 'percentage': 3.5, ...},
#   {'name': 'App Compatibility', 'count': 17, 'percentage': 3.1, ...},
#   ...
# ]
```

**Filtering:**
- Excludes "No Issue" (positive reviews)
- Excludes "Unknown" (unclassified)
- Sorts by mention count

### 2. Quote Extractor (`extract_quotes`)

Selects representative quotes for each theme:

| Priority | Reason |
|----------|--------|
| Negative sentiment | Most actionable feedback |
| Medium length (20-500 chars) | Not too brief or verbose |
| Diverse content | Avoid similar complaints |

**PII Filtering:** All quotes are cleaned before inclusion.

### 3. Action Generator (`generate_action_ideas`)

Uses Claude Sonnet 4 to generate actionable recommendations:

**Input Context:**
- Theme names and counts
- Sample user quotes
- Product name (IND MONEY)

**Output Format:**
```json
{
  "title": "Short action title (5-10 words)",
  "description": "Detailed description (2-3 sentences)",
  "priority": "high | medium | low",
  "effort": "quick-win | medium | large",
  "addresses_theme": "Theme name"
}
```

**Fallback:** If LLM fails, generates template-based recommendations.

### 4. Pulse Assembler

Generates two output formats:

| Format | Purpose |
|--------|---------|
| **Markdown** (.md) | Easy to read, version control friendly |
| **HTML** (.html) | Styled for email/presentation |

**HTML Styling:**
- Dark theme with accent colors
- Responsive design
- Emoji indicators for priority
- Star ratings for user quotes

## Usage

### Generate Weekly Pulse

```bash
# Default: last week
python -m src.note_generator

# Last 12 weeks
python -m src.note_generator --weeks 12

# Custom output directory
python -m src.note_generator --output-dir reports/
```

### Programmatic Usage

```python
from src.note_generator import generate_weekly_pulse

md, html, summary = generate_weekly_pulse(weeks=1)

# Access results
print(f"Top theme: {summary['top_themes'][0]['name']}")
print(f"Actions: {len(summary['actions'])}")
print(f"Files saved: {summary['files']}")
```

## Test Results

```
============================================================
STEP 3 TEST: Note Generation
============================================================
  ✓ PASS: Theme Selection (top 3 from 42 reviews)
  ✓ PASS: Quote Extraction (3 quotes per theme, PII filtered)
  ✓ PASS: Action Generation (3 AI-generated recommendations)
  ✓ PASS: Full Pipeline (MD + HTML output)

============================================================
✓ ALL TESTS PASSED
============================================================
```

## Files

| File | Purpose |
|------|---------|
| `src/note_generator.py` | Main pulse generation module |
| `test_note_generator.py` | Test script |
| `artifacts/pulses/` | Generated pulse documents |

## Output Files

Generated pulses are saved with timestamps:

```
artifacts/pulses/
├── pulse_20251203_202707.md
├── pulse_20251203_202707.html
└── ...
```

## Key Design Decisions

### 1. Focus on Actionable Issues

Only problem themes are included in the pulse. Positive reviews ("No Issue") are filtered out to ensure every item in the report is actionable.

### 2. Real User Quotes

Quotes are extracted directly from reviews (with PII filtered) rather than AI-generated summaries. This ensures authenticity and helps stakeholders understand the actual user voice.

### 3. Priority + Effort Matrix

Action recommendations include both priority (impact) and effort (cost) to help product teams make informed decisions:

| Priority | Effort | Recommendation |
|----------|--------|----------------|
| High | Quick-win | Do immediately |
| High | Large | Plan for next sprint |
| Medium | Medium | Add to backlog |
| Low | Large | Deprioritize |

### 4. Dual Output Formats

- **Markdown**: For developers, Slack, GitHub issues
- **HTML**: For stakeholders, email distribution, presentations

## Next Steps

**Step 4: Email Drafting** will:
1. Generate email subject and body from pulse
2. Format for email clients (HTML + plain text)
3. Integrate with Resend API for delivery

