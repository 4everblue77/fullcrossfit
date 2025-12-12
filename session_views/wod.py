
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
    return sum(nums) / len(nums) if nums else 5


def parse_time(text):
    nums = [int(n) for n in re.findall(r"\d+", text)]
    return sum(nums) / len(nums) if nums else 15


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
        ratio = (expected / tmin) if tmin and tmin > 0 else 0

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

    # --- Validate input early
    sid = session.get("session_id")
    if sid is None:
        st.error("No session_id provided to the WOD view.")
        return

    # --- Safer fetch: avoid .single() so 0 rows doesn't raise
    try:
        resp = (
            supabase.table("plan_sessions")
            .select("*")
            .eq("id", sid)
            .limit(1)          # fetch at most 1 row
            .execute()
        )
    except Exception as e:
        st.error(f"Failed to fetch session details (session_id={sid}).")
        st.caption(f"Debug: {e}")
               return

    rows = resp.data or []
    if not rows:
        st.error(f"Session details not found for session_id={sid}.")
        return

    session_data = rows[0]
    details = session_data.get('details', 'No details provided')


    # Detect WOD type from details
    wod_type = None
    for t in ["AMRAP", "Chipper", "Interval", "Tabata", "For Time", "Ladder", "Death by", "EMOM", "Alternating EMOM"]:
        if t.lower() in details.lower():
            wod_type = t
            break
    if not wod_type:
        wod_type = "WOD"

    # Extract movement lines (prefixed with "- ")
    exercises = [line.strip("- ").strip() for line in details.split("\n") if line.strip().startswith("-")]
    num_movements = len(exercises)

    st.title(f"🔥 {wod_type} Session")
    st.markdown(f"**Week:** {session['week']}\n**Day:** {session['day']}")
    st.write(f"**Details:** {details}")

    # ---------- Helpers ----------
    def format_mmss(seconds):
        s = int(max(0, seconds))
        return f"{s//60:02d}:{s%60:02d}"

    def parse_duration_minutes(text: str) -> int:
        """
        Matches '20 min', '20 mins', '20 minutes' (case-insensitive).
        Returns int minutes or 0.
        """
        m_dur = re.search(r"(\d+)\s*(?:minutes?|mins?|min)\b", text, flags=re.I)
        return int(m_dur.group(1)) if m_dur else 0

    def derive_tabata_cap_seconds(text: str, movements: int) -> int:
        """
        Parse 'X rounds of Ys work / Zs rest per movement' and compute total cap:
        cap = rounds * (work + rest) * movements
        Defaults: rounds=8, work=20s, rest=10s
        """
        rounds = 8
        work_s = 20
        rest_s = 10

        m_rounds = re.search(r"(\d+)\s*rounds", text, flags=re.I)
        if m_rounds:
            rounds = int(m_rounds.group(1))

        m_work = re.search(r"(\d+)\s*s\s*work", text, flags=re.I)
        if m_work:
            work_s = int(m_work.group(1))

        m_rest = re.search(r"(\d+)\s*s\s*rest", text, flags=re.I)
        if m_rest:
            rest_s = int(m_rest.group(1))

        return rounds * (work_s + rest_s) * max(1, movements)

    # ---------- Duration & Cap ----------
    # One robust parse for minutes (For Time/AMRAP/Interval/EMOM/Alternating EMOM)
    duration_minutes = parse_duration_minutes(details)

    continuous_styles = ["For Time", "AMRAP", "Chipper", "Ladder"]
    interval_styles = ["Interval", "EMOM", "Alternating EMOM", "Tabata"]

    DEFAULT_CAP_MIN = 20 if wod_type in ["For Time", "AMRAP"] else 15
    cap_seconds = int((duration_minutes or DEFAULT_CAP_MIN) * 60)

    # For Tabata multi-movement, use rounds × (work+rest) × movements
    if wod_type == "Tabata":
        tabata_cap = derive_tabata_cap_seconds(details, num_movements)
        # If details provided a minutes cap, choose the larger (more conservative) of the two; else use tabata_cap
        cap_seconds = max(cap_seconds, tabata_cap) if duration_minutes else tabata_cap

    if cap_seconds <= 0:
        cap_seconds = DEFAULT_CAP_MIN * 60  # safety

    # Unique skip key so external Pause/Stop can interrupt run_rest_timer
    skip_key = f"skip_wod_clock_{session['session_id']}"

    # ---------- Session state (persistent) ----------
    if "wod_clock_in_progress" not in st.session_state:
        st.session_state.wod_clock_in_progress = False
    if "wod_clock_paused" not in st.session_state:
        st.session_state.wod_clock_paused = False
    if "wod_clock_start_ts" not in st.session_state:
        st.session_state.wod_clock_start_ts = None
    if "wod_clock_remaining" not in st.session_state:
        st.session_state.wod_clock_remaining = cap_seconds
    # If a previous session left remaining > new cap (e.g., switching sessions), clamp it:
    st.session_state.wod_clock_remaining = min(st.session_state.wod_clock_remaining, cap_seconds)

    if "wod_clock_last_action" not in st.session_state:
        st.session_state.wod_clock_last_action = None  # 'start' | 'pause' | 'resume' | 'stop' | None
    if "wod_interval_count" not in st.session_state:
        st.session_state.wod_interval_count = 0  # display only (interval styles)

    # ---------- Controls ----------
    c1, c2, c3, c4, c5 = st.columns(5)
    start_clicked = c1.button("▶ Start WOD Session")
    pause_clicked = c2.button("⏸ Pause")
    resume_clicked = c3.button("⏯ Resume")
    stop_clicked = c4.button("⏹ Stop")
    back_clicked = c5.button("⬅ Back to Dashboard")

    # ---------- Back: leave session view ----------
    if back_clicked:
        st.session_state.wod_clock_in_progress = False
        st.session_state.wod_clock_paused = False
        st.session_state.wod_clock_start_ts = None
        st.session_state.wod_clock_remaining = cap_seconds     # reset to current cap
        st.session_state.wod_clock_last_action = None
        st.session_state[skip_key] = True  # ensure any timer loop exits
        st.session_state.selected_session = None
        st.rerun()

    # ---------- Start ----------
    if start_clicked and not st.session_state.wod_clock_in_progress:
        st.session_state.wod_clock_in_progress = True
        st.session_state.wod_clock_paused = False
        st.session_state.wod_clock_remaining = cap_seconds     # (re)start from full cap
        st.session_state.wod_clock_start_ts = time.time()      # <-- persistent segment start
        st.session_state.wod_clock_last_action = "start"
        st.session_state[skip_key] = False

    # ---------- Pause (interrupt current segment) ----------
    if pause_clicked and st.session_state.wod_clock_in_progress and not st.session_state.wod_clock_paused:
        st.session_state.wod_clock_last_action = "pause"
        st.session_state[skip_key] = True  # run_rest_timer should exit on next tick

    # ---------- Resume (start a new segment) ----------
    if resume_clicked and st.session_state.wod_clock_paused and st.session_state.wod_clock_remaining > 0:
        st.session_state.wod_clock_in_progress = True
        st.session_state.wod_clock_paused = False
        st.session_state.wod_clock_start_ts = time.time()      # <-- new segment start
        st.session_state.wod_clock_last_action = "resume"
        st.session_state[skip_key] = False

    # ---------- Stop (finalize) ----------
    if stop_clicked and st.session_state.wod_clock_in_progress:
        st.session_state.wod_clock_last_action = "stop"
        st.session_state[skip_key] = True  # interrupt utility timer

    # ---------- Progress header (updated each rerun) ----------
    # Safe elapsed calculation + clamped ratio for Streamlit progress
    elapsed_seconds = max(0, int(cap_seconds) - int(st.session_state.wod_clock_remaining or 0))
    progress_ratio = 0.0 if cap_seconds <= 0 else min(max(elapsed_seconds / float(cap_seconds), 0.0), 1.0)
    st.empty().progress(progress_ratio)

    # Show elapsed/remaining
    elapsed_ph = st.empty()
    remaining_ph = st.empty()
    elapsed_ph.markdown(f"**Elapsed:** {format_mmss(elapsed_seconds)}")
    remaining_ph.markdown(f"**Remaining:** {format_mmss(st.session_state.wod_clock_remaining)} (cap)")

    # =============================================================================
    # TIMER ENGINE
    # =============================================================================
    current_ph = st.empty()
    next_ph = st.empty()
    counter_ph = st.empty()

    if wod_type in continuous_styles:
        # Run the utility timer for the remaining seconds in this segment
        if st.session_state.wod_clock_in_progress and not st.session_state.wod_clock_paused and st.session_state.wod_clock_remaining > 0:
            run_rest_timer(
                st.session_state.wod_clock_remaining,
                label=f"{wod_type} Clock",
                next_item="End",
                skip_key=skip_key
            )
        # On return, compute TRUE elapsed in this segment using persistent start_ts
        actual_run = int(time.time() - st.session_state.wod_clock_start_ts) if st.session_state.wod_clock_start_ts is not None else 0
        actual_run = max(0, min(actual_run, st.session_state.wod_clock_remaining))
        st.session_state.wod_clock_remaining -= actual_run
        final_elapsed = cap_seconds - st.session_state.wod_clock_remaining

        # Decide terminal state
        if st.session_state.wod_clock_last_action == "pause" and st.session_state.wod_clock_remaining > 0:
            st.session_state.wod_clock_paused = True
            st.session_state.wod_clock_in_progress = False
            st.info(f"Paused at {format_mmss(final_elapsed)}")
            st.session_state[skip_key] = False  # clear for next resume
        elif st.session_state.wod_clock_last_action == "stop" or st.session_state.wod_clock_remaining <= 0:
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
        # Structured Work/Rest cycles using the same utility timer.
        # Determine reasonable defaults if not explicitly provided in details.
        # We'll still respect the overall cap_seconds for progress/termination.
        wm = None
        rm = None

        if wod_type == "EMOM":
            wm = wm or 1  # 1 minute work
            rm = rm or 0  # explicit rest not modeled; rest is whatever is left in the minute
        elif wod_type == "Alternating EMOM":
            wm = wm or 1
            rm = rm or 0
        elif wod_type == "Tabata":
            # Default Tabata: 20s work / 10s rest unless explicitly provided in seconds in details
            wm = 0  # minutes placeholder; we use seconds below
            rm = 0
        else:  # "Interval"
            wm = 2
            rm = 1

        if st.session_state.wod_clock_in_progress and not st.session_state.wod_clock_paused and st.session_state.wod_clock_remaining > 0:
            # Mark the segment start (for accurate elapsed)
            st.session_state.wod_clock_start_ts = time.time()

            # Status line
            counter_ph.markdown(f"**Remaining Time:** {format_mmss(st.session_state.wod_clock_remaining)}")

            if wod_type == "Tabata":
                # Parse seconds from details if present; else default 20s work / 10s rest
                m_work_s = re.search(r"(\d+)\s*s\s*work", details, flags=re.I)
                m_rest_s = re.search(r"(\d+)\s*s\s*rest", details, flags=re.I)
                work_s = int(m_work_s.group(1)) if m_work_s else 20
                rest_s = int(m_rest_s.group(1)) if m_rest_s else 10

                current_ph.subheader("Tabata Work: Go!")
                next_ph.info(f"Next: Rest ({rest_s}s)")
                run_rest_timer(work_s, label=f"Work ({work_s}s)", next_item=f"Rest ({rest_s}s)", skip_key=skip_key)

                # Rest phase (if not interrupted)
                if not st.session_state.get(skip_key):
                    current_ph.subheader("Tabata Rest")
                    next_ph.info(f"Next: Work ({work_s}s)")
                    run_rest_timer(rest_s, label=f"Rest ({rest_s}s)", next_item=f"Work ({work_s}s)", skip_key=skip_key)

            else:
                # Work phase (minutes)
                current_ph.subheader(f"Work Interval ({wm} min)")
                next_ph.info("Next: Rest" if rm > 0 else "Next: Work/Continue")
                run_rest_timer(int(wm * 60), label=f"Work ({wm} min)", next_item="Rest", skip_key=skip_key)

                # Rest phase (minutes) if not interrupted and rest > 0
                if rm > 0 and not st.session_state.get(skip_key):
                    current_ph.subheader(f"Rest Interval ({rm} min)")
                    next_ph.info("Next: Work")
                    run_rest_timer(int(rm * 60), label=f"Rest ({rm} min)", next_item="Work", skip_key=skip_key)

            # Segment accounting
            actual_run = int(time.time() - st.session_state.wod_clock_start_ts) if st.session_state.wod_clock_start_ts is not None else 0
            actual_run = max(0, min(actual_run, st.session_state.wod_clock_remaining))
            st.session_state.wod_clock_remaining -= actual_run
            final_elapsed = cap_seconds - st.session_state.wod_clock_remaining

            # Completed one interval cycle if not interrupted early
            if not st.session_state.get(skip_key):
                st.session_state.wod_interval_count += 1

            # Handle controls / cap
            if st.session_state.wod_clock_last_action == "pause" and st.session_state.wod_clock_remaining > 0:
                st.session_state.wod_clock_paused = True
                st.session_state.wod_clock_in_progress = False
                st.info(f"Paused at {format_mmss(final_elapsed)}")
                st.session_state[skip_key] = False
            elif st.session_state.wod_clock_last_action == "stop" or st.session_state.wod_clock_remaining <= 0:
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
        # Fallback: treat as continuous clock
        for ex in exercises:
            st.markdown(f"- {ex}")

        if st.session_state.wod_clock_in_progress and not st.session_state.wod_clock_paused and st.session_state.wod_clock_remaining > 0:
            run_rest_timer(
                st.session_state.wod_clock_remaining,
                label="WOD Clock",
                next_item="End",
                skip_key=skip_key
            )

        # Compute final elapsed from persistent start
        actual_run = int(time.time() - st.session_state.wod_clock_start_ts) if st.session_state.wod_clock_start_ts is not None else 0
        actual_run = max(0, min(actual_run, st.session_state.wod_clock_remaining))
        st.session_state.wod_clock_remaining -= actual_run
        final_elapsed = cap_seconds - st.session_state.wod_clock_remaining

        st.session_state.wod_autofill_min = int(final_elapsed // 60)
        st.session_state.wod_autofill_sec = int(final_elapsed % 60)
        st.session_state.wod_clock_in_progress = False
        st.session_state.wod_clock_paused = False
        st.session_state.wod_clock_last_action = None
        st.session_state[skip_key] = False
        st.success(f"Time cap reached at {format_mmss(final_elapsed)}")

    # ---- Result Recording Section ----
    st.subheader("Enter Your WOD Result")
    previous_result = (
        supabase.table('wod_results')
        .select('result_details', 'rating', 'level')   # include level if stored top-level
        .eq('session_id', session['session_id'])
        .eq('user_id', st.session_state.get('user_id', 1))
        .execute()
        .data
    )

    if previous_result:
        prev = previous_result[0]
        prev_level = prev.get('level') or prev['result_details'].get('level')  # fallback if stored inside details earlier
        st.info(
            f"Previously submitted: {prev['result_details']} "
            f"(Level: {prev_level if prev_level else 'N/A'}, Rating: {prev['rating']}/100)"
        )

    # Show performance targets and let user choose a level
    performance_targets = session_data.get("performance_targets", {})
    if performance_targets:
        st.markdown("**Performance Targets**")
        levels_order = ["Beginner", "Intermediate", "Advanced", "Elite"]
        for lvl in levels_order:
            if lvl in performance_targets:
                st.markdown(f"- **{lvl}**: {performance_targets[lvl]}")
        for k, v in performance_targets.items():
            if k not in levels_order:
                st.markdown(f"- **{k}**: {v}")
    else:
        st.info("No performance targets available for this session.")

    level = st.selectbox(
        "Select target level for rating",
        options=[opt for opt in ["Beginner", "Intermediate", "Advanced", "Elite"] if opt in performance_targets] or ["Intermediate"],
        index=0
    )

    user_result = {}
    if wod_type == "AMRAP":
        user_result["rounds"] = st.number_input("Rounds Completed", min_value=0, step=1)
        user_result["reps"] = st.number_input("Additional Reps", min_value=0, step=1)

    elif wod_type in ["For Time", "Chipper", "Ladder"]:
        col_m, col_s = st.columns(2)
        with col_m:
            time_min_only = st.number_input("Minutes", min_value=0, step=1)
        with col_s:
            time_sec_only = st.number_input("Seconds", min_value=0, max_value=59, step=1)
        user_result["time_min"] = float(time_min_only) + float(time_sec_only) / 60.0
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
            'result_details': user_result,   # keep detailed inputs here
            'level': level,                  # NEW: top-level column for easy querying
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

        # ✅ Fix: use the correct session id from `session`
        supabase.table('plan_sessions').update({'completed': True}).eq('id', session['session_id']).execute()

        st.success("WOD completed!")
        st.session_state.wod_running = False
        st.session_state.wod_paused = False
        st.session_state.selected_session = None
