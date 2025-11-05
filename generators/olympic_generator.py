import random

class OlympicGenerator:
    INTENSITY_SCHEDULE = {
        1: [60, 65],
        2: [65, 70],
        3: [70, 75],
        4: [75, 80],
        5: [85, 90],
        6: [60, 65]
    }

    def __init__(self, data, debug=False):
        self.exercises = data["exercises"]
        self.categories = data["categories"]
        self.category_mappings = data["category_mappings"]
        self.mappings = data["mappings"]
        self.muscle_groups = data["muscle_groups"]
        self.debug = debug

    def normalize_name(self, value):
        if isinstance(value, list):
            value = value[0]
        if isinstance(value, dict):
            value = value.get("text", "")
        return str(value).lower()

    def get_olympic_exercises(self):
        debug_info = {}
        cat_id = next((c["id"] for c in self.categories if self.normalize_name(c["name"]) == "olympic"), None)
        if not cat_id:
            debug_info["error"] = "Olympic category not found"
            return [], debug_info

        olympic_ex_ids = {m["exercise_id"] for m in self.category_mappings if m["category_id"] == cat_id}
        pool = [e for e in self.exercises if e["id"] in olympic_ex_ids]

        debug_info["exercise_ids"] = list(olympic_ex_ids)
        debug_info["pool"] = [e["name"] for e in pool]

        return pool, debug_info

    def get_muscles_for_exercise(self, exercise_id):
        muscle_ids = {m["musclegroup_id"] for m in self.mappings if m["exercise_id"] == exercise_id}
        return [mg["name"] for mg in self.muscle_groups if mg["id"] in muscle_ids]

    def generate(self, week=1):
        pool, debug_info = self.get_olympic_exercises()
        if not pool:
            return {"error": "No Olympic exercises found", "debug": debug_info}

        main_lift = random.choice(pool)
        exercise_id = main_lift["id"]
        intensity_range = self.INTENSITY_SCHEDULE.get(week, [65, 70])

        warmup_sets = [
            {"set": 1, "reps": 5, "intensity": intensity_range[0] - 20, "rest": 60, "notes": "Warmup"},
            {"set": 2, "reps": 3, "intensity": intensity_range[0] - 10, "rest": 60, "notes": "Warmup"}
        ]
        working_sets = [
            {"set": i + 1, "reps": 3, "intensity": intensity, "rest": 120, "notes": "Working"}
            for i, intensity in enumerate(intensity_range)
        ]

        exercises = []
        for i, s in enumerate(warmup_sets + working_sets):
            exercises.append({
                "name": main_lift["name"],
                "exercise_id": exercise_id,
                "set": s["set"],
                "reps": str(s["reps"]),
                "intensity": f"{s['intensity']}%",
                "rest": s["rest"],
                "notes": s["notes"],
                "tempo": "30X0",
                "expected_weight": "",
                "equipment": "Barbell",
                "exercise_order": i + 1
            })

        muscles = set(self.get_muscles_for_exercise(exercise_id))

        return {
            "type": "Olympic",
            "week": week,
            "exercise": main_lift["name"],
            "muscles": list(muscles),
            "time": 20,
            "details": f"Olympic lifting session focusing on {main_lift['name']}",
            "exercises": exercises,
            "sets": warmup_sets + working_sets,
            "debug": debug_info if self.debug else {}
        }
