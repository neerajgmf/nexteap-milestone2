"""
Theme Extraction & Classification Module
Dynamically discovers themes from reviews and classifies them using LLM.

Two-phase approach:
1. Theme Discovery: Analyze sample reviews to identify top ≤5 themes
2. Theme Classification: Assign each review to discovered themes

Supports:
- OpenRouter (recommended): Access to 100+ models via unified API
- Google Gemini (fallback): Direct Gemini API
"""

import json
import random
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
import pandas as pd

from .config import Config
from .pii_filter import filter_pii, batch_filter_pii

# Initialize LLM client based on configuration
_llm_client = None
_llm_provider = None


def _get_llm_client():
    """Get or create the LLM client based on configuration."""
    global _llm_client, _llm_provider
    
    if _llm_client is not None:
        return _llm_client, _llm_provider
    
    provider = Config.get_llm_provider()
    
    if provider == "openrouter":
        from openai import OpenAI
        _llm_client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=Config.OPENROUTER_API_KEY,
        )
        _llm_provider = "openrouter"
        print(f"  Using OpenRouter with model: {Config.OPENROUTER_MODEL}")
    elif provider == "gemini":
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        _llm_client = genai
        _llm_provider = "gemini"
        print("  Using Google Gemini")
    else:
        raise ValueError("No LLM provider configured. Set OPENROUTER_API_KEY or GEMINI_API_KEY")
    
    return _llm_client, _llm_provider


def _call_llm(prompt: str, expect_json: bool = True) -> str:
    """
    Call the configured LLM provider with a prompt.
    
    Args:
        prompt: The prompt text
        expect_json: If True, request JSON output format
        
    Returns:
        The LLM response text
    """
    client, provider = _get_llm_client()
    
    if provider == "openrouter":
        # OpenRouter uses OpenAI-compatible API
        kwargs = {
            "model": Config.OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
        }
        if expect_json:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message.content.strip()
    
    elif provider == "gemini":
        # Direct Gemini API
        model = client.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean up JSON if wrapped in code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
    
    raise ValueError(f"Unknown provider: {provider}")


# Fallback themes only used if discovery fails
FALLBACK_THEMES = {
    "App Performance": "App crashes, freezing, slow loading, bugs, technical issues",
    "User Experience": "UI/UX design, navigation, ease of use, feature discoverability", 
    "Trading & Stocks": "Stock trading, buying/selling, price accuracy, order execution",
    "Account & KYC": "Account setup, KYC verification, login issues, account blocking",
    "Customer Support": "Support response, issue resolution, communication quality",
}


def discover_themes(reviews: List[str], max_themes: int = 5, sample_size: int = 100) -> Dict[str, str]:
    """
    Dynamically discover themes from a sample of reviews using LLM.
    
    Args:
        reviews: List of review texts (already PII-filtered)
        max_themes: Maximum number of themes to discover (default: 5)
        sample_size: Number of reviews to sample for discovery
        
    Returns:
        Dict of theme_name -> description
    """
    if not reviews:
        print("  No reviews for theme discovery, using fallback themes")
        return FALLBACK_THEMES
    
    # Sample reviews for discovery (mix of ratings if available)
    if len(reviews) > sample_size:
        sample = random.sample(reviews, sample_size)
    else:
        sample = reviews
    
    # Prepare sample text
    sample_text = "\n".join([f"- {r[:300]}" for r in sample[:50]])  # Limit for prompt size
    
    prompt = f"""Analyze these user reviews for {Config.PRODUCT_NAME} app and identify the TOP {max_themes} ACTIONABLE problem areas/issues.

## Sample Reviews:
{sample_text}

## Task:
1. Identify the {max_themes} most common PROBLEMS, ISSUES, or PAIN POINTS users mention
2. Focus on SPECIFIC, ACTIONABLE issues - NOT generic praise like "great app" or "love it"
3. Give each theme a short, clear name (2-4 words)
4. Write a brief description of what the problem is

## Output Format:
Return ONLY a JSON object with theme names as keys and descriptions as values.

Example:
{{
  "Withdrawal Delays": "Money withdrawal taking too long, funds stuck, delayed payments",
  "App Crashes": "Application crashing, freezing, not loading properly",
  "KYC Problems": "Verification failing, documents rejected, long approval times",
  "Poor Support": "Unresponsive customer service, long wait times, unhelpful agents",
  "Data Accuracy": "Wrong stock prices, delayed market data, incorrect portfolio values"
}}

IMPORTANT:
- Focus ONLY on problems, complaints, and issues - NOT positive generic feedback
- Exactly {max_themes} themes
- Theme names should be specific and actionable
- Descriptions should explain the actual problem (5-15 words)
- Skip themes like "General Satisfaction" or "Positive Experience"
- Return ONLY valid JSON, no other text
"""

    try:
        text = _call_llm(prompt, expect_json=True)
        themes = json.loads(text)
        
        # Validate we got a dict with string keys/values
        if isinstance(themes, dict) and len(themes) > 0:
            # Limit to max_themes
            if len(themes) > max_themes:
                themes = dict(list(themes.items())[:max_themes])
            
            print(f"  Discovered {len(themes)} themes from reviews:")
            for name, desc in themes.items():
                print(f"    • {name}: {desc[:50]}...")
            return themes
        else:
            raise ValueError("Invalid themes format")
            
    except Exception as e:
        print(f"  Theme discovery failed ({e}), using fallback themes")
        return FALLBACK_THEMES


