import streamlit as st
import pandas as pd
import time
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from utils.timer import run_rest_timer

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


def calculate_1rm(weight: float, reps: int) -> float:
    """
    Calculate estimated 1RM using Epley formula.
    weight: actual weight lifted
    reps: number of reps performed
    """
    if reps <= 1:
        return weight
    return round(weight * (1 + 0.0333 * reps), 2)

def update_1rm_on_completion(exercise_name, completed_sets):
    for s in completed_sets:
        if s.get("completed") and s.get("actual_weight") and s.get("actual_reps"):
            weight = float(s["actual_weight"])
            reps = int(s["actual_reps"])
            calc_1rm = calculate_1rm(weight, reps)

            # Fetch latest max for comparison
            latest = supabase.table("exercise_maxes") \
                .select("*") \
                .eq("exercise_name", exercise_name) \
                .order("date", desc=True) \
                .limit(1) \
                .execute().data

            latest_max = None
            if latest:
                latest_max = latest[0].get("manual_1rm") or latest[0].get("calculated_1rm")

            # Insert only if new max is higher
            if not latest_max or calc_1rm > latest_max:
                supabase.table("exercise_maxes").insert({
                    "exercise_name": exercise_name,
                    "calculated_1rm": calc_1rm,
                    "source_set_id": s["id"],
                    "date": datetime.now().isoformat()
                }).execute()
                
