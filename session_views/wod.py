import streamlit as st

def render(session):
    # Show WOD type as header
    st.title(f"🔥 {session.get('session_type', 'WOD')} Session")

    # Show Week and Day
    st.markdown(f"**Week:** {session.get('week', '')}  \n **Day:** {session.get('day', '')}")

    # Show Details prominently
    st.write(f"**Details:** {session.get('details', 'No details provided')}")

    # Back to Dashboard button
    if st.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()