def get_theme_classification_prompt(reviews: List[str], themes: Dict[str, str] = None) -> str:
    """Generate the prompt for theme classification."""
    
    if themes is None:
        themes = FALLBACK_THEMES
    
    themes_text = "\n".join([f"- **{name}**: {desc}" for name, desc in themes.items()])
    reviews_text = "\n".join([f"{i+1}. {r[:500]}" for i, r in enumerate(reviews)])
    
    return f"""You are analyzing user reviews for {Config.PRODUCT_NAME} app to identify issues and problems.

## Problem Themes to classify into:
{themes_text}
- **No Issue**: Positive reviews without specific complaints or problems

## Task:
Classify each review into ONE of the themes above:
- If review mentions a PROBLEM or COMPLAINT → assign to matching problem theme
- If review is POSITIVE with NO specific issue → assign to "No Issue"

## Reviews to classify:
{reviews_text}

## Output Format:
Return a JSON array where each element has:
- "index": review number (1-based)
- "theme": exact theme name from above (including "No Issue" for positive reviews)
- "sentiment": "positive", "neutral", or "negative"
- "confidence": "high", "medium", or "low"

Example:
[
  {{"index": 1, "theme": "App Crashes", "sentiment": "negative", "confidence": "high"}},
  {{"index": 2, "theme": "No Issue", "sentiment": "positive", "confidence": "high"}}
]

Return ONLY the JSON array, no other text.
"""


def classify_reviews_batch(
    reviews: List[str],
    themes: Dict[str, str] = None,
    batch_size: int = 20
) -> List[Dict]:
    """
    Classify a batch of reviews into themes using Gemini.
    
    Args:
        reviews: List of review texts (already PII-filtered)
        themes: Dict of theme_name -> description (discovered or fallback)
        batch_size: Number of reviews per LLM call
        
    Returns:
        List of classification results
    """
    if not reviews:
        return []
    
    if themes is None:
        themes = FALLBACK_THEMES
    
    all_results = []
    
    # Process in batches
    for i in range(0, len(reviews), batch_size):
        batch = reviews[i:i + batch_size]
        prompt = get_theme_classification_prompt(batch, themes)
        
        try:
            text = _call_llm(prompt, expect_json=True)
            batch_results = json.loads(text)
            
            # Adjust indices to global position
            for result in batch_results:
                result['global_index'] = i + result['index'] - 1
            
            all_results.extend(batch_results)
            print(f"  Classified reviews {i+1}-{min(i+batch_size, len(reviews))}")
            
        except json.JSONDecodeError as e:
            print(f"  Warning: Failed to parse LLM response for batch {i//batch_size + 1}: {e}")
            # Create fallback results
            for j, _ in enumerate(batch):
                all_results.append({
                    'index': j + 1,
                    'global_index': i + j,
                    'theme': 'User Experience',  # Default fallback
                    'sentiment': 'neutral',
                    'confidence': 'low'
                })
        except Exception as e:
            print(f"  Error classifying batch {i//batch_size + 1}: {e}")
            continue
    
    return all_results


