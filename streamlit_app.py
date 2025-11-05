import streamlit as st
from supabase import create_client
from plan_generator import PlanGenerator





# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

plan_gen = PlanGenerator(supabase)

st.title("Workout Plan Generator")

# Fetch muscle groups for selection
muscle_groups = [mg["name"] for mg in supabase.table("md_muscle_groups").select("name").execute().data]
selected_muscles = st.multiselect("Select muscle groups:", muscle_groups)

if st.button("Generate Plan"):

    if selected_muscles:
        plan = plan_gen.generate_daily_plan(selected_muscles)
        st.subheader("Workout Plan")
        st.json(plan)

        st.subheader("Debug Info")
        st.json(plan["Debug"])
    else:
        st.warning("Please select at least one muscle group.")



