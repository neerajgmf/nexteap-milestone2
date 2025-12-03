# Step 2: Theme Extraction & Classification

## Overview

Step 2 implements dynamic theme discovery and classification using LLM (Claude Sonnet 4 via OpenRouter). The system automatically identifies **actionable problem areas** from user reviews, filtering out generic positive feedback to focus on issues that need attention.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                     THEME EXTRACTION PIPELINE                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  Reviews (DB)                                                       │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────┐                                                    │
│  │ PII Filter  │  Remove emails, phones, PAN, URLs                  │
│  └─────────────┘                                                    │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           PHASE 1: THEME DISCOVERY                          │    │
│  │  • Sample 50-100 reviews                                    │    │
│  │  • LLM identifies TOP 5 PROBLEM AREAS                       │    │
│  │  • Focus on actionable issues, not generic praise           │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │           PHASE 2: CLASSIFICATION                           │    │
│  │  • Classify each review into discovered themes              │    │
│  │  • "No Issue" for positive reviews without complaints       │    │
│  │  • Assign sentiment: positive/neutral/negative              │    │
│  └─────────────────────────────────────────────────────────────┘    │
│       │                                                             │
│       ▼                                                             │
│  ┌─────────────┐                                                    │
│  │ Update DB   │  Store theme + sentiment in Supabase              │
│  └─────────────┘                                                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. PII Filter (`src/pii_filter.py`)

Removes personally identifiable information before LLM processing:

| Pattern | Example | Replacement |
|---------|---------|-------------|
| Email | `john@email.com` | `[EMAIL]` |
| Phone (Indian) | `+91-9876543210` | `[PHONE]` |
| PAN Card | `ABCDE1234F` | `[PAN]` |
| Aadhaar | `1234 5678 9012` | `[AADHAAR]` |
| URLs | `www.example.com` | `[URL]` |
| IP Addresses | `192.168.1.1` | `[IP]` |

### 2. Theme Discovery

**Key Innovation**: Themes are discovered dynamically from the reviews themselves, not hardcoded.

```python
# Prompt focuses on ACTIONABLE problems
prompt = """Identify the TOP 5 ACTIONABLE problem areas/issues.
Focus on SPECIFIC, ACTIONABLE issues - NOT generic praise like "great app"
"""
```

**Example Discovered Themes:**
- 🔴 **Withdrawal Delays** - "Money withdrawal taking too long from US wallet"
- 🔴 **App Performance Issues** - "Application is laggy, not smooth"
- 🔴 **Poor Customer Support** - "Hard to contact support, unresponsive"
- 🔴 **KYC Account Blocking** - "Federal accounts getting blocked"
- 🔴 **UCID Creation Problems** - "System repeatedly creating new UCID numbers"

### 3. Classification

Each review is classified into:
- One of the discovered problem themes, OR
- **"No Issue"** for positive reviews without specific complaints

Plus sentiment analysis: `positive`, `neutral`, `negative`

## LLM Provider: OpenRouter

Using OpenRouter for flexible model access:

```python
# Config
OPENROUTER_API_KEY=sk-or-v1-xxx
OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

**Benefits:**
- Access to 100+ models via single API
- Easy model switching (Claude, GPT-4, Llama, etc.)
- OpenAI-compatible API format
- Automatic JSON output format

## Files Created/Modified

| File | Purpose |
|------|---------|
| `src/pii_filter.py` | PII detection and removal |
| `src/themer.py` | Theme discovery & classification |
| `src/config.py` | OpenRouter configuration |
| `test_themer.py` | End-to-end test script |

## Usage

### Run Theme Extraction

```bash
# Full pipeline with DB update
python -m src.themer --weeks 12

# Without DB update (dry run)
python -m src.themer --weeks 12 --no-db-update
```

### Test the Pipeline

```bash
python test_themer.py
```

## Test Results

```
============================================================
STEP 2 TEST: Theme Extraction & Classification
============================================================

TEST 1: PII Filter
✓ 5/5 patterns detected correctly

TEST 2: Theme Classification (Sample)
✓ Discovered 5 actionable themes
✓ All reviews classified
✓ "No Issue" assigned to positive reviews

TEST 3: Full Pipeline (30 reviews)
✓ Theme Distribution:
  - No Issue: 23 (76.7%)          ← Positive reviews filtered
  - App Performance Issues: 2 (6.7%)
  - Poor Customer Support: 2 (6.7%)
  - Withdrawal Delays: 1 (3.3%)
  - KYC Account Blocking: 1 (3.3%)
  - UCID Creation Problems: 1 (3.3%)

✓ ALL TESTS PASSED
```

## Key Design Decisions

### 1. Dynamic vs Hardcoded Themes

| Approach | Pros | Cons |
|----------|------|------|
| **Dynamic (Chosen)** | Adapts to changing issues, discovers specific problems | LLM cost per run |
| Hardcoded | Consistent, no LLM cost | Misses emerging issues |

### 2. Problem-Focused Discovery

We explicitly instruct the LLM to focus on **problems and complaints**, not generic positive feedback. This ensures:
- Actionable insights for product teams
- No noise from "Great app!" reviews
- Specific issues like "UCID Creation Problems" are discovered

### 3. "No Issue" Category

Positive reviews are classified as "No Issue" rather than forced into problem themes:
- Cleaner separation of signal vs noise
- Accurate statistics on issue prevalence
- Summary excludes "No Issue" from actionable themes

## Database Schema Update

The existing `reviews` table is updated with:

```sql
-- Updated columns
topics TEXT[]          -- Array containing theme name
sentiment_label TEXT   -- 'positive', 'neutral', 'negative'
sentiment_score FLOAT  -- -1.0 to 1.0
updated_at TIMESTAMP   -- When classification was done
```

## Next Steps

**Step 3: Note Generation** will use the classified themes to:
1. Select top 3 themes by frequency
2. Extract representative user quotes
3. Generate action ideas using LLM
4. Assemble one-page pulse document

