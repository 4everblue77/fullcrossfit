import random

class WODGenerator:
    def __init__(self, data, debug=False):
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]
        self.categories = data["categories"]
        self.category_mappings = data["category_mappings"]
        self.debug = debug

    def normalize_name(self, value):
        if isinstance(value, list):
            value = value[0]
        if isinstance(value, dict):
            value = value.get("text", "")
        return str(value).lower()

    def get_wod_exercises(self):
        wod_ex_ids = {m["exercise_id"] for m in self.category_mappings if self._is_wod_category(m["category_id"])}
        return [e for e in self.exercises if e["id"] in wod_ex_ids]

    def _is_wod_category(self, category_id):
        cat = next((c for c in self.categories if c["id"] == category_id), None)
        return cat and "wod" in self.normalize_name(cat["name"])

    def _get_target_pool(self, target_muscle):
        if not target_muscle:
            return []
        mg_id = next((mg["id"] for mg in self.muscle_groups if self.normalize_name(mg["name"]) == target_muscle.lower()), None)
        if not mg_id:
            return []
        exercise_ids = {m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id}
        return [e["name"] for e in self.exercises if e["id"] in exercise_ids]

    def _assign_details(self, exercise, format_type, stimulus):
        details = {}
        # Weight logic
        if any(lift in exercise for lift in ["Squat", "Deadlift", "Thruster"]):
            if stimulus == "anaerobic":
                details["weight"] = "Moderate to heavy (70–90% 1RM)"
            elif stimulus == "lactate threshold":
                details["weight"] = "Moderate (60–75% 1RM)"
            else:
                details["weight"] = "Light to moderate (40–60% 1RM)"
            details["reps"] = random.choice([6, 8, 10]) if stimulus == "anaerobic" else random.choice([8, 10, 12])
        elif any(cardio in exercise for cardio in ["Rowing", "Jumping"]):
            details["weight"] = "Bodyweight"
            details["reps"] = "Max effort" if stimulus == "anaerobic" else random.choice([15, 20])
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

    def _determine_order(self, format_type):
        if format_type in ["AMRAP", "Chipper", "For Time"]:
            return "Sequential"
        elif format_type in ["EMOM", "Interval Rounds"]:
            return "Circuit"
        elif format_type in ["Rounds for Time"]:
            return "Superset"
        return "Sequential"

    def _scale_wod_to_time(self, exercises, stimulus):
        min_time, max_time = self._get_time_bounds_for_stimulus(stimulus)
        attempt = 0
        scaled = exercises
        duplicates_added = 0

        while attempt < 5:
            total_time = sum(self._estimate_exercise_time(ex["details"]) for ex in scaled)
            if min_time <= total_time <= max_time:
                return {"exercises": scaled, "time": round(total_time), "duplicates_added": duplicates_added}

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

        return {"exercises": scaled, "time": round(sum(self._estimate_exercise_time(ex["details"]) for ex in scaled)), "duplicates_added": duplicates_added}

    def _get_time_bounds_for_stimulus(self, stimulus):
        stimulus = stimulus.lower()
        if stimulus == "anaerobic":
            return 8, 12
        elif stimulus in ["lactate threshold", "vo2 max"]:
            return 15, 30
        return 15, 20

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

    def generate(self, target_muscle=None, stimulus="anaerobic"):
        formats = {
            "anaerobic": ["For Time", "Sprint Intervals", "Tabata"],
            "lactate threshold": ["AMRAP", "Chipper", "For Time"],
            "vo2 max": ["EMOM", "Interval Rounds", "Rounds for Time"]
        }
        format_type = random.choice(formats.get(stimulus.lower(), ["AMRAP"]))

        full_pool = [e["name"] for e in self.get_wod_exercises()]
        target_pool = self._get_target_pool(target_muscle)

        target_sample = random.sample(target_pool, min(3, len(target_pool))) if target_pool else []
        random_sample = random.sample(full_pool, min(3, len(full_pool)))
        wod_exercises = target_sample + random_sample
        random.shuffle(wod_exercises)

        detailed_exercises = [{"name": ex, "details": self._assign_details(ex, format_type, stimulus)} for ex in wod_exercises]
        scaled_result = self._scale_wod_to_time(detailed_exercises, stimulus.lower())
        scaled_exercises = scaled_result["exercises"]
        actual_time = scaled_result["time"]

        result = {
            "type": "WOD",
            "stimulus": stimulus.capitalize(),
            "duration": f"{actual_time} min",
            "format": format_type,
            "order": self._determine_order(format_type),
            "focus": f"50% {target_muscle} + 50% general" if target_muscle else "General conditioning",
            "exercises": scaled_exercises,
            "time": actual_time,
            "details": f"{stimulus.capitalize()} WOD with format: {format_type}"
        }

        if self.debug:
            result["debug"] = {
                "format": format_type,
                "selected_exercises": wod_exercises,
                "scaled_time": actual_time
            }

        return result
