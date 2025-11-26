
import streamlit as st
from supabase import create_client

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🎯 Skill Session")
    st.markdown(f"**Week:** {session['week']}  \n **Day:** {session['day']}")

    # Fetch exercises for this session
    exercises = supabase.table("plan_session_exercises")         .select("*")         .eq("session_id", session["session_id"])         .order("exercise_order")         .execute().data

    if not exercises:
        st.warning("No exercises found for this skill session.")
        return

    # Sync completion state
    if "exercise_completion" not in st.session_state:
        st.session_state.exercise_completion = {}
    for ex in exercises:
        if ex["id"] not in st.session_state.exercise_completion:
            st.session_state.exercise_completion[ex["id"]] = ex.get("completed", False)

    # Progress bar
    completed_count = sum(1 for val in st.session_state.exercise_completion.values() if val)
    total_exercises = len(exercises)
    st.progress(completed_count / total_exercises if total_exercises else 0)
    st.markdown(f"**Progress:** {completed_count}/{total_exercises} exercises completed")

    # Render exercises with checkboxes
    st.markdown("### Exercises")
    for ex in exercises:
        ex_id = ex["id"]
        ex_name = ex["exercise_name"]
        reps = ex.get("reps", "")
        notes = ex.get("notes", "")
        label = f"{ex_name} ({reps}) - {notes}"
        st.session_state.exercise_completion[ex_id] = st.checkbox(label, value=st.session_state.exercise_completion[ex_id], key=f"chk_{ex_id}")

    # Back to Dashboard button
    if st.button("⬅ Back to Dashboard"):
        all_completed = all(st.session_state.exercise_completion.values())

        # Update exercises completion in Supabase
        for ex_id, completed in st.session_state.exercise_completion.items():
            supabase.table("plan_session_exercises").update({"completed": completed}).eq("id", ex_id).execute()

        # Update session completion if all exercises done
        if all_completed:
            supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()

        st.success("Progress saved. Returning to dashboard...")
        st.session_state.selected_session = None
        st.rerun()
