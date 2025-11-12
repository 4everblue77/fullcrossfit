import streamlit as st

st.title("🏠 Weekly Dashboard")

# Ensure a plan exists
full_plan = st.session_state.get("full_plan", None)
if not full_plan:
    st.warning("No plan generated yet. Please go to the Plan Generator page.")
    st.stop()

# Assume current week is the first one for now
current_week = list(full_plan.keys())[0]
week_data = full_plan[current_week]

st.subheader(current_week)

# Horizontal day selector
days = list(week_data.keys())
selected_day = st.radio("Select Day", days, horizontal=True)

day_data = week_data[selected_day]

# Display sessions for selected day
if day_data.get("Rest"):
    st.markdown("**Rest Day 💤**")
else:
    st.markdown(f"### Sessions for {selected_day}")

    for session_type, session_content in day_data["plan"].items():
        if session_type in ["Debug", "Total Time"]:
            continue

        # Icon mapping
        icon_map = {
            "Warmup": "🔥",
            "Heavy": "🏋️",
            "Olympic": "🏅",
            "Run": "🏃",
            "WOD": "📦",
            "Benchmark": "⭐",
            "Light": "💡",
            "Skill": "🎯",
            "Cooldown": "❄️"
        }
        icon = icon_map.get(session_type, "📋")

        # Completion indicator (placeholder logic)
        completed = False  # Replace with Supabase or session_state tracking
        indicator = "✅" if completed else "⚫"

        # Session card
        st.button(f"{icon} {session_type} {indicator}", key=session_type)

        # Show brief details
        if "details" in session_content:
            st.markdown(f"- {session_content['details']}")

        # Clicking button sets session in state for detail page
        if st.button(f"View {session_type} Details", key=f"view_{session_type}"):
            st.session_state.selected_session = {
                "type": session_type,
                "content": session_content,
                "day": selected_day,
                "week": current_week
            }
            st.switch_page("pages/3_📋_Session_Detail.py")
