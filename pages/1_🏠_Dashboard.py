import streamlit as st
from supabase import create_client

# Page config
st.set_page_config(page_title="FullCrossFit Dashboard", page_icon="🏠")

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize session state
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

# ✅ Helper function for styled session button
def render_session_button(session_type, details, icon, indicator, key):
    button_html = f"""
    <style>
        .session-btn {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border: 2px solid #ccc;
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
            background-color: #f9f9f9;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }}
        .session-btn:hover {{
            background-color: #e6f0ff;
        }}
        .session-left {{
            display: flex;
            align-items: center;
        }}
        .session-icon {{
            font-size: 32px;
            margin-right: 12px;
        }}
        .session-text {{
            display: flex;
            flex-direction: column;
        }}
        .session-title {{
            font-size: 22px;
            font-weight: bold;
        }}
        .session-details {{
            font-size: 14px;
            color: #555;
        }}
        .session-indicator {{
            font-size: 32px;
        }}
    </style>
    <div class="session-btn" onclick="document.getElementById('{key}').click()">
        <div class="session-left">
            <span class="session-icon">{icon}</span>
            <div class="session-text">
                <div class="session-title">{session_type}</div>
                <div class="session-details">{details}</div>
            </div>
        </div>
        <div class="session-indicator">{indicator}</div>
    </div>
    """
    st.markdown(button_html, unsafe_allow_html=True)
    return st.button("hidden_button", key=key, label_visibility="collapsed")

# ✅ Dashboard View
if st.session_state.selected_session is None:
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

    # Build plan
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
                    "session_id": s["id"]
                }
            full_plan[week_label][day_label] = {
                "muscles": day_sessions[0].get("target_muscle", "").split(", ") if day_sessions else [],
                "stimulus": "",
                "day_type": day_label,
                "plan": plan,
                "estimated_time": day.get("total_time", 0),
                "completed": day.get("completed", False)
            }

    # Display UI
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
            details = session_content.get("details", "No details available")

            if render_session_button(session_type, details, icon, indicator, key=f"view_{session_type}"):
                st.session_state.selected_session = {
                    "type": session_type,
                    "session_id": session_content["session_id"],
                    "details": details,
                    "day": selected_day,
                    "week": week_label
                }

# ✅ Session Detail View
else:
    session = st.session_state.selected_session
    st.title(f"📄 Session Detail: {session['type']}")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")
    st.markdown(f"**Details:** {session['details']}")

    # Completion toggle
    if st.button("✅ Mark as Completed"):
        supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success("Session marked as completed!")

    # Back button
    if st.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
