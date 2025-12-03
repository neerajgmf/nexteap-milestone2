import google.generativeai as genai
import json
from .config import Config

genai.configure(api_key=Config.GEMINI_API_KEY)

def analyze_reviews(reviews_df):
    """
    Analyzes reviews using Gemini to extract themes, quotes, and action items.
    """
    if reviews_df.empty:
        return None

    # Prepare the input text
    reviews_text = ""
    for index, row in reviews_df.iterrows():
        reviews_text += f"- [{row['date'].strftime('%Y-%m-%d')}] {row['source']} ({row['rating']}/5): {row['text']}\n"

    # Truncate if too long (basic safety, though Gemini context is large)
    if len(reviews_text) > 100000:
        reviews_text = reviews_text[:100000] + "...(truncated)"

    prompt = f"""
    You are a Product Analyst for {Config.PRODUCT_NAME}. 
    Analyze the following user reviews from the last {Config.WEEKS_TO_ANALYZE} weeks.
    
    Your goal is to generate a weekly insight report.
    
    Output must be valid JSON with the following structure:
    {{
        "top_themes": [
            {{
                "title": "Theme Title (e.g., Login Issues)",
                "description": "Brief description of the theme.",
                "sentiment": "positive|neutral|negative",
                "count": "Estimated number of reviews related to this"
            }}
        ],
        "user_quotes": [
            "Direct quote from a user 1",
            "Direct quote from a user 2",
            "Direct quote from a user 3"
        ],
        "action_ideas": [
            "Actionable idea 1",
            "Actionable idea 2",
            "Actionable idea 3"
        ]
    }}
    
    Constraints:
    - Max {Config.MAX_THEMES} themes.
    - Select real, impactful user quotes.
    - Action ideas should be specific and derived from the themes.
    - Do NOT include any PII (names, emails, etc.).
    
    Reviews:
    {reviews_text}
    """

    model = genai.GenerativeModel('gemini-2.0-flash')
    
    try:
        response = model.generate_content(prompt)
        # Clean up code blocks if present
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        return json.loads(text)
    except Exception as e:
        print(f"Error analyzing reviews with Gemini: {e}")
        return None
