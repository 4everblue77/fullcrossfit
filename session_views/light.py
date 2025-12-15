
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
# Helpers
# ---------------------------
SET_REGEX = re.compile(r"Set\s*\((\d+)\)", flags=re.IGNORECASE)

def parse_reps_only(note: str) -> str:
    """Extract a reps hint like '(8-10)' if present (display only)."""
    if not note:
        return ""
    normalized = note.replace("–", "-").replace("—", "-").replace("−", "-")
    normalized = re.sub(r"\s+", " ", normalized)
    m = re.search(r"\((\d+\s*-\s*\d+)\)", normalized)
    return m.group(1) if m else ""

def fetch_prev_best_for_exercise(exercise_name: str):
    """
    Previous best for an exercise from completed rows in plan_session_exercises.
    Uses highest actual_weight (simple, equipment-agnostic).
    Returns dict(weight, reps) or None.
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

def persist_block_changes(edited_df, original_df, row_ids):
    """
    Persist per-row changes for a block and rerun once
    so UI aligns with DB immediately (prevents needing to click twice).
    """
    if edited_df is None or original_df is None or not row_ids:
        return
    any_updated = False

    for i, row_id in enumerate(row_ids):
        is_done_now = bool(edited_df.loc[i, "Done"])
        weight_now  = str(edited_df.loc[i, "Weight"])
        reps_now    = str(edited_df.loc[i, "Reps"])

        was_done    = bool(original_df.loc[i, "Done"])
        weight_prev = str(original_df.loc[i, "Weight"])
        reps_prev   = str(original_df.loc[i, "Reps"])

        if (is_done_now != was_done) or (weight_now != weight_prev) or (reps_now != reps_prev):
            supabase.table("plan_session_exercises").update(
                {"completed": is_done_now, "actual_weight": weight_now, "actual_reps": reps_now}
            ).eq("id", row_id).execute()
            any_updated = True

    if any_updated:
        st.rerun()


# ---------------------------
# Block renderer
# ---------------------------
def render_set_block(block_title: str, rows: list, session, show_prev_bests: bool, session_ex_names: list):
    """
    Render one 'Set (n)' block.
    If show_prev_bests=True, show the Previous Bests expander above the editor for all session exercises.
    """
    st.markdown(f"### {block_title}")

    # --- 📈 Previous Bests (show once, above Set 1) ---
    if show_prev_bests and session_ex_names:
        with st.expander("📈 Previous Bests (this session’s exercises)", expanded=True):
            for ex_n in session_ex_names:
                prev_best = fetch_prev_best_for_exercise(ex_n)
                if prev_best and prev_best.get("weight"):
                    w = prev_best.get("weight")
                    r = prev_best.get("reps") if prev_best.get("reps") else "—"
                    st.markdown(f"- **{ex_n}**: best weight **{w}**, reps **{r}**")
                else:
                    st.markdown(f"- **{ex_n}**: no previous completed sets recorded")

    # --- Build table data ---
    data = []
    for row in rows:
        reps_hint = parse_reps_only(str(row.get("reps", "")))
        weight_value = row.get("actual_weight") if row.get("completed") else ""
        reps_display = row.get("actual_reps") if row.get("completed") else reps_hint

        data.append(
            {
                "ID": row["id"],
                "Exercise": row.get("exercise_name", ""),
                "Set": row.get("set_number", ""),
                "Weight": weight_value,
                "Reps": reps_display,
                "%RM": row.get("intensity", ""),  # kept for context; not used to compute
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
        key=f"editor_{session['session_id']}_{block_title}"
    )

    # Save instantly + rerun (prevents double-click)
    ids = df_original["ID"].tolist()
    persist_block_changes(edited_df, df_original, ids)

    # Group rest timer controls
    rest_default = int(df_original["Rest"].iloc[0]) if len(df_original) else 60
    rest_seconds = st.number_input(
        "Rest (seconds)", min_value=10, max_value=600, value=rest_default, step=10,
        key=f"rest_input_{session['session_id']}_{block_title}"
    )
    if st.button(
        f"▶ Start Rest Timer ({rest_seconds}s)",
        key=f"rest_button_{session['session_id']}_{block_title}"
    ):
        run_rest_timer(
            rest_seconds,
            label=f"{block_title} – Rest",
            next_item=None,
            skip_key=f"rest_skip_{session['session_id']}_{block_title}"
        )

    # Return edited_df for final “Back to Dashboard” pass
    return edited_df, ids


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

    # --- Group rows by 'Set (n)' in notes ---
    grouped = defaultdict(list)
    other_rows = []
    for row in sets_data:
        notes = str(row.get("notes", "") or "")
        m = SET_REGEX.search(notes)
        if m:
            idx = int(m.group(1))
            grouped[idx].append(row)
        else:
            other_rows.append(row)

    # Sort set indices numerically (Set 1, Set 2, Set 3, ...)
    ordered_keys = sorted(grouped.keys())

    # Progress
    total_sets = len(sets_data)
    completed_sets = sum(1 for r in sets_data if r.get("completed", False))
    st.progress(completed_sets / total_sets if total_sets else 0)
    st.markdown(f"**Progress:** {completed_sets}/{total_sets} sets completed")

    # Collect all exercise names in this session for the “Previous Bests” section
    session_ex_names = []
    for r in sets_data:
        ex_n = str(r.get("exercise_name", "")).strip()
        if ex_n and ex_n not in session_ex_names:
            session_ex_names.append(ex_n)

    # Render each Set block in order; show prev bests only above Set 1
    all_blocks = []  # (edited_df, ids)
    for ix, k in enumerate(ordered_keys):
        rows = grouped[k]
        block_title = f"Set ({k})"
        show_prev = ix == 0  # only above Set 1
        edited_df, ids = render_set_block(block_title, rows, session, show_prev, session_ex_names)
        all_blocks.append((edited_df, ids))

    # Render "Other" block last (if any rows lacked 'Set (n)')
    if other_rows:
        edited_df, ids = render_set_block("Other", other_rows, session, show_prev_bests=False, session_ex_names=[])
        all_blocks.append((edited_df, ids))

    # ---- Back to Dashboard (bulk save + mark session complete) ----
    if st.button("⬅ Back to Dashboard", key=f"back_to_dashboard_{session['session_id']}_{len(all_blocks)}"):
        all_completed = True
        for edited_df, ids in all_blocks:
            if edited_df is None:
                continue
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
        st.rerun
