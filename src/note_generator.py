"""
Note Generator Module
Generates a one-page weekly pulse document from classified reviews.

Components:
1. Top 3 Theme Selector - Picks most frequent problem themes
2. Quote Extractor - Selects representative user quotes
3. Action Generator - LLM generates actionable recommendations
4. Pulse Assembler - Creates final HTML/Markdown document
"""

import json
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple, Optional
import pandas as pd

from .config import Config
from .pii_filter import filter_pii


def _call_llm(prompt: str, expect_json: bool = True) -> str:
    """Import and use the LLM caller from themer module."""
    from .themer import _call_llm as themer_call_llm
    return themer_call_llm(prompt, expect_json)


def select_top_themes(df: pd.DataFrame, n: int = 3) -> List[Dict]:
    """
    Select top N problem themes by frequency.
    
    Args:
        df: DataFrame with 'theme' and 'sentiment_label' columns
        n: Number of top themes to select (default: 3)
        
    Returns:
        List of theme dicts with stats
    """
    # Filter out non-actionable themes
    issue_df = df[~df['theme'].isin(['Unknown', 'No Issue'])]
    
    if issue_df.empty:
        print("  No issues found in reviews")
        return []
    
    # Count themes
    theme_counts = issue_df['theme'].value_counts()
    top_themes = theme_counts.head(n)
    
    result = []
    for theme_name, count in top_themes.items():
        theme_df = issue_df[issue_df['theme'] == theme_name]
        
        # Calculate sentiment breakdown
        sentiments = theme_df['sentiment_label'].value_counts().to_dict()
        
        # Calculate average rating if available
        avg_rating = None
        if 'rating' in theme_df.columns:
            avg_rating = round(theme_df['rating'].mean(), 1)
        
        result.append({
            'name': theme_name,
            'count': int(count),
            'percentage': round((count / len(df)) * 100, 1),
            'avg_rating': avg_rating,
            'sentiments': sentiments,
            'negative_count': sentiments.get('negative', 0),
        })
    
    return result


def extract_quotes(df: pd.DataFrame, theme: str, n: int = 3) -> List[Dict]:
    """
    Extract representative quotes for a theme.
    
    Prioritizes:
    1. Negative sentiment (most actionable)
    2. Medium-length reviews (not too short, not too long)
    3. Diversity in content
    
    Args:
        df: DataFrame with reviews
        theme: Theme name to extract quotes for
        n: Number of quotes to extract
        
    Returns:
        List of quote dicts
    """
    text_col = 'text' if 'text' in df.columns else 'content'
    theme_df = df[df['theme'] == theme].copy()
    
    if theme_df.empty:
        return []
    
    quotes = []
    
    # Prioritize negative reviews first
    for sentiment in ['negative', 'neutral', 'positive']:
        if len(quotes) >= n:
            break
            
        sentiment_df = theme_df[theme_df['sentiment_label'] == sentiment]
        if sentiment_df.empty:
            continue
        
        # Calculate text lengths
        sentiment_df = sentiment_df.copy()
        sentiment_df['text_len'] = sentiment_df[text_col].str.len()
        
        # Filter to reasonable length (20-500 chars)
        good_length = sentiment_df[
            (sentiment_df['text_len'] >= 20) & 
            (sentiment_df['text_len'] <= 500)
        ]
        
        if good_length.empty:
            good_length = sentiment_df
        
        # Sort by length closest to median
        median_len = good_length['text_len'].median()
        good_length = good_length.copy()
        good_length['len_diff'] = abs(good_length['text_len'] - median_len)
        good_length = good_length.sort_values('len_diff')
        
        # Take quotes we need
        for _, row in good_length.iterrows():
            if len(quotes) >= n:
                break
            
            # Clean and filter PII
            quote_text = filter_pii(str(row[text_col]))
            
            # Skip if too short after cleaning
            if len(quote_text) < 15:
                continue
            
            # Truncate if needed
            if len(quote_text) > 200:
                quote_text = quote_text[:197] + "..."
            
            quotes.append({
                'text': quote_text,
                'sentiment': sentiment,
                'rating': int(row['rating']) if 'rating' in row and pd.notna(row['rating']) else None,
                'date': str(row['date'])[:10] if 'date' in row else None,
                'source': row.get('source', 'Unknown'),
            })
    
    return quotes[:n]


