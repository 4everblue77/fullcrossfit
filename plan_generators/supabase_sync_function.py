
# supabase_sync_function.py
import re
from typing import Optional, Union, Dict, Any
from datetime import datetime, timedelta, date as _date

# ---------- EXISTING HELPERS ----------
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

# ---------- FULL-WIPE SYNC (unchanged; for first-time creation) ----------
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

    # Full wipe (dev/seed). Reuses your original behavior. [1](https://danone-my.sharepoint.com/personal/john_matthews_danone_com/Documents/Microsoft%20Copilot%20Chat%20Files/2_%E2%9A%99%EF%B8%8F_Plan_Generator.py)
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
            total_minutes = _parse_minutes(day_data.get("estimated_time"))
            day_resp = supabase.table("plan_days").insert({
                "week_id": week_id,
                "day_number": day_number,
                "is_rest_day": bool(day_data.get("Rest", False)),
                "date": day_data.get("date") or None,
                "total_time": total_minutes
            }).execute()
            day_id = day_resp.data[0]["id"]
            summary["days"] += 1

            if day_data.get("Rest") or "plan" not in day_data:
                continue

            for session_type, session_data in day_data["plan"].items():
                if session_type in ["Debug", "Total Time"] or not isinstance(session_data, dict):
                    continue

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

                if "exercises" in session_data and isinstance(session_data["exercises"], list):
                    for i, ex in enumerate(session_data["exercises"], start=1):
                        exercise_name = (
                            ex.get("name")
                            or ex.get("exercise_name")
                            or ex.get("exercise")
                            or "Unknown"
                        )
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
                            "equipment": ex.get("equipment", "")
                        }).execute()
                        summary["exercises"] += 1

    return summary

# ---------- MERGE (NON-DESTRUCTIVE) SYNC ----------
DAY_INDEX = {"Mon": 1, "Tue": 2, "Wed": 3, "Thu": 4, "Fri": 5, "Sat": 6, "Sun": 7}

def _get_or_create_week(supabase, week_number: int, start_date: Optional[_date]) -> int:
    # weeks.number has a unique constraint (per your schema). [1](https://danone-my.sharepoint.com/personal/john_matthews_danone_com/Documents/Microsoft%20Copilot%20Chat%20Files/2_%E2%9A%99%EF%B8%8F_Plan_Generator.py)
    resp = supabase.table("plan_weeks").select("id").eq("number", week_number).execute()
    if resp.data:
        return resp.data[0]["id"]
    payload = {"number": week_number, "notes": f"Week {week_number}"}
    if start_date:
        payload["start_date"] = start_date
    ins = supabase.table("plan_weeks").insert(payload).execute()
    return ins.data[0]["id"]

def _get_or_create_day(supabase, week_id: int, day_name: str, day_date_iso: Optional[str], total_minutes: int, is_rest: bool) -> int:
    day_number = DAY_INDEX.get(day_name, None)
    assert day_number is not None, f"Unknown day name: {day_name}"
    q = supabase.table("plan_days").select("id").eq("week_id", week_id).eq("day_number", day_number).execute()
    payload = {
        "week_id": week_id,
        "day_number": day_number,
        "is_rest_day": bool(is_rest),
        "total_time": int(total_minutes or 0),
        "date": day_date_iso or None,
    }
    if q.data:
        day_id = q.data[0]["id"]
        supabase.table("plan_days").update(payload).eq("id", day_id).execute()
        return day_id
    ins = supabase.table("plan_days").insert(payload).execute()
    return ins.data[0]["id"]

def _insert_exercises(supabase, session_id: int, exercises: Optional[list], data: Dict[str, Any], append: bool = False):
    if not exercises or not isinstance(exercises, list):
        return
    start_order = 1
    if append:
        cur = supabase.table("plan_session_exercises").select("exercise_order").eq("session_id", session_id).order("exercise_order", desc=True).limit(1).execute()
        if cur.data:
            start_order = int(cur.data[0]["exercise_order"]) + 1

    for idx, ex in enumerate(exercises, start=start_order):
        exercise_name = (
            ex.get("name")
            or ex.get("exercise_name")
            or ex.get("exercise")
            or "Unknown"
        )
        exercise_id = _resolve_exercise_id({"name": exercise_name, "exercise_id": ex.get("exercise_id")}, data)
        supabase.table("plan_session_exercises").insert({
            "session_id": session_id,
            "exercise_name": exercise_name,
            "exercise_id": exercise_id,
            "set_number": ex.get("set", 1),
            "reps": ex.get("reps", ""),
            "intensity": ex.get("intensity", ""),
            "rest": ex.get("rest", 0),
            "notes": ex.get("notes", ""),
            "exercise_order": idx,
            "completed": False,
            "actual_reps": "",
            "actual_weight": "",
            "tempo": ex.get("tempo", ""),
            "expected_weight": ex.get("expected_weight", ""),
            "equipment": ex.get("equipment", "")
        }).execute()

