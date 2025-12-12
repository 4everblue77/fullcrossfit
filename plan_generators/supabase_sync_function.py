
# supabase_sync_function.py

import re
from typing import Optional, Union, Dict, Any


def _parse_minutes(value: Optional[Union[str, int, float]]) -> int:
    """
    Return a safe integer minute count from mixed inputs:
      - None -> 0
      - int/float -> rounded int
      - '20 min', '15 minutes' -> 20, 15
      - '00:20:00' or 'MM:SS' -> minutes (floor)
      - 'Time Cap: 30 min' -> 30
    Fallback to 0 if unparseable.
    """
    if value is None:
        return 0

    if isinstance(value, (int, float)):
        try:
            return max(0, int(round(float(value))))
        except Exception:
            return 0

    s = str(value).strip().lower()
    if not s:
        return 0

    # Plain integer string
    if s.isdigit():
        return int(s)

    # 'X min' / 'X minutes' anywhere in the string
    m = re.search(r'(\d+)\s*(min|mins|minute|minutes)\b', s)
    if m:
        return int(m.group(1))

    # Time-like: HH:MM(:SS) or MM:SS -> minutes
    parts = s.split(':')
    if len(parts) >= 2 and all(p.isdigit() for p in parts[:2]):
        hours = int(parts[0]) if len(parts) == 3 else 0
        minutes = int(parts[1])
        return max(0, hours * 60 + minutes)

    # Fallback: first integer anywhere
    m2 = re.search(r'(\d+)', s)
    if m2:
        return int(m2.group(1))

    return 0


def _resolve_exercise_id(ex_item: Dict[str, Any], data: Dict[str, Any]) -> Optional[int]:
    """
    Tries to resolve an exercise_id for insertion:
      - Prefer explicit id in ex_item (from exercise_pool)
      - Else attempt lookup by name via data["exercises"] (legacy catalog)
    """
    if isinstance(ex_item.get("exercise_id"), int):
        return ex_item["exercise_id"]

    name = ex_item.get("name") or ex_item.get("exercise_name")
    if not name:
        return None

    for e in data.get("exercises", []):
        if e.get("name") == name:
            return e.get("id")

    return None


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

    # Clear previous plan (id > 0 is a safe full wipe for seed/dev)
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
            # Compute a robust total_time for the day
            # Prefer already-computed numeric minutes; fall back to parsing the display string or 0
            total_minutes = _parse_minutes(day_data.get("estimated_time"))

            # Insert day
            day_resp = supabase.table("plan_days").insert({
                "week_id": week_id,
                "day_number": day_number,
                "is_rest_day": bool(day_data.get("Rest", False)),
                "date": day_data.get("date") or None,
                "total_time": total_minutes
            }).execute()
            day_id = day_resp.data[0]["id"]
            summary["days"] += 1

            # Skip rest days or missing plan payload
            if day_data.get("Rest") or "plan" not in day_data:
                continue

            for session_type, session_data in day_data["plan"].items():
                # Skip debugging/summary entries or malformed blocks
                if session_type in ["Debug", "Total Time"] or not isinstance(session_data, dict):
                    continue

                # Robust per-session duration:
                # - Prefer explicit numeric 'time'
                # - Else parse section-level 'Estimated Time'
                # - Else 0
                session_minutes = _parse_minutes(
                    session_data.get("time", None) if session_data.get("time") is not None
                    else session_data.get("Estimated Time", None)
                )

                payload = {
                    "day_id": day_id,
                    "type": session_type,
                    "target_muscle": ", ".join(day_data.get("muscles", [])),
                    "duration": session_minutes,
                    "details": session_data.get("details", ""),
                    "focus_muscle": session_data.get("focus_muscle", "")
                }

                if session_type == "WOD":
                    payload["performance_targets"] = session_data.get("Performance Targets", {})

                session_resp = supabase.table("plan_sessions").insert(payload).execute()
                session_id = session_resp.data[0]["id"]
                summary["sessions"] += 1

                # Insert exercises for the session
                if "exercises" in session_data and isinstance(session_data["exercises"], list):
                    for i, ex in enumerate(session_data["exercises"], start=1):
                        # Name resolution
                        exercise_name = (
                            ex.get("name")
                            or ex.get("exercise_name")
                            or ex.get("exercise")
                            or "Unknown"
                        )

                        # Prefer id carried through from exercise_pool; else legacy lookup by name
                        exercise_id = _resolve_exercise_id(
                            {"name": exercise_name, "exercise_id": ex.get("exercise_id")},
                            data
                        )

                        supabase.table("plan_session_exercises").insert({
                            "session_id": session_id,
                            "exercise_name": exercise_name,
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
                            "equipment": ex.get("equipment","")                        
                        }).execute()
                        summary["exercises"] += 1