def generate_action_ideas(themes: List[Dict], quotes_by_theme: Dict[str, List[Dict]], n: int = 3) -> List[Dict]:
    """
    Generate actionable recommendations using LLM.
    
    Args:
        themes: List of top theme dicts
        quotes_by_theme: Dict mapping theme names to their quotes
        n: Number of action ideas to generate
        
    Returns:
        List of action idea dicts
    """
    if not themes:
        return []
    
    # Build context for LLM
    themes_context = []
    for theme in themes:
        theme_quotes = quotes_by_theme.get(theme['name'], [])
        quotes_text = "\n".join([f'  - "{q["text"]}"' for q in theme_quotes[:3]])
        themes_context.append(f"""
**{theme['name']}** ({theme['count']} mentions, {theme['percentage']}% of reviews)
Sample complaints:
{quotes_text}
""")
    
    themes_text = "\n".join(themes_context)
    
    prompt = f"""You are a product manager analyzing user feedback for {Config.PRODUCT_NAME} app.

## Top User Complaints This Week:
{themes_text}

## Task:
Generate exactly {n} specific, actionable recommendations to address these issues.

## Requirements:
- Each action should be SPECIFIC and IMPLEMENTABLE
- Prioritize by impact (address issues affecting most users first)
- Include both quick wins and longer-term fixes
- Be practical for a mobile app development team

## Output Format:
Return a JSON array with exactly {n} objects:
[
  {{
    "title": "Short action title (5-10 words)",
    "description": "Detailed description of what to do (2-3 sentences)",
    "priority": "high" | "medium" | "low",
    "effort": "quick-win" | "medium" | "large",
    "addresses_theme": "Theme name this action addresses"
  }}
]

Return ONLY the JSON array.
"""

    try:
        text = _call_llm(prompt, expect_json=True)
        
        # Clean up JSON if wrapped in code blocks
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        actions = json.loads(text)
        
        # Validate and clean
        valid_actions = []
        for action in actions[:n]:
            if isinstance(action, dict) and 'title' in action:
                valid_actions.append({
                    'title': action.get('title', ''),
                    'description': action.get('description', ''),
                    'priority': action.get('priority', 'medium'),
                    'effort': action.get('effort', 'medium'),
                    'addresses_theme': action.get('addresses_theme', ''),
                })
        
        return valid_actions
        
    except json.JSONDecodeError as e:
        print(f"  Error parsing actions JSON: {e}")
        print(f"  Raw response: {text[:200]}...")
        return _generate_fallback_actions(themes)
    except Exception as e:
        print(f"  Error generating actions: {e}")
        return _generate_fallback_actions(themes)


def _generate_fallback_actions(themes: List[Dict]) -> List[Dict]:
    """Generate basic action recommendations without LLM when API fails."""
    actions = []
    
    action_templates = {
        'Customer Support': {
            'title': 'Improve customer support response times',
            'description': 'Implement ticket prioritization and set SLA targets for response times. Consider adding live chat support.',
            'effort': 'medium',
        },
        'App': {
            'title': 'Fix app stability and performance issues',
            'description': 'Prioritize crash fixes and performance optimization. Add crash reporting for better debugging.',
            'effort': 'medium',
        },
        'Withdrawal': {
            'title': 'Streamline withdrawal process',
            'description': 'Review and optimize the withdrawal pipeline. Add status tracking and proactive notifications.',
            'effort': 'large',
        },
        'Data': {
            'title': 'Improve data accuracy and display',
            'description': 'Audit data sources for accuracy. Fix display issues and add missing indicators.',
            'effort': 'medium',
        },
        'default': {
            'title': 'Address user complaints',
            'description': 'Review user feedback and prioritize fixes based on impact.',
            'effort': 'medium',
        },
    }
    
    for theme in themes[:3]:
        # Find matching template
        template = action_templates.get('default')
        for key in action_templates:
            if key.lower() in theme['name'].lower():
                template = action_templates[key]
                break
        
        actions.append({
            'title': template['title'],
            'description': template['description'],
            'priority': 'high' if theme.get('negative_count', 0) > 10 else 'medium',
            'effort': template['effort'],
            'addresses_theme': theme['name'],
        })
    
    return actions


