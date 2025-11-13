import streamlit as st

def render(session):
    st.title("📦 WOD")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")
    st.info("WOD UI coming soon...")
