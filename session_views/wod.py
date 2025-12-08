
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

def calculate_rating(wod_type, user_result, targets, level="Intermediate"):
    expected = 0
    ratio = 0

    
    # Pick the level target, fall back to Intermediate, then to a sensible default
    def level_target(default_text):
        return targets.get(level) or targets.get("Intermediate") or default_text

    
    if wod_type == 'AMRAP':
        expected = parse_rounds(level_target('5-6 rounds'))
        ratio = (user_result.get('rounds', 0) + user_result.get('reps', 0) / 10) / expected if expected else 0

    elif wod_type in ['For Time', 'Chipper', 'Ladder']:
        expected = parse_time(level_target('15-20 min'))
        # Faster time ⇒ higher rating (expected / actual)
        tmin = user_result.get('time_min')
        ratio = (expected / tmin) if tmin and tmin > 0 else  0

    elif wod_type == 'Interval':
        expected = parse_rounds(level_target('6 intervals'))
        ratio = (user_result.get('rounds', 0) + user_result.get('reps', 0) / 10) / expected if expected else 0

    elif wod_type == 'Tabata':
        expected = parse_rounds(level_target('10 reps'))
        ratio = user_result.get('avg_reps_per_round', 0) / expected if expected else 0

    elif wod_type in ['Death by', 'EMOM', 'Alternating EMOM']:
        expected = parse_rounds(level_target('10 rounds'))
        ratio = (user_result.get('rounds_completed', 0) + user_result.get('reps', 0) / 10) / expected if expected else 0


    else:
        expected = parse_rounds(level_target('10 reps'))
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
    counter_placeholder = st.empty()

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

        if wod_type == "Interval" and work_minutes and rest_minutes:

            interval_count = 0
            while elapsed < total_seconds:
                remaining_time = max(total_seconds - elapsed, 0)
                counter_placeholder.markdown(
                    f"**Intervals Completed:** {interval_count}\n"
                    f"**Remaining Time:** {remaining_time//60} min {remaining_time%60}s"
                )
                # Work phase
                current_placeholder.subheader(f"Work Interval {interval_count+1}: Complete as many rounds/reps as possible")
                next_placeholder.info("Next: Rest")
                run_rest_timer(work_minutes * 60, label="Work", next_item="Rest", skip_key=f"skip_work_{interval_count}")
                elapsed += work_minutes * 60
    
                # Rest phase
                if elapsed < total_seconds:
                    current_placeholder.subheader("Rest Interval")
                    next_placeholder.info("Next: Work")
                    run_rest_timer(rest_minutes * 60, label="Rest", next_item="Work", skip_key=f"skip_rest_{interval_count}")
                    elapsed += rest_minutes * 60
                interval_count += 1
                progress_placeholder.progress(min(elapsed / total_seconds, 1.0))

        else:
            for i, ex in enumerate(exercises):
                next_ex = exercises[i+1] if i+1 < len(exercises) else None
                progress_placeholder.progress(elapsed / total_seconds)
                progress_placeholder.markdown(f"**Elapsed:** {elapsed//60} min")
                current_placeholder.empty()
                next_placeholder.empty()
                current_placeholder.subheader(f"Current: {ex}")
                next_placeholder.info(f"Next: {next_ex if next_ex else 'None'}")

                run_rest_timer(60, label=ex, next_item=next_ex, skip_key=f"skip_generic_{i}")
                elapsed += 60
                progress_placeholder.progress(min(elapsed / total_seconds, 1.0))

    # --- Result Recording Section ---
    st.subheader("Enter Your WOD Result")

    previous_result = (
        supabase.table('wod_results')
        .select('result_details', 'rating', 'level')  # <-- include level if stored top-level
        .eq('session_id', session['session_id'])
        .eq('user_id', st.session_state.get('user_id', 1))
        .execute()
        .data
    )
    if previous_result:
        prev = previous_result[0]
        prev_level = prev.get('level') or prev['result_details'].get('    prev_level = prev.get('level') or prev['result_details'].get('level')  # fallback if you stored inside details earlier
        st.info(
            f"Previously submitted: {prev['result_details']} "
            f"(Level: {prev_level if prev_level else 'N/A'}, Rating: {prev['rating']}/100)"
    st.write("DEBUG previous_result:", previous_result)



    # NEW: Show performance targets and let user choose a level
    performance_targets = session_data.get("performance_targets", {})
    if performance_targets:
        st.markdown("**Performance Targets**")
        # Pretty print levels in a consistent order if available
        levels_order = ["Beginner", "Intermediate", "Advanced", "Elite"]
        for lvl in levels_order:
            if lvl in performance_targets:
                st.markdown(f"- **{lvl}**: {performance_targets[lvl]}")
        # Include any other keys not in the above order
        for k, v in performance_targets.items():
            if k not in levels_order:
                st.markdown(f"- **{k}**: {v}")
    else:
        st.info("No performance targets available for this session.")
    
    # NEW: Level selector used for rating
    level = st.selectbox("Select target level for rating", 
                         options=[opt for opt in ["Beginner", "Intermediate", "Advanced", "Elite"] if opt in performance_targets] 
                         or ["Intermediate"],
                         index=0)
    
    user_result = {}


    # Inputs differ by wod_type
    if wod_type == "AMRAP":
        user_result["rounds"] = st.number_input("Rounds Completed", min_value=0, step=1)
        user_result["reps"] = st.number_input("Additional Reps", min_value=0, step=1)
    
    elif wod_type in ["For Time", "Chipper", "Ladder"]:
        # NEW: minutes + seconds
        col_m, col_s = st.columns(2)
        with col_m:
            time_min_only = st.number_input("Minutes", min_value=0, step=1)
        with col_s:
            time_sec_only = st.number_input("Seconds", min_value=0, max_value=59, step=1)
        user_result["time_min"] = float(time_min_only) + float(time_sec_only) / 60.0
        # Store raw mm:ss too for clarity
        user_result["time_mmss"] = f"{int(time_min_only):02d}:{int(time_sec_only):02d}"
    
    elif wod_type == "Interval":
        user_result["rounds"] = st.number_input("Total Rounds Completed", min_value=0, step=1)
        user_result["reps"] = st.number_input("Additional Reps", min_value=0, step=1)
    
    elif wod_type == "Tabata":
        user_result["avg_reps_per_round"] = st.number_input("Average Reps per Round", min_value=0, step=1)
    
    elif wod_type in ["Death by", "EMOM", "Alternating EMOM"]:
        user_result["rounds_completed"] = st.number_input("Rounds Completed", min_value=0, step=1)
    
    else:
        user_result["score"] = st.number_input("Score", min_value=0, step=1)


    notes = st.text_area("Notes (optional)")



    if st.button("Submit Result"):
        rating = calculate_rating(wod_type, user_result, performance_targets, level    rating = calculate_rating(wod_type, user_result, performance_targets, level=level)
    
        existing_result = (
            supabase.table('wod_results')
            .select('id')
            .eq('session_id', session['session_id'])
            .eq('user_id', st.session_state.get('user_id', 1))
            .execute()
            .data
        )
    
        payload = {
            'result_details': user_result,     # keep detailed inputs here
            'level': level,                    # <-- NEW: top-level column for easy querying
            'notes': notes,
            'rating': rating,
            'timestamp': datetime.utcnow().isoformat(),
        }
    
        if existing_result:
            supabase.table('wod_results').update(payload).eq('id', existing_result[0]['id']).execute()
            st.success(f"Result updated! Your rating: {rating}/100")
        else:
            supabase.table('wod_results').insert({
                'session_id': session['session_id'],
                'user_id': st.session_state.get('user_id', 1),
                **payload
            }).execute()

        st.success("WOD completed!")
        st.session_state.selected_session = None
        st.rerun()
