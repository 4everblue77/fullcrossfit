import streamlit as st
from supabase import create_client

# Page config
st.set_page_config(page_title="FullCrossFit Dashboard", page_icon="🏠")

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Session state
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

# Dashboard view
st.title("🏠 Weekly Dashboard")

# Fetch weeks
weeks = supabase.table("plan_weeks").select("*").order("number").execute().data
if not weeks:
    st.warning("No plan found in Supabase.")
    st.stop()

current_week = weeks[0]
week_label = f"Week {current_week['number']}"

# Fetch days and sessions
days = supabase.table("plan_days").select("*").eq("week_id", current_week["id"]).execute().data
day_ids = [d["id"] for d in days]
sessions = supabase.table("plan_sessions").select("*").in_("day_id", day_ids).execute().data

# Build plan structure
full_plan = {week_label: {}}
for day in days:
    day_label = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][day["day_number"]-1]
    if day["is_rest_day"]:
        full_plan[week_label][day_label] = {"Rest": True}
    else:
        day_sessions = [s for s in sessions if s["day_id"] == day["id"]]
        plan = {s["type"]: {
            "completed": s.get("completed", False),
            "session_id": s["id"]
        } for s in day_sessions}
        full_plan[week_label][day_label] = {"plan": plan}

# ✅ Build day labels with completion status
days_list = []
for day_label, day_info in full_plan[week_label].items():
    if day_info.get("Rest"):
        status = "💤"
    else:
        sessions_for_day = day_info["plan"].values()
        if all(s["completed"] for s in sessions_for_day):
            status = "✅"
        else:
            status = "⚫"
    days_list.append(f"{day_label} {status}")

# Show radio with updated labels
selected_day_label = st.radio("Select Day", days_list, horizontal=True)
selected_day = selected_day_label.split()[0]  # Extract actual day name
day_data = full_plan[week_label][selected_day]

# Render sessions
if day_data.get("Rest"):
    st.markdown("**Rest Day 💤**")
else:
    st.markdown(f"### Sessions for {selected_day}")
    for session_type, session_content in day_data["plan"].items():
        icon_map = {
            "Warmup": "🔥", "Heavy": "🏋️", "Olympic": "🏅", "Run": "🏃",
            "WOD": "📦", "Benchmark": "⭐", "Light": "💡", "Skill": "🎯", "Cooldown": "❄️"
        }
        icon = icon_map.get(session_type, "📋")
        indicator = "✅" if session_content.get("completed") else "⚫"

        # Button text: icon + session type + status
        button_text = f"{icon} {session_type}    {indicator}"

        if st.button(button_text, key=session_content["session_id"], use_container_width=True):
            st.session_state.selected_session = {
                "session_id": session_content["session_id"],
                "type": session_type,
                "day": selected_day,
                "week": week_label
            }
            st.switch_page("SessionDetail")  # ✅ Navigate to detail page
