import streamlit as st
import pandas as pd
import time
from supabase import create_client
from collections import defaultdict

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🏋 Heavy Session")
    st.markdown(f"**Week:** {session['week']}  \n **Day:** {session['day']}")

    # Fetch sets from DB
    sets_data = supabase.table("plan_session_exercises") \
        .select("*") \
        .eq("session_id", session["session_id"]) \
        .order("exercise_order") \
        .execute().data

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

    # Render each exercise
    all_dfs = []  # To store edited data for saving later
    all_ids = []

    def render_block(block_name, block_sets):
        if not block_sets:
            return None, []
        st.markdown(f"**{block_name} Sets**")

        # Prepare DataFrame
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
                "Done": completed,
                "Rest": row.get("rest", 90)  # Default 90s if missing
            })

        df = pd.DataFrame(data)

        edited_df = st.data_editor(
            df.drop(columns=["ID", "Rest"]),
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

        # Detect newly completed sets and show timer
        for i, done in enumerate(edited_df["Done"]):
            if done and not df.loc[i, "Done"]:  # Newly marked complete
                rest_seconds = int(df.loc[i, "Rest"])
                st.write(f"✅ Set {edited_df.loc[i, 'Set']} completed! Rest timer:")
                timer_placeholder = st.empty()
                skip = st.button(f"⏭ Skip Rest for Set {edited_df.loc[i, 'Set']}")

                for remaining in range(rest_seconds, 0, -1):
                    if skip:
                        timer_placeholder.markdown("⏭ Timer skipped! Ready for next set.")
                        break
                    mins, secs = divmod(remaining, 60)
                    timer_placeholder.markdown(f"⏳ Rest: **{mins:02d}:{secs:02d}**")
                    time.sleep(1)
                else:
                    if not skip:
                        timer_placeholder.markdown("🔥 Ready for next set!")

        return edited_df, df["ID"].tolist()

    # Loop through exercises
    for ex_name, sets in grouped_exercises.items():
        st.subheader(ex_name)
        warmup_sets = [s for s in sets if str(s.get("notes", "")).lower().startswith("warmup")]
        working_sets = [s for s in sets if s not in warmup_sets]

        warmup_df, warmup_ids = render_block("🔥 Warmup", warmup_sets)
        working_df, working_ids = render_block("💪 Working", working_sets)

        if warmup_df is not None:
            all_dfs.append((warmup_df, warmup_ids))
        if working_df is not None:
            all_dfs.append((working_df, working_ids))

    # Back to Dashboard button with save logic
    if st.button("⬅ Back to Dashboard"):
        for edited_df, ids in all_dfs:
            for i, row_id in enumerate(ids):
                supabase.table("plan_session_exercises").update({
                    "completed": bool(edited_df.loc[i, "Done"]),
                    "actual_weight": str(edited_df.loc[i, "Weight"]),
                    "actual_reps": str(edited_df.loc[i, "Reps"])
                }).eq("id", row_id).execute()

        st.success("Progress saved. Returning to dashboard...")
        st.session_state.selected_session = None
        st.rerun()
