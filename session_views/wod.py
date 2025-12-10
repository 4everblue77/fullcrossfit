
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





    # --- Global Timer Logic ---

    
    # Helpers
    def parse_duration_minutes(text: str) -> int | None:
        """
        Find the first 'X min', 'X mins', or 'X minutes' (case-insensitive).
        Returns int minutes or None.
        """
        m = re.findall(r"(\d+)\s*(?:minutes?|mins?|min)\b", text, flags=re.I)
        return int(m[0]) if m else None
    
    def parse_work_rest(text: str) -> tuple[int | None, int | None]:
        """
        Parse explicit 'work X min' and 'rest Y min' from text; returns (work, rest) minutes.
        """
        w = re.search(r"work\s*(\d+)\s*(?:minutes?|mins?|min)\b", text, flags=re.I)
        r = re.search(r"rest\s*(\d+)\s*(?:minutes?|mins?|min)\b", text, flags=re.I)
        return (int(w.group(1)) if w else None, int(r.group(1)) if r else None)
    
    def format_mmss(seconds: float) -> str:
        s = int(max(seconds, 0))
        return f"{s//60:02d}:{s%60:02d}"
    
    # Determine session cap and any explicit work/rest
    duration_minutes = parse_duration_minutes(details)  # e.g., "For Time for 20 minutes"
    work_minutes, rest_minutes = parse_work_rest(details)
    
    # UI placeholders
    progress_ph = st.empty()
    elapsed_ph = st.empty()
    remaining_ph = st.empty()
    current_ph = st.empty()
    next_ph = st.empty()
    counter_ph = st.empty()
    
    # Controls
    c1, c2, c3, c4, c5 = st.columns(5)
    if "wod_running" not in st.session_state:
        st.session_state.wod_running = False
    if "wod_paused" not in st.session_state:
        st.session_state.wod_paused = False
    if "wod_timer_start" not in st.session_state:
        st.session_state.wod_timer_start = None
    if "wod_elapsed" not in st.session_state:
        st.session_state.wod_elapsed = 0.0
    # for interval styles
    if "wod_interval_count" not in st.session_state:
        st.session_state.wod_interval_count = 0
    
    start_clicked = c1.button("▶ Start WOD Session")
    pause_clicked = c2.button("⏸ Pause")
    resume_clicked = c3.button("⏯ Resume")
    stop_clicked = c4.button("⏹ Stop")
    back_clicked = c5.button("⬅ Back to Dashboard")
    
    DEFAULT_CAP_MIN = 20 if wod_type in ["For Time", "AMRAP"] else 15
    total_seconds_cap = int((duration_minutes or DEFAULT_CAP_MIN) * 60)
    
    # Button handlers
    now_ts = time.time()
    if start_clicked and not st.session_state.wod_running:
        st.session_state.wod_running = True
        st.session_state.wod_paused = False
        # start from current elapsed to support restart after pause
        st.session_state.wod_timer_start = now_ts - st.session_state.wod_elapsed
    
    if pause_clicked and st.session_state.wod_running:
        st.session_state.wod_paused = True
        st.session_state.wod_running = False
        st.session_state.wod_elapsed = now_ts - st.session_state.wod_timer_start
    
    if resume_clicked and not st.session_state.wod_running:
        st.session_state.wod_running = True
        st.session_state.wod_paused = False
        st.session_state.wod_timer_start = now_ts - st.session_state.wod_elapsed
    
    if stop_clicked:
        # freeze elapsed and set auto-fill values for result inputs
        st.session_state.wod_running = False
        st.session_state.wod_paused = False
        # ensure elapsed is computed up to now
        if st.session_state.wod_timer_start is not None:
            st.session_state.wod_elapsed = now_ts - st.session_state.wod_timer_start
        st.session_state.wod_autofill_min = int(st.session_state.wod_elapsed // 60)
        st.session_state.wod_autofill_sec = int(st.session_state.wod_elapsed % 60)
        st.info(f"Stopped at {format_mmss(st.session_state.wod_elapsed)}")
    
    if back_clicked:
        st.session_state.wod_running = False
        st.session_state.wod_paused = False
        st.session_state.selected_session = None
        st.rerun()
    
    # Live timer update
    if st.session_state.wod_running and not st.session_state.wod_paused:
        st.session_state.wod_elapsed = time.time() - st.session_state.wod_timer_start
    
    elapsed = st.session_state.wod_elapsed
    remaining = max(total_seconds_cap - elapsed, 0)
    
    # Display progress
    progress_ph.progress(min(elapsed / total_seconds_cap, 1.0))
    elapsed_ph.markdown(f"**Elapsed:** {format_mmss(elapsed)}")
    remaining_ph.markdown(f"**Remaining:** {format_mmss(remaining)} (cap)")
    
    # Decide timer style
    continuous_styles = ["For Time", "AMRAP", "Chipper", "Ladder"]
    interval_styles = ["Interval", "EMOM", "Alternating EMOM", "Tabata"]
    
    if wod_type in continuous_styles:
        # Show exercises but DO NOT tie time slices to them
        current_ph.subheader("Exercises (follow as prescribed)")
        for i, ex in enumerate(exercises):
            nxt = exercises[i+1] if i+1 < len(exercises) else None
            st.markdown(f"- {ex}")
            if nxt:
                next_ph.info(f"Next: {nxt}")
    
        # Cap reached ⇒ stop automatically and set auto-fill for result inputs
        if elapsed >= total_seconds_cap and st.session_state.wod_running:
            st.session_state.wod_running = False
            st.session_state.wod_paused = False
            st.session_state.wod_autofill_min = int(elapsed // 60)
            st.session_state.wod_autofill_sec = int(elapsed % 60)
            st.success(f"Time cap reached at {format_mmss(elapsed)}")
    
    elif wod_type in interval_styles:
        # Structured timer logic using your run_rest_timer
        # Determine defaults per style if not explicitly given
        wm = work_minutes
        rm = rest_minutes
    
        if wod_type == "EMOM":
            # 1-minute work blocks; rest is whatever remains in the minute
            # If work/rest explicitly given, honor them; else default to 1/0
            wm = wm or 1
            rm = rm or 0
        elif wod_type == "Alternating EMOM":
            # Treat as EMOM with alternating exercise focus (UI only)
            wm = wm or 1
            rm = rm or 0
        elif wod_type == "Tabata":
            # Typical Tabata 20s on / 10s off unless specified
            # run_rest_timer expects seconds, so we will convert below
            wm = wm or 0  # minutes
            rm = rm or 0  # minutes
            # We'll run using seconds directly (20s/10s) ignoring minutes defaults
        else:  # "Interval"
            wm = wm or 2  # sensible default if not provided
            rm = rm or 1
    
        # Interval engine: run work/rest blocks until cap
        # NOTE: run_rest_timer() handles the sleep/skip and UI re-render per block.
        elapsed_local = elapsed
        interval_count = st.session_state.wod_interval_count
    
        # Display status line
        counter_ph.markdown(
            f"**Intervals Completed:** {interval_count}  \n"
            f"**Remaining Time:** {format_mmss(remaining)}"
        )
    
        if st.session_state.wod_running and not st.session_state.wod_paused and remaining > 0:
            if wod_type == "Tabata":
                # Work phase: 20s
                current_ph.subheader(f"Tabata Work #{interval_count + 1}: Go!")
                next_ph.info("Next: Rest (10s)")
                run_rest_timer(20, label="Work (20s)", next_item="Rest (10s)", skip_key=f"tabata_work_{interval_count}")
                # Rest 10s
                current_ph.subheader("Tabata Rest")
                next_ph.info("Next: Work (20s)")
                run_rest_timer(10, label="Rest (10s)", next_item="Work (20s)", skip_key=f"tabata_rest_{interval_count}")
                interval_count += 1
    
            else:
                # Work phase (minutes)
                current_ph.subheader(f"Work Interval #{interval_count + 1}")
                next_ph.info("Next: Rest")
                run_rest_timer(int(wm * 60), label=f"Work ({wm} min)", next_item="Rest", skip_key=f"work_{interval_count}")
                elapsed_local += int(wm * 60)
                # Rest phase (minutes) if any remaining cap
                if elapsed_local < total_seconds_cap and rm > 0:
                    current_ph.subheader("Rest Interval")
                    next_ph.info("Next: Work")
                    run_rest_timer(int(rm * 60), label=f"Rest ({rm} min)", next_item="Work", skip_key=f"rest_{interval_count}")
                    elapsed_local += int(rm * 60)
                interval_count += 1
    
            # Update session state after completing an interval cycle
            st.session_state.wod_interval_count = interval_count
            # Recompute elapsed from clock to keep consistent
            st.session_state.wod_elapsed = time.time() - st.session_state.wod_timer_start
    
        # Auto-stop at cap and set auto-fill
        if elapsed >= total_seconds_cap and st.session_state.wod_running:
            st.session_state.wod_running = False
            st.session_state.wod_paused = False
            st.session_state.wod_autofill_min = int(elapsed // 60)
            st.session_state.wod_autofill_sec = int(elapsed % 60)
            st.success(f"Time cap reached at {format_mmss(elapsed)}")
    
    else:
        # Fallback: treat as continuous
        current_ph.subheader("Exercises (follow as prescribed)")
        for i, ex in enumerate(exercises):
            st.markdown(f"- {ex}")
        if elapsed >= total_seconds_cap and st.session_state.wod_running:
            st.session_state.wod_running = False
            st.session_state.wod_paused = False
            st.session_state.wod_autofill_min = int(elapsed // 60)
            st.session_state.wod_autofill_sec = int(elapsed % 60)
            st.success(f"Time cap reached at {format_mmss(elapsed)}")


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
