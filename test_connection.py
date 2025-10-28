from dotenv import load_dotenv
import os
import psycopg2

# Load environment variables from .env file
load_dotenv()

try:
    conn = psycopg2.connect(
        host=os.getenv('SUPABASE_HOST'),
        database=os.getenv('SUPABASE_DB'),
        user=os.getenv('SUPABASE_USER'),
        password=os.getenv('SUPABASE_PASSWORD'),
        port=os.getenv('SUPABASE_PORT', 5432)
    )
    print("✅ Connection to Supabase PostgreSQL was successful.")
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")