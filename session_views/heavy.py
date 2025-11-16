
import streamlit as st
from supabase import create_client
from collections import defaultdict

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🏋 Heavy Session")
    st.markdown(f"**Week:** {session['week']} /n **Day:** {session['day']}")

    # ✅ Inject CSS for horizontal scroll
    st.markdown("""
    <style>
    .scroll-table {overflow-x:auto;}
    table {border-collapse:collapse;width:100%;min-width:700px;}
    th, td {border:1px solid #ddd;padding:8px;text-align:center;}
    th {background-color:#f4f4f4;font-weight:bold;}
    </style>
    """, unsafe_allow_html=True)

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

    # Render each exercise
    for ex_name, sets in grouped_exercises.items():
        st.subheader(ex_name)

        warmup_sets = [s for s in sets if str(s.get("notes", "")).lower().startswith("warmup")]
        working_sets = [s for s in sets if s not in warmup_sets]

        def render_block(block_name, block_sets):
            if not block_sets:
                return []
            st.markdown(f"**{block_name}**")

            # Table header
            st.markdown("<div class='scroll-table'><table><thead><tr><th>Set</th><th>%RM</th><th>Weight</th><th>Reps</th><th>Done</th></tr></thead><tbody>", unsafe_allow_html=True)

            ids = []
            for idx, row in enumerate(block_sets):
                ids.append(row["id"])
                completed = row.get("completed", False)
                planned_reps = row.get("reps", "")
                actual_reps = row.get("actual_reps", "")
                reps_value = actual_reps if completed and actual_reps else planned_reps

                # Embed Streamlit widgets inside table cells
                col_weight = st.text_input("", value=str(row.get("actual_weight", "")), key=f"weight_{block_name}_{idx}")
                col_reps = st.text_input("", value=str(reps_value), key=f"reps_{block_name}_{idx}")
                col_done = st.checkbox("", value=completed, key=f"done_{block_name}_{idx}")

                # Render row visually with placeholders replaced by widget values
                st.markdown(f"<tr><td>{row.get('set_number','')}</td><td>{row.get('intensity','')}</td><td>{col_weight}</td><td>{col_reps}</td><td>{'✅' if col_done else '⬜'}</td></tr>", unsafe_allow_html=True)

            st.markdown("</tbody></table></div>", unsafe_allow_html=True)
            return ids

        warmup_ids = render_block("Warmup", warmup_sets)
        working_ids = render_block("Working", working_sets)

        if st.button(f"✅ Save Progress for {ex_name}"):
            # Update DB for all sets
            for idx, row_id in enumerate(warmup_ids):
                supabase.table("plan_session_exercises").update({
                    "completed": st.session_state.get(f"done_Warmup_{idx}"),
                    "actual_weight": st.session_state.get(f"weight_Warmup_{idx}"),
                    "actual_reps": st.session_state.get(f"reps_Warmup_{idx}")
                }).eq("id", row_id).execute()

            for idx, row_id in enumerate(working_ids):
                supabase.table("plan_session_exercises").update({
                    "completed": st.session_state.get(f"done_Working_{idx}"),
                    "actual_weight": st.session_state.get(f"weight_Working_{idx}"),
                    "actual_reps": st.session_state.get(f"reps_Working_{idx}")
                }).eq("id", row_id).execute()

            st.success(f"Progress for {ex_name} saved to Supabase")

    if st.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()
