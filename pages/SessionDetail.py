import streamlit as st
from supabase import create_client

# Page config
st.set_page_config(page_title="Session Detail", page_icon="📄")

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Get selected session
session = st.session_state.get("selected_session")

if not session:
    st.warning("No session selected. Go back to Dashboard.")
    st.switch_page("Dashboard")
else:
    st.title(f"📄 Session Detail: {session['type']}")
    st.markdown(f"**Week:** {session['week']} | **Day:** {session['day']}")

    if st.button("✅ Mark as Completed", use_container_width=True):
        supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success("Session marked as completed!")

    if st.button("⬅ Back to Dashboard", use_container_width=True):
        st.session_state.selected_session = None
        st.switch_page("Dashboard")
