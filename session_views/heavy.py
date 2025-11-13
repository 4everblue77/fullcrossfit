import streamlit as st

def render(session):
    st.title("🏋️ Heavy Session")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")
    st.info("Heavy session UI coming soon...")
