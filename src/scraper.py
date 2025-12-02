from google_play_scraper import Sort, reviews

import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
from .config import Config

def save_reviews_to_supabase(df):
    """Saves reviews to Supabase."""
    if df.empty:
        return

    try:
        supabase: Client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        # Convert DataFrame to list of dicts
        # Ensure date is string format for JSON serialization if needed, but supabase client handles it usually.
        # We might need to handle duplicates. Upsert is best if we have a unique ID.
        # Since we don't have a unique ID from the source guaranteed to be unique across both, 
        # we might rely on Supabase to generate IDs, but that risks duplicates.
        # For now, let's just insert. A better approach would be to generate a hash of the content+date as ID.
        
        records = df.to_dict(orient='records')
        
        # Convert timestamps to string if needed
        for record in records:
            if isinstance(record['date'], pd.Timestamp):
                record['date'] = record['date'].isoformat()

        # Assuming table name is 'reviews'
        data = supabase.table("reviews").upsert(records, on_conflict="text,date,source").execute()
        print(f"Saved {len(records)} reviews to Supabase.")
        
    except Exception as e:
        print(f"Error saving to Supabase: {e}")

def fetch_google_play_reviews(app_id, country='in', lang='en', count=200):
    """Fetches reviews from Google Play Store."""
    try:
        result, _ = reviews(
            app_id,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=count
        )
        
        df = pd.DataFrame(result)
        if df.empty:
            return pd.DataFrame()

        # Normalize columns
        df = df[['content', 'score', 'at']]
        df.columns = ['text', 'rating', 'date']
        df['source'] = 'Google Play'
        return df
    except Exception as e:
        print(f"Error fetching Google Play reviews: {e}")
        return pd.DataFrame()

import requests

def fetch_app_store_reviews(app_id, country='in'):
    """Fetches reviews from Apple App Store via RSS feed."""
    try:
        # Apple RSS Feed URL
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"
        response = requests.get(url)
        response.raise_for_status()
        
        data = response.json()
        entries = data.get('feed', {}).get('entry', [])
        
        reviews_list = []
        for entry in entries:
            # Skip the first entry if it's the app info (sometimes happens)
            if 'im:rating' not in entry:
                continue
                
            review = {
                'text': entry.get('content', {}).get('label', ''),
                'rating': int(entry.get('im:rating', {}).get('label', 0)),
                'date': entry.get('updated', {}).get('label', ''),
                'source': 'App Store'
            }
            reviews_list.append(review)
            
        df = pd.DataFrame(reviews_list)
        if df.empty:
            return pd.DataFrame()

        # Normalize date
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        print(f"Error fetching App Store reviews: {e}")
        return pd.DataFrame()

def get_recent_reviews(google_play_id=None, app_store_id=None, country='in', weeks=12):
    """Fetches and combines reviews from both sources for the configured timeframe."""
    gp_reviews = pd.DataFrame()
    if google_play_id:
        print(f"Fetching Google Play reviews for {google_play_id}...")
        gp_reviews = fetch_google_play_reviews(google_play_id, country=country)
    
    as_reviews = pd.DataFrame()
    if app_store_id:
        print(f"Fetching App Store reviews for {app_store_id}...")
        as_reviews = fetch_app_store_reviews(app_store_id, country=country)
    
    all_reviews = pd.concat([gp_reviews, as_reviews], ignore_index=True)
    
    if all_reviews.empty:
        return pd.DataFrame()

    # Filter by date
    from datetime import timezone
    cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks)
    all_reviews['date'] = pd.to_datetime(all_reviews['date'], utc=True)
    recent_reviews = all_reviews[all_reviews['date'] >= cutoff_date]
    
    # Save to Supabase
    save_reviews_to_supabase(recent_reviews)
    
    return recent_reviews
