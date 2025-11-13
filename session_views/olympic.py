import streamlit as st

def render(session):
    st.title("🏅 Olympic Lifting")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")
    st.info("Olympic lifting UI coming soon...")
