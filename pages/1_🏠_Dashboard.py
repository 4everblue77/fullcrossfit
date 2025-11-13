import streamlit as st
from supabase import create_client
from urllib.parse import quote

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

    # Build plan structure
    full_plan = {week_label: {}}
    for day in days:
        day_label = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][day["day_number"]-1]
        if day["is_rest_day"]:
            full_plan[week_label][day_label] = {"Rest": True}
        else:
            day_sessions = [s for s in sessions if s["day_id"] == day["id"]]
            plan = {s["type"]: {
                "details": s.get("details", ""),
                "completed": s.get("completed", False),
                "session_id": s["id"]
            } for s in day_sessions}
            full_plan[week_label][day_label] = {"plan": plan}

    # Display week and day selector
    st.subheader(week_label)
    days_list = list(full_plan[week_label].keys())
    selected_day = st.radio("Select Day", days_list, horizontal=True)
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
            details = session_content.get("details", "No details available")
            indicator = "✅" if session_content.get("completed") else "⚫"

            # Encode params for safe URL
            session_id = session_content["session_id"]
            url = (
                f"?session_id={session_id}"
                f"&type={quote(session_type)}"
                f"&details={quote(details)}"
                f"&day={quote(selected_day)}"
                f"&week={quote(week_label)}"
            )

            # Render link button
            st.link_button(
                label=f"{icon} {session_type}\n{details}\nStatus: {indicator}",
                url=url
            )

# Detect query params
params = st.experimental_get_query_params()
if "session_id" in params and st.session_state.selected_session is None:
    st.session_state.selected_session = {
        "session_id": params["session_id"][0],
        "type": params["type"][0],
        "details": params["details"][0],
        "day": params["day"][0],
        "week": params["week"][0]
    }

# Session detail view
if st.session_state.selected_session:
    session = st.session_state.selected_session
    st.title(f"📄 Session Detail: {session['type']}")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")
    st.markdown(f"**Details:** {session['details']}")

    if st.button("✅ Mark as Completed"):
        supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success("Session marked as completed!")

    if st.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.experimental_set_query_params()  # Clear params