def render(session):
    st.title("🏅 Olympic Session")
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


        # Fetch latest 1RM for this exercise
        latest_max = supabase.table("exercise_maxes") \
            .select("*") \
            .eq("exercise_name", ex_name) \
            .order("date", desc=True) \
            .limit(1) \
            .execute().data
        
        latest_1rm = None
        if latest_max:
            latest_1rm = latest_max[0].get("manual_1rm") or latest_max[0].get("calculated_1rm")
        
                
        # Prepare DataFrame
        data = []
        for row in block_sets:
            completed = row.get("completed", False)
            planned_reps = row.get("reps", "")
            actual_reps = row.get("actual_reps", "")
            reps_value = actual_reps if completed and actual_reps else planned_reps

            
            # Calculate suggested weight if %RM and 1RM exist
            suggested_weight = ""
            if latest_1rm and row.get("intensity"):
                try:
                    percent_rm = float(row.get("intensity").replace("%", ""))
                    suggested_weight = round(latest_1rm * (percent_rm / 100), 2)
                except ValueError:
                    suggested_weight = ""
        
            # Use actual weight if present, else suggested weight
            weight_value = row.get("actual_weight") or suggested_weight

            data.append({
                "ID": row["id"],
                "Set": row.get("set_number", ""),
                "%RM": row.get("intensity", ""),
                "Weight": weight_value,
                "Reps": reps_value,
                "Done": completed,
                "Rest": row.get("rest", 90)  # Default 90s if missing
            })


        df_original = pd.DataFrame(data)
        
        edited_df = st.data_editor(
            df_original.drop(columns=["ID", "Rest"]),
            num_rows="fixed",
            width='stretch',
            hide_index=True,
            column_config={
                "Set": st.column_config.NumberColumn("Set", disabled=True),
                "%RM": st.column_config.TextColumn("%RM", disabled=True),
                "Weight": st.column_config.NumberColumn("Weight", format="%.2f"),
                "Reps": st.column_config.TextColumn("Reps"),
                "Done": st.column_config.CheckboxColumn("Done")
            },
            key=f"editor_{session['session_id']}_{ex_name}_{block_name}"
        )
        return edited_df, df["ID"].tolist()

    # Loop through exercises
    all_dfs = []
    for ex_name, sets in grouped_exercises.items():
        st.subheader(ex_name)
        warmup_sets = [s for s in sets if str(s.get("notes", "")).lower().startswith("warmup")]
        working_sets = [s for s in sets if s not in warmup_sets]


        # Warmup block
        warmup_df, warmup_df_original, warmup_ids = render_block("🔥 Technique Warmup", warmup_sets, ex_name, session)
        if warmup_df is not None:
            # Instant persistence for warmup rows
            for i, row_id in enumerate(warmup_ids):
                is_done_now = bool(warmup_df.loc[i, "Done"])
                weight_now  = str(warmup_df.loc[i, "Weight"])
                reps_now    = str(warmup_df.loc[i, "Reps"])

                was_done    = bool(warmup_df_original.loc[i, "Done"])
                weight_prev = str(warmup_df_original.loc[i, "Weight"])
                reps_prev   = str(warmup_df_original.loc[i, "Reps"])

                if (is_done_now != was_done) or (weight_now != weight_prev) or (reps_now != reps_prev):
                    supabase.table("plan_session_exercises").update({
                        "completed": is_done_now,
                        "actual_weight": weight_now,
                        "actual_reps": reps_now
                    }).eq("id", row_id).execute()

                    if is_done_now and not was_done:
                        update_1rm_on_completion(ex_name, [{
                            "id": row_id,
                            "completed": True,
                            "actual_weight": weight_now,
                            "actual_reps": reps_now,
                            "set_number": warmup_df.loc[i, "Set"]
                        }])
    
            # Warmup (group) timer controls
            warmup_rest = max([int(s.get("rest", 60)) for s in warmup_sets], default=60)
            warmup_rest = st.number_input(
                "Warmup Rest (seconds)", min_value=10, max_value=600, value=warmup_rest, step=10,
                key=f"olympic_warmup_rest_input_{session['session_id']}_{ex_name}"
            )
            if st.button(
                f"▶ Start Warmup Rest Timer ({warmup_rest}s)",
                key=f"olympic_warmup_rest_button_{session['session_id']}_{ex_name}"
            ):
                run_rest_timer(
                    warmup_rest, label="Warmup Set Rest", next_item=None,
                    skip_key=f"olympic_warmup_rest_skip_{session['session_id']}_{ex_name}"
                )


            
        # Working block
        working_df, working_df_original, working_ids = render_block("💪 Main Lifts", working_sets, ex_name, session)
        if working_df is not None:
            # Instant persistence for working rows
            for i, row_id in enumerate(working_ids):
                is_done_now = bool(working_df.loc[i, "Done"])
                weight_now  = str(working_df.loc[i, "Weight"])
                reps_now    = str(working_df.loc[i, "Reps"])

                was_done    = bool(working_df_original.loc[i, "Done"])
                weight_prev = str(working_df_original.loc[i, "Weight"])
                reps_prev   = str(working_df_original.loc[i, "Reps"])

                if (is_done_now != was_done) or (weight_now != weight_prev) or (reps_now != reps_prev):
                    supabase.table("plan_session_exercises").update({
                        "completed": is_done_now,
                        "actual_weight": weight_now,
                        "actual_reps": reps_now
                    }).eq("id", row_id).execute()

                    if is_done_now and not was_done:
                        update_1rm_on_completion(ex_name, [{
                            "id": row_id,
                            "completed": True,
                            "actual_weight": weight_now,
                            "actual_reps": reps_now,
                            "set_number": working_df.loc[i, "Set"]
                        }])
    
            # Working (group) timer controls
            working_rest = max([int(s.get("rest", 120)) for s in working_sets], default=120)
            working_rest = st.number_input(
                "Working Rest (seconds)", min_value=10, max_value=600, value=working_rest, step=10,
                key=f"olympic_working_rest_input_{session['session_id']}_{ex_name}"
            )
            if st.button(
                f"▶ Start Working Rest Timer ({working_rest}s)",
                key=f"olympic_working_rest_button_{session['session_id']}_{ex_name}"
            ):
                run_rest_timer(
                    working_rest, label="Working Set Rest", next_item=None,
                    skip_key=f"olympic_working_rest_skip_{session['session_id']}_{ex_name}"
                )



        if warmup_df is not None:
            all_dfs.append((ex_name, warmup_df, warmup_ids))
        if working_df is not None:
            all_dfs.append((ex_name, working_df, working_ids))
        

    # Back to Dashboard button with save logic
      
    if st.button("⬅ Back to Dashboard"):
        all_completed = True  # Assume all done until proven otherwise
    
        for ex_name, edited_df, ids in all_dfs:
            completed_sets_list = []
            for i, row_id in enumerate(ids):
                is_done = bool(edited_df.loc[i, "Done"])
                supabase.table("plan_session_exercises").update({
                    "completed": is_done,
                    "actual_weight": str(edited_df.loc[i, "Weight"]),
                    "actual_reps": str(edited_df.loc[i, "Reps"])
                }).eq("id", row_id).execute()
    
                completed_sets_list.append({
                    "id": row_id,
                    "completed": is_done,
                    "actual_weight": edited_df.loc[i, "Weight"],
                    "actual_reps": edited_df.loc[i, "Reps"],
                    "set_number": edited_df.loc[i, "Set"]
                })
    
                if not is_done:
                    all_completed = False  # Found an incomplete set
    
            update_1rm_on_completion(ex_name, completed_sets_list)
    
        # ✅ Mark session complete if all sets are done
        if all_completed:
            supabase.table("plan_sessions").update({"completed": True}) \
                .eq("id", session["session_id"]).execute()
    
        st.success("Progress saved. Returning to dashboard...")
        st.session_state.selected_session = None
        st.rerun()
