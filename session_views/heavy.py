
import streamlit as st
from supabase import create_client

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🏋 Heavy Session")
    st.markdown(f"**Week:** {session['week']}  
**Day:** {session['day']}")

    # ✅ Detect session change and reset state
    if "current_session_id" not in st.session_state or st.session_state.current_session_id != session["session_id"]:
        st.session_state.current_session_id = session["session_id"]
        st.session_state.exercise_completion = {}
        st.session_state.set_completion = {}
        st.session_state.session_completed = session.get("completed", False)

    # ✅ Fetch exercises ordered by exercise_order
    exercises = supabase.table("plan_session_exercises")         .select("*")         .eq("session_id", session["session_id"])         .order("exercise_order")         .execute().data

    if not exercises:
        st.warning("No exercises found for this heavy session.")
        return

    # ✅ Split into Warmup and Working blocks based on notes
    warmup_block = [ex for ex in exercises if ex.get("notes", "").lower().startswith("warmup")]
    working_block = [ex for ex in exercises if ex.get("notes", "").lower().startswith("working") or ex not in warmup_block]

    # ✅ Initialize completion states
    for ex in exercises:
        ex_id = ex["id"]
        if ex_id not in st.session_state.exercise_completion:
            st.session_state.exercise_completion[ex_id] = ex.get("completed", False)
        if ex_id not in st.session_state.set_completion:
            total_sets = int(ex.get("sets", 1))
            st.session_state.set_completion[ex_id] = [False] * total_sets

    # ✅ Overall progress
    total_sets = sum(len(sets) for sets in st.session_state.set_completion.values())
    completed_sets = sum(sum(1 for s in sets if s) for sets in st.session_state.set_completion.values())
    overall_fraction = completed_sets / total_sets if total_sets > 0 else 0
    st.progress(min(overall_fraction, 1.0))
    st.markdown(f"**Progress:** {completed_sets}/{total_sets} sets completed")

    def render_block(block_name, block_exercises):
        st.subheader(block_name)
        for ex in block_exercises:
            ex_id = ex["id"]
            name = ex.get("exercise_name", "Unnamed Exercise")
            sets = int(ex.get("sets", 1))
            reps = ex.get("reps", "-")
            intensity = ex.get("intensity", 0)  # %RM
            weight_display = f"{intensity}% RM" if intensity else "Bodyweight"
            notes = ex.get("notes", "")

            st.markdown(f"**{name}**")
            st.markdown(f"Sets: {sets} | Reps: {reps} | Weight: {weight_display}")
            if notes:
                st.caption(notes)

            # ✅ Render set checkboxes
            cols = st.columns(sets)
            for i in range(sets):
                checked = st.session_state.set_completion[ex_id][i]
                if cols[i].checkbox(f"Set {i+1}", value=checked, key=f"{ex_id}_set_{i}"):
                    st.session_state.set_completion[ex_id][i] = True
                else:
                    st.session_state.set_completion[ex_id][i] = False

            # ✅ Mark exercise complete if all sets done
            st.session_state.exercise_completion[ex_id] = all(st.session_state.set_completion[ex_id])

    # ✅ Render Warmup and Working blocks
    if warmup_block:
        render_block("🔥 Warmup Sets", warmup_block)
    if working_block:
        render_block("💪 Working Sets", working_block)

    # ✅ Buttons
    col1, col2 = st.columns(2)
    if col1.button("✅ Save Progress"):
        # Save session completion if all exercises done
        all_done = all(st.session_state.exercise_completion.values())
        st.session_state.session_completed = all_done

        supabase.table("plan_sessions").update({"completed": st.session_state.session_completed}).eq("id", session["session_id"]).execute()

        for ex_id, completed in st.session_state.exercise_completion.items():
            supabase.table("plan_session_exercises").update({"completed": completed}).eq("id", ex_id).execute()

        st.success("Progress saved to Supabase")

    if col2.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()

    # ✅ Manual adjustments
    with st.expander("Manual Adjustments"):
        for ex in exercises:
            ex_id = ex["id"]
            ex_name = ex["exercise_name"]
            if st.button(f"Toggle {ex_name}", key=f"toggle_{ex_id}"):
                st.session_state.exercise_completion[ex_id] = not st.session_state.exercise_completion[ex_id]

        if st.button("🔄 Reset All"):
            for ex_id in st.session_state.exercise_completion.keys():
                st.session_state.exercise_completion[ex_id] = False
                st.session_state.set_completion[ex_id] = [False] * len(st.session_state.set_completion[ex_id])
            st.success("All sets reset!")
