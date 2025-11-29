
import streamlit as st
import re
from supabase import create_client
from datetime import datetime
from utils.timer import run_rest_timer

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    # Fetch session details
    session_data = supabase.table("plan_sessions").select("*").eq("id", session["session_id"]).single().execute().data
    if not session_data:
        st.error("Session details not found.")
        return

    details = session_data.get('details', 'No details provided')
    wod_type = None
    for t in ["AMRAP", "Chipper", "Interval", "Tabata", "For Time", "Ladder", "Death by", "EMOM", "Alternating EMOM"]:
        if t.lower() in details.lower():
            wod_type = t
            break
    if not wod_type:
        wod_type = "WOD"

    exercises = [line.strip("- ") for line in details.split("\n") if line.strip().startswith("-")]

    st.title(f"🔥 {wod_type} Session")
    st.markdown(f"**Week:** {session['week']}  \n **Day:** {session['day']}")
    st.write(f"**Details:** {details}")

    # Detect duration and intervals
    duration_minutes = None
    work_minutes = None
    rest_minutes = None
    match_duration = re.search(r"(\d+)\s*min", details.lower())
    if match_duration:
        duration_minutes = int(match_duration.group(1))
    if "work" in details.lower() and "rest" in details.lower():
        work_match = re.search(r"work\s*(\d+)\s*min", details.lower())
        rest_match = re.search(r"rest\s*(\d+)\s*min", details.lower())
        if work_match:
            work_minutes = int(work_match.group(1))
        if rest_match:
            rest_minutes = int(rest_match.group(1))

    # Placeholders
    progress_placeholder = st.empty()
    current_placeholder = st.empty()
    next_placeholder = st.empty()

    # Control buttons
    col1, col2, col3 = st.columns(3)
    if "wod_running" not in st.session_state:
        st.session_state.wod_running = False
    if "wod_paused" not in st.session_state:
        st.session_state.wod_paused = False

    if col1.button("▶ Start WOD Session"):
        st.session_state.wod_running = True
        st.session_state.wod_paused = False
    if col2.button("⏸ Pause"):
        st.session_state.wod_paused = True
    if col3.button("⬅ Back to Dashboard"):
        st.session_state.wod_running = False
        st.session_state.selected_session = None
        st.rerun()

    # Execute WOD logic
    if st.session_state.wod_running and not st.session_state.wod_paused:
        total_seconds = (duration_minutes * 60) if duration_minutes else 900
        elapsed = 0

        for i, ex in enumerate(exercises):
            next_ex = exercises[i+1] if i+1 < len(exercises) else None

            # Update progress
            progress_placeholder.progress(elapsed / total_seconds)
            progress_placeholder.markdown(f"**Elapsed:** {elapsed//60} min")

            # Clear previous placeholders
            current_placeholder.empty()
            next_placeholder.empty()

            # Show current and next
            current_placeholder.subheader(f"Current: {ex}")
            next_placeholder.info(f"Next: {next_ex if next_ex else 'None'}")

            # Determine work/rest logic based on WOD type
            if wod_type == "AMRAP" and duration_minutes:
                run_rest_timer(duration_minutes * 60, label="AMRAP", next_item=next_ex, skip_key=f"skip_amrap")
                elapsed += duration_minutes * 60
                break  # AMRAP runs full duration
            elif wod_type in ["For Time", "Chipper", "Ladder"]:
                run_rest_timer(60, label=ex, next_item=next_ex, skip_key=f"skip_ex_{i}")
                elapsed += 60
            elif wod_type == "Interval" and work_minutes and rest_minutes:
                run_rest_timer(work_minutes * 60, label=f"Work: {ex}", next_item="Rest", skip_key=f"skip_work_{i}")
                elapsed += work_minutes * 60
                if next_ex:
                    run_rest_timer(rest_minutes * 60, label="Rest", next_item=next_ex, skip_key=f"skip_rest_{i}")
                    elapsed += rest_minutes * 60
            elif wod_type == "Tabata":
                for r in range(8):
                    run_rest_timer(20, label=f"Round {r+1} Work", next_item="Rest", skip_key=f"skip_tabata_work_{r}")
                    run_rest_timer(10, label="Rest", next_item=next_ex, skip_key=f"skip_tabata_rest_{r}")
                    elapsed += 30
            elif wod_type in ["EMOM", "Alternating EMOM", "Death by"]:
                for m in range(duration_minutes or 15):
                    run_rest_timer(60, label=f"Minute {m+1}", next_item=next_ex, skip_key=f"skip_emom_{m}")
                    elapsed += 60
            else:
                run_rest_timer(60, label=ex, next_item=next_ex, skip_key=f"skip_generic_{i}")
                elapsed += 60

            # Update progress after each segment
            progress_placeholder.progress(min(elapsed / total_seconds, 1.0))

        # Mark session complete
        supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success("WOD completed!")
        st.session_state.selected_session = None
        st.rerun()
