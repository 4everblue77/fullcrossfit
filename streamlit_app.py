import streamlit as st
from supabase import create_client
from plan_generator import PlanGenerator
from datetime import date

# Connect to Supabase
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize PlanGenerator
plan_gen = PlanGenerator(supabase)

st.title("12-Week Workout Plan Generator")

debug_mode = st.checkbox("Enable Debug Mode")
view_mode = st.radio("Select View Mode:", ["Weekly Summary", "Daily Details"])

if st.button("Generate & Save 12-Week Plan"):
    full_plan = plan_gen.generate_full_plan()

    # Insert weeks, days, sessions, and exercises into Supabase
    for week_num, week_data in enumerate(full_plan.values(), start=1):
        # Insert into plan_weeks
        week_insert = supabase.table("plan_weeks").insert({
            "number": week_num,
            "start_date": str(date.today()),  # or calculate based on cycle start
            "notes": f"Week {week_num} of 12-week plan"
        }).execute()
        week_id = week_insert.data[0]["id"]

        for day_num, (day_label, day_data) in enumerate(week_data.items(), start=1):
            # Insert into plan_days
            day_insert = supabase.table("plan_days").insert({
                "week_id": week_id,
                "day_number": day_num,
                "is_rest_day": day_data.get("Rest", False),
                "total_time": day_data.get("estimated_time", 0),
                "completed": False
            }).execute()
            day_id = day_insert.data[0]["id"]

            if not day_data.get("Rest"):
                # Insert sessions
                for session_type, session_content in day_data["plan"].items():
                    if session_type == "Debug":
                        continue

                    session_insert = supabase.table("plan_sessions").insert({
                        "day_id": day_id,
                        "type": session_type,
                        "target_muscle": ", ".join(day_data["muscles"]),
                        "duration": session_content.get("time", 0),
                        "details": session_content.get("details", ""),
                        "completed": False
                    }).execute()
                    session_id = session_insert.data[0]["id"]

                    # Insert exercises if available
                    if "supersets" in session_content:
                        for idx, superset in enumerate(session_content["supersets"], start=1):
                            supabase.table("plan_session_exercises").insert({
                                "session_id": session_id,
                                "exercise_name": superset.get("Superset", ""),
                                "set_number": idx,
                                "reps": superset.get("Reps", ""),
                                "intensity": "",
                                "rest": 60,
                                "notes": "",
                                "completed": False,
                                "actual_reps": "",
                                "actual_weight": ""
                            }).execute()
                    elif "general" in session_content or "specific" in session_content:
                        # Warmup or cooldown exercises
                        exercises = session_content.get("general", []) + session_content.get("specific", []) + session_content.get("activities", [])
                        for idx, ex in enumerate(exercises, start=1):
                            supabase.table("plan_session_exercises").insert({
                                "session_id": session_id,
                                "exercise_name": ex.get("exercise", ""),
                                "set_number": idx,
                                "reps": "",
                                "intensity": "",
                                "rest": 30,
                                "notes": "",
                                "completed": False,
                                "actual_reps": "",
                                "actual_weight": ""
                            }).execute()

    st.success("✅ 12-week plan generated and saved to Supabase!")

    # Display plan in Streamlit
    for week_label, week_data in full_plan.items():
        st.header(week_label)
        if view_mode == "Weekly Summary":
            for day_label, day_data in week_data.items():
                if day_data.get("Rest"):
                    st.markdown(f"**{day_label}:** Rest Day 💤")
                else:
                    muscles = ", ".join(day_data["muscles"])
                    stim = day_data["stimulus"]
                    time = day_data["estimated_time"]
                    st.markdown(f"**{day_label}:** {muscles} | Stimulus: `{stim}` | Estimated Time: `{time} min`")
        else:
            for day_label, day_data in week_data.items():
                st.subheader(day_label)
                if day_data.get("Rest"):
                    st.markdown("**Rest Day 💤**")
                else:
                    st.markdown(f"**Target Muscles:** {', '.join(day_data['muscles'])}")
                    st.markdown(f"**Stimulus:** `{day_data['stimulus']}`")
                    st.markdown(f"**Estimated Time:** `{day_data['estimated_time']} min`")
                    for section, content in day_data["plan"].items():
                        if section != "Debug":
                            st.markdown(f"**{section}**")
                            st.json(content)
                    if debug_mode:
                        st.markdown("**Debug Info**")
                        st.json(day_data["plan"].get("Debug", {}))
