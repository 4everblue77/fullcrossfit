import streamlit as st
from supabase import create_client

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    # Fetch session details from plan_sessions using session_id
    session_data = supabase.table("plan_sessions")         .select("*")         .eq("id", session["session_id"])         .single()         .execute().data

    if not session_data:
        st.error("Session details not found.")
        return

    # Show WOD type as header
    st.title(f"🔥 {session_data.get('session_type', 'WOD')} Session")

    # Show Week and Day
    st.markdown(f"**Week:** {session['week']}  \n **Day:** {session['day']}")

    # Show Details prominently
    st.write(f"**Details:** {session_data.get('details', 'No details provided')}")

    # Back to Dashboard button
    if st.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()
