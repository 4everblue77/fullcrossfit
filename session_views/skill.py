
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

    
    # ---- Sync rest seconds state (from DB) ----
    if "exercise_rest" not in st.session_state:
        st.session_state.exercise_rest = {}
    for ex in exercises:
        ex_id = ex["id"]
        try:
            default_rest = int(ex.get("rest") or 90)
        except (ValueError, TypeError):
            default_rest = 90
        if ex_id not in st.session_state.exercise_rest:
            st.session_state.exercise_rest[ex_id] = default_rest



    # Render exercises with checkboxes + rest timer controls
    st.markdown("### Exercises")
    for ex in exercises:
        ex_id = ex["id"]
        ex_name = ex.get("exercise_name", "Exercise")
        reps = ex.get("reps", "")
        notes = ex.get("notes", "")
        label = f"{ex_name} ({reps}) - {notes}".strip(" -()")

        # Row container for each exercise
        with st.container(border=True):
            # Completion checkbox
            checked = st.checkbox(
                label,
                value=st.session_state.exercise_completion[ex_id],
                key=f"chk_{ex_id}"
            )
            st.session_state.exercise_completion[ex_id] = checked

            # Rest settings + timer
            col1, col2 = st.columns([1, 1], vertical_alignment="center")

    
            with col1:
                rest_val = st.number_input(
                    "Rest (seconds)",
                    min_value=10,
                    max_value=600,
                    step=10,
                    value=int(st.session_state.exercise_rest[ex_id]),
                    key=f"rest_{ex_id}",
                    help="Defaulted from plan_session_exercises.rest"
                )
                # Normalize and save into state
                try:
                    st.session_state.exercise_rest[ex_id] = int(rest_val)
                except (ValueError, TypeError):
                    st.session_state.exercise_rest[ex_id] = 90

            with col2:
                btn_label = f"▶ Start Rest Timer ({st.session_state.exercise_rest[ex_id]}s)"
                if st.button(btn_label, key=f"start_rest_{ex_id}"):
                    # Use a unique skip_key per session/exercise to allow cancelling/skipping
                    skip_key = f"rest_skip_{session['session_id']}_{ex_id}"
                    # Label shows which exercise this rest pertains to
                    try:
                        run_rest_timer(
                            st.session_state.exercise_rest[ex_id],
                            label=f"Rest – {ex_name}",
                            next_item=None,
                            skip_key=skip_key
                        )


                    except NameError:
                        st.error(
                            "run_rest_timer is not defined. See the helper implementation below."
                        )

    st.divider()


    
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
