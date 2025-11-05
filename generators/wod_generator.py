import random

class WODGenerator:
    def __init__(self, data, debug=False):
        self.data = data  # ✅ Store full data dictionary
        self.exercise_pool = data["exercise_pool"]
        self.debug = debug


    def get_combined_exercise_pool(self):
        # ✅ Pull all exercises from exercise_pool
        return [ex["exercise"] for ex in self.exercise_pool]

    def get_exercises_by_muscle_group(self, muscle_group_id):
        # ✅ Filter by musclegroup_id
        return [ex["exercise"] for ex in self.exercise_pool if ex["musclegroup_id"] == muscle_group_id]

    def _parse_time_str(self, t):
        t = str(t).strip().lower()
        if "min" in t:
            return float(t.replace("min", "").strip())
        if ":" in t:
            mins, secs = map(int, t.split(":"))
            return mins + secs / 60
        return float(t)

    def _estimate_exercise_time(self, details):
        if "duration" in details:
            return self._parse_time_str(details["duration"])
        if "sets" in details and "work" in details:
            work_min = self._parse_time_str(details["work"])
            rest_min = self._parse_time_str(details.get("rest", "0"))
            return (work_min + rest_min) * details["sets"]
        if "rounds" in details and "reps" in details:
            reps = details["reps"] if isinstance(details["reps"], int) else 10
            time_per_rep = 0.07 if "weight" in details and "Bodyweight" not in details.get("weight", "") else 0.05
            return (reps * time_per_rep + 0.3) * details["rounds"]
        return 2  # fallback

    def _get_time_bounds_for_stimulus(self, stimulus):
        stimulus = stimulus.lower()
        if stimulus == "anaerobic":
            return 8, 12
        elif stimulus in ["lactate threshold", "vo2 max"]:
            return 15, 30
        return 15, 20

    def _assign_details(self, exercise, format_type, stimulus):
        details = {}
        # Basic logic for reps/weight
        if any(lift in exercise for lift in ["Squat", "Deadlift", "Thruster"]):
            details["weight"] = "Moderate to heavy (70–90% 1RM)" if stimulus == "anaerobic" else "Moderate (60–75% 1RM)"
            details["reps"] = random.choice([6, 8, 10]) if stimulus == "anaerobic" else random.choice([8, 10, 12])
        else:
            details["weight"] = "Light to moderate (40–60% 1RM)"
            details["reps"] = random.choice([10, 12, 15])

        # Format-specific details
        if format_type == "Tabata":
            details.update({"sets": 8, "work": "20s", "rest": "10s"})
        elif format_type == "Sprint Intervals":
            details.update({"sets": 6, "work": "30s", "rest": "90s"})
        elif format_type == "AMRAP":
            details.update({"duration": "15 min", "goal": "Max rounds"})
        elif format_type == "Chipper":
            details.update({"rounds": 1, "goal": "Complete sequentially"})
        elif format_type == "For Time":
            details.update({"rounds": 2, "goal": "Complete as fast as possible"})
        elif format_type == "Rounds for Time":
            details.update({"rounds": 3, "goal": "Complete each round"})
        elif format_type == "Interval Rounds":
            details.update({"sets": 4, "work": "2 min", "rest": "1 min"})
        else:
            details.update({"sets": 3, "rest": "60s"})
        return details

    def _scale_wod_to_time(self, exercises, stimulus):
        min_time, max_time = self._get_time_bounds_for_stimulus(stimulus)
        attempt = 0
        scaled = exercises
        while attempt < 5:
            total_time = sum(self._estimate_exercise_time(ex["details"]) for ex in scaled)
            if total_time == 0:
                return {"exercises": scaled, "time": 0}
            if min_time <= total_time <= max_time:
                return {"exercises": scaled, "time": round(total_time)}
            scale_factor = min((min_time if total_time < min_time else max_time) / total_time, 2.0)
            new_scaled = []
            for ex in scaled:
                details = ex["details"].copy()
                if "sets" in details:
                    details["sets"] = min(20, max(1, int(details["sets"] * scale_factor)))
                elif "rounds" in details:
                    details["rounds"] = min(20, max(1, int(details["rounds"] * scale_factor)))
                elif "duration" in details:
                    original_duration = self._parse_time_str(details["duration"])
                    scaled_duration = max(min_time, min(max_time, int(original_duration * scale_factor)))
                    details["duration"] = f"{scaled_duration} min"
                new_scaled.append({"name": ex["name"], "details": details})
            scaled = new_scaled
            attempt += 1
        return {"exercises": scaled, "time": round(sum(self._estimate_exercise_time(ex["details"]) for ex in scaled))}

    def generate(self, target_muscle=None, stimulus="anaerobic"):
    """
    target_muscle: Muscle name (string) or None
    stimulus: Training stimulus (e.g., 'anaerobic', 'lactate threshold', 'vo2 max')
    """
    # Debug info
    debug_info = {
        "target_muscle": target_muscle,
        "available_muscles": [mg["name"] for mg in self.data["muscle_groups"]]
    }

    # Resolve muscle name to ID
    target_muscle_id = None
    if target_muscle:
        target_muscle_id = next(
            (mg["id"] for mg in self.data["muscle_groups"] if mg["name"].lower() == target_muscle.lower()),
            None
        )
        if not target_muscle_id:
            debug_info["error"] = f"Muscle '{target_muscle}' not found"
    
    # Continue with existing logic using target_muscle_id
    formats = {
        "anaerobic": ["For Time", "Sprint Intervals", "Tabata"],
        "lactate threshold": ["AMRAP", "Chipper", "For Time"],
        "vo2 max": ["EMOM", "Interval Rounds", "Rounds for Time"]
    }
    format_type = random.choice(formats.get(stimulus.lower(), ["AMRAP"]))

    full_pool = self.get_combined_exercise_pool()
    target_pool = self.get_exercises_by_muscle_group(target_muscle_id) if target_muscle_id else []

    target_sample = random.sample(target_pool, min(3, len(target_pool))) if target_pool else []
    random_sample = random.sample(full_pool, min(3, len(full_pool)))
    wod_exercises = target_sample + random_sample
    random.shuffle(wod_exercises)

    detailed_exercises = []
    id_to_name = {m["id"]: m["name"] for m in self.data["muscle_groups"]}
    for ex in wod_exercises:
        musclegroup_id = next((item["musclegroup_id"] for item in self.exercise_pool if item["exercise"] == ex), None)
        muscle_name = id_to_name.get(musclegroup_id, "Unknown")
        details = self._assign_details(ex, format_type, stimulus)
        detailed_exercises.append({"name": ex, "muscle_group": muscle_name, "details": details})

    scaled_result = self._scale_wod_to_time(detailed_exercises, stimulus.lower())
    scaled_exercises = scaled_result["exercises"]
    actual_time = scaled_result["time"]

    result = {
        "type": "WOD",
        "stimulus": stimulus.capitalize(),
        "duration": f"{actual_time} min",
        "format": format_type,
        "order": "Circuit",
        "focus": f"50% target muscle + 50% general" if target_muscle_id else "General conditioning",
        "target_muscle_id": target_muscle_id,
        "target_muscle_name": target_muscle if target_muscle else "None",
        "exercises": scaled_exercises,
        "time": actual_time,
        "details": f"{stimulus.capitalize()} WOD with format: {format_type}"
    }

    if self.debug:
        result["debug"] = debug_info

