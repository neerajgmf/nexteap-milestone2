#!/usr/bin/env python3
"""
Quick Stats CLI
Console-based analytics for review data with rich formatting.

Usage:
    python utils/quick_stats.py                    # Fetch fresh data and show stats
    python utils/quick_stats.py --from-db         # Load from Supabase database
    python utils/quick_stats.py --csv path.csv    # Analyze existing CSV
    python utils/quick_stats.py --weeks 8         # Specify time window
    python utils/quick_stats.py --no-fetch        # Use last saved CSV
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

console = Console()


def get_latest_csv() -> str:
    """Find the most recent CSV in artifacts/reviews/"""
    artifacts_dir = Path(__file__).parent.parent / 'artifacts' / 'reviews'
    if not artifacts_dir.exists():
        return None
    
    csvs = list(artifacts_dir.glob('*.csv'))
    if not csvs:
        return None
    
    # Sort by modification time, get newest
    return str(max(csvs, key=lambda p: p.stat().st_mtime))


def load_from_supabase(weeks: int = 12) -> pd.DataFrame:
    """Load reviews directly from Supabase database."""
    from src.config import Config
    
    if not Config.SUPABASE_URL or not Config.SUPABASE_KEY:
        console.print("[red]Supabase credentials not configured.[/red]")
        return pd.DataFrame()
    
    try:
        from supabase import create_client
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        # Calculate cutoff date
        cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).isoformat()
        
        # Fetch reviews from DB
        result = supabase.table('reviews').select('*').gte('date', cutoff).order('date', desc=True).execute()
        
        if not result.data:
            console.print("[yellow]No reviews found in database.[/yellow]")
            return pd.DataFrame()
        
        df = pd.DataFrame(result.data)
        
        # Rename columns to match expected format
        column_map = {
            'content': 'text',
            'thumbs_up_count': 'thumbs_up'
        }
        df = df.rename(columns=column_map)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        
        console.print(f"[green]Loaded {len(df)} reviews from Supabase[/green]")
        return df
        
    except Exception as e:
        console.print(f"[red]Error loading from Supabase: {e}[/red]")
        return pd.DataFrame()


def load_reviews(csv_path: str = None, fetch_fresh: bool = True, from_db: bool = False, weeks: int = 12) -> pd.DataFrame:
    """Load reviews from CSV, database, or fetch fresh."""
    
    # Option 1: Load from database
    if from_db:
        console.print("[cyan]Loading from Supabase database...[/cyan]")
        return load_from_supabase(weeks=weeks)
    
    # Option 2: Load from specific CSV
    if csv_path and os.path.exists(csv_path):
        console.print(f"[dim]Loading from: {csv_path}[/dim]")
        df = pd.read_csv(csv_path)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        return df
    
    # Option 3: Fetch fresh from APIs
    if fetch_fresh:
        console.print("[cyan]Fetching fresh reviews from APIs...[/cyan]")
        from src.scraper import get_recent_reviews
        return get_recent_reviews(weeks=weeks, save_to_db=False, save_to_csv=True)
    
    # Option 4: Use cached CSV
    latest = get_latest_csv()
    if latest:
        console.print(f"[dim]Using cached: {latest}[/dim]")
        df = pd.read_csv(latest)
        df['date'] = pd.to_datetime(df['date'], utc=True)
        return df
    
    console.print("[red]No data available. Run with --from-db or --fetch to get reviews.[/red]")
    return pd.DataFrame()


def rating_bar(rating: float, max_rating: int = 5, width: int = 10) -> str:
    """Create a simple ASCII bar for rating."""
    filled = int((rating / max_rating) * width)
    empty = width - filled
    return '█' * filled + '░' * empty


def print_overview(df: pd.DataFrame):
    """Print overall statistics."""
    if df.empty:
        console.print("[yellow]No data to analyze.[/yellow]")
        return
    
    total = len(df)
    avg_rating = df['rating'].mean()
    date_range = f"{df['date'].min().strftime('%Y-%m-%d')} → {df['date'].max().strftime('%Y-%m-%d')}"
    
    # Rating color based on score
    if avg_rating >= 4.0:
        rating_color = "green"
    elif avg_rating >= 3.0:
        rating_color = "yellow"
    else:
        rating_color = "red"
    
    overview = Table.grid(padding=(0, 2))
    overview.add_column(style="bold")
    overview.add_column()
    
    overview.add_row("Total Reviews", f"[bold cyan]{total:,}[/bold cyan]")
    overview.add_row("Date Range", f"[dim]{date_range}[/dim]")
    overview.add_row("Avg Rating", f"[{rating_color}]{avg_rating:.2f}/5[/{rating_color}] {rating_bar(avg_rating)}")
    
    console.print(Panel(overview, title="[bold]📊 Overview[/bold]", border_style="blue"))


def print_source_breakdown(df: pd.DataFrame):
    """Print breakdown by source."""
    if df.empty or 'source' not in df.columns:
        return
    
    table = Table(title="📱 By Source", box=box.ROUNDED)
    table.add_column("Source", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Avg Rating", justify="right")
    table.add_column("", justify="left")  # Bar
    
    for source in df['source'].unique():
        subset = df[df['source'] == source]
        count = len(subset)
        avg = subset['rating'].mean()
        
        color = "green" if avg >= 4.0 else "yellow" if avg >= 3.0 else "red"
        table.add_row(
            source,
            str(count),
            f"[{color}]{avg:.2f}[/{color}]",
            rating_bar(avg)
        )
    
    console.print(table)


def print_rating_distribution(df: pd.DataFrame):
    """Print rating distribution histogram."""
    if df.empty or 'rating' not in df.columns:
        return
    
    table = Table(title="⭐ Rating Distribution", box=box.ROUNDED)
    table.add_column("Rating", style="bold", justify="center")
    table.add_column("Count", justify="right")
    table.add_column("Distribution", justify="left")
    
    total = len(df)
    for rating in range(5, 0, -1):
        count = len(df[df['rating'] == rating])
        pct = (count / total) * 100 if total > 0 else 0
        bar_len = int(pct / 2)  # Scale to ~50 chars max
        
        # Color based on rating
        if rating >= 4:
            bar_color = "green"
        elif rating >= 3:
            bar_color = "yellow"
        else:
            bar_color = "red"
        
        bar = f"[{bar_color}]{'█' * bar_len}[/{bar_color}]"
        table.add_row(
            f"{'⭐' * rating}",
            f"{count} ({pct:.1f}%)",
            bar
        )
    
    console.print(table)


def print_weekly_trend(df: pd.DataFrame):
    """Print weekly review volume trend."""
    if df.empty or 'date' not in df.columns:
        return
    
    # Group by week (convert to naive datetime to avoid period warning)
    df = df.copy()
    df['week'] = df['date'].dt.tz_localize(None).dt.to_period('W').dt.start_time
    weekly = df.groupby('week').agg({
        'rating': ['count', 'mean']
    }).reset_index()
    weekly.columns = ['week', 'count', 'avg_rating']
    weekly = weekly.sort_values('week', ascending=False).head(8)  # Last 8 weeks
    
    table = Table(title="📈 Weekly Trend (Last 8 Weeks)", box=box.ROUNDED)
    table.add_column("Week", style="dim")
    table.add_column("Reviews", justify="right")
    table.add_column("Avg", justify="right")
    table.add_column("Volume", justify="left")
    
    max_count = weekly['count'].max() if len(weekly) > 0 else 1
    
    for _, row in weekly.iterrows():
        week_str = row['week'].strftime('%b %d')
        count = int(row['count'])
        avg = row['avg_rating']
        bar_len = int((count / max_count) * 20) if max_count > 0 else 0
        
        color = "green" if avg >= 4.0 else "yellow" if avg >= 3.0 else "red"
        table.add_row(
            week_str,
            str(count),
            f"[{color}]{avg:.1f}[/{color}]",
            f"[cyan]{'█' * bar_len}[/cyan]"
        )
    
    console.print(table)


def print_sample_reviews(df: pd.DataFrame, n: int = 5):
    """Print sample of recent reviews."""
    if df.empty:
        return
    
    console.print(f"\n[bold]📝 Sample Recent Reviews (n={n})[/bold]\n")
    
    samples = df.nsmallest(n, 'date') if 'date' in df.columns else df.head(n)
    
    for _, row in samples.iterrows():
        rating = int(row.get('rating', 0))
        stars = '⭐' * rating + '☆' * (5 - rating)
        source = row.get('source', 'Unknown')
        text = str(row.get('text', ''))[:200]
        if len(str(row.get('text', ''))) > 200:
            text += '...'
        date_str = row['date'].strftime('%Y-%m-%d') if pd.notna(row.get('date')) else ''
        
        color = "green" if rating >= 4 else "yellow" if rating >= 3 else "red"
        
        console.print(Panel(
            f"[dim]{date_str} • {source}[/dim]\n{stars}\n\n{text}",
            border_style=color,
            padding=(0, 1)
        ))


def print_low_rating_alerts(df: pd.DataFrame, threshold: int = 2, n: int = 3):
    """Highlight recent low-rating reviews."""
    if df.empty:
        return
    
    low_rated = df[df['rating'] <= threshold].head(n)
    if low_rated.empty:
        console.print(f"\n[green]✓ No reviews with rating ≤{threshold} in recent data[/green]")
        return
    
    console.print(f"\n[bold red]⚠️  Low Rating Alerts (rating ≤{threshold})[/bold red]\n")
    
    for _, row in low_rated.iterrows():
        text = str(row.get('text', ''))[:150]
        if len(str(row.get('text', ''))) > 150:
            text += '...'
        date_str = row['date'].strftime('%Y-%m-%d') if pd.notna(row.get('date')) else ''
        
        console.print(Panel(
            f"[dim]{date_str}[/dim] [red]{'⭐' * int(row['rating'])}[/red]\n{text}",
            border_style="red"
        ))


def main():
    parser = argparse.ArgumentParser(description="Quick stats for app reviews")
    parser.add_argument('--csv', type=str, help="Path to CSV file to analyze")
    parser.add_argument('--from-db', action='store_true', help="Load reviews from Supabase database")
    parser.add_argument('--weeks', type=int, default=12, help="Weeks of data to fetch (default: 12)")
    parser.add_argument('--no-fetch', action='store_true', help="Don't fetch new data, use cached CSV")
    parser.add_argument('--samples', type=int, default=3, help="Number of sample reviews to show")
    args = parser.parse_args()
    
    console.print("\n[bold blue]═══════════════════════════════════════════════════[/bold blue]")
    console.print("[bold]         IND MONEY Review Analytics Console[/bold]")
    console.print("[bold blue]═══════════════════════════════════════════════════[/bold blue]\n")
    
    # Load data
    df = load_reviews(
        csv_path=args.csv,
        fetch_fresh=not args.no_fetch and not args.from_db,
        from_db=args.from_db,
        weeks=args.weeks
    )
    
    if df.empty:
        return
    
    console.print()
    
    # Print all stats
    print_overview(df)
    console.print()
    print_source_breakdown(df)
    console.print()
    print_rating_distribution(df)
    console.print()
    print_weekly_trend(df)
    print_low_rating_alerts(df)
    
    if args.samples > 0:
        print_sample_reviews(df, n=args.samples)
    
    console.print("\n[dim]Run with --help for more options[/dim]\n")


if __name__ == "__main__":
    main()

