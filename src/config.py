import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # LLM Provider - OpenRouter (recommended) or Gemini
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    
    # Fallback to Gemini if OpenRouter not configured
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    
    # Email
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")
    SENDER_EMAIL = os.getenv("SENDER_EMAIL", "onboarding@resend.dev")
    RECIPIENT_EMAIL = os.getenv("RECIPIENT_EMAIL")
    
    # Supabase
    SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

    # Product Details
    PRODUCT_NAME = "IND MONEY"
    GOOGLE_PLAY_ID = "in.indwealth"
    APP_STORE_ID = "1450178837"
    APP_STORE_COUNTRY = "in"

    # Analysis Settings
    MAX_THEMES = 5
    WEEKS_TO_ANALYZE = 12
    
    @classmethod
    def get_llm_provider(cls) -> str:
        """Return which LLM provider is configured."""
        if cls.OPENROUTER_API_KEY:
            return "openrouter"
        elif cls.GEMINI_API_KEY:
            return "gemini"
        return "none"
