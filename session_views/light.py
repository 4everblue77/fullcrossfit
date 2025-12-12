
import streamlit as st
import pandas as pd
import time
import re
from supabase import create_client
from collections import defaultdict
from datetime import datetime
from utils.timer import run_rest_timer

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Utility Functions ---
def calculate_1rm(weight: float, reps: int) -> float:
    """Calculate estimated 1RM using Epley formula."""
    if reps <= 1:
        return weight
    return round(weight * (1 + 0.0333 * reps), 2)

def parse_reps_and_weight(note, one_rm):
    normalized_note = note.replace("–", "-").replace("—", "-").replace("−", "-")
    normalized_note = re.sub(r'\s+', ' ', normalized_note)
    reps_match = re.search(r'(\d+\s*-\s*\d+)', normalized_note)
    reps = reps_match.group(1) if reps_match else ""
    pct_match = re.search(r'(\d+)\s*%?\s*1RM', normalized_note)
    pct = int(pct_match.group(1)) if pct_match else 0
    suggested_weight = round(one_rm * (pct / 100), 2) if pct > 0 and one_rm > 0 else None
    return reps, suggested_weight

def render_superset_block(superset_name, superset_sets,session):
    """Render a superset block with both exercises grouped."""
    st.markdown(f"### {superset_name}")
    data = []
    for row in superset_sets:
        reps_value, suggested_weight = parse_reps_and_weight(str(row.get("reps", "")), 0)
        weight_value = row.get("actual_weight") if row.get("completed") else (suggested_weight if suggested_weight else 0.0)
        reps_display = row.get("actual_reps") if row.get("completed") else reps_value
        data.append({
            "ID": row["id"],
            "Exercise": row.get("exercise_name", ""),
            "Set": row.get("set_number", ""),
            "Weight": weight_value,
            "Reps": reps_display,
            "%RM": row.get("intensity", ""),
            "Done": row.get("completed", False),
            "Rest": row.get("rest", 60)
        })


    df_original = pd.DataFrame(data)

    edited_df = st.data_editor(
        df_original.drop(columns=["ID", "Rest", "Set"]),
        num_rows="fixed",
        width='stretch',
        hide_index=True,
        column_config={
            "Exercise": st.column_config.TextColumn("Exercise", disabled=True),
            "Weight": st.column_config.NumberColumn("Weight", format="%.2f"),
            "Reps": st.column_config.TextColumn("Reps"),
            "%RM": st.column_config.TextColumn("%RM", disabled=True),
            "Done": st.column_config.CheckboxColumn("Done")
        },
        key=f"editor_{session['session_id']}_{superset_name}"  # stable per session+superset
    )


    # timer
    rest_seconds = int(df["Rest"].iloc[0])  # use first row's rest value
    rest_seconds = st.number_input("Rest (seconds)", min_value=10, max_value=600, value=rest_seconds, step=10, key=f"light_rest_input{session['session_id']}_{superset_name}")
    if st.button(
        f"▶ Start Rest Timer ({rest_seconds}s)",
        key = f"(light_rest_button{session['session_id']}_{superset_name}"
    ):
        run_rest_timer(rest_seconds, label="Rest", next_item=None,
                       skip_key=f"light_rest_skip{session['session_id']}_{superset_name}")
        
    return edited_df, df["ID"].tolist()
 
# --- Main Render ---
def render(session):
    st.title("💡 Light Session")
    st.markdown(f"**Week:** {session['week']}  \n**Day:** {session['day']}")

    sets_data = supabase.table("plan_session_exercises") \
        .select("*") \
        .eq("session_id", session["session_id"]) \
        .order("exercise_order") \
        .execute().data

    if not sets_data:
        st.warning("No sets found for this light session.")
        return

    # ✅ Group by Superset using notes

    superset_groups = defaultdict(list)
    for row in sets_data:
        match = re.search(r"Set (\d+)", row.get("notes", ""))
        superset_key = f"Set {match.group(1)}" if match else "Other"
        superset_groups[superset_key].append(row)


    total_sets = len(sets_data)
    completed_sets = sum(1 for r in sets_data if r.get("completed", False))
    st.progress(completed_sets / total_sets if total_sets else 0)
    st.markdown(f"**Progress:** {completed_sets}/{total_sets} sets completed")

    all_dfs = []

    for superset_name, superset_sets in superset_groups.items():
        edited_df, df_original, ids = render_superset_block(superset_name, superset_sets, session)
    
        if edited_df is not None:
            # Instant persistence per row
            for i, row_id in enumerate(ids):
                is_done_now = bool(edited_df.loc[i, "Done"])
                weight_now  = str(edited_df.loc[i, "Weight"])
                reps_now    = str(edited_df.loc[i, "Reps"])
    
                was_done    = bool(df_original.loc[i, "Done"])
                weight_prev = str(df_original.loc[i, "Weight"])
                reps_prev   = str(df_original.loc[i, "Reps"])
    
                # Only write if something changed
                if (is_done_now != was_done) or (weight_now != weight_prev) or (reps_now != reps_prev):
                    supabase.table("plan_session_exercises").update({
                        "completed": is_done_now,
                        "actual_weight": weight_now,
                        "actual_reps": reps_now
                    }).eq("id", row_id).execute()
    
                    # If newly completed, update 1RM and start a per-row rest timer (optional)
                    if is_done_now and not was_done:
                        exercise_name = df_original.loc[i, "Exercise"]
                        update_1rm_on_completion(exercise_name, [{
                            "id": row_id,
                            "completed": True,
                            "actual_weight": weight_now,
                            "actual_reps": reps_now,
                            # "set_number": df_original.loc[i, "Set"]  # available if needed
                        }])
    
                                           # Optional per-row rest timer
                        rest_seconds = int(df_original.loc[i, "Rest"])
                        run_rest_timer(
                            rest_seconds,
                            label=f"{superset_name} – {exercise_name}",
                            next_item=None,
                            skip_key=f"light_row_rest_{session['session_id']}_{superset_name}_{i}"
                        )
    
            # Keep for final completion check (optional)

            all_dfs.append((superset_name, edited_df, ids))

    # ✅ Save progress
    if st.button("⬅ Back to Dashboard", key=f"back_to_dashboard_{session['session_id']}_{len(all_dfs)}"):
        all_completed = True
        for superset_name, edited_df, ids in all_dfs:
            completed_sets_list = []
            for i, row_id in enumerate(ids):
                is_done = bool(edited_df.loc[i, 'Done'])
                supabase.table('plan_session_exercises').update({
                    'completed': is_done,
                    'actual_weight': str(edited_df.loc[i, 'Weight']),
                    'actual_reps': str(edited_df.loc[i, 'Reps'])
                }).eq('id', row_id).execute()
                completed_sets_list.append({
                    'id': row_id,
                    'completed': is_done,
                    'actual_weight': edited_df.loc[i, 'Weight'],
                    'actual_reps': edited_df.loc[i, 'Reps']
                    #,'set_number': edited_df.loc[i, 'Set']
                })
                if not is_done:
                    all_completed = False
        if all_completed:
            supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success("Progress saved. Returning to dashboard...")
        st.session_state.selected_session = None
        st.rerun()
