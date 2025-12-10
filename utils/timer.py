
import streamlit as st
import time
import streamlit.components.v1 as components

def run_rest_timer(
    seconds,
    label="Rest",
    next_item=None,
    skip_key=None,
    session_scope_key: str = None,
    precountdown_seconds: int = 5,
    parent=None
):
    """
    Unified rest timer for all session types.

    Args:
        seconds (int): Duration of rest in seconds.
        label (str): Label for the timer (e.g., "Set", "Superset").
        next_item (str): Optional name of next exercise or superset.
        skip_key (str): Unique key for skip button state. If None, auto-generated.
        session_scope_key (str): Stable key for pre-countdown scoping across a workout.
        precountdown_seconds (int): One-time pre-countdown length (per scope).
        parent: Optional Streamlit container (e.g., st.container(), st.sidebar, st.expander).
    """

    # ---------- Choose a valid container ----------
    # If parent is None, create a container; avoid using the st module directly in a 'with'.
    container = parent if parent is not None else st.container()

    # ---------- One-time pre-countdown (scoped per workout session) ----------
    scope_value = (
        session_scope_key
        if session_scope_key is not None
        else st.session_state.get("selected_session", "global_scope")
    )
    precnt_flag_key = f"precnt_shown_scope_{scope_value}"

    # Enter the context only if the container supports it
    # Most st containers do; module 'st' does not (we avoided that above).
    with container:
        if precountdown_seconds > 0 and not st.session_state.get(precnt_flag_key, False):
            prep_placeholder = st.empty()
            prep_progress = st.empty()

            for remaining in range(precountdown_seconds, 0, -1):
                prep_placeholder.markdown(
                    f"### ⏱️ Get ready: {remaining}s",
                    unsafe_allow_html=True,
                )
                # Optional cue each second (replace with real audio if you add it)
                components.html(
                    """
                    <script>
                        var audio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
                        audio.play();
                    </script>
                    """,
                    height=0
                )
                prep_progress.progress((precountdown_seconds - remaining) / precountdown_seconds)
                time.sleep(1)

            prep_placeholder.empty()
            prep_progress.empty()
            st.session_state[precnt_flag_key] = True

        # ---------- Main countdown UI ----------
        status_placeholder = st.empty()
        timer_placeholder = st.empty()
        progress_placeholder = st.empty()
        skip_placeholder = st.empty()

        # Use a safe default skip key
        if skip_key is None:
            skip_key = f"skip_rest_{label}_{next_item or 'none'}_{seconds}"

        # Initial status
        next_text = f" → Next: {next_item}" if next_item else ""
        status_placeholder.markdown(
            f"<h4>✅ {label} -> {next_text}</h4>",
            unsafe_allow_html=True
        )

        # Skip button wiring
        if skip_key not in st.session_state:
            st.session_state[skip_key] = False

        skip = skip_placeholder.button("⏭ Skip Rest", key=f"skip_btn_{skip_key}")
        if skip:
            st.session_state[skip_key] = True

        # Countdown loop
        for remaining in range(seconds, 0, -1):
            if st.session_state.get(skip_key, False):
                timer_placeholder.markdown(
                    "<h3 style='color:#ff4b4b;'>⏭ Timer skipped! Ready for next.</h3>",
                    unsafe_allow_html=True
                )
                break

            mins, secs = divmod(remaining, 60)
            timer_placeholder.markdown(
                f"<h1 style='text-align:center; color:#28a745;'>⏳ {mins:02d}:{secs:02d}</h1>",
                unsafe_allow_html=True
            )
            progress_placeholder.progress((seconds - remaining) / seconds)

            # ✅ Beep on last 3 seconds and every minute mark
            if remaining <= 3 or remaining % 60 == 0:
                components.html(
                    """
                    <script>
                        var audio = new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg');
                        audio.play();
                    </script>
                    """,
                    height=0
                )

            time.sleep(1)
        else:
            timer_placeholder.markdown(
                "<h3 style='color:#28a745;'>🔥 Ready for next!</h3>",
                unsafe_allow_html=True
            )

        # Clear placeholders
        time.sleep(1)
        status_placeholder.empty()
        timer_placeholder.empty()
        progress_placeholder.empty()
        skip_placeholder.empty()

