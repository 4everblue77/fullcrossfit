from supabase import create_client
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Missing Supabase credentials. Check your .env file.")
else:
    try:
        # Create Supabase client
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Test query: fetch rows from 'skills' table
        response = supabase.table("skills").select("*").limit(5).execute()

        print("✅ Connection successful! Sample data:")
        print(response.data)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
