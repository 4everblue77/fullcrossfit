import streamlit as st
from supabase import create_client

from session_views import warmup, heavy, olympic, wod, cooldown

# ✅ Page config
st.set_page_config(page_title="FullCrossFit Dashboard", page_icon="🏠", layout="wide")

# ✅ Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ✅ Session state
if "selected_session" not in st.session_state:
    st.session_state.selected_session = None

# ✅ Cached data fetch
@st.cache_data(ttl=60)
def fetch_weeks():
    return supabase.table("plan_weeks").select("*").order("number").execute().data

@st.cache_data(ttl=60)
def fetch_days(week_id):
    return supabase.table("plan_days").select("*").eq("week_id", week_id).execute().data

@st.cache_data(ttl=60)
def fetch_sessions(day_ids):
    return supabase.table("plan_sessions").select("*").in_("day_id", day_ids).execute().data

@st.cache_data(ttl=60)
def fetch_exercises(session_id):
    return supabase.table("plan_session_exercises").select("*").eq("session_id", session_id).order("set_number").execute().data

# ✅ Dashboard view
if st.session_state.selected_session is None:
    st.title("🏠 Weekly Dashboard")

    # Fetch weeks
    weeks = fetch_weeks()
    if not weeks:
        st.warning("No plan found in Supabase.")
        st.stop()

    # Week selection
    week_labels = [f"Week {w['number']}" for w in weeks]
    selected_week_label = st.selectbox("Select Week", week_labels)
    current_week = next(w for w in weeks if f"Week {w['number']}" == selected_week_label)

    # Fetch days and sessions
    days = fetch_days(current_week["id"])
    day_ids = [d["id"] for d in days]
    sessions = fetch_sessions(day_ids)

    # ✅ Build plan structure ensuring all 7 days
    expected_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    full_plan = {selected_week_label: {}}

    for i, label in enumerate(expected_labels, start=1):
        day = next((d for d in days if d["day_number"] == i), None)
        if day:
            if day.get("is_rest_day"):
                full_plan[selected_week_label][label] = {"Rest": True}
            else:
                day_sessions = [s for s in sessions if s["day_id"] == day["id"]]
                plan = {s["type"]: {
                    "completed": s.get("completed", False),
                    "session_id": s["id"]
                } for s in day_sessions}
                full_plan[selected_week_label][label] = {"plan": plan}
        else:
            # Inject missing day as rest
            full_plan[selected_week_label][label] = {"Rest": True}

    # ✅ Build day labels with completion status
    days_list = []
    for day_label, day_info in full_plan[selected_week_label].items():
        if day_info.get("Rest"):
            status_icon = "💤"
            days_list.append(f"{status_icon} {day_label}")
        else:
            sessions_for_day = day_info["plan"].values()
            completed_count = sum(1 for s in sessions_for_day if s.get("completed") is True)
            total_count = len(sessions_for_day)

            if completed_count == 0:
                status_icon = "⚫"
            elif completed_count == total_count:
                status_icon = "✅"
            else:
                status_icon = "🟡"

            days_list.append(f"{status_icon} {day_label} {completed_count}/{total_count}")

    # Show radio with updated labels
    selected_day_label = st.radio("Select Day", days_list, horizontal=True)
    selected_day = selected_day_label.split()[1]  # Always second element is day name
    day_data = full_plan[selected_week_label][selected_day]

    # Render sessions
    if day_data.get("Rest"):
        st.markdown("**Rest Day 💤**")
    else:
        st.markdown(f"### Sessions for {selected_day}")

        # ✅ Enforce session order
        session_order = ["Warmup", "Heavy", "Olympic", "Run", "WOD", "Benchmark", "Light", "Skill", "Cooldown"]
        ordered_sessions = sorted(day_data["plan"].items(),
                                  key=lambda x: session_order.index(x[0]) if x[0] in session_order else len(session_order))

        for session_type, session_content in ordered_sessions:
            icon_map = {
                "Warmup": "🔥", "Heavy": "🏋️", "Olympic": "🏅", "Run": "🏃",
                "WOD": "📦", "Benchmark": "⭐", "Light": "💡", "Skill": "🎯", "Cooldown": "❄️"
            }
            icon = icon_map.get(session_type, "📋")
            indicator = "✅" if session_content.get("completed") else "⚫"

            button_text = f"{icon} {session_type}    {indicator}"
            if st.button(button_text, key=session_content["session_id"], use_container_width=True):
                st.session_state.selected_session = {
                    "session_id": session_content["session_id"],
                    "type": session_type,
                    "day": selected_day,
                    "week": selected_week_label
                }
                st.rerun()

# ✅ Routing to session detail
if st.session_state.selected_session:
    session = st.session_state.selected_session
    session_type = session["type"]

    if session_type == "Warmup":
        warmup.render(session)
    elif session_type == "Heavy":
        heavy.render(session)
    elif session_type == "Olympic":
        olympic.render(session)
    elif session_type == "WOD":
        wod.render(session)    
    elif session_type == "Light":
        cooldown.render(session)
    elif session_type == "Cooldown":
        cooldown.render(session)
    else:
        st.error("Unknown session type.")
