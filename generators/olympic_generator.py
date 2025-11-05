import random

class OlympicGenerator:
    INTENSITY_SCHEDULE = {
        1: [70, 75],
        2: [75, 80],
        3: [80, 85],
        4: [85, 90],
        5: [90, 95],  # Peak
        6: [65, 70]   # Deload
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
                "exercise": main_lift["name"],
                "intensity": intensity_range[0] - 10,
                "reps": 3,
                "rest": 60
            }
        ]
    
        working_sets = [
            {
                "set": i + 1,
                "type": "Working",
                "exercise": main_lift["name"],
                "intensity": intensity,
                "reps": 3,
                "rest": 120
            }
            for i, intensity in enumerate(intensity_range)
        ]
    
        muscles = set(self.get_muscles_for_exercise(main_lift["id"]))
    
        # ✅ Format for Supabase syncing
        exercises = []
        for s in warmup_sets + working_sets:
            exercises.append({
                "name": s["exercise"],
                "set": s["set"],
                "reps": str(s["reps"]),
                "intensity": f"{s['intensity']}%",
                "rest": s["rest"],
                "notes": s["type"]
            })
    
        result = {
            "type": "Olympic",
            "week": week,
            "exercise": main_lift["name"],
            "muscles": list(muscles),
            "time": 20,
            "details": f"Olympic lifting session focusing on {main_lift['name']}",
            "sets": warmup_sets + working_sets,
            "exercises": exercises  # ✅ Enables syncing
        }
    
        if self.debug:
            result["debug"] = debug_info
    
        return result
