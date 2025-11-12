import streamlit as st
from supabase import create_client

st.title("📄 Session Details")

selected_session = st.session_state.get("selected_session", None)

if not selected_session:
    st.warning("No session selected. Go back to the Dashboard.")
    st.stop()

session_type = selected_session["type"]
session_id = selected_session["session_id"]
day = selected_session["day"]
week = selected_session["week"]

st.subheader(f"{session_type} - {day} ({week})")

# ✅ Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ✅ Fetch exercises for this session
exercises = supabase.table("plan_session_exercises").select("*").eq("session_id", session_id).execute().data

if not exercises:
    st.info("No exercises available for this session.")
else:
    for i, ex in enumerate(exercises, start=1):
        st.markdown(f"**{i}. {ex.get('exercise_name', '[Exercise]')}**")
        st.write(f"Sets: {ex.get('set_number', '')}, Reps: {ex.get('reps', '')}")
        if ex.get("expected_weight"):
            st.write(f"Expected Weight: {ex['expected_weight']}")
        if ex.get("tempo"):
            st.write(f"Tempo: {ex['tempo']}")
        if ex.get("rest"):
            st.write(f"Rest: {ex['rest']} sec")

# ✅ Completion toggle
if st.button("Mark Session as Completed"):
    supabase.table("plan_sessions").update({"completed": True}).eq("id", session_id).execute()
    st.success(f"{session_type} marked as completed!")
