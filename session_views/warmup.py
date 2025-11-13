import streamlit as st
import time
from supabase import create_client

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🔥 Warmup")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")

    # Fetch exercises for this session
    exercises = supabase.table("plan_session_exercises") \
        .select("*") \
        .eq("session_id", session["session_id"]) \
        .order("set_number") \
        .execute().data

    if not exercises:
        st.warning("No exercises found for this warmup.")
        return

    # ✅ Initialize state
    if "exercise_index" not in st.session_state:
        st.session_state.exercise_index = 0
    if "phase" not in st.session_state:
        st.session_state.phase = "exercise"
    # Always reset running when entering view (no auto-start)
    st.session_state.running = False
    if "remaining_time" not in st.session_state:
        st.session_state.remaining_time = None

    # Current exercise and durations
    current_ex = exercises[st.session_state.exercise_index]
    exercise_name = current_ex["exercise_name"]
    exercise_duration = int(current_ex.get("duration", 30))  # Default 30 sec
    rest_duration = int(current_ex.get("rest", 30))          # Default 30 sec
    duration = exercise_duration if st.session_state.phase == "exercise" else rest_duration

    # If first time or phase changed, reset remaining_time
    if st.session_state.remaining_time is None:
        st.session_state.remaining_time = duration

    # ✅ Overall progress bar
    overall_progress = st.progress(0)
    overall_percent = int((st.session_state.exercise_index / len(exercises)) * 100)
    overall_progress.progress(overall_percent)

    # Display exercise info
    st.markdown(f"### Exercise {st.session_state.exercise_index + 1} of {len(exercises)}")
    st.markdown(f"**{exercise_name}**")
    st.markdown(f"Phase: {st.session_state.phase.capitalize()}")

    # Placeholder for circular countdown
    placeholder = st.empty()

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
        placeholder.markdown(circle_html, unsafe_allow_html=True)

    # ✅ Sound alert
    def play_sound():
        st.markdown("""
        <audio autoplay>
            <source src="https://actions.google.com/sounds/v1/alarms/beep_short.ogg" type="     """, unsafe_allow_html=True)

    # Buttons
    col1, col2, col3 = st.columns(3)
    if col1.button("▶ Start / Continue"):
        st.session_state.running = True
    if col2.button("⏸ Stop"):
        st.session_state.running = False
    if col3.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()

    # ✅ Timer loop with pause/resume
    if st.session_state.running:
        while st.session_state.remaining_time > 0 and st.session_state.running:
            percent = (st.session_state.remaining_time / duration) * 100
            render_circle(percent, st.session_state.remaining_time)
            time.sleep(1)
            st.session_state.remaining_time -= 1

        # ✅ If timer finished and still running
        if st.session_state.remaining_time <= 0 and st.session_state.running:
            play_sound()
            # Switch phase or move to next exercise
            if st.session_state.phase == "exercise":
                st.session_state.phase = "rest"
                st.session_state.remaining_time = rest_duration
            else:
                st.session_state.phase = "exercise"
                st.session_state.exercise_index += 1
                if st.session_state.exercise_index < len(exercises):
                    next_ex = exercises[st.session_state.exercise_index]
                    st.session_state.remaining_time = int(next_ex.get("duration", 30))
                else:
                    # ✅ All exercises done
                    supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
                    st.success("Warmup completed!")
                    st.session_state.selected_session = None
            st.rerun()
