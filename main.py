import streamlit as st
from supabase import create_client
import random

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

EXERCISE_DURATION = 30
TRANSITION_TIME = 5
WARMUP_TIME = 10  # minutes

# Fetch exercises by category
def get_general_warmup():
    response = supabase.table("md_exercises").select("name").execute()
    return [row["name"] for row in response.data]

# Fetch exercises by muscle group
def get_exercises_by_muscle(muscle):
    # Get muscle group ID
    mg_response = supabase.table("md_muscle_groups").select("id").eq("name", muscle).execute()
    if not mg_response.data:
        return []
    mg_id = mg_response.data[0]["id"]

    # Get exercise IDs mapped to this muscle group
    map_response = supabase.table("md_map_exercise_muscle_groups").select("exercise_id").eq("musclegroup_id", mg_id).execute()
    exercise_ids = [row["exercise_id"] for row in map_response.data]

    if not exercise_ids:
        return []

    # Fetch exercise names
    ex_response = supabase.table("md_exercises").select("name").in_("id", exercise_ids).execute()
    return [row["name"] for row in ex_response.data]

# Generate warmup plan
def generate_warmup(muscles):
    general_pool = get_general_warmup()
    general_selected = random.sample(general_pool, min(8, len(general_pool)))

    specific_pool = []
    for muscle in muscles:
        specific_pool.extend(get_exercises_by_muscle(muscle))
    specific_selected = random.sample(specific_pool, min(8, len(specific_pool)))

    general_plan = [{"exercise": ex, "duration": EXERCISE_DURATION, "transition": TRANSITION_TIME} for ex in general_selected]
    specific_plan = [{"exercise": ex, "duration": EXERCISE_DURATION, "transition": TRANSITION_TIME} for ex in specific_selected]

    return {
        "type": "Warmup",
        "muscles": muscles,
        "time": WARMUP_TIME,
        "details": "10-minute warmup split into general and specific components",
        "general": general_plan,
        "specific": specific_plan
    }

# Streamlit UI
st.title("Supabase Warmup Generator")
selected_muscles = st.multiselect("Select muscle groups:", [mg["name"] for mg in supabase.table("md_muscle_groups").select("name").execute().data])

if st.button("Generate Warmup"):
    if selected_muscles:
        warmup = generate_warmup(selected_muscles)
        st.json(warmup)
    else:
