
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
    st.title("🏆 Benchmark WOD")
    st.markdown(f"**Week:** {session['week']}  \n **Day:** {session['day']}")



    # Fetch session details first
    session_data = supabase.table("plan_sessions").select("*").eq("id", session["session_id"]).single().execute().data
    details_text = session_data.get("details", "")
    
    # Extract benchmark WOD ID from details (assuming it's numeric)
    import re
    match_id = re.search(r"\b\d+\b", details_text)
    if not match_id:
        st.error("No benchmark WOD ID found in session details.")
        return
    
    benchmark_id = int(match_id.group(0))
    
    # Fetch benchmark WOD details
    wod_data = supabase.table("benchmark_wods").select("*").eq("id", benchmark_id).single().execute().data



    workout_name = wod_data.get("name", "Unnamed WOD")
    workout_type = wod_data.get("type", "Unknown")
    description = wod_data.get("description","Who knows ??")
    estimated_time = wod_data.get("estimated_time", "N/A")
    beginner = wod_data.get("beginner", "")
    intermediate = wod_data.get("intermediate", "")
    advanced = wod_data.get("advanced", "")
    elite = wod_data.get("elite", "")
    wodwell_url = wod_data.get("wodwell_url", "")

    # Display WOD details
    st.subheader(workout_name)
    st.write(f"**Type:** {workout_type}")
    st.write(f"**Description:** {description}")
    st.write(f"**Estimated Time:** {estimated_time}")
    st.write("**Target Times:**")
    st.write(f"- Beginner: {beginner}")
    st.write(f"- Intermediate: {intermediate}")
    st.write(f"- Advanced: {advanced}")
    st.write(f"- Elite: {elite}")
    if wodwell_url:
        st.markdown(f"[View on WODwell]({wodwell_url})")

    # Timer placeholders
    timer_placeholder = st.empty()
    progress_placeholder = st.empty()
    stop_placeholder = st.empty()

    # Detect duration for AMRAP or For Time
    duration_minutes = None
    match_duration = re.search(r"(\d+)\s*min", estimated_time.lower())
    if match_duration:
        duration_minutes = int(match_duration.group(1))

    # Timer logic
    if st.button("▶ Start Timer", key="start_timer"):
        if workout_type == "AMRAP" and duration_minutes:
            run_countdown(duration_minutes * 60, timer_placeholder, progress_placeholder, stop_placeholder)
        elif workout_type == "For Time":
            run_stopwatch(timer_placeholder, progress_placeholder, stop_placeholder)
        else:
            st.warning("No timer logic available for this workout type.")

    # Result submission
    st.subheader("Enter Your Result")
    user_result = {}
    if workout_type == "AMRAP":
        user_result["rounds"] = st.number_input("Rounds Completed", min_value=0, step=1)
    elif workout_type == "For Time":
        user_result["time_min"] = st.number_input("Time Taken (minutes)", min_value=0.0, step=0.1)
    else:
        user_result["score"] = st.number_input("Score", min_value=0, step=1)

    if st.button("Submit Result", key="submit_result_btn"):
        rating = calculate_rating(workout_type, user_result, intermediate)
        supabase.table("benchmark_results").insert({
            "benchmark_wod_id": wod_data["id"],
            "session_id": session["session_id"],
            "user_id": st.session_state.get("user_id", 1),
            "result_details": user_result,
            "rating": rating,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        supabase.table("plan_sessions").update({"completed": True}).eq("id", session["session_id"]).execute()
        st.success(f"Result saved! Your rating: {rating}/100")
        st.session_state.selected_session = None
        st.rerun()

    # Display previous benchmark results
    results = supabase.table("benchmark_results").select("result_details, rating, timestamp").eq("benchmark_wod_id", wod_data["id"]).eq("user_id", st.session_state.get("user_id", 1)).order("timestamp", desc=True).execute().data
    if results:
        st.subheader("Previous Results")
        for r in results:
            st.write(f"{r['timestamp']}: {r['result_details']} (Rating: {r['rating']}/100)")

    if st.button("⬅ Back to Dashboard", key='back_to_dashboard_btn'):
        st.session_state.selected_session = None
        st.rerun()

# --- Rating Calculation ---
def parse_time(text):
    nums = [int(n) for n in re.findall(r"\d+", text)]
    return sum(nums)/len(nums) if nums else 15

def parse_rounds(text):
    nums = [int(n) for n in re.findall(r"\d+", text)]
    return sum(nums)/len(nums) if nums else 5

def calculate_rating(workout_type, user_result, intermediate_target):
    expected = 0
    ratio = 0
    if workout_type == 'AMRAP':
        expected = parse_rounds(intermediate_target)
        ratio = user_result.get('rounds', 0) / expected if expected else 0
    elif workout_type == 'For Time':
        expected = parse_time(intermediate_target)
        ratio = expected / user_result.get('time_min', 1) if user_result.get('time_min') else 0
    else:
        expected = parse_rounds(intermediate_target)
        ratio = user_result.get('score', 0) / expected if expected else 0
    return min(int(ratio * 100), 100)

# --- Timer Functions ---
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
