
import random

class OlympicGenerator:
    # --- 6-week %RM scheme to match heavy progression ---
    TOP_SETS = {
        1: 77,
        2: 80,
        3: 81,
        4: 83,
        5: 85,
        6: 89  # midpoint for the 88–90% range
    }

    BACKOFF_SCHEME = {
        1: {"sets": 3, "reps": 5, "pct": 61},
        2: {"sets": 3, "reps": 5, "pct": 64},
        3: {"sets": 4, "reps": 4, "pct": 66},
        4: {"sets": 4, "reps": 4, "pct": 71},
        5: {"sets": 5, "reps": 3, "pct": 72},
        6: {"sets": 3, "reps": 2, "pct": 80},
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
        return str(value).lower().strip()

    def get_olympic_exercises(self):
        debug_info = {}
        cat_id = next((c["id"] for c in self.categories
                       if self.normalize_name(c["name"]) == "olympic"), None)
        if not cat_id:
            debug_info["error"] = "Olympic category not found"
            return [], debug_info

        olympic_ex_ids = {m["exercise_id"] for m in self.category_mappings
                          if m["category_id"] == cat_id}
        pool = [e for e in self.exercises if e["id"] in olympic_ex_ids]
        debug_info["exercise_ids"] = list(olympic_ex_ids)
        debug_info["pool"] = [e["name"] for e in pool]
        return pool, debug_info

    def get_muscles_for_exercise(self, exercise_id):
        muscle_ids = {m["musclegroup_id"] for m in self.mappings
                      if m["exercise_id"] == exercise_id}
        return [mg["name"] for mg in self.muscle_groups if mg["id"] in muscle_ids]

    def generate(self, week=1):
        pool, debug_info = self.get_olympic_exercises()
        if not pool:
            return {"error": "No Olympic exercises found", "debug": debug_info}

        main_lift = random.choice(pool)
        exercise_id = main_lift["id"]

        # --- Warmups: 40% x5, 55% x3, 70% x1, then 75% (W1-4) or 80% (W5-6) x1 ---
        warmup_base = [
            {"reps": 5, "pct": 40},
            {"reps": 3, "pct": 55},
            {"reps": 1, "pct": 70},
        ]
        warmup_base.append({"reps": 1, "pct": 75 if week <= 4 else 80})

        warmup_sets = [
            {
                "set": i + 1,
                "reps": w["reps"],
                "intensity": f"{w['pct']}%",
                "rest": 60,
                "notes": "Warmup"
            }
            for i, w in enumerate(warmup_base)
        ]

        # --- Top single ---
        top_pct = self.TOP_SETS.get(week, 77)
        top_set = {
            "set": len(warmup_sets) + 1,
            "reps": 1,
            "intensity": f"{top_pct}%",
            "rest": 180,
            "notes": "Working"
        }

        # --- Backoffs (match the agreed progression) ---
        scheme = self.BACKOFF_SCHEME[week]
        backoffs = [
            {
                "set": len(warmup_sets) + 1 + i + 1,
                "reps": scheme["reps"],
                "intensity": f"{scheme['pct']}%",
                "rest": 150,
                "notes": "Working"
            }
            for i in range(scheme["sets"])
        ]

        all_sets = warmup_sets + [top_set] + backoffs

        exercises = []
        for i, s in enumerate(all_sets):
            exercises.append({
                "name": main_lift["name"],
                "exercise_id": exercise_id,
                "set": s["set"],
                "reps": str(s["reps"]),
                "intensity": s["intensity"],
                "rest": s["rest"],
                "notes": s["notes"],
                "tempo": "30X0",       # keep your existing tempo for Olympic lifts
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
            "sets": all_sets,
            "debug": debug_info if self.debug else {}
        }