def generate_pulse_markdown(
    themes: List[Dict],
    quotes_by_theme: Dict[str, List[Dict]],
    actions: List[Dict],
    period_start: datetime,
    period_end: datetime,
    total_reviews: int,
    reviews_with_issues: int,
) -> str:
    """
    Generate the weekly pulse as Markdown.
    
    Returns:
        Markdown string
    """
    # Header
    md = f"""# {Config.PRODUCT_NAME} Weekly Pulse

**Period:** {period_start.strftime('%B %d')} - {period_end.strftime('%B %d, %Y')}  
**Total Reviews:** {total_reviews}  
**Reviews with Issues:** {reviews_with_issues} ({round(reviews_with_issues/total_reviews*100, 1) if total_reviews > 0 else 0}%)

---

## 🔍 Top Issues This Week

"""
    
    # Top themes
    for i, theme in enumerate(themes, 1):
        md += f"""### {i}. {theme['name']}

**{theme['count']} mentions** ({theme['percentage']}% of reviews) | Avg Rating: {'⭐' * int(theme['avg_rating'] or 3)} ({theme['avg_rating'] or 'N/A'})

"""
        # Add quotes
        quotes = quotes_by_theme.get(theme['name'], [])
        if quotes:
            md += "**What users are saying:**\n\n"
            for quote in quotes:
                rating_stars = '⭐' * (quote['rating'] or 3) if quote['rating'] else ''
                md += f"> \"{quote['text']}\" {rating_stars}\n>\n"
            md += "\n"
    
    # Action items
    md += """---

## 💡 Recommended Actions

"""
    
    for i, action in enumerate(actions, 1):
        priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(action['priority'], '⚪')
        effort_badge = {'quick-win': '⚡ Quick Win', 'medium': '📅 Medium', 'large': '🏗️ Large'}.get(action['effort'], '')
        
        md += f"""### {i}. {action['title']}

{priority_emoji} **{action['priority'].upper()}** | {effort_badge}

{action['description']}

*Addresses: {action['addresses_theme']}*

"""
    
    # Footer
    md += f"""---

*Generated on {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} by AI Review Analyzer*
"""
    
    return md


def generate_pulse_html(markdown_content: str) -> str:
    """
    Convert markdown pulse to styled HTML.
    
    Args:
        markdown_content: Markdown string
        
    Returns:
        HTML string
    """
    # Simple markdown to HTML conversion
    html = markdown_content
    
    # Headers
    html = html.replace('# ' + Config.PRODUCT_NAME, f'<h1>{Config.PRODUCT_NAME}')
    
    # Convert markdown to basic HTML
    lines = html.split('\n')
    html_lines = []
    in_blockquote = False
    
    for line in lines:
        # Headers
        if line.startswith('### '):
            html_lines.append(f'<h3>{line[4:]}</h3>')
        elif line.startswith('## '):
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '):
            html_lines.append(f'<h1>{line[2:]}</h1>')
        # Blockquotes
        elif line.startswith('> '):
            if not in_blockquote:
                html_lines.append('<blockquote>')
                in_blockquote = True
            html_lines.append(f'<p>{line[2:]}</p>')
        elif line.startswith('>'):
            continue  # Empty blockquote line
        # Horizontal rules
        elif line.strip() == '---':
            if in_blockquote:
                html_lines.append('</blockquote>')
                in_blockquote = False
            html_lines.append('<hr>')
        # Bold
        elif '**' in line:
            import re
            line = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', line)
            html_lines.append(f'<p>{line}</p>')
        # Italic
        elif line.startswith('*') and line.endswith('*'):
            html_lines.append(f'<p><em>{line[1:-1]}</em></p>')
        # Regular paragraph
        elif line.strip():
            if in_blockquote:
                html_lines.append('</blockquote>')
                in_blockquote = False
            html_lines.append(f'<p>{line}</p>')
    
    if in_blockquote:
        html_lines.append('</blockquote>')
    
    body = '\n'.join(html_lines)
    
    # Wrap in HTML template
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{Config.PRODUCT_NAME} Weekly Pulse</title>
    <style>
        :root {{
            --primary: #1a1a2e;
            --secondary: #16213e;
            --accent: #e94560;
            --text: #eaeaea;
            --muted: #a0a0a0;
            --success: #4ecca3;
            --warning: #ffc93c;
            --danger: #ff6b6b;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: var(--text);
            min-height: 100vh;
            padding: 2rem;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: rgba(255,255,255,0.05);
            border-radius: 16px;
            padding: 2rem;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255,255,255,0.1);
        }}
        
        h1 {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
            color: var(--accent);
        }}
        
        h2 {{
            font-size: 1.5rem;
            margin: 1.5rem 0 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--accent);
        }}
        
        h3 {{
            font-size: 1.2rem;
            margin: 1.5rem 0 0.5rem;
            color: var(--success);
        }}
        
        p {{
            margin: 0.5rem 0;
        }}
        
        strong {{
            color: var(--warning);
        }}
        
        blockquote {{
            background: rgba(233, 69, 96, 0.1);
            border-left: 4px solid var(--accent);
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 0 8px 8px 0;
            font-style: italic;
        }}
        
        blockquote p {{
            margin: 0.25rem 0;
        }}
        
        hr {{
            border: none;
            border-top: 1px solid rgba(255,255,255,0.1);
            margin: 2rem 0;
        }}
        
        em {{
            color: var(--muted);
            font-size: 0.9rem;
        }}
        
        .emoji {{
            font-size: 1.2em;
        }}
    </style>
</head>
<body>
    <div class="container">
        {body}
    </div>
