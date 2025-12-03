"""
Review Scraper Module
Fetches reviews from Google Play and App Store, enriches with metadata,
stores in Supabase and exports to CSV.
"""

import hashlib
import os
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
from google_play_scraper import Sort, reviews

from .config import Config


def generate_review_hash(text: str, date: str, source: str) -> str:
    """Generate a unique hash for deduplication."""
    content = f"{text}|{date}|{source}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def clean_text(text: str) -> str:
    """Clean review text - remove excess whitespace, normalize."""
    if not text:
        return ""
    # Basic cleanup
    text = " ".join(text.split())
    return text.strip()


def fetch_google_play_reviews(app_id: str, country: str = 'in', lang: str = 'en', count: int = 500) -> pd.DataFrame:
    """
    Fetches reviews from Google Play Store with enriched metadata.
    
    Returns DataFrame with columns:
    - text, rating, date, source, title, username, device, thumbs_up, 
      app_version, developer_replied, review_id, review_hash
    """
    try:
        print(f"  Fetching up to {count} Google Play reviews...")
        result, _ = reviews(
            app_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=count
        )
        
        if not result:
            print("  No Google Play reviews found.")
            return pd.DataFrame()
        
        df = pd.DataFrame(result)
        
        # Build enriched dataframe
        enriched = pd.DataFrame({
            'text': df['content'].apply(clean_text),
            'rating': df['score'],
            'date': pd.to_datetime(df['at'], utc=True),
            'source': 'Google Play',
            'title': '',  # Google Play doesn't have titles in this API
            'username': df.get('userName', '').apply(lambda x: x[:2] + '***' if x else 'Anonymous'),  # Anonymize
            'device': df.get('reviewCreatedVersion', ''),
            'thumbs_up': df.get('thumbsUpCount', 0),
            'app_version': df.get('reviewCreatedVersion', ''),
            'developer_replied': df.get('replyContent', '').apply(lambda x: bool(x) if pd.notna(x) else False),
            'review_id': df.get('reviewId', ''),
        })
        
        # Generate hash for deduplication
        enriched['review_hash'] = enriched.apply(
            lambda row: generate_review_hash(row['text'], str(row['date']), row['source']), 
            axis=1
        )
        
        print(f"  Fetched {len(enriched)} Google Play reviews.")
        return enriched
        
    except Exception as e:
        print(f"  Error fetching Google Play reviews: {e}")
        return pd.DataFrame()


def fetch_app_store_reviews(app_id: str, country: str = 'in') -> pd.DataFrame:
    """
    Fetches reviews from Apple App Store via RSS feed with enriched metadata.
    
    Note: RSS feed is limited to ~50 most recent reviews.
    """
    try:
        print(f"  Fetching App Store reviews...")
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        entries = data.get('feed', {}).get('entry', [])
        
        reviews_list = []
        for entry in entries:
            # Skip the first entry if it's the app info
            if 'im:rating' not in entry:
                continue
            
            review = {
                'text': clean_text(entry.get('content', {}).get('label', '')),
                'rating': int(entry.get('im:rating', {}).get('label', 0)),
                'date': entry.get('updated', {}).get('label', ''),
                'source': 'App Store',
                'title': entry.get('title', {}).get('label', ''),
                'username': entry.get('author', {}).get('name', {}).get('label', '')[:2] + '***' if entry.get('author') else 'Anonymous',
                'device': '',  # Not available in RSS
                'thumbs_up': int(entry.get('im:voteSum', {}).get('label', 0)) if entry.get('im:voteSum') else 0,
                'app_version': entry.get('im:version', {}).get('label', ''),
                'developer_replied': False,  # Not available in RSS
                'review_id': entry.get('id', {}).get('label', ''),
            }
            reviews_list.append(review)
        
        if not reviews_list:
            print("  No App Store reviews found.")
            return pd.DataFrame()
        
        df = pd.DataFrame(reviews_list)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        
        # Generate hash for deduplication
        df['review_hash'] = df.apply(
            lambda row: generate_review_hash(row['text'], str(row['date']), row['source']), 
            axis=1
        )
        
        print(f"  Fetched {len(df)} App Store reviews.")
        return df
        
    except Exception as e:
        print(f"  Error fetching App Store reviews: {e}")
        return pd.DataFrame()


