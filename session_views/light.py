
import streamlit as st
import pandas as pd
import re
from supabase import create_client
from collections import defaultdict
from utils.timer import run_rest_timer

# ---------------------------
# Supabase setup
# ---------------------------
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------------------------
# Utility (display only)
# ---------------------------
def parse_reps_and_weight(note):
    """
    Parse a textual reps note like '(8-10)' from 'note' field.
    This returns the reps string only (no %1RM or suggested weights).
    """
    normalized_note = (
        note.replace("–", "-").replace("—", "-").replace("−", "-")
    )
    normalized_note = re.sub(r'\s+', ' ', normalized_note)
    reps_match = re.search(r'\((\d+\s*-\s*\d+)\)', normalized_note)
    reps = reps_match.group(1) if reps_match else ""
    return reps


def fetch_prev_best_for_exercise(exercise_name: str):
    """
    Fetch previous best for the given exercise from plan_session_exercises
    using the highest actual_weight in completed sets (simple, equipment-agnostic).
    Returns dict with keys: weight, reps. If none found, returns None.
    """
    try:
        rows = (
            supabase.table("plan_session_exercises")
            .select("*")
            .eq("exercise_name", exercise_name)
            .eq("completed", True)
            .order("actual_weight", desc=True)
            .limit(1)
            .execute()
            .data
        )
    except Exception:
        rows = None

    if rows:
        best = rows[0]
        return {
            "weight": best.get("actual_weight"),
            "reps": best.get("actual_reps"),
        }
    return None


# ---------------------------
# Single-click save helper
# ---------------------------
def persist_block_changes(edited_df, original_df, row_ids):
    """
    Persist per-row changes for a block (superset), then rerun once
    so UI aligns with DB immediately (prevents needing to click twice).
    """
    if edited_df is None or original_df is None or not row_ids:
        return

    any_updated = False

    for i, row_id in enumerate(row_ids):
        # Current (edited) values
        is_done_now = bool(edited_df.loc[i, "Done"])
        weight_now = str(edited_df.loc[i, "Weight"])
        reps_now = str(edited_df.loc[i, "Reps"])

        # Previous (original snapshot) values
        was_done = bool(original_df.loc[i, "Done"])
        weight_prev = str(original_df.loc[i, "Weight"])
        reps_prev = str(original_df.loc[i, "Reps"])

        # Write only if something changed
        if (is_done_now != was_done) or (weight_now != weight_prev) or (reps_now != reps_prev):
            supabase.table("plan_session_exercises").update(
                {
                    "completed": is_done_now,
                    "actual_weight": weight_now,
                    "actual_reps": reps_now,
                }
            ).eq("id", row_id).execute()
            any_updated = True

            # Optional per-row rest timer on newly completed set
            if is_done_now and not was_done:
                # We do not update 1RMs anymore by request
                pass

    if any_updated:
        # Single rerun after all updates so table reflects DB instantly
        st.rerun()


