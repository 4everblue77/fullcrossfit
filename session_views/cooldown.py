import streamlit as st

def render(session):
    st.title("❄️ Cooldown")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")
    st.info("Cooldown UI coming soon...")
