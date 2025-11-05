import random

EXERCISE_DURATION = 30  # seconds per rep estimate for time calculation
TRANSITION_TIME = 5     # seconds between exercises

class HeavyGenerator:
    def __init__(self, data, debug=False):
        """
        data: dict containing preloaded Supabase tables:
            - exercises
            - muscle_groups
            - mappings (exercise-muscle)
            - categories
            - category_mappings (exercise-category)
        debug: bool to enable debug info
        """
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]
        self.categories = data["categories"]
        self.category_mappings = data["category_mappings"]
        self.debug = debug

    def normalize_name(self, value):
        """Normalize name field to lowercase string."""
        if isinstance(value, list):
            value = value[0]
        if isinstance(value, dict):
            value = value.get("text", "")
        return return str(value).lower().replace("_", "/").strip()

    def get_exercises_by_muscle_and_type(self, muscle, category_name):
        debug_info = {
            "muscle": muscle,
            "mg_names": [self.normalize_name(mg["name"]) for mg in self.muscle_groups],
            "category_names": [self.normalize_name(c["name"]) for c in self.categories]
        }

        mg_id = next((mg["id"] for mg in self.muscle_groups if self.normalize_name(mg["name"]) == muscle.lower()), None)
        if not mg_id:
            debug_info["error"] = "Muscle group not found"
            return [], debug_info

        cat_id = next((c["id"] for c in self.categories if self.normalize_name(c["name"]) == category_name.lower()), None)
        if not cat_id:
            debug_info["error"] = "Category not found"
            return [], debug_info

        muscle_ex_ids = {m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id}
        category_ex_ids = {m["exercise_id"] for m in self.category_mappings if m["category_id"] == cat_id}
        exercise_ids = muscle_ex_ids.intersection(category_ex_ids)

        debug_info.update({
            "muscle_ex_ids": list(muscle_ex_ids),
            "category_ex_ids": list(category_ex_ids),
            "intersection": list(exercise_ids)
        })

        pool = [e["name"] for e in self.exercises if e["id"] in exercise_ids]
        if not pool:
            pool = [e["name"] for e in self.exercises]

        return pool, debug_info

    def generate(self, target, week=1):
        if isinstance(target, list):
            target = target[0]

        pool, debug_info = self.get_exercises_by_muscle_and_type(target, "Heavy")
        exercise = random.choice(pool) if pool else "No exercise available"

        intensity_schedule = {
            1: [60, 65, 70],
            2: [65, 70, 75],
            3: [70, 75, 80],
            4: [75, 80, 85],
            5: [80, 85, 90],
            6: [60, 65, 70]  # deload
        }

        working_intensities = intensity_schedule.get(week, [65, 70, 75])
        warmup_intensities = [
            (0.5 * working_intensities[0], 8),
            (0.7 * working_intensities[0], 6),
            (0.85 * working_intensities[0], 3)
        ]

        warmup_sets = [
            {"set": i + 1, "type": "Warmup", "intensity": round(intensity, 1), "reps": reps, "rest": 60}
            for i, (intensity, reps) in enumerate(warmup_intensities)
        ]

        working_sets = [
            {"set": i + 1, "type": "Working", "intensity": intensity, "reps": 5, "rest": 180}
            for i, intensity in enumerate(working_intensities)
        ]

        def estimate_set_time(reps, rest):
            return (reps * 5 + rest) / 60  # convert to minutes

        total_time = sum(estimate_set_time(s["reps"], s["rest"]) for s in warmup_sets + working_sets)
        total_time = max(20, round(total_time))

        
        # Convert sets into unified exercise format
        exercises = []
        for s in warmup_sets + working_sets:
            exercises.append({
                "name": exercise,
                "set": s["set"],
                "reps": str(s["reps"]),
                "intensity": f"{s['intensity']}%",
                "rest": s["rest"],
                "notes": s["type"]
            })


        result = {
            "type": "Heavy",
            "target": target,
            "week": week,
            "exercise": exercise,
            "time": total_time,
            "details": f"Progressive strength session for {target} using {exercise}",
            "sets": warmup_sets + working_sets,
            "exercises": exercises
        }

        if self.debug:
            result["debug"] = debug_info

        return result
