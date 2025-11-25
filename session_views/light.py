
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

def update_1rm_on_completion(exercise_name, completed_sets):
    for s in completed_sets:
        if s.get('completed') and s.get('actual_weight') and s.get('actual_reps'):
            weight = float(s['actual_weight'])
            reps = int(s['actual_reps'])
            calc_1rm = calculate_1rm(weight, reps)

            latest = supabase.table('exercise_maxes') \
                .select('*') \
                .eq('exercise_name', exercise_name) \
                .order('date', desc=True) \
                .limit(1) \
                .execute().data

            latest_max = None
            if latest:
                latest_max = latest[0].get('manual_1rm') or latest[0].get('calculated_1rm')

            if not latest_max or calc_1rm > latest_max:
                supabase.table('exercise_maxes').insert({
                    'exercise_name': exercise_name,
                    'calculated_1rm': calc_1rm,
                    'source_set_id': s['id'],
                    'date': datetime.utcnow().isoformat()
                }).execute()



def parse_reps_and_weight(note, one_rm):
    #st.write(f"🔍 Parsing note: '{note}' | 1RM: {one_rm}")

    # Normalize dashes and spaces
    normalized_note = note.replace("–", "-").replace("—", "-").replace("−", "-")
    normalized_note = re.sub(r'\s+', ' ', normalized_note)  # collapse spaces

    # Debug normalized note
    #st.write(f"🔍 Normalized note: '{normalized_note}'")

    # Match reps range
    reps_match = re.search(r'(\d+\s*-\s*\d+)', normalized_note)
    reps = reps_match.group(1) if reps_match else ""

    # Match percentage
    pct_match = re.search(r'(\d+)\s*%?\s*1RM', normalized_note)
    pct = int(pct_match.group(1)) if pct_match else 0

    suggested_weight = round(one_rm * (pct / 100), 2) if pct > 0 and one_rm > 0 else None

    #st.write(f"✅ Parsed reps: '{reps}', pct: {pct}, suggested weight: {suggested_weight}")
    return reps, suggested_weight



# --- Render Block ---
def render_block(block_name, block_sets, ex_name, one_rm):
    if not block_sets:
        return None, []

    st.markdown(f"**{block_name} Sets**")

    data = []
    for row in block_sets:
        note = str(row.get("reps", "")) or str(row.get("notes", ""))
        reps_value, suggested_weight = parse_reps_and_weight(note, one_rm)

        planned_sets = int(row.get("sets", 3))  # Default 3 sets
        for set_num in range(1, planned_sets + 1):
            data.append({
                "ID": f"{row['id']}_{set_num}",
                "Set": set_num,
                "Weight": suggested_weight if suggested_weight else 0.0,
                "Reps": reps_value if reps_value else "",
                "Done": False,
                "Rest": row.get("rest", 60)
            })

    df = pd.DataFrame(data)

    edited_df = st.data_editor(
        df.drop(columns=["ID", "Rest"]),
        num_rows="fixed",
        width='stretch',
        hide_index=True,
        column_config={
            "Set": st.column_config.NumberColumn("Set", disabled=True),
            "Weight": st.column_config.NumberColumn("Weight", format="%.2f"),
            "Reps": st.column_config.TextColumn("Reps"),
            "Done": st.column_config.CheckboxColumn("Done")
        },
        key=f"editor_{block_name}_{ex_name}"
    )

    # Rest timer logic
    for i, done in enumerate(edited_df["Done"]):
        if done and not df.loc[i, "Done"]:
            rest_seconds = int(df.loc[i, "Rest"])
            status_placeholder = st.empty()
            timer_placeholder = st.empty()
            progress_placeholder = st.empty()
            skip_placeholder = st.empty()

            status_placeholder.markdown(
                f"<h4>✅ Set {edited_df.loc[i, 'Set']} completed! Rest timer:</h4>",
                unsafe_allow_html=True
            )

            skip_button_key = f"skip_light_{block_name}_{ex_name}_{edited_df.loc[i, 'Set']}_{i}"
            skip_state_key = f"skip_state_light_{block_name}_{ex_name}_{edited_df.loc[i, 'Set']}_{i}"
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
    st.markdown(f"**Week:** {session['week']}  \n **Day:** {session['day']}")

    sets_data = supabase.table("plan_session_exercises") \
        .select("*") \
        .eq("session_id", session["session_id"]) \
        .order("exercise_order") \
        .execute().data

    if not sets_data:
        st.warning("No sets found for this light session.")
        return

    grouped_exercises = defaultdict(list)
    for row in sets_data:
        grouped_exercises[row["exercise_name"]].append(row)
    for ex_name in grouped_exercises:
        grouped_exercises[ex_name].sort(key=lambda r: r.get("set_number", 1))

    total_sets = len(sets_data)
    completed_sets = sum(1 for r in sets_data if r.get("completed", False))
    st.progress(completed_sets / total_sets if total_sets else 0)
    st.markdown(f"**Progress:** {completed_sets}/{total_sets} sets completed")

    all_dfs = []

    for ex_name, sets in grouped_exercises.items():
        st.subheader(ex_name)

        latest_max = supabase.table('exercise_maxes') \
            .select('calculated_1rm, manual_1rm') \
            .eq('exercise_name', ex_name) \
            .order('date', desc=True) \
            .limit(1) \
            .execute().data
        one_rm = latest_max[0].get('manual_1rm') or latest_max[0].get('calculated_1rm') if latest_max else 0

        warmup_sets = [s for s in sets if str(s.get('notes', '')).lower().startswith('warmup')]
        working_sets = [s for s in sets if s not in warmup_sets]

        warmup_df, warmup_ids = render_block('🔥 Warmup', warmup_sets, ex_name, one_rm)
        working_df, working_ids = render_block('💪 Working', working_sets, ex_name, one_rm)

        if warmup_df is not None:
            all_dfs.append((ex_name, warmup_df, warmup_ids))
        if working_df is not None:
            all_dfs.append((ex_name, working_df, working_ids))

    # ✅ Single Back to Dashboard button
   
    if st.button("⬅ Back to Dashboard", key=f"back_to_dashboard_{session['session_id']}_{len(all_dfs)}"):
        all_completed = True
    
        for ex_name, edited_df, ids in all_dfs:
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
    
            update_1rm_on_completion(ex_name, completed_sets_list)
    
        if all_completed:
            supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
    
        st.success("Progress saved. Returning to dashboard...")
        st.session_state.selected_session = None
        st.rerun()
