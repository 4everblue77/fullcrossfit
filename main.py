import psycopg2
import random
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Database configuration from environment
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'dbname': os.getenv('DB_NAME'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT', '5432')  # default to 5432
}


def get_connection():
    return psycopg2.connect(**DB_CONFIG)

# --- Fetch Exercises by Muscle Group and Category ---
def fetch_exercises(muscle_group, category):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT e.name
                FROM md_exercises e
                JOIN md_map_exercise_muscle_groups mg ON e.id = mg.exercise_id
                JOIN md_muscle_groups m ON mg.musclegroup_id = m.id
                JOIN md_map_exercise_categories ec ON e.id = ec.exercise_id
                JOIN md_categories c ON ec.category_id = c.id
                WHERE m.name = %s AND c.name ILIKE %s
            """, (muscle_group, category))
            return [row[0] for row in cur.fetchall()]

# --- Fetch Skill Plan for a Given Week ---
def fetch_skill_plan(skill_name, week):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT sp.focus, sp.session_plan
                FROM skill_plans sp
                JOIN skills s ON sp.skill_id = s.skill_id
                WHERE s.skill_name = %s AND sp.week = %s
            """, (skill_name, week))
            result = cur.fetchone()
            if result:
                return {
                    "focus": result[0],
                    "session_plan": result[1]
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
