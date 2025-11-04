from supabase import create_client
import os
import random

# Load environment variables or Streamlit secrets
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch all exercises
def get_all_exercises():
    response = supabase.table("md_exercises").select("id, name, description").execute()
    return response.data

# Fetch muscle groups
def get_muscle_groups():
    response = supabase.table("md_muscle_groups").select("id, name").execute()
    return response.data

# Fetch exercise-muscle mappings
def get_exercise_mappings():
    response = supabase.table("md_map_exercise_muscle_groups").select("exercise_id, musclegroup_id").execute()
    return response.data

# Build dynamic pools
def build_exercise_pool():
    exercises = get_all_exercises()
    mappings = get_exercise_mappings()
    muscle_groups = {mg["id"]: mg["name"] for mg in get_muscle_groups()}

    pool = {}
    for m_id, m_name in muscle_groups.items():
        pool[m_name] = []

    for map_row in mappings:
        ex_id = map_row["exercise_id"]
        mg_id = map_row["musclegroup_id"]
        exercise = next((e for e in exercises if e["id"] == ex_id), None)
        if exercise:
            pool[muscle_groups[mg_id]].append(exercise["name"])

    return pool

# Example usage
EXERCISE_POOL = build_exercise_pool()
print("Dynamic Exercise Pool:", EXERCISE_POOL)

# Generate warmup dynamically
def generate_warmup(muscles):
    pool = []
    for muscle in muscles:
        pool.extend(EXERCISE_POOL.get(muscle, []))
    selected = random.sample(pool, min(8, len(pool)))
    return {"Warmup Exercises": selected}
