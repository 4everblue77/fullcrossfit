import random

EXERCISE_DURATION = 30  # seconds per rep estimate for time calculation
TRANSITION_TIME = 5     # seconds between exercises


class HeavyGenerator:
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
        return str(value).lower().replace("_", "/").strip()

    def get_exercises_by_muscle_and_type(self, muscle, category_name):
        mg_id = next((mg["id"] for mg in self.muscle_groups
                      if self.normalize_name(mg["name"]) == muscle.lower()), None)

        if not mg_id:
            return [], {"error": "Muscle group not found"}

        cat_id = next((c["id"] for c in self.categories
                       if self.normalize_name(c["name"]) == category_name.lower()), None)

        if not cat_id:
            return [], {"error": "Category not found"}

        muscle_ex_ids = {m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id}
        category_ex_ids = {m["exercise_id"] for m in self.category_mappings if m["category_id"] == cat_id}

        exercise_ids = muscle_ex_ids.intersection(category_ex_ids)
        pool = [e["name"] for e in self.exercises if e["id"] in exercise_ids]

        if not pool:
            pool = [e["name"] for e in self.exercises]

        return pool, {}

    # NEW 6-week %RM scheme
    TOP_SETS = {
        1: 77,
        2: 80,
        3: 81,
        4: 83,
        5: 85,
        6: 89  # use midpoint of 88–90
    }

    BACKOFF_SCHEME = {
        1: {"sets": 3, "reps": 5, "pct": 61},
        2: {"sets": 3, "reps": 5, "pct": 64},
        3: {"sets": 4, "reps": 4, "pct": 66},
        4: {"sets": 4, "reps": 4, "pct": 71},
        5: {"sets": 5, "reps": 3, "pct": 72},
        6: {"sets": 3, "reps": 2, "pct": 80},
    }

    def generate(self, target, week=1):
        if isinstance(target, list):
            target = target[0]

        pool, debug_info = self.get_exercises_by_muscle_and_type(target, "Heavy")
        exercise_name = random.choice(pool) if pool else "No exercise available"
        exercise_id = next((e["id"] for e in self.exercises if e["name"] == exercise_name), None)

        # Warmup logic
        warmup_base = [
            {"reps": 5, "pct": 40},
            {"reps": 3, "pct": 55},
            {"reps": 1, "pct": 70},
        ]

        if week <= 4:
            warmup_base.append({"reps": 1, "pct": 75})
        else:
            warmup_base.append({"reps": 1, "pct": 80})

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

        # Top set
        top_pct = self.TOP_SETS.get(week, 77)
        top_set = {
            "set": len(warmup_sets) + 1,
            "reps": 1,
            "intensity": f"{top_pct}%",
            "rest": 180,
            "notes": "Working"
        }

        # Backoff sets
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
                "name": exercise_name,
                "exercise_id": exercise_id,
                "set": s["set"],
                "reps": str(s["reps"]),
                "intensity": s["intensity"],
                "rest": s["rest"],
                "notes": s["notes"],
                "tempo": "20X0",
                "expected_weight": "",
                "equipment": "Barbell",
                "exercise_order": i + 1
            })

        return {
            "type": "Heavy",
            "target": target,
            "week": week,
            "exercise": exercise_name,
            "time": 20,
            "details": f"Progressive heavy session for {target} using {exercise_name}",
            "exercises": exercises,
            "sets": all_sets,
            "debug": debug_info if self.debug else {}
       
