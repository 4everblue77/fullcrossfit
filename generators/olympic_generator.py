import random

class OlympicGenerator:
    INTENSITY_SCHEDULE = {
        1: [60, 65],
        2: [65, 70],
        3: [70, 75],
        4: [75, 80],
        5: [85, 90],  # Peak
        6: [60, 65],  # Deload
        7: [70, 75],
        8: [75, 80],
        9: [80, 85],
        10: [85, 90],
        11: [90, 95],  # Peak
        12: [65, 70]   # Deload
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

        # Pick main lift and variations
        main_lift = random.choice(pool)
        variations = [e for e in pool if e["id"] != main_lift["id"]]

        intensity_range = self.INTENSITY_SCHEDULE.get(week, [65, 70])

        warmup_sets = [
            {
                "set": 1,
                "type": "Warmup",
                "exercise": main_lift["name"],
                "intensity": intensity_range[0] - 20,
                "reps": 5,
                "rest": 60
            },
            {
                "set": 2,
                "type": "Warmup",
                "exercise": random.choice(variations)["name"] if variations else main_lift["name"],
                "intensity": intensity_range[0] - 10,
                "reps": 3,
                "rest": 60
            }
        ]

        working_sets = [
            {
                "set": i + 1,
                "type": "Working",
                "exercise": random.choice([main_lift] + variations)["name"],
                "intensity": intensity,
                "reps": 3,
                "rest": 120
            }
            for i, intensity in enumerate(intensity_range)
        ]

        # Collect muscles
        muscles = set()
        for s in warmup_sets + working_sets:
            ex_id = next((e["id"] for e in pool if e["name"] == s["exercise"]), None)
            if ex_id:
                muscles.update(self.get_muscles_for_exercise(ex_id))

        result = {
            "type": "Olympic",
            "week": week,
            "exercise": main_lift["name"],
            "muscles": list(muscles),
            "time": 20,
            "details": f"Olympic lifting session focusing on {main_lift['name']}",
            "sets": warmup_sets + working_sets
        }

        if self.debug:
            result["debug"] = debug_info

        return result
