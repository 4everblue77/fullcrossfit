import streamlit as st
from supabase import create_client

st.set_page_config(page_title="FullCrossFit Dashboard", page_icon="🏠")
st.title("🏠 Weekly Dashboard")

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ✅ Get all weeks
weeks = supabase.table("plan_weeks").select("*").order("number").execute().data
if not weeks:
    st.warning("No plan found in Supabase.")
    st.stop()

# Assume current week is the first one
current_week = weeks[0]
week_label = f"Week {current_week['number']}"

# ✅ Get all days for this week
days = supabase.table("plan_days").select("*").eq("week_id", current_week["id"]).execute().data
day_ids = [d["id"] for d in days]

# ✅ Get all sessions for these days in one query
sessions = supabase.table("plan_sessions").select("*").in_("day_id", day_ids).execute().data

# ✅ Build full_plan without exercises
full_plan = {week_label: {}}
for day in days:
    day_label = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][day["day_number"]-1]
    if day["is_rest_day"]:
        full_plan[week_label][day_label] = {"Rest": True, "details": "Rest day"}
    else:
        day_sessions = [s for s in sessions if s["day_id"] == day["id"]]
        plan = {}
        for s in day_sessions:
            plan[s["type"]] = {
                "details": s.get("details", ""),
                "time": s.get("duration", 0),
                "completed": s.get("completed", False),
                "session_id": s["id"]  # ✅ Needed for Page 3
            }
        full_plan[week_label][day_label] = {
            "muscles": day_sessions[0].get("target_muscle", "").split(", ") if day_sessions else [],
            "stimulus": "",
            "day_type": day_label,
            "plan": plan,
            "estimated_time": day.get("total_time", 0),
            "completed": day.get("completed", False)
        }

# ✅ Display UI
st.subheader(week_label)
days_list = list(full_plan[week_label].keys())
selected_day = st.radio("Select Day", days_list, horizontal=True)
day_data = full_plan[week_label][selected_day]

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

        # Show session summary
        st.markdown(f"**{icon} {session_type} {indicator}**")
        if "details" in session_content:
            st.markdown(f"- {session_content['details']}")

        # ✅ Button to view details in Page 3
        if st.button(f"View {session_type} Details", key=f"view_{session_type}"):
            st.session_state.selected_session = {
                "type": session_type,
                "session_id": session_content["session_id"],
                "day": selected_day,
                "week": week_label
            }
            st.switch_page("pages/3_📄_Session_Detail.py")
        
