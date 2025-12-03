import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev") # Default Resend testing email
    RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL") # User's email
    
    SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    # Use service role key for writes (bypasses RLS), fallback to anon key
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    # Product Details
    PRODUCT_NAME = "IND MONEY"
    GOOGLE_PLAY_ID = "in.indwealth"
    APP_STORE_ID = "1450178837"
    APP_STORE_COUNTRY = "in"

    # Analysis Settings
    MAX_THEMES = 5
    WEEKS_TO_ANALYZE = 12
