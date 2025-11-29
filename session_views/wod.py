
import streamlit as st
import re
from supabase import create_client
from datetime import datetime
from utils.timer import run_rest_timer

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

    # --- Global Timer Logic ---
    progress_placeholder = st.empty()
    current_placeholder = st.empty()
    next_placeholder = st.empty()

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

    if st.session_state.wod_running and not st.session_state.wod_paused:
        total_seconds = (duration_minutes * 60) if duration_minutes else 900
        elapsed = 0
        for i, ex in enumerate(exercises):
            next_ex = exercises[i+1] if i+1 < len(exercises) else None
            progress_placeholder.progress(elapsed / total_seconds)
            progress_placeholder.markdown(f"**Elapsed:** {elapsed//60} min")
            current_placeholder.empty()
            next_placeholder.empty()
            current_placeholder.subheader(f"Current: {ex}")
            next_placeholder.info(f"Next: {next_ex if next_ex else 'None'}")

            if wod_type == "AMRAP" and duration_minutes:
                run_rest_timer(duration_minutes * 60, label="AMRAP", next_item=next_ex, skip_key=f"skip_amrap")
                elapsed += duration_minutes * 60
                break
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

            progress_placeholder.progress(min(elapsed / total_seconds, 1.0))

    # --- Result Recording Section ---
    st.subheader("Enter Your WOD Result")
    previous_result = supabase.table('wod_results').select('result_details', 'rating').eq('session_id', session['session_id']).eq('user_id', st.session_state.get('user_id', 1)).execute().data
    if previous_result:
        prev = previous_result[0]
        st.info(f"Previously submitted result: {prev['result_details']} (Rating: {prev['rating']}/100)")

    performance_targets = session_data.get("performance_targets", {})
    user_result = {}
    if wod_type == "AMRAP":
        user_result["rounds"] = st.number_input("Rounds Completed", min_value=0, step=1)
    elif wod_type == "For Time":
        user_result["time_min"] = st.number_input("Time Taken (minutes)", min_value=0.0, step=0.1)
    elif wod_type == "Interval":
        user_result["intervals_completed"] = st.number_input("Intervals Completed", min_value=0, step=1)
    elif wod_type == "Tabata":
        user_result["avg_reps_per_round"] = st.number_input("Average Reps per Round", min_value=0, step=1)
    elif wod_type in ["Death by", "EMOM", "Alternating EMOM"]:
        user_result["rounds_completed"] = st.number_input("Rounds Completed", min_value=0, step=1)
    else:
        user_result["score"] = st.number_input("Score", min_value=0, step=1)

    if st.button("Submit Result"):
        rating = calculate_rating(wod_type, user_result, performance_targets)
        existing_result = supabase.table('wod_results').select('id').eq('session_id', session['session_id']).eq('user_id', st.session_state.get('user_id', 1)).execute().data
        if existing_result:
            supabase.table('wod_results').update({
                'result_details': user_result,
                'rating': rating,
                'timestamp': datetime.utcnow().isoformat()
            }).eq('id', existing_result[0]['id']).execute()
            st.success(f'Result updated! Your rating: {rating}/100')
        else:
            supabase.table('wod_results').insert({
                'session_id': session['session_id'],
                'user_id': st.session_state.get('user_id', 1),
                'result_details': user_result,
                'rating': rating,
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
            st.success(f'Result saved! Your rating: {rating}/100')
        supabase.table('plan_sessions').update({'completed': True}).eq('id', session['session_id']).execute()

    # Display historical performance
    results = supabase.table("wod_results").select("rating, timestamp").eq("user_id", st.session_state.get("user_id", 1)).order("timestamp", desc=True).execute().data
    if results:
        st.subheader("Performance Over Time")
        st.line_chart([r["rating"] for r in results])



        supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success("WOD completed!")
        st.session_state.selected_session = None
        st.rerun()
