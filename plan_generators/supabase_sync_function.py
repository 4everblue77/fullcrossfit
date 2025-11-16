def sync_plan_to_supabase(supabase, full_plan, data):
    """
    Syncs a generated plan to Supabase tables.
    - Clears previous plan data.
    - Inserts weeks, days, sessions, and exercises.
    - Stores performance_targets for WOD sessions.
    - Ensures numeric values for total_time and duration.
    - Returns a summary of inserted rows.
    """
    summary = {"weeks": 0, "days": 0, "sessions": 0, "exercises": 0}

    # Clear previous plan
    supabase.table("plan_session_exercises").delete().gt("id", 0).execute()
    supabase.table("plan_sessions").delete().gt("id", 0).execute()
    supabase.table("plan_days").delete().gt("id", 0).execute()
    supabase.table("plan_weeks").delete().gt("id", 0).execute()

    for week_number, (week_label, week_data) in enumerate(full_plan.items(), start=1):
        # Insert week
        week_resp = supabase.table("plan_weeks").insert({
            "number": week_number,
            "notes": week_label
        }).execute()
        week_id = week_resp.data[0]["id"]
        summary["weeks"] += 1

        for day_number, (day_label, day_data) in enumerate(week_data.items(), start=1):
            # Insert day
            day_resp = supabase.table("plan_days").insert({
                "week_id": week_id,
                "day_number": day_number,
                "is_rest_day": day_data.get("Rest", False),
                "total_time": int(day_data.get("estimated_time", 0))
            }).execute()
            day_id = day_resp.data[0]["id"]
            summary["days"] += 1

            if day_data.get("Rest") or "plan" not in day_data:
                continue

            for session_type, session_data in day_data["plan"].items():
                if session_type in ["Debug", "Total Time"] or not isinstance(session_data, dict):
                    continue

                payload = {
                    "day_id": day_id,
                    "type": session_type,
                    "target_muscle": ", ".join(day_data.get("muscles", [])),
                    "duration": int(session_data.get("time", 0)),
                    "details": session_data.get("details", "")
                }

                if session_type == "WOD":
                    payload["performance_targets"] = session_data.get("Performance Targets", {})

                session_resp = supabase.table("plan_sessions").insert(payload).execute()
                session_id = session_resp.data[0]["id"]
                summary["sessions"] += 1

                if "exercises" in session_data and isinstance(session_data["exercises"], list):
                    for i, ex in enumerate(session_data["exercises"], start=1):
                        exercise_id = next((e["id"] for e in data["exercises"] if e["name"] == ex["name"]), None)
                        supabase.table("plan_session_exercises").insert({
                            "session_id": session_id,
                            "exercise_name": ex["name"],
                            "exercise_id": exercise_id,
                            "set_number": ex.get("set", 1),
                            "reps": ex.get("reps", ""),
                            "intensity": ex.get("intensity", ""),
                            "rest": ex.get("rest", 0),
                            "notes": ex.get("notes", ""),
                            "exercise_order": i,
                            "completed": False,
                            "actual_reps": "",
                            "actual_weight": "",
                            "tempo": ex.get("tempo", ""),
                            "expected_weight": ex.get("expected_weight", ""),
                            "equipment": ex.get("equipment", "")
                        }).execute()
                        summary["exercises"] += 1

    return summary
