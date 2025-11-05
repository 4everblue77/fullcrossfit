import streamlit as st
from supabase import create_client
from plan_generator import PlanGenerator
import pandas as pd

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize PlanGenerator
plan_gen = PlanGenerator(supabase)

st.title("12-Week CrossFit Plan Generator")

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
            st.header(week_label)

            for day_label, day_data in week_data.items():
                st.subheader(day_label)

                if day_data.get("Rest"):
                    st.markdown("**Rest Day 💤**")
                else:
                    st.markdown(f"**Target Muscles:** {', '.join(day_data.get('muscles', []))}")
                    st.markdown(f"**Stimulus:** `{day_data.get('stimulus', 'N/A')}`")
                    st.markdown(f"**Estimated Time:** `{day_data.get('estimated_time', 'N/A')} min`")

                    # Show each section with Tuesday/Thursday logic applied
                    if "plan" in day_data:
                        for section, content in day_data["plan"].items():
                            if section != "Debug":
                                # Skip Light on Tuesday and Warmup/Cooldown/Light on Thursday
                                if (day_label == "Tue" and section == "Light") or \
                                   (day_label == "Thu" and section in ["Warmup", "Cooldown", "Light"]):
                                    continue

                                st.markdown(f"### {section}")
                                if isinstance(content, dict):
                                    if "details" in content:
                                        st.markdown(f"**Details:** {content['details']}")
                                    st.json(content)
                                else:
                                    st.json(content)

                    if debug_mode and "Debug" in day_data.get("plan", {}):
                        st.markdown("**Debug Info**")
                        st.json(day_data["plan"]["Debug"])

    # Export to CSV
    if st.button("Export Plan to CSV"):
        rows = []
        for week_label, week_data in full_plan.items():
            for day_label, day_data in week_data.items():
                if day_data.get("Rest"):
                    rows.append([week_label, day_label, "Rest", "", "", "", ""])
                else:
                    if "plan" in day_data:
                        for section, content in day_data["plan"].items():
                            if section != "Debug" and isinstance(content, dict):
                                # Apply Tuesday/Thursday logic for export
                                if (day_label == "Tue" and section == "Light") or \
                                   (day_label == "Thu" and section in ["Warmup", "Cooldown", "Light"]):
                                    continue

                                rows.append([
                                    week_label,
                                    day_label,
                                    section,
                                    ", ".join(day_data.get("muscles", [])),
                                    day_data.get("stimulus", ""),
                                    content.get("details", ""),
                                    content.get("time", "")
                                ])
        df = pd.DataFrame(rows, columns=["Week", "Day", "Type", "Target Muscles", "Stimulus", "Details", "Duration"])
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "12_week_plan.csv", "text/csv")
