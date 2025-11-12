import streamlit as st
from supabase import create_client

st.set_page_config(page_title="FullCrossFit Dashboard", page_icon="🏠")
st.title("🏠 Weekly Dashboard")

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ✅ Check if any weeks exist
weeks = supabase.table("plan_weeks").select("*").execute().data

if not weeks or len(weeks) == 0:
    st.warning("No plan found in Supabase.")
    st.write("""
    👉 Use the **Plan Generator** page from the sidebar to create your 6-week plan.
    Once generated, you'll see your weekly overview here.
    """)
    st.stop()

# ✅ Build full_plan from Supabase
full_plan = {}
for week in weeks:
    week_label = f"Week {week['number']}"
    full_plan[week_label] = {}

    # Get days for this week
    days = supabase.table("plan_days").select("*").eq("week_id", week["id"]).execute().data
    for day in days:
        day_label = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][day["day_number"]-1]
        if day["is_rest_day"]:
            full_plan[week_label][day_label] = {"Rest": True, "details": "Rest day"}
        else:
            # Get sessions for this day
            sessions = supabase.table("plan_sessions").select("*").eq("day_id", day["id"]).execute().data
            plan = {}
            for s in sessions:
                plan[s["type"]] = {
                    "details": s.get("details", ""),
                    "time": s.get("duration", 0),
                    "completed": s.get("completed", False)
                }
            full_plan[week_label][day_label] = {
                "muscles": s.get("target_muscle", "").split(", "),
                "stimulus": "",
                "day_type": day_label,
                "plan": plan,
                "estimated_time": day.get("total_time", 0),
                "completed": day.get("completed", False)
            }

# ✅ Display current week
current_week = list(full_plan.keys())[0]
week_data = full_plan[current_week]

st.subheader(current_week)

# Horizontal day selector
days = list(week_data.keys())
selected_day = st.radio("Select Day", days, horizontal=True)

day_data = week_data[selected_day]

# Display sessions
if day_data.get("Rest"):
    st.markdown("**Rest Day 💤**")
else:
    st.markdown(f"### Sessions for {selected_day}")
    for session_type, session_content in day_data["plan"].items():
        if session_type in ["Debug", "Total Time"]:
            continue

        icon_map = {
            "Warmup": "🔥", "Heavy": "🏋️", "Olympic": "🏅", "Run": "🏃",
            "WOD": "📦", "Benchmark": "⭐", "Light": "💡", "Skill": "🎯", "Cooldown": "❄️"
        }
        icon = icon_map.get(session_type, "📋")
        indicator = "✅" if session_content.get("completed") else "⚫"

        st.button(f"{icon} {session_type} {indicator}", key=session_type)
        if "details" in session_content:
            st.markdown(f"- {session_content['details']}")
