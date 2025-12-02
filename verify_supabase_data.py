import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd

load_dotenv()

SUPABASE_URL = os.getenv("NEXT_PUBLIC_SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
ANON_KEY = os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")

def verify_data():
    if not SUPABASE_URL:
        print("Error: Supabase URL not found.")
        return

    print(f"URL: {SUPABASE_URL}")
    if SERVICE_KEY:
        print(f"Service Key loaded: {SERVICE_KEY[:5]}...")
    else:
        print("Service Key NOT loaded.")
        
    if ANON_KEY:
        print(f"Anon Key loaded: {ANON_KEY[:5]}...")
    else:
        print("Anon Key NOT loaded.")

    client = None
    
    # Try Service Key first
    if SERVICE_KEY:
        try:
            print("\nAttempting connection with Service Key...")
            client = create_client(SUPABASE_URL, SERVICE_KEY)
            # Test query
            client.table("reviews").select("count", count="exact").limit(1).execute()
            print("Success with Service Key!")
        except Exception as e:
            print(f"Failed with Service Key: {e}")
            client = None

    # Try Anon Key if Service Key failed
    if not client and ANON_KEY:
        try:
            print("\nAttempting connection with Anon Key...")
            client = create_client(SUPABASE_URL, ANON_KEY)
            # Test query
            client.table("reviews").select("count", count="exact").limit(1).execute()
            print("Success with Anon Key!")
        except Exception as e:
            print(f"Failed with Anon Key: {e}")
            client = None
            
    if not client:
        print("\nCould not connect to Supabase with either key.")
        return

    try:
        print("\n--- Verifying Google Play Data ---")
        response = client.table("reviews") \
            .select("*") \
            .eq("source", "Google Play") \
            .order("date", desc=True) \
            .limit(5) \
            .execute()
        
        gp_reviews = response.data
        if not gp_reviews:
            print("No Google Play reviews found in Supabase.")
        else:
            for r in gp_reviews:
                print(f"Date: {r.get('date')}, Rating: {r.get('rating')}")
                print(f"Text: {r.get('text')[:100]}...")
                print("-" * 20)

        print("\n--- Verifying App Store Data ---")
        response = client.table("reviews") \
            .select("*") \
            .eq("source", "App Store") \
            .order("date", desc=True) \
            .limit(5) \
            .execute()
            
        as_reviews = response.data
        if not as_reviews:
            print("No App Store reviews found in Supabase.")
        else:
            for r in as_reviews:
                print(f"Date: {r.get('date')}, Rating: {r.get('rating')}")
                print(f"Text: {r.get('text')[:100]}...")
                print("-" * 20)

    except Exception as e:
        print(f"Error querying data: {e}")

if __name__ == "__main__":
    verify_data()
