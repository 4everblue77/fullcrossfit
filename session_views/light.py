
import streamlit as st
import pandas as pd
import time
import re
from supabase import create_client
from collections import defaultdict
from datetime import datetime

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

def render_superset_block(superset_name, superset_sets):
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

    df = pd.DataFrame(data)
    edited_df = st.data_editor(
        df.drop(columns=["ID", "Rest"]),
        num_rows="fixed",
        width='stretch',
        hide_index=True,
        column_config={
            "Exercise": st.column_config.TextColumn("Exercise", disabled=True),
            "Set": st.column_config.NumberColumn("Set", disabled=True),
            "Weight": st.column_config.NumberColumn("Weight", format="%.2f"),
            "Reps": st.column_config.TextColumn("Reps"),
            "%RM": st.column_config.TextColumn("%RM", disabled=True),
            "Done": st.column_config.CheckboxColumn("Done")
        },
        key=f"editor_{superset_name}"
    )

    # Rest timer logic
    for i, done in enumerate(edited_df["Done"]):
        if done and not df.loc[i, "Done"]:
            rest_seconds = int(df.loc[i, "Rest"])
            status_placeholder = st.empty()
            timer_placeholder = st.empty()
            progress_placeholder = st.empty()
            skip_placeholder = st.empty()
            status_placeholder.markdown(f"<h4>✅ Set {edited_df.loc[i, 'Set']} completed! Rest timer:</h4>", unsafe_allow_html=True)
            skip_button_key = f"skip_rest_{superset_name}_{edited_df.loc[i, 'Set']}_{i}"
            skip_state_key = f"skip_state_{superset_name}_{edited_df.loc[i, 'Set']}_{i}"
            skip = skip_placeholder.button(f"⏭ Skip Rest for Set {edited_df.loc[i, 'Set']}", key=skip_button_key)
            if skip:
                st.session_state[skip_state_key] = True
            for remaining in range(rest_seconds, 0, -1):
                if st.session_state.get(skip_state_key, False):
                    timer_placeholder.markdown("<h3 style='color:#ff4b4b;'>⏭ Timer skipped! Ready for next set.</h3>", unsafe_allow_html=True)
                    break
                mins, secs = divmod(remaining, 60)
                timer_placeholder.markdown(f"<h1 style='text-align:center; color:#28a745;'>⏳ {mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
                progress_placeholder.progress((rest_seconds - remaining) / rest_seconds)
                time.sleep(1)
            else:
                if not st.session_state.get(skip_state_key, False):
                    timer_placeholder.markdown("<h3 style='color:#28a745;'>🔥 Ready for next set!</h3>", unsafe_allow_html=True)
            status_placeholder.empty()
            timer_placeholder.empty()
            progress_placeholder.empty()
            skip_placeholder.empty()

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
        edited_df, ids = render_superset_block(superset_name, superset_sets)
        if edited_df is not None:
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
                    'actual_reps': edited_df.loc[i, 'Reps'],
                    'set_number': edited_df.loc[i, 'Set']
                })
                if not is_done:
                    all_completed = False
        if all_completed:
            supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success("Progress saved. Returning to dashboard...")
        st.session_state.selected_session = None
        st.rerun()
