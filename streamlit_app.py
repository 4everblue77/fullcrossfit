import streamlit as st
from supabase import create_client
from plan_generator import PlanGenerator

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize plan generator
plan_gen = PlanGenerator(supabase)

st.title("12-Week Workout Plan Generator")

debug_mode = st.checkbox("Enable Debug Mode")
view_mode = st.radio("Select View Mode:", ["Weekly Summary", "Daily Details"])

if st.button("Generate 12-Week Plan"):
    full_plan = plan_gen.generate_full_plan()

    for week_label, week_data in full_plan.items():
        st.header(week_label)

        if view_mode == "Weekly Summary":
            for day_label, day_data in week_data.items():
                if day_data.get("Rest"):
                    st.markdown(f"**{day_label}:** Rest Day 💤")
                else:
                    muscles = ", ".join(day_data["muscles"])
                    stim = day_data["stimulus"]
                    time = day_data["estimated_time"]
                    st.markdown(f"**{day_label}:** {muscles} | Stimulus: `{stim}` | Estimated Time: `{time} min`")
        else:
            for day_label, day_data in week_data.items():
                st.subheader(f"{day_label}")
                if day_data.get("Rest"):
                    st.markdown("**Rest Day 💤**")
                else:
                    st.markdown(f"**Target Muscles:** {', '.join(day_data['muscles'])}")
                    st.markdown(f"**Stimulus:** `{day_data['stimulus']}`")
                    st.markdown(f"**Estimated Time:** `{day_data['estimated_time']} min`")

                    for section, content in day_data["plan"].items():
                        if section != "Debug":
                            st.markdown(f"**{section}**")
                            st.json(content)

                    if debug_mode:
                        st.markdown("**Debug Info**")
                        st.json(day_data["plan"].get("Debug", {}))
