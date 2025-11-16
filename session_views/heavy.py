
import streamlit as st
import pandas as pd
from supabase import create_client
from collections import defaultdict

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🏋 Heavy Session")
    st.markdown(f"**Week:** {session['week']}  /n**Day:** {session['day']}")

    # Fetch sets from DB
    sets_data = supabase.table("plan_session_exercises")         .select("*")         .eq("session_id", session["session_id"])         .order("exercise_order")         .execute().data

    if not sets_data:
        st.warning("No sets found for this heavy session.")
        return

    # Group by exercise_name
    grouped_exercises = defaultdict(list)
    for row in sets_data:
        grouped_exercises[row["exercise_name"]].append(row)

    for ex_name in grouped_exercises:
        grouped_exercises[ex_name].sort(key=lambda r: r.get("set_number", 1))

    # Overall progress
    total_sets = len(sets_data)
    completed_sets = sum(1 for r in sets_data if r.get("completed", False))
    st.progress(completed_sets / total_sets if total_sets else 0)
    st.markdown(f"**Progress:** {completed_sets}/{total_sets} sets completed")

    # Render each exercise using st.data_editor
    for ex_name, sets in grouped_exercises.items():
        st.subheader(ex_name)

        warmup_sets = [s for s in sets if str(s.get("notes", "")).lower().startswith("warmup")]
        working_sets = [s for s in sets if s not in warmup_sets]

        def render_block(block_name, block_sets):
            if not block_sets:
                return None, []
            st.markdown(f"**{block_name} Sets**")

            # Prepare DataFrame for editable table
            data = []
            for row in block_sets:
                completed = row.get("completed", False)
                planned_reps = row.get("reps", "")
                actual_reps = row.get("actual_reps", "")
                reps_value = actual_reps if completed and actual_reps else planned_reps
                data.append({
                    "ID": row["id"],
                    "Set": row.get("set_number", ""),
                    "%RM": row.get("intensity", ""),
                    "Weight": row.get("actual_weight", ""),
                    "Reps": reps_value,
                    "Done": completed
                })

            df = pd.DataFrame(data)

            edited_df = st.data_editor(
                df.drop(columns=["ID"]),
                num_rows="fixed",
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Set": st.column_config.NumberColumn("Set", disabled=True),
                    "%RM": st.column_config.TextColumn("%RM", disabled=True),
                    "Weight": st.column_config.TextColumn("Weight"),
                    "Reps": st.column_config.TextColumn("Reps"),
                    "Done": st.column_config.CheckboxColumn("Done")
                }
            )

            return edited_df, df["ID"].tolist()

        warmup_df, warmup_ids = render_block("🔥 Warmup", warmup_sets)
        working_df, working_ids = render_block("💪 Working", working_sets)

        # Save button
        if st.button(f"✅ Save Progress for {ex_name}"):
            # Update DB for warmup sets
            if warmup_df is not None:
                for i, row_id in enumerate(warmup_ids):
                    supabase.table("plan_session_exercises").update({
                        "completed": bool(warmup_df.loc[i, "Done"]),
                        "actual_weight": str(warmup_df.loc[i, "Weight"]),
                        "actual_reps": str(warmup_df.loc[i, "Reps"])
                    }).eq("id", row_id).execute()

            # Update DB for working sets
            if working_df is not None:
                for i, row_id in enumerate(working_ids):
                    supabase.table("plan_session_exercises").update({
                        "completed": bool(working_df.loc[i, "Done"]),
                        "actual_weight": str(working_df.loc[i, "Weight"]),
                        "actual_reps": str(working_df.loc[i, "Reps"])
                    }).eq("id", row_id).execute()

            st.success(f"Progress for {ex_name} saved to Supabase")

    # Back to Dashboard button
    if st.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()