# ---------------------------
# Superset block renderer
# ---------------------------
def render_superset_block(superset_name, superset_sets, session):
    """
    Render a superset block (two+ exercises grouped by the same 'Set (n)' note).
    Shows previous bests above the editor, then the editable table, then timers.
    """
    st.markdown(f"### {superset_name}")

    # --- 🔎 Previous bests (before Set 1 UI) ---
    # Each row has an exercise_name; gather unique names and show best weight & reps.
    ex_names = []
    for row in superset_sets:
        ex_n = str(row.get("exercise_name", "")).strip()
        if ex_n and ex_n not in ex_names:
            ex_names.append(ex_n)

    if ex_names:
        with st.expander("📈 Previous Bests (per exercise)", expanded=True):
            for ex_n in ex_names:
                prev_best = fetch_prev_best_for_exercise(ex_n)
                if prev_best and prev_best.get("weight"):
                    w = prev_best.get("weight")
                    r = prev_best.get("reps") if prev_best.get("reps") else "—"
                    st.markdown(f"- **{ex_n}**: best weight **{w}**, reps **{r}**")
                else:
                    st.markdown(f"- **{ex_n}**: no previous completed sets recorded")

    # --- Table (editor) ---
    data = []
    for row in superset_sets:
        reps_value = parse_reps_and_weight(str(row.get("reps", "")))
        weight_value = row.get("actual_weight") if row.get("completed") else ""
        reps_display = row.get("actual_reps") if row.get("completed") else reps_value

        data.append(
            {
                "ID": row["id"],
                "Exercise": row.get("exercise_name", ""),
                "Set": row.get("set_number", ""),
                "Weight": weight_value,
                "Reps": reps_display,
                "%RM": row.get("intensity", ""),  # retained for context; not auto-derived
                "Done": row.get("completed", False),
                "Rest": row.get("rest", 60),
            }
        )

    df_original = pd.DataFrame(data)

    edited_df = st.data_editor(
        df_original.drop(columns=["ID", "Rest", "Set"]),
        num_rows="fixed",
        width="stretch",
        hide_index=True,
        column_config={
            "Exercise": st.column_config.TextColumn("Exercise", disabled=True),
            "Weight": st.column_config.NumberColumn("Weight", format="%.2f"),
            "Reps": st.column_config.TextColumn("Reps"),
            "%RM": st.column_config.TextColumn("%RM", disabled=True),
            "Done": st.column_config.CheckboxColumn("Done"),
        },
        key=f"editor_{session['session_id']}_{superset_name}"  # stable per session+superset
    )

    # Group rest timer
    rest_seconds = int(df_original["Rest"].iloc[0]) if len(df_original) else 60
    rest_seconds = st.number_input(
        "Rest (seconds)",
        min_value=10, max_value=600, value=rest_seconds, step=10,
        key=f"light_rest_input_{session['session_id']}_{superset_name}"
    )
    if st.button(
        f"▶ Start Rest Timer ({rest_seconds}s)",
        key=f"light_rest_button_{session['session_id']}_{superset_name}"
    ):
        run_rest_timer(
            rest_seconds,
            label="Rest",
            next_item=None,
            skip_key=f"light_rest_skip_{session['session_id']}_{superset_name}"
        )

    return edited_df, df_original, df_original["ID"].tolist()


# ---------------------------
# Main render
# ---------------------------
def render(session):
    st.title("💡 Light Session")
    st.markdown(f"**Week:** {session['week']}\n**Day:** {session['day']}")

    # Pull sets for this session
    sets_data = (
        supabase.table("plan_session_exercises")
        .select("*")
        .eq("session_id", session["session_id"])
        .order("exercise_order")
        .execute()
        .data
    )

    if not sets_data:
        st.warning("No sets found for this light session.")
        return

    # Group rows into supersets based on notes "Set (n)"
    superset_groups = defaultdict(list)
    for row in sets_data:
        match = re.search(r"Set \((\d+)\)", row.get("notes", ""))
        superset_key = f"Set {match.group(1)}" if match else "Other"
        superset_groups[superset_key].append(row)

    # Progress
    total_sets = len(sets_data)
    completed_sets = sum(1 for r in sets_data if r.get("completed", False))
    st.progress(completed_sets / total_sets if total_sets else 0)
    st.markdown(f"**Progress:** {completed_sets}/{total_sets} sets completed")

    # Render supersets
    all_dfs = []
    for superset_name, superset_sets in superset_groups.items():
        edited_df, df_original, ids = render_superset_block(superset_name, superset_sets, session)

        if edited_df is not None:
            # one-click persistence + rerun (removes double-tick requirement)
            persist_block_changes(edited_df, df_original, ids)

            # Collect for final session-complete check (bulk save)
            all_dfs.append((superset_name, edited_df, ids))

    # ---- Back to Dashboard (bulk save + mark session complete) ----
    if st.button("⬅ Back to Dashboard", key=f"back_to_dashboard_{session['session_id']}_{len(all_dfs)}"):
        all_completed = True
        for superset_name, edited_df, ids in all_dfs:
            for i, row_id in enumerate(ids):
                is_done = bool(edited_df.loc[i, "Done"])
                supabase.table("plan_session_exercises").update(
                    {
                        "completed": is_done,
                        "actual_weight": str(edited_df.loc[i, "Weight"]),
                        "actual_reps": str(edited_df.loc[i, "Reps"]),
                    }
                ).eq("id", row_id).execute()

                if not is_done:
                    all_completed = False

        if all_completed:
            supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()

        st.success("Progress saved. Returning to dashboard...")
        st.session_state.selected_session = None
       
