import streamlit as st
import time
import re
from supabase import create_client

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    # Fetch session details from plan_sessions using session_id
    session_data = supabase.table("plan_sessions")         .select("*")         .eq("id", session["session_id"])         .single()         .execute().data

    if not session_data:
        st.error("Session details not found.")
        return

    details = session_data.get('details', 'No details provided')
    
    # Detect WOD type from details
    wod_type = None
    for t in ["AMRAP", "Chipper", "Interval", "Tabata", "For Time", "Ladder", "Death by", "EMOM", "Alternating EMOM"]:
        if t.lower() in details.lower():
            wod_type = t
            break
    if not wod_type:
        wod_type = "WOD"


    st.title(f"🔥 {wod_type} Session")
    st.markdown(f"**Week:** {session['week']}  \n **Day:** {session['day']}")
    st.write(f"**Details:** {details}")

    # Timer placeholders
    timer_placeholder = st.empty()
    progress_placeholder = st.empty()
    stop_placeholder = st.empty()

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

    # Timer logic based on WOD type
    if st.button("▶ Start Timer", key="start_timer"):
        if wod_type == "AMRAP" and duration_minutes:
            run_countdown(duration_minutes * 60, timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "For Time":
            run_stopwatch(timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "Chipper":
            run_stopwatch(timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "Interval" and work_minutes and rest_minutes:
            run_interval(work_minutes, rest_minutes, duration_minutes, timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "Tabata":
            run_tabata(timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "Ladder":
            run_stopwatch(timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "Death by":
            run_emom(duration_minutes or 15, timer_placeholder, progress_placeholder, stop_placeholder, death_by=True)
        elif wod_type in ["EMOM", "Alternating EMOM"]:
            run_emom(duration_minutes or 15, timer_placeholder, progress_placeholder, stop_placeholder)
        else:
            st.warning("No timer logic available for this WOD type.")

    # Back to Dashboard button
    if st.button("⬅ Back to Dashboard"):
        st.session_state.selected_session = None
        st.rerun()

def run_countdown(total_seconds, timer_placeholder, progress_placeholder, stop_placeholder):
    stop_key = "stop_timer"
    st.session_state[stop_key] = False
    for remaining in range(total_seconds, 0, -1):
        if st.session_state.get(stop_key, False):
            timer_placeholder.markdown("<h3 style='color:#ff4b4b;'>⏹ Timer stopped!</h3>", unsafe_allow_html=True)
            break
        mins, secs = divmod(remaining, 60)
        timer_placeholder.markdown(f"<h1 style='text-align:center; color:#28a745;'>⏳ {mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
        progress_placeholder.progress((total_seconds - remaining) / total_seconds)
        if stop_placeholder.button("⏹ Stop Timer", key=f"stop_timer_{time.time()}"):
            st.session_state[stop_key] = True
        time.sleep(1)
    else:
        timer_placeholder.markdown("<h3 style='color:#28a745;'>✅ Time's up!</h3>", unsafe_allow_html=True)

def run_stopwatch(timer_placeholder, progress_placeholder, stop_placeholder):
    stop_key = "stop_timer"
    st.session_state[stop_key] = False
    elapsed = 0
    while not st.session_state.get(stop_key, False):
        mins, secs = divmod(elapsed, 60)
        timer_placeholder.markdown(f"<h1 style='text-align:center; color:#007bff;'>⏱ {mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
        progress_placeholder.progress(min(elapsed / 1800, 1.0))  # Cap at 30 min
        if stop_placeholder.button("⏹ Stop Timer", key=f"stop_timer_{time.time()}"):
            st.session_state[stop_key] = True
        time.sleep(1)
        elapsed += 1

def run_interval(work, rest, total, timer_placeholder, progress_placeholder, stop_placeholder):
    stop_key = "stop_timer"
    st.session_state[stop_key] = False
    total_seconds = total * 60 if total else (work + rest) * 60 * 5
    elapsed = 0
    while elapsed < total_seconds and not st.session_state.get(stop_key, False):
        # Work phase
        for remaining in range(work * 60, 0, -1):
            if st.session_state.get(stop_key, False): break
            mins, secs = divmod(remaining, 60)
            timer_placeholder.markdown(f"<h3 style='color:#28a745;'>Work: {mins:02d}:{secs:02d}</h3>", unsafe_allow_html=True)
            time.sleep(1)
            elapsed += 1
        # Rest phase
        for remaining in range(rest * 60, 0, -1):
            if st.session_state.get(stop_key, False): break
            mins, secs = divmod(remaining, 60)
            timer_placeholder.markdown(f"<h3 style='color:#ffc107;'>Rest: {mins:02d}:{secs:02d}</h3>", unsafe_allow_html=True)
            time.sleep(1)
            elapsed += 1
        if stop_placeholder.button("⏹ Stop Timer", key=f"stop_timer_{time.time()}"):
            st.session_state[stop_key] = True

def run_tabata(exercises, timer_placeholder, progress_placeholder, stop_placeholder):
    stop_key = "stop_timer"
    st.session_state[stop_key] = False
    rounds = 8
    for ex in exercises:
        timer_placeholder.markdown(f"<h3 style='color:#007bff;'>Starting {ex}</h3>", unsafe_allow_html=True)
        for r in range(1, rounds + 1):
            # Work 20s
            for remaining in range(20, 0, -1):
                if st.session_state.get(stop_key, False): break
                timer_placeholder.markdown(f"<h3 style='color:#28a745;'>Round {r} Work: {remaining}s</h3>", unsafe_allow_html=True)
                time.sleep(1)
            # Rest 10s
            for remaining in range(10, 0, -1):
                if st.session_state.get(stop_key, False): break
                timer_placeholder.markdown(f"<h3 style='color:#ffc107;'>Round {r} Rest: {remaining}s</h3>", unsafe_allow_html=True)
                time.sleep(1)
            if stop_placeholder.button("⏹ Stop Timer", key=f"stop_{ex}_{r}"):
                st.session_state[stop_key] = True
                break
        if st.session_state.get(stop_key, False):
            break
        # Short break between exercises
        timer_placeholder.markdown("<h3 style='color:#6c757d;'>Break before next exercise...</h3>", unsafe_allow_html=True)
        time.sleep(30)
    timer_placeholder.markdown("<h3 style='color:#28a745;'>✅ Tabata Complete!</h3>", unsafe_allow_html=True)

def run_emom(minutes, timer_placeholder, progress_placeholder, stop_placeholder, death_by=False):
    stop_key = "stop_timer"
    st.session_state[stop_key] = False
    for m in range(1, minutes + 1):
        if st.session_state.get(stop_key, False): break
        reps_info = f"Perform {m} reps" if death_by else "Perform assigned reps"
        timer_placeholder.markdown(f"<h3 style='color:#28a745;'>Minute {m}: {reps_info}</h3>", unsafe_allow_html=True)
        for remaining in range(60, 0, -1):
            if st.session_state.get(stop_key, False): break
            mins, secs = divmod(remaining, 60)
            progress_placeholder.progress((60 - remaining) / 60)
            time.sleep(1)
        if stop_placeholder.button("⏹ Stop Timer", key=f"stop_timer_{time.time()}"):
            st.session_state[stop_key] = True
            break
    timer_placeholder.markdown("<h3 style='color:#28a745;'>✅ EMOM Complete!</h3>", unsafe_allow_html=True)
