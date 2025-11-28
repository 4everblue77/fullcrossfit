
import streamlit as st
from supabase import create_client
from timer import run_rest_timer

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🔥 Warmup")
    st.markdown(f"**Week:** {session['week']}  \n**Day:** {session['day']}")

    exercises = supabase.table("plan_session_exercises")        .select("*")        .eq("session_id", session["session_id"])        .order("exercise_order")        .execute().data

    if not exercises:
        st.warning("No exercises found for this warmup.")
        return

    # Initialize session state for control
    if "warmup_running" not in st.session_state:
        st.session_state.warmup_running = False
    if "warmup_paused" not in st.session_state:
        st.session_state.warmup_paused = False

    # Global progress bar
    completed_exercises = sum(1 for ex in exercises if ex.get("completed"))
    st.progress(completed_exercises / len(exercises))
    st.markdown(f"**Progress:** {completed_exercises}/{len(exercises)} exercises completed")

    # Control buttons
    col1, col2, col3 = st.columns(3)
    if col1.button("▶ Start Session", key=f"start_session_{session['session_id']}"):
        st.session_state.warmup_running = True
        st.session_state.warmup_paused = False
    if col2.button("⏸ Pause", key=f"pause_session_{session['session_id']}"):
        st.session_state.warmup_paused = True
    if col3.button("⬅ Back to Dashboard", key=f"back_session_{session['session_id']}"):
        st.session_state.warmup_running = False
        st.session_state.selected_session = None
        st.rerun()

    # Show current and next exercise names at all times
    if st.session_state.warmup_running:
        current_index = 0
        st.subheader("Current Exercise: " + exercises[current_index]['exercise_name'])
        next_ex_name = exercises[current_index+1]['exercise_name'] if current_index+1 < len(exercises) else "None"
        st.info("Next Exercise: " + next_ex_name)

    # Execute session if running and not paused
    if st.session_state.warmup_running and not st.session_state.warmup_paused:
        for i, ex in enumerate(exercises):
            next_ex_name = exercises[i+1]['exercise_name'] if i+1 < len(exercises) else None

            # Display current and next exercise before timer
            st.subheader(f"Current: {ex['exercise_name']}")
            st.info(f"Next: {next_ex_name if next_ex_name else 'None'}")

            # Exercise phase
            run_rest_timer(int(ex.get("duration", 30)), label=ex['exercise_name'], next_item=next_ex_name, skip_key=f"skip_ex_{ex['id']}")
            supabase.table("plan_session_exercises").update({"completed": True}).eq("id", ex["id"]).execute()

            # Rest phase (if not last exercise)
            if next_ex_name:
                run_rest_timer(int(ex.get("rest", 30)), label="Rest", next_item=next_ex_name, skip_key=f"skip_rest_{ex['id']}")

        # Mark session complete
        supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success("Warmup completed!")
        st.session_state.selected_session = None
        st.rerun()
