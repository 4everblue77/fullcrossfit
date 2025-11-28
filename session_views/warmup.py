
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

    # Global progress bar
    completed_exercises = sum(1 for ex in exercises if ex.get("completed"))
    st.progress(completed_exercises / len(exercises))
    st.markdown(f"**Progress:** {completed_exercises}/{len(exercises)} exercises completed")

    for i, ex in enumerate(exercises):
        st.subheader(f"Exercise {i+1}: {ex['exercise_name']}")
        next_ex_name = exercises[i+1]['exercise_name'] if i+1 < len(exercises) else None

        # Exercise phase using run_rest_timer
        run_rest_timer(int(ex.get("duration", 30)), label=ex['exercise_name'], next_item=next_ex_name, skip_key=f"skip_ex_{ex['id']}")
        supabase.table("plan_session_exercises").update({"completed": True}).eq("id", ex["id"]).execute()

        # Rest phase using run_rest_timer
        if next_ex_name:
            run_rest_timer(int(ex.get("rest", 30)), label="Rest", next_item=next_ex_name, skip_key=f"skip_rest_{ex['id']}")

    # Mark session complete
    supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
    st.success("Warmup completed!")
    st.session_state.selected_session = None
    st.rerun()