def save_reviews_to_supabase(df: pd.DataFrame) -> bool:
    """
    Saves reviews to Supabase with upsert (avoids duplicates).
    Returns True on success.
    """
    if df.empty:
        return False
    
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        print("  Supabase credentials not configured. Skipping database save.")
        return False
    
    try:
        from supabase import create_client
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        # Prepare records - map to Supabase schema
        records = []
        for _, row in df.iterrows():
            record = {
                'source': row['source'],
                'review_id': row['review_hash'],  # Use hash as unique ID
                'rating': int(row['rating']),
                'date': row['date'].isoformat() if hasattr(row['date'], 'isoformat') else str(row['date']),
                'content': row['text'],
                'thumbs_up_count': int(row.get('thumbs_up', 0)),
                'app_version': row.get('app_version', ''),
            }
            records.append(record)
        
        # Upsert to avoid duplicates
        result = supabase.table("reviews").upsert(records, on_conflict="source,review_id").execute()
        print(f"  Saved {len(records)} reviews to Supabase.")
        return True
        
    except Exception as e:
        print(f"  Error saving to Supabase: {e}")
        return False


def save_reviews_to_csv(df: pd.DataFrame, filename: str = None) -> str:
    """
    Saves reviews to a timestamped CSV file in artifacts/reviews/.
    Returns the filepath.
    """
    if df.empty:
        return ""
    
    if filename is None:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H%M%S')
        filename = f"reviews_{timestamp}.csv"
    
    # Ensure artifacts directory exists
    artifacts_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'artifacts', 'reviews')
    os.makedirs(artifacts_dir, exist_ok=True)
    
    filepath = os.path.join(artifacts_dir, filename)
    
    # Select columns for export (exclude internal fields)
    export_cols = ['date', 'source', 'rating', 'title', 'text', 'thumbs_up', 'app_version', 'developer_replied']
    available_cols = [c for c in export_cols if c in df.columns]
    
    df[available_cols].to_csv(filepath, index=False)
    print(f"  Saved {len(df)} reviews to {filepath}")
    return filepath


def get_recent_reviews(
    google_play_id: str = None,
    app_store_id: str = None,
    country: str = 'in',
    weeks: int = 12,
    save_to_db: bool = True,
    save_to_csv: bool = True,
    gp_count: int = 500
) -> pd.DataFrame:
    """
    Fetches and combines reviews from both sources for the configured timeframe.
    
    Args:
        google_play_id: Google Play app ID
        app_store_id: App Store app ID  
        country: Country code for both stores
        weeks: Number of weeks to include (8-12 recommended)
        save_to_db: Whether to save to Supabase
        save_to_csv: Whether to export to CSV
        gp_count: Number of Google Play reviews to fetch
        
    Returns:
        DataFrame with all reviews within the date range
    """
    print(f"\n{'='*50}")
    print(f"Fetching reviews for last {weeks} weeks")
    print(f"{'='*50}")
    
    # Use config defaults if not provided
    if google_play_id is None:
        google_play_id = Config.GOOGLE_PLAY_ID
    if app_store_id is None:
        app_store_id = Config.APP_STORE_ID
    
    all_reviews = []
    
    # Fetch Google Play reviews
    if google_play_id:
        gp_reviews = fetch_google_play_reviews(google_play_id, country=country, count=gp_count)
        if not gp_reviews.empty:
            all_reviews.append(gp_reviews)
    
    # Fetch App Store reviews
    if app_store_id:
        as_reviews = fetch_app_store_reviews(app_store_id, country=country)
        if not as_reviews.empty:
            all_reviews.append(as_reviews)
    
    if not all_reviews:
        print("\nNo reviews fetched from any source.")
        return pd.DataFrame()
    
    # Combine all reviews
    combined = pd.concat(all_reviews, ignore_index=True)
    
    # Filter by date range
    cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    combined['date'] = pd.to_datetime(combined['date'], utc=True)
    recent = combined[combined['date'] >= cutoff_date].copy()
    
    # Remove duplicates based on review_hash
    original_count = len(recent)
    recent = recent.drop_duplicates(subset=['review_hash'], keep='first')
    if original_count != len(recent):
        print(f"  Removed {original_count - len(recent)} duplicate reviews.")
    
    # Sort by date descending
    recent = recent.sort_values('date', ascending=False).reset_index(drop=True)
    
    print(f"\n{'='*50}")
    print(f"Total reviews in last {weeks} weeks: {len(recent)}")
    print(f"  - Google Play: {len(recent[recent['source'] == 'Google Play'])}")
    print(f"  - App Store: {len(recent[recent['source'] == 'App Store'])}")
    print(f"{'='*50}")
    
    # Save to database
    if save_to_db:
        save_reviews_to_supabase(recent)
    
    # Save to CSV
    csv_path = ""
    if save_to_csv:
        csv_path = save_reviews_to_csv(recent)
    
    return recent


# Convenience function for CLI usage
def run_ingestion(weeks: int = 12, save_db: bool = True, save_csv: bool = True) -> pd.DataFrame:
    """Run the full ingestion pipeline with default config."""
    return get_recent_reviews(
        weeks=weeks,
        save_to_db=save_db,
        save_to_csv=save_csv
    )
