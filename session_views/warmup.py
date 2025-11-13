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

    # ✅ Detect session change and reset state
    if "current_session_id" not in st.session_state or st.session_state.current_session_id != session["session_id"]:
        st.session_state.current_session_id = session["session_id"]
        st.session_state.exercise_index = None
        st.session_state.phase = "exercise"
        st.session_state.running = False
        st.session_state.remaining_time = None

    # ✅ Fetch exercises
    exercises = supabase.table("plan_session_exercises") \
        .select("*") \
        .eq("session_id", session["session_id"]) \
        .order("set_number") \
        .execute().data

    if not exercises:
        st.warning("No exercises found for this warmup.")
        return

    completed_count = sum(1 for ex in exercises if ex.get("completed", False))
    first_incomplete_index = next((i for i, ex in enumerate(exercises) if not ex.get("completed", False)), None)


    if first_incomplete_index is None:
        st.info("Warmup marked as completed, but you can adjust below.")
        # Do NOT return — allow manual adjustments
        st.session_state.exercise_index = len(exercises) - 


    if st.session_state.exercise_index is None:
        st.session_state.exercise_index = first_incomplete_index

    current_ex = exercises[st.session_state.exercise_index]
    exercise_name = current_ex["exercise_name"]
    exercise_duration = int(current_ex.get("duration", 30))
    rest_duration = int(current_ex.get("rest", 30))
    duration = exercise_duration if st.session_state.phase == "exercise" else rest_duration

    if st.session_state.remaining_time is None:
        st.session_state.remaining_time = duration

    # ✅ Overall progress bar (include current exercise)
    overall_progress = st.progress(0)
    overall_percent = int(((completed_count + (1 if st.session_state.phase == "exercise" else 0)) / len(exercises)) * 100)
    overall_progress.progress(overall_percent)

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

    def play_sound():
        st.markdown("""
        <audio autoplay>
            <source src="https://actions.google.com/sounds/v_short.ogg
        </audio>
        """, unsafe_allow_html=True)

    # ✅ Buttons
    col1, col2, col3 = st.columns(3)
    if col1.button("▶ Start / Resume"):
        st.session_state.running = True
    if col2.button("⏸ Pause"):
        st.session_state.running = False

    if col3.button("⬅ Back to Dashboard"):
        if st.session_state.session_completed:
            # Mark session and all exercises as completed
            supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
            for ex in exercises:
                supabase.table("plan_session_exercises").update({"completed": True}).eq("id", ex["id"]).execute()
        else:
            # Unmark session and save individual exercise states
            supabase.table("plan_sessions").update({"completed": False}).eq("id", session["session_id"]).execute()
            for ex in exercises:
                supabase.table("plan_session_exercises").update({
                    "completed": st.session_state.exercise_completion[ex["id"]]
                }).eq("id", ex["id"]).execute()
    
        st.session_state.selected_session = None
        st.rerun()


    # ✅ Collapsible summary section
    with st.expander("Exercise Summary"):
        st.markdown("**Adjust completion status manually if needed:**")
    
        # Session-level toggle
        if "session_completed" not in st.session_state:
            st.session_state.session_completed = session.get("completed", False)
    
        st.session_state.session_completed = st.checkbox(
            "Mark entire session as completed",
            value=st.session_state.session_completed,
            key="session_completed_toggle"
        )
    
        # Exercise-level toggles
        if "exercise_completion" not in st.session_state:
            st.session_state.exercise_completion = {
                ex["id"]: ex.get("completed", False) for ex in exercises
            }
    
        for ex in exercises:
            ex_id = ex["id"]
            ex_name = ex["exercise_name"]
            disabled = st.session_state.session_completed  # Disable if session is marked complete
            st.session_state.exercise_completion[ex_id] = st.checkbox(
                ex_name,
                value=st.session_state.exercise_completion[ex_id],
                key=f"chk_{ex_id}",
                disabled=disabled
            )


    # ✅ Timer loop without blocking
    if st.session_state.running:
        color = "#f00" if st.session_state.phase == "exercise" else "#00f"
        percent = (st.session_state.remaining_time / duration) * 100
        progress_position = completed_count + (1 if st.session_state.phase == "exercise" else 0)

        render_circle(percent, st.session_state.remaining_time, exercise_name,
                      progress_position, len(exercises), color)


        time.sleep(1)
        st.session_state.remaining_time -= 1

        if st.session_state.remaining_time <= 0:
            play_sound()
            if st.session_state.phase == "exercise":
                supabase.table("plan_session_exercises").update({"completed": True}).eq("id", current_ex["id"]).execute()
                completed_count += 1
                st.session_state.phase = "rest"
                duration = rest_duration
                st.session_state.remaining_time = rest_duration
            else:
                st.session_state.exercise_index += 1
                if st.session_state.exercise_index >= len(exercises):
                    supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
                    st.success("Warmup completed!")
                    st.session_state.selected_session = None
                    st.rerun()
                else:
                    current_ex = exercises[st.session_state.exercise_index]
                    exercise_name = current_ex["exercise_name"]
                    exercise_duration = int(current_ex.get("duration", 30))
                    rest_duration = int(current_ex.get("rest", 30))
                    st.session_state.phase = "exercise"
                    duration = exercise_duration
                    st.session_state.remaining_time = exercise_duration

        st.rerun()
