import streamlit as st

st.title("📋 Session Details")

selected_session = st.session_state.get("selected_session", None)

if not selected_session:
    st.warning("No session selected. Go back to the Dashboard.")
    st.stop()

session_type = selected_session["type"]
session_content = selected_session["content"]
day = selected_session["day"]
week = selected_session["week"]

st.subheader(f"{session_type} - {day} ({week})")

# Display exercises
if "exercises" in session_content and isinstance(session_content["exercises"], list):
    for i, ex in enumerate(session_content["exercises"], start=1):
        st.markdown(f"**{i}. {ex.get('name', '[Exercise]')}**")
        st.write(f"Sets: {ex.get('set', '')}, Reps: {ex.get('reps', '')}")
        if ex.get("expected_weight"):
            st.write(f"Expected Weight: {ex['expected_weight']}")
        if ex.get("tempo"):
            st.write(f"Tempo: {ex['tempo']}")
        if ex.get("rest"):
            st.write(f"Rest: {ex['rest']} sec")
else:
    st.info("No exercises available for this session.")

# Completion toggle
if st.button("Mark Session as Completed"):
    # Placeholder: Update Supabase or session_state
    st.success(f"{session_type} marked as completed!")
