
# 2_⚙️_Plan_Generator.py
import streamlit as st
from supabase import create_client
import pandas as pd
from datetime import datetime, timedelta, date

# Plan generators
from plan_generators.crossfit_generator import CrossFitPlanGenerator, UpdateScope, _normalize_iso_date
from plan_generators.supabase_sync_function import merge_plan_patch_to_supabase

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Sidebar
st.sidebar.title("Plan Options")
plan_type = st.sidebar.selectbox("Select Plan Type", ["CrossFit"])  # Focused for now
st.title(f"6-Week {plan_type} Plan Generator")

# Start date
start_date_dt = st.date_input("Select Start Date", datetime.today()).strftime("%Y-%m-%d")

# Initialize generator
if plan_type == "CrossFit":
    plan_gen = CrossFitPlanGenerator(supabase)
    skills = [s["skill_name"] for s in plan_gen.fetch_skills()]
    selected_skill = st.selectbox("Select Skill for Skill Sessions", skills)
else:
    st.warning("Selected plan type is not implemented.")
    st.stop()

debug_mode = st.checkbox("Enable Debug Mode")
sync_full_wipe = st.checkbox("Sync Full Plan to Supabase (full wipe)")

# Session state
if "full_plan" not in st.session_state:
    st.session_state.full_plan = None
if "patch_plan" not in st.session_state:
    st.session_state.patch_plan = None

# Info panel: Existing plan?
exists = plan_gen.plan_exists(start_date_dt, weeks=6)
st.info(f"Plan exists in Supabase for the 6-week window starting {start_date_dt}: {'Yes' if exists else 'No'}")
# Uses generator-level detector aligned to plan_days.date. [1](https://danone-my.sharepoint.com/personal/john_matthews_danone_com/Documents/Microsoft%20Copilot%20Chat%20Files/2_%E2%9A%99%EF%B8%8F_Plan_Generator.py)

# --- Full plan generation ---
st.subheader("Generate Full Plan")
if st.button(f"Generate 6-Week {plan_type} Plan"):
    st.session_state.full_plan = None
    full_plan = plan_gen.generate_full_plan(start_date=start_date_dt, skill=selected_skill)
    st.session_state.full_plan = full_plan
    if sync_full_wipe:
        plan_gen.sync_plan_to_supabase(full_plan)  # full-wipe first-time creation path [1](https://danone-my.sharepoint.com/personal/john_matthews_danone_com/Documents/Microsoft%20Copilot%20Chat%20Files/2_%E2%9A%99%EF%B8%8F_Plan_Generator.py)
        st.success("Full plan synced to Supabase (full wipe).")

# Display full plan
if st.session_state.full_plan:
    full_plan = st.session_state.full_plan
    week_tabs = st.tabs([f"Week {i}" for i in range(1, 7)])
    for idx, (week_label, week_data) in enumerate(full_plan.items()):
        with week_tabs[idx]:
            st.header(week_label)
            for day_label, day_data in week_data.items():
                st.subheader(f"{day_label} ({day_data.get('date', '')})")
                if day_data.get("Rest"):
                    st.markdown("**Rest Day 💤**")
                else:
                    st.markdown(f"**Target Muscles:** {', '.join(day_data.get('muscles', []))}")
                    st.markdown(f"**Stimulus:** `{day_data.get('stimulus', 'N/A')}`")
                    st.markdown(f"**Estimated Time:** `{day_data.get('estimated_time', 'N/A')} min`")
                    if "plan" in day_data:
                        for section, content in day_data["plan"].items():
                            if section != "Debug":
                                # Keep your previous UI exclusions (Tue Light; Thu Warmup/Cooldown/Light)
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

    # Export CSV
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

# --- Partial update controls ---
st.subheader("Partial Update (Merge Only)")

# Choose scope
weeks_selected = st.multiselect("Weeks to update", options=list(range(1, 7)), default=[])
days_selected = st.multiselect("Days to update", options=["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], default=[])
sections_selected = st.multiselect(
    "Sections to update",
    options=["Warmup", "Heavy", "Olympic", "Run", "WOD", "Benchmark", "Light", "Skill", "Cooldown"],
    default=[]
)

# Provide specific date selection (precomputed 6-week window)
window_dates = [(datetime.strptime(start_date_dt, "%Y-%m-%d").date() + timedelta(days=i)).isoformat() for i in range(42)]
dates_selected = st.multiselect("Specific dates to update (optional)", options=window_dates, default=[])

replace_section = st.radio(
    "Exercise update mode for selected sections",
    options=["Replace exercises in selected sections", "Append exercises to selected sections"],
    index=0
)
replace_flag = (replace_section == "Replace exercises in selected sections")

col_a, col_b = st.columns(2)
with col_a:
    if st.button("Generate Patch"):
        scope = UpdateScope(
            weeks=set(weeks_selected) if weeks_selected else None,
            days=set(days_selected) if days_selected else None,
            dates=set([_normalize_iso_date(d) for d in dates_selected]) if dates_selected else None,
            sections=set(sections_selected) if sections_selected else None
        )
        st.session_state.patch_plan = plan_gen.generate_partial_plan(start_date_dt, scope, skill=selected_skill)
        if st.session_state.patch_plan:
            st.success("Patch generated.")
        else:
            st.warning("Scope produced an empty patch. Adjust your selections.")

with col_b:
    if st.button("Merge Patch to Supabase"):
        if not st.session_state.patch_plan:
            st.warning("Generate a patch first.")
        else:
            summary = plan_gen.sync_partial_plan_to_supabase(
                st.session_state.patch_plan,
                start_date=start_date_dt,
                replace_section=replace_flag
            )  # non-destructive merge aligned to your schema [1](https://danone-my.sharepoint.com/personal/john_matthews_danone_com/Documents/Microsoft%20Copilot%20Chat%20Files/2_%E2%9A%99%EF%B8%8F_Plan_Generator.py)
            st.success(f"Merged: {summary}")

# Show patch if present
if st.session_state.patch_plan:
    st.subheader("Patch preview")
   
