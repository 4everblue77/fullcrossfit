import streamlit as st
from supabase import create_client
import os
import random

# Load secrets from Streamlit Cloud
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Fetch data from Supabase
@st.cache_data
def get_all_exercises():
    return supabase.table("md_exercises").select("id, name, description").execute().data

@st.cache_data
def get_muscle_groups():
    return supabase.table("md_muscle_groups").select("id, name").execute().data

@st.cache_data
def get_exercise_mappings():
    return supabase.table("md_map_exercise_muscle_groups").select("exercise_id, musclegroup_id").execute().data

# Build dynamic exercise pool
@st.cache_data
def build_exercise_pool():
    exercises = get_all_exercises()
    mappings = get_exercise_mappings()
    muscle_groups = {mg["id"]: mg["name"] for mg in get_muscle_groups()}

    pool = {m_name: [] for m_name in muscle_groups.values()}
    for map_row in mappings:
        ex_id = map_row["exercise_id"]
        mg_id = map_row["musclegroup_id"]
        exercise = next((e for e in exercises if e["id"] == ex_id), None)
        if exercise:
            pool[muscle_groups[mg_id]].append(exercise["name"])
    return pool

EXERCISE_POOL = build_exercise_pool()

# Streamlit UI
st.title("Supabase-Driven Workout Generator")

st.subheader("Dynamic Exercise Pool")
st.json(EXERCISE_POOL)

# Warmup generator
def generate_warmup(muscles):
    pool = []
    for muscle in muscles:
        pool.extend(EXERCISE_POOL.get(muscle, []))
    selected = random.sample(pool, min(8, len(pool)))
    return selected

st.subheader("Generate Warmup")
selected_muscles = st.multiselect("Select muscle groups:", list(EXERCISE_POOL.keys()))
if st.button("Generate Warmup"):
    if selected_muscles:
        warmup_plan = generate_warmup(selected_muscles)
        st.write("Warmup Exercises:")
        for ex in warmup_plan:
            st.write(f"- {ex}")
    else:
        st.warning("Please select at least one muscle group.")
