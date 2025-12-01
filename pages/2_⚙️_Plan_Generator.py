
import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime

# Plan generators
from plan_generators.crossfit_generator import CrossFitPlanGenerator
from plan_generators.phat_generator import PHATPlanGenerator
from plan_generators.run5k_generator import Run5KPlanGenerator

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Sidebar for plan type selection
st.sidebar.title("Plan Options")
plan_type = st.sidebar.selectbox("Select Plan Type", ["CrossFit", "PHAT", "5km Improvement"])

# ✅ New input for start date
start_date = st.date_input("Select Start Date", datetime.today()).isoformat()

# Initialize appropriate plan generator
if plan_type == "CrossFit":
    plan_gen = CrossFitPlanGenerator(supabase)
    
    skills = [s["skill_name"] for s in plan_gen.fetch_skills()]
    selected_skill = st.selectbox("Select Skill for Skill Sessions", skills)

elif plan_type == "PHAT":
    plan_gen = PHATPlanGenerator(supabase)
elif plan_type == "5km Improvement":
    plan_gen = Run5KPlanGenerator(supabase)
else:
    st.warning("Selected plan type is not implemented.")
    st.stop()

st.title(f"6-Week {plan_type} Plan Generator")



debug_mode = st.checkbox("Enable Debug Mode")
sync_to_supabase = st.checkbox("Sync Plan to Supabase")

if "full_plan" not in st.session_state:
    st.session_state.full_plan = None

if st.button(f"Generate 6-Week {plan_type} Plan"):
    st.session_state.full_plan = None
    # ✅ Pass start_date to generator
    full_plan = plan_gen.generate_full_plan(start_date=start_date, skill=selected_skill)
    st.session_state.full_plan = full_plan

    if sync_to_supabase and hasattr(plan_gen, "sync_plan_to_supabase"):
        plan_gen.sync_plan_to_supabase(full_plan)
        st.success("Plan synced to Supabase!")

# Display plan if available
if st.session_state.full_plan:
    full_plan = st.session_state.full_plan
    week_tabs = st.tabs([f"Week {i}" for i in range(1, 7)])

    for idx, (week_label, week_data) in enumerate(full_plan.items()):
        with week_tabs[idx]:
            st.header(week_label)
            for day_label, day_data in week_data.items():
                st.subheader(f"{day_label} ({day_data.get('date', '')})")  # ✅ Show actual date
                if day_data.get("Rest"):
                    st.markdown("**Rest Day 💤**")
                else:
                    st.markdown(f"**Target Muscles:** {', '.join(day_data.get('muscles', []))}")
                    st.markdown(f"**Stimulus:** `{day_data.get('stimulus', 'N/A')}`")
                    st.markdown(f"**Estimated Time:** `{day_data.get('estimated_time', 'N/A')} min`")

                    if "plan" in day_data:
                        for section, content in day_data["plan"].items():
                            if section != "Debug":
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

    if st.button("Export Plan to CSV"):
        rows = []
        for week_label, week_data in full_plan.items():
            for day_label, day_data in week_data.items():
                if day_data.get("Rest"):
                    rows.append([week_label, day_label, day_data.get("date", ""), "Rest", "", "", "", ""])
                else:
                    if "plan" in day_data:
                        for section, content in day_data["plan"].items():
                            if section != "Debug" and isinstance(content, dict):
                                if (day_label == "Tue" and section == "Light") or \
                                   (day_label == "Thu" and section in ["Warmup", "Cooldown", "Light"]):
                                    continue
                                rows.append([
                                    week_label,
                                    day_label,
                                    day_data.get("date", ""),
                                    section,
                                    ", ".join(day_data.get("muscles", [])),
                                    day_data.get("stimulus", ""),
                                    content.get("details", ""),
                                    content.get("time", "")
                                ])
        df = pd.DataFrame(rows, columns=["Week", "Day", "Date", "Type", "Target Muscles", "Stimulus", "Details", "Duration"])
        csv = df.to_csv(index=False)
        st.download_button("Download CSV", csv, "6_week_plan.csv", "text/csv")
