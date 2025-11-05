import streamlit as st
import pandas as pd
from supabase import create_client
from plan_generator import PlanGenerator

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize PlanGenerator
plan_gen = PlanGenerator(supabase)

st.title("12-Week Workout Plan Generator")

debug_mode = st.checkbox("Enable Debug Mode")

# Clear previous plan when button clicked
if "full_plan" not in st.session_state:
    st.session_state.full_plan = None

if st.button("Generate 12-Week Plan"):
    st.session_state.full_plan = None  # Reset previous data
    full_plan = plan_gen.generate_full_plan()
    st.session_state.full_plan = full_plan

# Display plan if available
if st.session_state.full_plan:
    full_plan = st.session_state.full_plan

    # Tabs for each week
    week_tabs = st.tabs([f"Week {i}" for i in range(1, 13)])

    for idx, (week_label, week_data) in enumerate(full_plan.items()):
        with week_tabs[idx]:
            st.subheader(week_label)

            for day_label, day_data in week_data.items():
                st.markdown(f"### {day_label}")
                if day_data.get("Rest"):
                    st.markdown("**Rest Day 💤**")
                else:
                    st.markdown(f"**Target Muscles:** {', '.join(day_data.get('muscles', []))}")
                    st.markdown(f"**Stimulus:** `{day_data.get('stimulus', 'N/A')}`")
                    st.markdown(f"**Estimated Time:** `{day_data.get('estimated_time', 'N/A')} min`")
                
                    for section, content in day_data["plan"].items():
                        if section != "Debug":
                            st.markdown(f"### {section}")
                            if isinstance(content, dict):
                                if "details" in content:
                                    st.markdown(f"**Details:** {content['details']}")
                                st.json(content)
                

    # Export to CSV
    if st.button("Export Plan to CSV"):
        rows = []
        for week_label, week_data in full_plan.items():
            for day_label, day_data in week_data.items():
                if day_data.get("Rest"):
                    rows.append({
                        "Week": week_label,
                        "Day": day_label,
                        "Type": "Rest",
                        "Target Muscles": "",
                        "Stimulus": "",
                        "Estimated Time": ""
                    })
                else:
                    rows.append({
                        "Week": week_label,
                        "Day": day_label,
                        "Type": "Workout",
                        "Target Muscles": ", ".join(day_data.get("muscles", [])),
                        "Stimulus": day_data.get("stimulus", ""),
                        "Estimated Time": day_data.get("estimated_time", "")
                    })
        df = pd.DataFrame(rows)
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "12_week_plan.csv", "text/csv")