</body>
</html>
"""


def generate_weekly_pulse(
    df: pd.DataFrame = None,
    weeks: int = 1,
    output_dir: str = "artifacts/pulses"
) -> Tuple[str, str, Dict]:
    """
    Generate a complete weekly pulse report.
    
    Args:
        df: DataFrame with classified reviews (optional, will load from DB if not provided)
        weeks: Number of weeks to analyze
        output_dir: Directory to save output files
        
    Returns:
        Tuple of (markdown_content, html_content, summary_dict)
    """
    import os
    
    print("\n" + "="*60)
    print("Generating Weekly Pulse")
    print("="*60)
    
    # Load data if not provided
    if df is None:
        print("\n[1/5] Loading classified reviews from database...")
        from supabase import create_client
        supabase = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
        
        cutoff = (datetime.now(timezone.utc) - timedelta(weeks=weeks)).isoformat()
        result = supabase.table('reviews').select('*').gte('date', cutoff).execute()
        
        if not result.data:
            print("No reviews found in database.")
            return "", "", {}
        
        df = pd.DataFrame(result.data)
        df['text'] = df['content']
        
        # Check if reviews are classified
        if 'topics' not in df.columns or df['topics'].isna().all():
            print("  Reviews not classified. Running theme extraction first...")
            from .themer import extract_themes_from_reviews
            df, _ = extract_themes_from_reviews(df, max_themes=Config.MAX_THEMES)
        else:
            # Extract theme from topics array
            df['theme'] = df['topics'].apply(lambda x: x[0] if isinstance(x, list) and x else 'Unknown')
    
    print(f"  Loaded {len(df)} reviews")
    
    # Calculate period
    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(weeks=weeks)
    
    # Step 2: Select top themes
    print("\n[2/5] Selecting top 3 themes...")
    top_themes = select_top_themes(df, n=3)
    
    if not top_themes:
        print("  No actionable themes found")
        return "", "", {}
    
    for theme in top_themes:
        print(f"  • {theme['name']}: {theme['count']} mentions ({theme['percentage']}%)")
    
    # Step 3: Extract quotes
    print("\n[3/5] Extracting representative quotes...")
    quotes_by_theme = {}
    for theme in top_themes:
        quotes = extract_quotes(df, theme['name'], n=3)
        quotes_by_theme[theme['name']] = quotes
        print(f"  • {theme['name']}: {len(quotes)} quotes")
    
    # Step 4: Generate action ideas
    print("\n[4/5] Generating action recommendations...")
    actions = generate_action_ideas(top_themes, quotes_by_theme, n=3)
    print(f"  Generated {len(actions)} action items")
    
    # Step 5: Assemble pulse document
    print("\n[5/5] Assembling pulse document...")
    
    # Calculate stats
    issue_df = df[~df['theme'].isin(['Unknown', 'No Issue'])]
    reviews_with_issues = len(issue_df)
    
    # Generate markdown
    md_content = generate_pulse_markdown(
        themes=top_themes,
        quotes_by_theme=quotes_by_theme,
        actions=actions,
        period_start=period_start,
        period_end=period_end,
        total_reviews=len(df),
        reviews_with_issues=reviews_with_issues,
    )
    
    # Generate HTML
    html_content = generate_pulse_html(md_content)
    
    # Save files
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    md_path = os.path.join(output_dir, f"pulse_{timestamp}.md")
    html_path = os.path.join(output_dir, f"pulse_{timestamp}.html")
    
    with open(md_path, 'w') as f:
        f.write(md_content)
    print(f"  Saved: {md_path}")
    
    with open(html_path, 'w') as f:
        f.write(html_content)
    print(f"  Saved: {html_path}")
    
    # Summary dict
    summary = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'period_start': period_start.isoformat(),
        'period_end': period_end.isoformat(),
        'total_reviews': len(df),
        'reviews_with_issues': reviews_with_issues,
        'top_themes': top_themes,
        'actions': actions,
        'files': {
            'markdown': md_path,
            'html': html_path,
        }
    }
    
    print("\n" + "="*60)
    print("✓ Weekly Pulse Generated Successfully")
    print("="*60)
    
    return md_content, html_content, summary


# CLI entry point
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate weekly pulse report")
    parser.add_argument('--weeks', type=int, default=1, help="Weeks of data to analyze")
    parser.add_argument('--output-dir', type=str, default="artifacts/pulses", help="Output directory")
    args = parser.parse_args()
    
    md, html, summary = generate_weekly_pulse(
        weeks=args.weeks,
        output_dir=args.output_dir
    )
    
    if summary:
        print("\n" + "="*60)
        print("Summary:")
        print("="*60)
        print(json.dumps(summary, indent=2, default=str))