def extract_themes_from_reviews(df: pd.DataFrame, max_themes: int = 5) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Extract and assign themes to reviews in a DataFrame.
    
    Two-phase approach:
    1. Discover themes dynamically from the review content
    2. Classify each review into discovered themes
    
    Args:
        df: DataFrame with 'text' or 'content' column
        max_themes: Maximum number of themes to discover (default: 5)
        
    Returns:
        Tuple of (DataFrame with 'theme'/'sentiment_label' columns, discovered themes dict)
    """
    print("\n" + "="*50)
    print("Theme Extraction & Classification")
    print("="*50)
    
    # Get text column
    text_col = 'text' if 'text' in df.columns else 'content'
    if text_col not in df.columns:
        raise ValueError("DataFrame must have 'text' or 'content' column")
    
    # Step 1: Filter PII from all reviews
    print(f"\n[1/4] Filtering PII from {len(df)} reviews...")
    cleaned_texts = batch_filter_pii(df[text_col].fillna('').tolist())
    
    # Step 2: Discover themes dynamically from the reviews
    print(f"\n[2/4] Discovering themes from reviews...")
    discovered_themes = discover_themes(cleaned_texts, max_themes=max_themes)
    
    # Step 3: Classify reviews using discovered themes
    print(f"\n[3/4] Classifying reviews into {len(discovered_themes)} themes...")
    classifications = classify_reviews_batch(cleaned_texts, themes=discovered_themes)
    
    # Step 4: Map results back to DataFrame
    print(f"\n[4/4] Mapping classifications to reviews...")
    
    # Create lookup by global index
    classification_map = {c['global_index']: c for c in classifications}
    
    # Add columns
    themes = []
    sentiments = []
    
    for idx in range(len(df)):
        if idx in classification_map:
            c = classification_map[idx]
            themes.append(c.get('theme', 'Unknown'))
            sentiments.append(c.get('sentiment', 'neutral'))
        else:
            themes.append('Unknown')
            sentiments.append('neutral')
    
    df = df.copy()
    df['theme'] = themes
    df['sentiment_label'] = sentiments
    
    # Print summary
    print("\n" + "="*50)
    print("Discovered Themes:")
    print("="*50)
    for name, desc in discovered_themes.items():
        print(f"  • {name}: {desc}")
    
    print("\n" + "="*50)
    print("Theme Distribution:")
    print("="*50)
    theme_counts = df['theme'].value_counts()
    for theme, count in theme_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {theme}: {count} ({pct:.1f}%)")
    
    print("\nSentiment Distribution:")
    sentiment_counts = df['sentiment_label'].value_counts()
    for sentiment, count in sentiment_counts.items():
        pct = (count / len(df)) * 100
        print(f"  {sentiment}: {count} ({pct:.1f}%)")
    
    return df, discovered_themes


def get_theme_summary(df: pd.DataFrame, discovered_themes: Dict[str, str] = None) -> Dict:
    """
    Generate a summary of themes with representative quotes.
    
    Args:
        df: DataFrame with 'theme' and 'sentiment_label' columns
        discovered_themes: Dict of theme names to descriptions (from discovery phase)
    
    Returns:
        Dict with theme summaries, quotes, and stats
    """
    text_col = 'text' if 'text' in df.columns else 'content'
    
    summary = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_reviews': len(df),
        'discovered_themes': discovered_themes or {},  # Include discovered themes
        'themes': []
    }
    
    # Count reviews with actual issues (excluding "No Issue" and "Unknown")
    issue_df = df[~df['theme'].isin(['Unknown', 'No Issue'])]
    summary['reviews_with_issues'] = len(issue_df)
    summary['reviews_without_issues'] = len(df) - len(issue_df)
    
    for theme in df['theme'].unique():
        # Skip non-actionable themes
        if theme in ['Unknown', 'No Issue']:
            continue
            
        theme_df = df[df['theme'] == theme]
        
        # Get sentiment breakdown
        sentiments = theme_df['sentiment_label'].value_counts().to_dict()
        
        # Get representative quotes (1 per sentiment if available)
        quotes = []
        for sentiment in ['negative', 'neutral', 'positive']:
            sentiment_df = theme_df[theme_df['sentiment_label'] == sentiment]
            if not sentiment_df.empty:
                # Get a medium-length review as quote
                lengths = sentiment_df[text_col].str.len()
                median_len = lengths.median()
                closest_idx = (lengths - median_len).abs().idxmin()
                quote_text = sentiment_df.loc[closest_idx, text_col]
                # Truncate and clean
                quote_text = filter_pii(str(quote_text)[:200])
                if len(str(sentiment_df.loc[closest_idx, text_col])) > 200:
                    quote_text += "..."
                quotes.append({
                    'text': quote_text,
                    'sentiment': sentiment,
                    'rating': int(sentiment_df.loc[closest_idx, 'rating']) if 'rating' in sentiment_df.columns else None
                })
        
        theme_summary = {
            'name': theme,
            'description': discovered_themes.get(theme, '') if discovered_themes else '',
            'count': len(theme_df),
            'percentage': round((len(theme_df) / len(df)) * 100, 1),
            'avg_rating': round(theme_df['rating'].mean(), 2) if 'rating' in theme_df.columns else None,
            'sentiments': sentiments,
            'quotes': quotes[:3]  # Max 3 quotes per theme
        }
        summary['themes'].append(theme_summary)
    
    # Sort themes by count
    summary['themes'].sort(key=lambda x: x['count'], reverse=True)
    
    return summary


def update_reviews_in_db(df: pd.DataFrame) -> bool:
    """
    Update reviews in Supabase with theme and sentiment.
    
    Args:
        df: DataFrame with 'review_id', 'theme', 'sentiment_label' columns
        
    Returns:
        True on success
    """
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        print("Supabase credentials not configured. Skipping DB update.")
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        # Map sentiment to score
        sentiment_scores = {'negative': -1.0, 'neutral': 0.0, 'positive': 1.0}
        
        updated = 0
        for _, row in df.iterrows():
            review_id = row.get('review_id') or row.get('id')
            if not review_id:
                continue
            
            update_data = {
                'topics': [row['theme']],  # Store as array
                'sentiment_label': row['sentiment_label'],
                'sentiment_score': sentiment_scores.get(row['sentiment_label'], 0.0),
                'updated_at': datetime.now(timezone.utc).isoformat()
            }
            
            try:
                supabase.table('reviews').update(update_data).eq('review_id', review_id).execute()
                updated += 1
            except Exception as e:
                # Try with 'id' column
                try:
                    supabase.table('reviews').update(update_data).eq('id', review_id).execute()
                    updated += 1
                except:
                    pass
        
        print(f"Updated {updated}/{len(df)} reviews in Supabase")
        return True
        
    except Exception as e:
        print(f"Error updating Supabase: {e}")
        return False


def run_theme_extraction(weeks: int = 12, update_db: bool = True) -> Tuple[pd.DataFrame, Dict]:
    """
    Run the full theme extraction pipeline.
    
    Args:
        weeks: Number of weeks of data to process
        update_db: Whether to update Supabase with results
        
    Returns:
        Tuple of (classified DataFrame, theme summary dict)
    """
    print("\n" + "="*60)
    print(f"Running Theme Extraction for last {weeks} weeks")
    print("="*60)
    
    # Load reviews from database
    from supabase import create_client
    supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    
    cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).isoformat()
    result = supabase.table('reviews').select('*').gte('date', cutoff).execute()
    
    if not result.data:
        print("No reviews found in database.")
        return pd.DataFrame(), {}
    
    df = pd.DataFrame(result.data)
    df['text'] = df['content']  # Normalize column name
    print(f"Loaded {len(df)} reviews from database")
    
    # Extract themes (returns DataFrame and discovered themes)
    df, discovered_themes = extract_themes_from_reviews(df, max_themes=Config.MAX_THEMES)
    
    # Generate summary with discovered themes
    summary = get_theme_summary(df, discovered_themes)
    
    # Update database
    if update_db:
        print("\nUpdating database with classifications...")
        update_reviews_in_db(df)
    
    return df, summary


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract themes from reviews")
    parser.add_argument('--weeks', type=int, default=12, help="Weeks of data to analyze")
    parser.add_argument('--no-db-update', action='store_true', help="Skip database update")
    args = parser.parse_args()
    
    df, summary = run_theme_extraction(
        weeks=args.weeks,
        update_db=not args.no_db_update
    )
    
    if summary:
        print("\n" + "="*60)
        print("Theme Summary (JSON):")
        print("="*60)
        print(json.dumps(summary, indent=2))

