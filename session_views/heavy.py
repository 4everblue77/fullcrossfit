
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

    # ✅ Inject CSS for responsive table
    st.markdown("""
    <style>
    .responsive-table {width:100%; border-collapse:collapse;}
    .responsive-table th, .responsive-table td {border:1px solid #ddd; padding:8px; text-align:center;}
    .responsive-table th {background-color:#f4f4f4; font-weight:bold;}
    @media (max-width:768px) {
        .responsive-table thead {display:none;}
        .responsive-table tr {display:block; margin-bottom:10px;}
        .responsive-table td {display:flex; justify-content:space-between; padding:10px;}
    }
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
                return [], []
            st.markdown(f"**{block_name}**")

            html = "<table class='responsive-table'><thead><tr><th>Set</th><th>%RM</th><th>Weight</th><th>Reps</th><th>Done</th></tr></thead><tbody>"
            ids = []
            for row in block_sets:
                row_id = row["id"]
                ids.append(row_id)
                completed = row.get("completed", False)
                planned_reps = row.get("reps", "")
                actual_reps = row.get("actual_reps", "")
                reps_value = actual_reps if completed and actual_reps else planned_reps

                # Render inputs using Streamlit placeholders
                weight_ph = st.empty()
                reps_ph = st.empty()
                done_ph = st.empty()

                weight_val = weight_ph.text_input(f"Weight for {row_id}", value=str(row.get("actual_weight", "")), key=f"weight_{row_id}")
                reps_val = reps_ph.text_input(f"Reps for {row_id}", value=str(reps_value), key=f"reps_{row_id}")
                done_val = done_ph.checkbox(f"Done {row_id}", value=completed, key=f"done_{row_id}")

                html += f"<tr><td>{row.get('set_number','')}</td><td>{row.get('intensity','')}</td><td>{weight_val}</td><td>{reps_val}</td><td>{'✅' if done_val else '⬜'}</td></tr>"
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)
            return ids

        warmup_ids = render_block("🔥 Warmup Sets", warmup_sets)
        working_ids = render_block("💪 Working Sets", working_sets)

        if st.button(f"✅ Save Progress for {ex_name}"):
            for row_id in warmup_ids + working_ids:
                supabase.table("plan_session_exercises").update({
                    "completed": st.session_state.get(f"done_{row_id}"),
                    "actual_weight": st.session_state.get(f"weight_{row_id}"),
                    "actual_reps": st.session_state.get(f"reps_{row_id}")
                }).eq("id", row_id).execute()
            st.success(f"Progress for {ex_name} saved to Supabase")

    if st.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()