def _upsert_session_and_exercises(
    supabase,
    day_id: int,
    session_type: str,
    session_minutes: int,
    target_muscle: str,
    details: str,
    focus_muscle: str,
    performance_targets: Optional[Dict[str, Any]],
    exercises: Optional[list],
    data: Dict[str, Any],
    *,
    replace_section: bool = True
) -> int:
    """
    Upserts a session (match on day_id + type) and optionally replaces its exercises.
    - If session exists: update fields; optionally delete exercises then reinsert (replace_section=True)
    - If not exists: insert.
    """
    sel = supabase.table("plan_sessions").select("id").eq("day_id", day_id).eq("type", session_type).execute()
    payload = {
        "day_id": day_id,
        "type": session_type,
        "target_muscle": target_muscle or "",
        "duration": int(session_minutes or 0),
        "details": details or "",
        "focus_muscle": focus_muscle or "",
    }
    if session_type == "WOD" and performance_targets is not None:
        payload["performance_targets"] = performance_targets

    if sel.data:
        sess_id = sel.data[0]["id"]
        supabase.table("plan_sessions").update(payload).eq("id", sess_id).execute()
        if replace_section:
            supabase.table("plan_session_exercises").delete().eq("session_id", sess_id).execute()
            _insert_exercises(supabase, sess_id, exercises, data)
        else:
            _insert_exercises(supabase, sess_id, exercises, data, append=True)
        return sess_id
    else:
        ins = supabase.table("plan_sessions").insert(payload).execute()
        sess_id = ins.data[0]["id"]
        _insert_exercises(supabase, sess_id, exercises, data)
        return sess_id

def merge_plan_patch_to_supabase(
    supabase,
    patch_plan: dict,
    data: dict,
    *,
    start_date: Optional[str] = None,
    replace_section: bool = True
) -> Dict[str, int]:
    """
    Merge-only sync: upserts weeks, days, and only the sessions present in patch_plan.
    Does NOT delete other weeks/days/sessions.

    Arguments:
      - patch_plan: structure like CrossFitPlanGenerator.generate_partial_plan(...) returns
      - data: catalogs (exercises, etc.) used for exercise_id resolution
      - start_date: iso 'YYYY-MM-DD' (to populate plan_weeks.start_date, optional)
      - replace_section:
          True  => for any session included in the patch, delete its existing exercises first, then reinsert
          False => append exercises to any existing ones (merge)

    Returns: summary counts
    """
    summary = {"weeks": 0, "days": 0, "sessions": 0, "exercises": 0}
    start_d = datetime.strptime(start_date, "%Y-%m-%d").date() if start_date else None

    for week_label, week_blob in patch_plan.items():
        try:
            week_number = int(str(week_label).split()[-1])
        except Exception:
            week_number = None

        wk_start = None
        if start_d and week_number:
            wk_start = start_d + timedelta(days=(week_number - 1) * 7)

        week_id = _get_or_create_week(supabase, week_number or 0, wk_start)
        summary["weeks"] += 1

        for day_name, day_data in week_blob.items():
            total_minutes = _parse_minutes(day_data.get("estimated_time"))
            day_id = _get_or_create_day(
                supabase,
                week_id=week_id,
                day_name=day_name,
                day_date_iso=day_data.get("date"),
                total_minutes=total_minutes,
                is_rest=bool(day_data.get("Rest", False)),
            )
            summary["days"] += 1

            if day_data.get("Rest") or "plan" not in day_data:
                continue

            for session_type, session_payload in day_data["plan"].items():
                if session_type in ("Total Time", "Debug"):
                    continue
                if not isinstance(session_payload, dict):
                    continue
                session_minutes = _parse_minutes(
                    session_payload.get("time", None)
                    if session_payload.get("time") is not None
                    else session_payload.get("Estimated Time", None)
                )
                target_muscle = ", ".join(day_data.get("muscles", []))
                details = session_payload.get("details", "")
                focus_muscle = session_payload.get("focus_muscle", "")
                perf_targets = session_payload.get("Performance Targets", {}) if session_type == "WOD" else None
                exs = session_payload.get("exercises", [])

                sess_id = _upsert_session_and_exercises(
                    supabase,
                    day_id=day_id,
                    session_type=session_type,
                    session_minutes=session_minutes,
                    target_muscle=target_muscle,
                    details=details,
                    focus_muscle=focus_muscle,
                    performance_targets=perf_targets,
                    exercises=exs,
                    data=data,
                    replace_section=replace_section
                )
                summary["sessions"] += 1
                summary["exercises"] += (len(exs) or 0)

   
