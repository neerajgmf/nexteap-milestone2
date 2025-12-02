import os
import sys

# Add the current directory to the python path so we can import src
sys.path.append(os.getcwd())

from src.scraper import get_recent_reviews
from src.analyzer import analyze_reviews
from src.mailer import send_email

def main():
    print("--- Starting Test Run ---")
    
    # 1. Fetch
    print("\n1. Fetching reviews...")
    reviews = get_recent_reviews()
    print(f"   Fetched {len(reviews)} reviews.")
    if not reviews.empty:
        print("\n   --- Sample Reviews ---")
        print(reviews[['date', 'rating', 'source', 'text']].head(3).to_string())
        print("   ----------------------\n")
    
    if reviews.empty:
        print("   No reviews found. Exiting.")
        return

    # 2. Analyze
    print("\n2. Analyzing reviews with Gemini...")
    analysis = analyze_reviews(reviews)
    if analysis:
        print("   Analysis successful.")
        print(f"   Top Themes: {len(analysis.get('top_themes', []))}")
    else:
        print("   Analysis failed. Exiting.")
        return

    # 3. Email
    print("\n3. Sending email...")
    # Uncomment to actually send email during test
    # email_response = send_email(analysis)
    # print(f"   Email sent: {email_response}")
    
    # For testing, just print the HTML content or structure
    from src.mailer import generate_html_email
    html = generate_html_email(analysis)
    print(f"   Generated HTML length: {len(html)} chars")
    
    # Save HTML to a file for preview
    with open("test_report.html", "w") as f:
        f.write(html)
    print("   Saved preview to test_report.html")

    print("\n--- Test Run Complete ---")

if __name__ == "__main__":
    main()
