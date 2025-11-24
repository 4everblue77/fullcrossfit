
import streamlit as st
import time
import re
from supabase import create_client
from datetime import datetime

# Supabase setup
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def render(session):
    # Fetch session details from plan_sessions using session_id
    session_data = supabase.table("plan_sessions").select("*").eq("id", session["session_id"]).single().execute().data
    if not session_data:
        st.error("Session details not found.")
        return

    
    # Check for previously entered result
    previous_result = supabase.table('wod_results') \
        .select('result_details', 'rating') \
        .eq('session_id', session['session_id']) \
        .eq('user_id', st.session_state.get('user_id', 1)) \
        .execute().data


    details = session_data.get('details', 'No details provided')
    wod_type = None
    for t in ["AMRAP", "Chipper", "Interval", "Tabata", "For Time", "Ladder", "Death by", "EMOM", "Alternating EMOM"]:
        if t.lower() in details.lower():
            wod_type = t
            break
    if not wod_type:
        wod_type = "WOD"

    exercises = []
    for line in details.split("\n"):
        if line.strip().startswith("-"):
            exercises.append(line.strip("- "))

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

    # Timer logic
    if st.button("▶ Start Timer", key="start_timer"):
        if wod_type == "AMRAP" and duration_minutes:
            run_countdown(duration_minutes * 60, timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type in ["For Time", "Chipper", "Ladder"]:
            run_stopwatch(timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "Interval" and work_minutes and rest_minutes:
            run_interval(work_minutes, rest_minutes, duration_minutes, timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "Tabata":
            run_tabata(exercises, timer_placeholder, progress_placeholder, stop_placeholder)
        elif wod_type == "Death by":
            run_emom(duration_minutes or 15, timer_placeholder, progress_placeholder, stop_placeholder, death_by=True)
        elif wod_type in ["EMOM", "Alternating EMOM"]:
            run_emom(duration_minutes or 15, timer_placeholder, progress_placeholder, stop_placeholder)
        else:
            st.warning("No timer logic available for this WOD type.")

    # --- NEW: Performance Rating Section ---
    st.subheader("Enter Your WOD Result")

    
    # Display previous result if exists
    if previous_result:
        prev = previous_result[0]
        st.info(f"Previously submitted result: {prev['result_details']} (Rating: {prev['rating']}/100)")

    performance_targets = session_data.get("performance_targets", {})
    user_result = {}

    if wod_type == "AMRAP":
        user_result["rounds"] = st.number_input("Rounds Completed", min_value=0, step=1)
    elif wod_type == "For Time":
        user_result["time_min"] = st.number_input("Time Taken (minutes)", min_value=0.0, step=0.1)
    else:
        user_result["score"] = st.number_input("Score", min_value=0, step=1)

    # Handle Submit Result button
    if st.button("Submit Result", key="submit_result_btn"):
        st.session_state['pending_result'] = {
            'rating': calculate_rating(wod_type, user_result, performance_targets),
            'user_result': user_result
        }
        existing_result = supabase.table('wod_results').select('id').eq('session_id', session['session_id']).eq('user_id', st.session_state.get('user_id', 1)).execute().data
        st.session_state['existing_result'] = existing_result
        st.rerun()
    
    # Handle overwrite confirmation or insert
    if 'pending_result' in st.session_state:
        rating = st.session_state['pending_result']['rating']
        user_result = st.session_state['pending_result']['user_result']
        existing_result = st.session_state.get('existing_result', [])
        if existing_result:
            st.warning('A previous result exists for this session.')
            col1, col2 = st.columns(2)
            with col1:
                overwrite = st.button('Yes, Overwrite', key='overwrite_btn')
            with col2:
                cancel = st.button('Cancel', key='cancel_btn')
            if cancel:
                st.warning('Submission cancelled.')
                st.session_state.pop('pending_result')
                st.session_state.pop('existing_result')
                st.stop()
            if overwrite:
                supabase.table('wod_results').update({
                    'result_details': user_result,
                    'rating': rating,
                    'timestamp': datetime.utcnow().isoformat()
                }).eq('id', existing_result[0]['id']).execute()
                supabase.table('plan_sessions').update({'completed': True}).eq('id', session['session_id']).execute()
                st.success(f'Result updated! Your rating: {rating}/100')
                st.session_state.pop('pending_result')
                st.session_state.pop('existing_result')
                st.rerun()
        else:
            supabase.table('wod_results').insert({
                'session_id': session['session_id'],
                'user_id': st.session_state.get('user_id', 1),
                'result_details': user_result,
                'rating': rating,
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
            supabase.table('plan_sessions').update({'completed': True}).eq('id', session['session_id']).execute()
            st.success(f'Result saved! Your rating: {rating}/100')
            st.session_state.pop('pending_result')
            st.rerun()
            # Display historical performance
            results = supabase.table("wod_results").select("rating, timestamp").eq("user_id", st.session_state.get("user_id", 1)).order("timestamp", desc=True).execute().data
            if results:
                st.subheader("Performance Over Time")
                st.line_chart([r["rating"] for r in results])




        # Display historical performance
        results = supabase.table("wod_results").select("rating, timestamp").eq("user_id", st.session_state.get("user_id", 1)).order("timestamp", desc=True).execute().data
        if results:
            st.subheader("Performance Over Time")
            st.line_chart([r["rating"] for r in results])

    if st.button("⬅ Back to Dashboard", key='back_to_dashboard_btn'):
        st.session_state.selected_session = None
        st.rerun()

# --- Helper Functions ---
def parse_rounds(text):
    nums = [int(n) for n in re.findall(r"\d+", text)]
    return sum(nums)/len(nums) if nums else 5

def parse_time(text):
    nums = [int(n) for n in re.findall(r"\d+", text)]
    return sum(nums)/len(nums) if nums else 15

def calculate_rating(wod_type, user_result, targets):
    expected = 0
    ratio = 0
    if wod_type == 'AMRAP':
        expected = parse_rounds(targets.get('Intermediate', '5-6 rounds'))
        ratio = user_result.get('rounds', 0) / expected if expected else 0
    elif wod_type in ['For Time', 'Chipper', 'Ladder']:
        expected = parse_time(targets.get('Intermediate', '15-20 min'))
        ratio = expected / user_result.get('time_min', 1) if user_result.get('time_min') else 0
    elif wod_type == 'Interval':
        expected = parse_rounds(targets.get('Intermediate', '6 intervals'))
        ratio = user_result.get('intervals_completed', 0) / expected if expected else 0
    elif wod_type == 'Tabata':
        expected = parse_rounds(targets.get('Intermediate', '10 reps'))
        ratio = user_result.get('avg_reps_per_round', 0) / expected if expected else 0
    elif wod_type in ['Death by', 'EMOM', 'Alternating EMOM']:
        expected = parse_rounds(targets.get('Intermediate', '10 rounds'))
        ratio = user_result.get('rounds_completed', 0) / expected if expected else 0
    else:
        expected = parse_rounds(targets.get('Intermediate', '10 reps'))
        ratio = user_result.get('score', 0) / expected if expected else 0
    return min(int(ratio * 100), 100)

# --- Existing Timer Functions ---
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
        for remaining in range(work * 60, 0, -1):
            if st.session_state.get(stop_key, False): break
            mins, secs = divmod(remaining, 60)
            timer_placeholder.markdown(f"<h3 style='color:#28a745;'>Work: {mins:02d}:{secs:02d}</h3>", unsafe_allow_html=True)
            time.sleep(1)
            elapsed += 1
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
            for remaining in range(20, 0, -1):
                if st.session_state.get(stop_key, False): break
                timer_placeholder.markdown(f"<h3 style='color:#28a745;'>Round {r} Work: {remaining}s</h3>", unsafe_allow_html=True)
                time.sleep(1)
            for remaining in range(10, 0, -1):
                if st.session_state.get(stop_key, False): break
                timer_placeholder.markdown(f"<h3 style='color:#ffc107;'>Round {r} Rest: {remaining}s</h3>", unsafe_allow_html=True)
                time.sleep(1)
            if stop_placeholder.button(f"⏹ Stop Timer", key=f"stop_{ex}_{r}"):
                st.session_state[stop_key] = True
                break
        if st.session_state.get(stop_key, False): break
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
            progress_placeholder.progress((60 - remaining) / 60)
            time.sleep(1)
        if stop_placeholder.button("⏹ Stop Timer", key=f"stop_timer_{time.time()}"):
            st.session_state[stop_key] = True
            break
    timer_placeholder.markdown("<h3 style='color:#28a745;'>✅ EMOM Complete!</h3>", unsafe_allow_html=True)
