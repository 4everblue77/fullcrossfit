import streamlit as st
import time
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🔥 Warmup")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")

    exercises = supabase.table("plan_session_exercises") \
        .select("*") \
        .eq("session_id", session["session_id"]) \
        .order("set_number") \
        .execute().data

    if not exercises:
        st.warning("No exercises found for this warmup.")
        return

    # Initialize state
    if "exercise_index" not in st.session_state:
        st.session_state.exercise_index = 0
    if "phase" not in st.session_state:
        st.session_state.phase = "exercise"
    if "running" not in st.session_state:
        st.session_state.running = False

    current_ex = exercises[st.session_state.exercise_index]
    exercise_name = current_ex["exercise_name"]
    duration = int(current_ex.get("rest", 30)) if st.session_state.phase == "rest" else 30

    st.markdown(f"### Exercise {st.session_state.exercise_index + 1} of {len(exercises)}")
    st.markdown(f"**{exercise_name}**")
    st.markdown(f"Phase: {st.session_state.phase.capitalize()}")

    # Circular progress placeholder
    progress_placeholder = st.empty()

    def render_circle(percent, remaining_time):
        circle_html = f"""
        <div style="display:flex;justify-content:center;align-items:center;position:relative;">
            <svg width="150" height="150" viewBox="0 0 36 36">
                <path stroke="#eee" stroke-width="3" fill="none" d="M18 2a16 16 0 1 1 0 32 16 16 0 1 1 0-32"/>
                <path stroke="#f00" stroke-width="3" fill="none" stroke-dasharray="{percent},100" d="M18 2a16 16 0 1 1 0 32 16 16 0 1 1 0-32"/>
            </svg>
            <div style="position:absolute;font-size:24px;">{remaining_time}s</div>
        </div>
        """
        progress_placeholder.markdown(circle_html, unsafe_allow_html=True)

    # Buttons
    col1, col2, col3 = st.columns(3)
    if col1.button("▶ Start"):
        st.session_state.running = True
    if col2.button("⏸ Stop"):
        st.session_state.running = False
    if col3.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()

    # Timer loop
    if st.session_state.running:
        for t in range(duration, 0, -1):
            percent = (t / duration) * 100
            render_circle(percent, t)
            time.sleep(1)

        # Switch phase or move to next exercise
        if st.session_state.phase == "exercise":
            st.session_state.phase = "rest"
        else:
            st.session_state.phase = "exercise"
            st.session_state.exercise_index += 1

        # If all exercises done
        if st.session_state.exercise_index >= len(exercises):
            supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
            st.success("Warmup completed!")
            st.session_state.selected_session = None

        st.rerun()
