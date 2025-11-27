
import streamlit as st
from supabase import create_client

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    st.title("🏃 Run Session")
    st.markdown(f"**Week:** {session['week']}  \n **Day:** {session['day']}")

    # Fetch session details
    session_details = supabase.table("plan_sessions")         .select("*")         .eq("id", session["session_id"])         .execute().data

    if not session_details:
        st.warning("No details found for this run session.")
        return

    details = session_details[0]

    # Display run details
    st.markdown("### Session Details")
    distance = details.get("distance", "Not specified")
    duration = details.get("duration", "Not specified")
    pace = details.get("pace", "Not specified")
    notes = details.get("notes", "")

    st.write(f"**Distance:** {distance}")
    st.write(f"**Duration:** {duration}")
    st.write(f"**Pace:** {pace}")
    if notes:
        st.write(f"**Notes:** {notes}")

    # Completion checkbox
    if "run_completed" not in st.session_state:
        st.session_state.run_completed = details.get("completed", False)

    st.session_state.run_completed = st.checkbox("Mark session as completed", value=st.session_state.run_completed)

    # Back to Dashboard button
    if st.button("⬅ Back to Dashboard"):
        supabase.table("plan_sessions").update({"completed": st.session_state.run_completed}).eq("id", session["session_id"]).execute()
        st.success("Run session status saved. Returning to dashboard...")
        st.session_state.selected_session = None
        st.rerun()
