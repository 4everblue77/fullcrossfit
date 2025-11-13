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

    # Fetch exercises
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
    if "running" not in st.session_state:
        st.session_state.running = False
    if "remaining_time" not in st.session_state:
        st.session_state.remaining_time = None

    current_ex = exercises[st.session_state.exercise_index]
    exercise_name = current_ex["exercise_name"]
    exercise_duration = int(current_ex.get("duration", 30))
    rest_duration = int(current_ex.get("rest", 30))
    duration = exercise_duration if st.session_state.phase == "exercise" else rest_duration

    # Reset remaining_time if None
    if st.session_state.remaining_time is None:
        st.session_state.remaining_time = duration

    # ✅ Overall progress bar
    overall_progress = st.progress(0)
    overall_percent = int((st.session_state.exercise_index / len(exercises)) * 100)
    overall_progress.progress(overall_percent)

    # ✅ Responsive circular timer with text inside
    placeholder = st.empty()

    def render_circle(percent, remaining_time, exercise_name, index, total, color):
        circle_html = f"""
        <div style="display:flex;justify-content:center;align-items:center;width:100%;">
            <div style="position:relative;width:100%;max-width:500px;">
                <svg width="100%" height="100%" viewBox="0 0 36 36">
                    <path stroke="#eee" stroke-width="3" fill="none" d="M18 2a16 16 0 1 1 0 32 16 16 0 1 1 0-32"/>
                    <path stroke="{color}" stroke-width="3" fill="none" stroke-dasharray="{percent},100" d="M18 2a16 16 0 1 1 0 32 16 16 0 1 1 0-32"/>
                </svg>
                <div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;">
                    <div style="font-size:18px;">Exercise {index} of {total}</div>
                    <div style="font-size:20px;font-weight:bold;">{exercise_name}</div>
                    <div style="font-size:18px;">{remaining_time}s</div>
                </div>
            </div>
        </div>
        """
        placeholder.markdown(circle_html, unsafe_allow_html=True)

    # ✅ Sound alert
    def play_sound():
        st.markdown("""
        <audio autoplay>
            https://actions.google.com/sounds/v1/alarms/beep_short.ogg
        </audio>
        """, unsafe_allow_html=True)

    # Buttons
    col1, col2, col3 = st.columns(3)
    if col1.button("▶ Start / Continue"):
        st.session_state.running = True
    if col2.button("⏸ Stop"):
        st.session_state.running = False
    if col3.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()

    # ✅ Timer loop with auto-continue
    if st.session_state.running:
        while st.session_state.running:
            color = "#f00" if st.session_state.phase == "exercise" else "#00f"
            percent = (st.session_state.remaining_time / duration) * 100
            render_circle(percent, st.session_state.remaining_time, exercise_name,
                          st.session_state.exercise_index + 1, len(exercises), color)
            time.sleep(1)
            st.session_state.remaining_time -= 1

            # Phase finished
            if st.session_state.remaining_time <= 0:
                play_sound()
                if st.session_state.phase == "exercise":
                    # Switch to rest
                    st.session_state.phase = "rest"
                    duration = rest_duration
                    st.session_state.remaining_time = rest_duration
                else:
                    # Move to next exercise
                    st.session_state.exercise_index += 1
                    if st.session_state.exercise_index >= len(exercises):
                        # ✅ All exercises done
                        supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
                        st.success("Warmup completed!")
                        st.session_state.selected_session = None
                        st.rerun()
                    else:
                        next_ex = exercises[st.session_state.exercise_index]
                        exercise_name = next_ex["exercise_name"]
                        exercise_duration = int(next_ex.get("duration", 30))
                        rest_duration = int(next_ex.get("rest", 30))
                        st.session_state.phase = "exercise"
                        duration = exercise_duration
                        st.session_state.remaining_time = exercise_duration

                # ✅ Update overall progress
                overall_percent = int((st.session_state.exercise_index / len(exercises)) * 100)
                overall_progress.progress(overall_percent)

            # Refresh UI
            render_circle(percent, st.session_state.remaining_time, exercise_name,
                          st.session_state.exercise_index + 1, len(exercises), color)
