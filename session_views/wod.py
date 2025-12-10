
import streamlit as st
import re
from supabase import create_client
from datetime import datetime
from utils.timer import run_rest_timer
import time

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


    # --- Global Timer Logic (uses run_rest_timer) ---

    
    def format_mmss(seconds):
        s = int(max(0, seconds))
        return f"{s//60:02d}:{s%60:02d}"
    
    # Robust duration parser: matches "20 min", "20 mins", "20 minutes"
    duration_minutes = None
    work_minutes = None
    rest_minutes = None
    
    match_duration = re.search(r"(\d+)\s*(?:minutes?|mins?|min)\b", details.lower())
    if match_duration:
        duration_minutes = int(match_duration.group(1))
    
    if "work" in details.lower() and "rest" in details.lower():
        work_match = re.search(r"work\s*(\d+)\s*(?:minutes?|mins?|min)\b", details.lower())
        rest_match = re.search(r"rest\s*(\d+)\s*(?:minutes?|mins?|min)\b", details.lower())
        if work_match:
            work_minutes = int(work_match.group(1))
        if rest_match:
            rest_minutes = int(rest_match.group(1))
    
    # Placeholders
    progress_ph = st.empty()
    elapsed_ph = st.empty()
    remaining_ph = st.empty()
    current_ph = st.empty()
    next_ph = st.empty()
    counter_ph = st.empty()
    
    # Controls and session state
    c1, c2, c3, c4, c5 = st.columns(5)
    continuous_styles = ["For Time", "AMRAP", "Chipper", "Ladder"]
    interval_styles = ["Interval", "EMOM", "Alternating EMOM", "Tabata"]
    
    DEFAULT_CAP_MIN = 20 if wod_type in ["For Time", "AMRAP"] else 15
    cap_seconds = int((duration_minutes or DEFAULT_CAP_MIN) * 60)
    if cap_seconds <= 0:
        cap_seconds = DEFAULT_CAP_MIN * 60
    
    # Unique skip key per session to control run_rest_timer externally
    skip_key = f"skip_wod_clock_{session['session_id']}"
    
    # Initialize state
    if "wod_clock_in_progress" not in st.session_state:
        st.session_state.wod_clock_in_progress = False
    if "wod_clock_paused" not in st.session_state:
        st.session_state.wod_clock_paused = False
    if "wod_clock_start_ts" not in st.session_state:
        st.session_state.wod_clock_start_ts = None
    if "wod_clock_remaining" not in st.session_state:
        st.session_state.wod_clock_remaining = cap_seconds
    if "wod_clock_last_action" not in st.session_state:
        st.session_state.wod_clock_last_action = None  # 'start' | 'pause' | 'resume' | 'stop' | None
    
    start_clicked = c1.button("▶ Start WOD Session")
    pause_clicked = c2.button("⏸ Pause")
    resume_clicked = c3.button("⏯ Resume")
    stop_clicked = c4.button("⏹ Stop")
    back_clicked = c5.button("⬅ Back to Dashboard")
    
    # Back action
    if back_clicked:
        st.session_state.wod_clock_in_progress = False
        st.session_state.wod_clock_paused = False
        st.session_state.wod_clock_start_ts = None
        st.session_state.wod_clock_remaining = cap_seconds
        st.session_state.wod_clock_last_action = None
        st.session_state[skip_key] = True  # ensure any timer loop exits
        st.session_state.selected_session = None
        st.rerun()
    
    # START
    if start_clicked and not st.session_state.wod_clock_in_progress:
        st.session_state.wod_clock_in_progress = True
        st.session_state.wod_clock_paused = False
        st.session_state.wod_clock_remaining = cap_seconds
        st.session_state.wod_clock_start_ts = time.time()
        st.session_state.wod_clock_last_action = "start"
        # Clear skip flag before launching timer
        st.session_state[skip_key] = False
    
    # PAUSE (implemented as stop-with-remaining)
    if pause_clicked and st.session_state.wod_clock_in_progress and not st.session_state.wod_clock_paused:
        st.session_state.wod_clock_last_action = "pause"
        # Signal the timer to exit at next tick
        st.session_state[skip_key] = True
    
    # RESUME
    if resume_clicked and st.session_state.wod_clock_paused and st.session_state.wod_clock_remaining > 0:
        st.session_state.wod_clock_in_progress = True
        st.session_state.wod_clock_paused = False
        st.session_state.wod_clock_start_ts = time.time()
        st.session_state.wod_clock_last_action = "resume"
        st.session_state[skip_key] = False  # clear skip before resuming
    
    # STOP (finalize and auto-fill)
    if stop_clicked and st.session_state.wod_clock_in_progress:
        st.session_state.wod_clock_last_action = "stop"
        st.session_state[skip_key] = True
    
    # ---- DISPLAY & TIMER ENGINE ----
    # Common info (progress bar based on remaining)
    elapsed_seconds = cap_seconds - st.session_state.wod_clock_remaining
    progress_ph.progress(min(elapsed_seconds / float(cap_seconds), 1.0))
    elapsed_ph.markdown(f"**Elapsed:** {format_mmss(elapsed_seconds)}")
    remaining_ph.markdown(f"**Remaining:** {format_mmss(st.session_state.wod_clock_remaining)} (cap)")
    
    if wod_type in continuous_styles:
        # Show exercises but do NOT slice time by exercise list
        current_ph.subheader("Exercises (follow as prescribed)")
        for i, ex in enumerate(exercises):
            nxt = exercises[i+1] if i+1 < len(exercises) else None
            st.markdown(f"- {ex}")
            if nxt:
                next_ph.info(f"Next: {nxt}")
    
        # If the clock is in progress, run the utility timer for the current remaining chunk
        if st.session_state.wod_clock_in_progress and not st.session_state.wod_clock_paused and st.session_state.wod_clock_remaining > 0:
            # Capture start for accurate elapsed on return
            start_ts = time.time()
            # Drive the utility timer; it will auto-update the UI each second
            run_rest_timer(
                st.session_state.wod_clock_remaining,
                label=f"{wod_type} Clock",
                next_item="End",
                skip_key=skip_key
            )
            # When the utility returns, compute how much time actually ran
            actual_run = int(time.time() - start_ts)
            # Clamp to remaining
            actual_run = max(0, min(actual_run, st.session_state.wod_clock_remaining))
            st.session_state.wod_clock_remaining -= actual_run
    
            # Decide what happened based on last action & remaining
            if st.session_state.wod_clock_last_action == "pause" and st.session_state.wod_clock_remaining > 0:
                # Mark paused; user can resume
                st.session_state.wod_clock_paused = True
                st.session_state.wod_clock_in_progress = False
                st.info(f"Paused at {format_mmss(cap_seconds - st.session_state.wod_clock_remaining)}")
                # Reset skip for next resume
                st.session_state[skip_key] = False
    
            elif st.session_state.wod_clock_last_action == "stop" or st.session_state.wod_clock_remaining <= 0:
                # Finalize result auto-fill
                final_elapsed = cap_seconds - st.session_state.wod_clock_remaining
                st.session_state.wod_autofill_min = int(final_elapsed // 60)
                st.session_state.wod_autofill_sec = int(final_elapsed % 60)
                st.session_state.wod_clock_in_progress = False
                st.session_state.wod_clock_paused = False
                st.session_state.wod_clock_last_action = None
                st.session_state[skip_key] = False
                if st.session_state.wod_clock_remaining <= 0:
                    st.success(f"Time cap reached at {format_mmss(final_elapsed)}")
                else:
                    st.info(f"Stopped at {format_mmss(final_elapsed)}")
    
    elif wod_type in interval_styles:
        # Structured Work/Rest using the utility timer
        wm = work_minutes
        rm = rest_minutes
    
        if wod_type == "EMOM":
            wm = wm or 1
            rm = rm or 0
        elif wod_type == "Alternating EMOM":
            wm = wm or 1
            rm = rm or 0
        elif wod_type == "Tabata":
            # Default Tabata: 20s work / 10s rest (seconds), unless minutes explicitly provided
            wm = wm or 0  # minutes placeholder; we'll use seconds if not provided
            rm = rm or 0
        else:  # "Interval"
            wm = wm or 2
            rm = rm or 1
    
        if st.session_state.wod_clock_in_progress and not st.session_state.wod_clock_paused and st.session_state.wod_clock_remaining > 0:
            # Display status
            counter_ph.markdown(
                f"**Remaining Time:** {format_mmss(st.session_state.wod_clock_remaining)}"
            )
    
            start_ts = time.time()
    
            if wod_type == "Tabata" and not (work_minutes or rest_minutes):
                # Work 20s
                current_ph.subheader("Tabata Work: Go!")
                next_ph.info("Next: Rest (10s)")
                run_rest_timer(20, label="Work (20s)", next_item="Rest (10s)", skip_key=skip_key)
                # Rest 10s
                current_ph.subheader("Tabata Rest")
                next_ph.info("Next: Work (20s)")
                run_rest_timer(10, label="Rest (10s)", next_item="Work (20s)", skip_key=skip_key)
    
            else:
                # Work phase (minutes)
                current_ph.subheader(f"Work Interval ({wm} min)")
                next_ph.info("Next: Rest")
                run_rest_timer(int(wm * 60), label=f"Work ({wm} min)", next_item="Rest", skip_key=skip_key)
                # Rest phase (minutes)
                if rm > 0 and st.session_state.get(skip_key) is not True:
                    current_ph.subheader(f"Rest Interval ({rm} min)")
                    next_ph.info("Next: Work")
                    run_rest_timer(int(rm * 60), label=f"Rest ({rm} min)", next_item="Work", skip_key=skip_key)
    
            # After work+rest (or skip), compute actual run time and update remaining
            actual_run = int(time.time() - start_ts)
            actual_run = max(0, min(actual_run, st.session_state.wod_clock_remaining))
            st.session_state.wod_clock_remaining -= actual_run
    
            # Handle controls
            if st.session_state.wod_clock_last_action == "pause" and st.session_state.wod_clock_remaining > 0:
                st.session_state.wod_clock_paused = True
                st.session_state.wod_clock_in_progress = False
                st.info(f"Paused at {format_mmss(cap_seconds - st.session_state.wod_clock_remaining)}")
                st.session_state[skip_key] = False
    
            elif st.session_state.wod_clock_last_action == "stop" or st.session_state.wod_clock_remaining <= 0:
                final_elapsed = cap_seconds - st.session_state.wod_clock_remaining
                st.session_state.wod_autofill_min = int(final_elapsed // 60)
                st.session_state.wod_autofill_sec = int(final_elapsed % 60)
                st.session_state.wod_clock_in_progress = False
                st.session_state.wod_clock_paused = False
                st.session_state.wod_clock_last_action = None
                st.session_state[skip_key] = False
                if st.session_state.wod_clock_remaining <= 0:
                    st.success(f"Time cap reached at {format_mmss(final_elapsed)}")
                else:
                    st.info(f"Stopped at {format_mmss(final_elapsed)}")
    
    else:
        # Fallback: treat as continuous
        current_ph.subheader("Exercises (follow as prescribed)")
        for ex in exercises:
            st.markdown(f"- {ex}")
        if st.session_state.wod_clock_in_progress and not st.session_state.wod_clock_paused and st.session_state.wod_clock_remaining > 0:
            start_ts = time.time()
            run_rest_timer(st.session_state.wod_clock_remaining, label="WOD Clock", next_item="End", skip_key=skip_key)
            actual_run = int(time.time() - start_ts)
            actual_run = max(0, min(actual_run, st.session_state.wod_clock_remaining))
            st.session_state.wod_clock_remaining -= actual_run
            final_elapsed = cap_seconds - st.session_state.wod_clock_remaining
            st.session_state.wod_autofill_min = int(final_elapsed // 60)
            st.session_state.wod_autofill_sec = int(final_elapsed % 60)
            st.session_state.wod_clock_in_progress = False
            st.session_state.wod_clock_paused = False
            st.session_state.wod_clock_last_action = None
            st.session_state[skip_key] = False      



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
        prev_level = prev.get('level') or prev['result_details'].get('level')  # fallback if you stored inside details earlier
        st.info(
            f"Previously submitted: {prev['result_details']} "
            f"(Level: {prev_level if prev_level else 'N/A'}, Rating: {prev['rating']}/100)")




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
        rating = calculate_rating(wod_type, user_result, performance_targets, level=level)
    
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

        supabase.table('plan_sessions').update({'completed': True}).eq('id',session_id).execute()

        st.success("WOD completed!")
        st.session_state.wod_running = False
        st.session_state.wod_paused = False
        st.session_state.selected_session = None
        st.rerun()
