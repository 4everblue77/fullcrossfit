from supabase import create_client
from dotenv import load_dotenv
import os
import random

# Load environment variables
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Create Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Fetch Exercises by Muscle Group and Category ---
def fetch_exercises(muscle_group, category=None):
    # Step 1: Get exercise IDs for the muscle group
    muscle_group_id = get_muscle_group_id(muscle_group)
    mapping_response = supabase.table("md_map_exercise_muscle_groups") \
        .select("exercise_id") \
        .eq("musclegroup_id", muscle_group_id) \
        .execute()

    exercise_ids = [row["exercise_id"] for row in mapping_response.data]

    # Step 2: Fetch exercise names using those IDs
    query = supabase.table("md_exercises").select("name").in_("id", exercise_ids)

    # Optional: Filter by category if provided
    if category:
        query = query.eq("category", category)

    response = query.execute()
    return [row["name"] for row in response.data]

# Helper: Get muscle group ID
def get_muscle_group_id(name):
    response = supabase.table("md_muscle_groups").select("id").eq("name", name).execute()
    return response.data[0]["id"] if response.data else None

# --- Fetch Skill Plan for a Given Week ---
def fetch_skill_plan(skill_name, week):
    response = supabase.table("skill_plans") \
        .select("focus, session_plan") \
        .eq("week", week) \
        .in_("skill_id", supabase.table("skills")
             .select("skill_id")
             .eq("skill_name", skill_name)
             .execute().data) \
        .execute()
    if response.data:
        return {
            "focus": response.data[0]["focus"],
            "session_plan": response.data[0]["session_plan"]
        }
    return None

# --- Generate Warmup Session ---
def generate_warmup(muscles):
    general = fetch_exercises("General", "general warmup")
    specific = []
    for muscle in muscles:
        specific += fetch_exercises(muscle, "specific warmup")
    return {
        "type": "Warmup",
        "muscles": muscles,
        "details": "10-minute warmup split into general and specific components",
        "general": random.sample(general, min(8, len(general))),
        "specific": random.sample(specific, min(8, len(specific)))
    }

# --- Generate Cooldown Session ---
def generate_cooldown(muscles):
    cooldown = []
    for muscle in muscles:
        cooldown += fetch_exercises(muscle, "Cooldown")
    cooldown += fetch_exercises("General", "Cooldown")
    return {
        "type": "Cooldown",
        "muscles": muscles,
        "details": f"10-minute cooldown targeting {', '.join(muscles)}",
        "activities": random.sample(cooldown, min(10, len(cooldown)))
    }

# --- Generate Skill Session ---
def generate_skill_session(skill_name, week):
    plan = fetch_skill_plan(skill_name, week)
    if not plan:
        return {"error": f"No skill plan found for {skill_name} week {week}"}
    return {
        "type": "Skill",
        "week": week,
        "target": skill_name,
        "focus": plan["focus"],
        "details": plan["session_plan"]
    }

# --- Example Usage ---
if __name__ == "__main__":
    week = 3
    skill = "Overhead Squat"
    muscles = ["Shoulders", "Quads"]

    warmup = generate_warmup(muscles)
    cooldown = generate_cooldown(muscles)
    skill_session = generate_skill_session(skill, week)

    print("\n--- Warmup ---")
    print(warmup)

    print("\n--- Skill Session ---")
    print(skill_session)

    print("\n--- Cooldown ---")
    print(cooldown)
