
import streamlit as st
from supabase import create_client
from collections import defaultdict

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🏋 Heavy Session")
    st.markdown(f"**Week:** {session['week']}  /n**Day:** {session['day']}")

    # ✅ Initialize session_state keys
    if "actual_values" not in st.session_state:
        st.session_state.actual_values = {}
    if "set_completion" not in st.session_state:
        st.session_state.set_completion = {}
    if "current_session_id" not in st.session_state or st.session_state.current_session_id != session["session_id"]:
        st.session_state.current_session_id = session["session_id"]
        st.session_state.actual_values.clear()
        st.session_state.set_completion.clear()
        st.session_state.session_completed = session.get("completed", False)

    # ✅ Fetch all sets for this session
    sets_data = supabase.table("plan_session_exercises")         .select("*")         .eq("session_id", session["session_id"])         .order("exercise_order")         .execute().data

    if not sets_data:
        st.warning("No sets found for this heavy session.")
        return

    # ✅ Group by exercise_name
    grouped_exercises = defaultdict(list)
    for row in sets_data:
        grouped_exercises[row["exercise_name"]].append(row)

    # Sort sets within each exercise by set_number
    for ex_name in grouped_exercises:
        grouped_exercises[ex_name].sort(key=lambda r: r.get("set_number", 1))

    # ✅ Initialize state for each row
    for row in sets_data:
        row_id = row["id"]
        completed = row.get("completed", False)
        st.session_state.set_completion[row_id] = completed

        # Logic for reps fallback
        planned_reps = row.get("reps", "")
        actual_reps = row.get("actual_reps", "")
        reps_value = actual_reps if completed and actual_reps else planned_reps

        st.session_state.actual_values[row_id] = {
            "weight": row.get("actual_weight", ""),
            "reps": reps_value
        }

    # ✅ Overall progress
    total_sets = len(sets_data)
    completed_sets = sum(1 for v in st.session_state.set_completion.values() if v)
    st.progress(completed_sets / total_sets if total_sets else 0)
    st.markdown(f"**Progress:** {completed_sets}/{total_sets} sets completed")

    # ✅ Render each exercise
    for ex_name, sets in grouped_exercises.items():
        st.subheader(ex_name)

        # Split warmup vs working based on notes or intensity
        warmup_sets = [s for s in sets if str(s.get("notes", "")).lower().startswith("warmup")]
        working_sets = [s for s in sets if s not in warmup_sets]

        def render_block(block_name, block_sets):
            if not block_sets:
                return
            st.markdown(f"**{block_name}**")

            # Header row
            header = st.container()
            hcols = header.columns([1,1,1,1,1])
            hcols[0].markdown("**Set**")
            hcols[1].markdown("**%RM**")
            hcols[2].markdown("**Weight**")
            hcols[3].markdown("**Reps**")
            hcols[4].markdown("**Done**")

            # Rows
            for row in block_sets:
                row_id = row["id"]
                rcols = st.container().columns([1,1,1,1,1])
                set_num = row.get("set_number", "?")
                intensity = row.get("intensity", "")
                rcols[0].write(set_num)
                rcols[1].write(intensity)

                # Editable weight and reps
                weight_key = f"weight_{row_id}"
                reps_key = f"reps_{row_id}"
                st.session_state.actual_values[row_id]["weight"] = rcols[2].text_input("", value=str(st.session_state.actual_values[row_id]["weight"]), key=weight_key)
                st.session_state.actual_values[row_id]["reps"] = rcols[3].text_input("", value=str(st.session_state.actual_values[row_id]["reps"]), key=reps_key)

                # Checkbox for completion
                done_key = f"done_{row_id}"
                checked = st.session_state.set_completion[row_id]
                if rcols[4].checkbox("", value=checked, key=done_key):
                    st.session_state.set_completion[row_id] = True
                else:
                    st.session_state.set_completion[row_id] = False

        if warmup_sets:
            render_block("🔥 Warmup Sets", warmup_sets)
        if working_sets:
            render_block("💪 Working Sets", working_sets)

    # ✅ Buttons
    col1, col2 = st.columns(2)
    if col1.button("✅ Save Progress"):
        # Update DB for each set
        for row_id in st.session_state.set_completion.keys():
            supabase.table("plan_session_exercises").update({
                "completed": st.session_state.set_completion[row_id],
                "actual_weight": st.session_state.actual_values[row_id]["weight"],
                "actual_reps": st.session_state.actual_values[row_id]["reps"]
            }).eq("id", row_id).execute()

        # Update session completion if all sets done
        all_done = all(st.session_state.set_completion.values())
        st.session_state.session_completed = all_done
        supabase.table("plan_sessions").update({"completed": all_done}).eq("id", session["session_id"]).execute()

        st.success("Progress saved to Supabase")

    if col2.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()

    # ✅ Manual reset
    with st.expander("Manual Adjustments"):
        if st.button("🔄 Reset All"):
            for row_id in st.session_state.set_completion.keys():
                st.session_state.set_completion[row_id] = False
                st.session_state.actual_values[row_id]["weight"] = ""
                st.session_state.actual_values[row_id]["reps"] = sets_data[[r["id"] for r in sets_data].index(row_id)]["reps"]
            st.success("All sets reset!")
