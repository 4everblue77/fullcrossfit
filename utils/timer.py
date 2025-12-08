
import streamlit as st
import time
import streamlit.components.v1 as components

def run_rest_timer(seconds, label="Rest", next_item=None, skip_key=None):
    """
    Unified rest timer for all session types.
    
    Args:
        seconds (int): Duration of rest in seconds.
        label (str): Label for the timer (e.g., "Set", "Superset").
        next_item (str): Optional name of next exercise or superset.
        skip_key (str): Unique key for skip button state.
    """

    
    # ---------- One-time pre-countdown (5s) ----------
    if "rest_timer_first_run_shown" not in st.session_state:
        st.session_state["rest_timer_first_run_shown"] = False

    status_placeholder = st.empty()
    timer_placeholder = st.empty()
    progress_placeholder = st.empty()
    skip_placeholder = st.empty()

    # Initial status
    next_text = f" → Next: {next_item}" if next_item else ""
    status_placeholder.markdown(f"<h4>✅ {label} -> {next_text}</h4>", unsafe_allow_html=True)

    
    # ---- 5-second pre-countdown shown only once per session ----
    if not st.session_state["rest_timer_first_run_shown"]:
        prep_placeholder = st.empty()
        prep_progress = st.empty()
        for prep_remaining in range(5, 0, -1):
            prep_placeholder.markdown(f""" ### ⏱️ Get ready: {prep_remaining}s""", unsafe_allow_html=True, )
            # optional short beep each second
            components.html("""""", height=0)
            prep_progress.progress((5 - prep_remaining) / 5)
            time.sleep(1)
        prep_placeholder.empty()
        prep_progress.empty()
        st.session_state["rest_timer_first_run_shown"] = True


    # Skip button
    if skip_key not in st.session_state:
        st.session_state[skip_key] = False
    skip = skip_placeholder.button("⏭ Skip Rest", key=f"skip_btn_{skip_key}")
    if skip:
        st.session_state[skip_key] = True

    # Countdown loop
    for remaining in range(seconds, 0, -1):
        if st.session_state.get(skip_key, False):
            timer_placeholder.markdown("<h3 style='color:#ff4b4b;'>⏭ Timer skipped! Ready for next.</h3>", unsafe_allow_html=True)
            break
        mins, secs = divmod(remaining, 60)
        timer_placeholder.markdown(f"<h1 style='text-align:center; color:#28a745;'>⏳ {mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
        progress_placeholder.progress((seconds - remaining) / seconds)

        
        # ✅ Beep on last 3 seconds
        if remaining <= 3 or remaining % 60 == 0:


            components.html(f"""
            <script>
                var audio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
                audio.play();
            </script>
            """, height=0)



        time.sleep(1)
    else:         
        timer_placeholder.markdown("<h3 style='color:#28a745;'>🔥 Ready for next!</h3>", unsafe_allow_html=True)

    # Clear placeholders
    time.sleep(1)
    status_placeholder.empty()
    timer_placeholder.empty()
    progress_placeholder.empty()
    skip_placeholder.empty()
