import streamlit as st
import pandas as pd
from supabase import create_client

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🔥 WOD Session")
    st.markdown(f"**Week:** {session.get('week', '')}  \n **Day:** {session.get('day', '')}")
    st.info(f"Target Muscles: {session.get('target_muscle', 'General')}")
    st.write(f"**Details:** {session.get('details', '')}")
    st.write(f"**Duration:** {session.get('duration', 0)} min")

    # Fetch exercises for this WOD session
    exercises = supabase.table("plan_session_exercises")         .select("*")         .eq("session_id", session["session_id"])         .order("set_number")         .execute().data

    if not exercises:
        st.warning("No exercises found for this WOD session.")
        return

    # Prepare DataFrame
    data = []
    for ex in exercises:
        data.append({
            "ID": ex["id"],
            "Exercise": ex.get("exercise_name", ""),
            "Set": ex.get("set_number", ""),
            "Reps": ex.get("reps", ""),
            "Intensity": ex.get("intensity", ""),
            "Notes": ex.get("notes", ""),
            "Done": ex.get("completed", False)
        })

    df = pd.DataFrame(data)

    edited_df = st.data_editor(
        df.drop(columns=["ID"]),
        width='stretch',
        num_rows="fixed",
        hide_index=True,
        column_config={
            "Exercise": st.column_config.TextColumn("Exercise", disabled=True),
            "Set": st.column_config.NumberColumn("Set", disabled=True),
            "Reps": st.column_config.TextColumn("Reps"),
            "Intensity": st.column_config.TextColumn("Intensity", disabled=True),
            "Notes": st.column_config.TextColumn("Notes", disabled=True),
            "Done": st.column_config.CheckboxColumn("Done")
        }
    )

    # Save progress
    if st.button("⬅ Back to Dashboard"):
        for i, row_id in enumerate(df["ID"]):
            supabase.table("plan_session_exercises").update({
                "completed": bool(edited_df.loc[i, "Done"])
            }).eq("id", row_id).execute()
        st.success("Progress saved. Returning to dashboard...")
        st.session_state.selected_session = None
        st.rerun()
