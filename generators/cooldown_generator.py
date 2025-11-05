import random

COOLDOWN_DURATION = 55  # seconds per exercise
TRANSITION_TIME = 5     # seconds
TOTAL_COOLDOWN_TIME = 10  # minutes

class CooldownGenerator:
    def __init__(self, data):
        """
        data: dict containing preloaded Supabase tables:
            - exercises
            - muscle_groups
            - mappings (exercise-muscle)
            - categories
            - category_mappings
        """
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]
        self.categories = data["categories"]
        self.category_mappings = data["category_mappings"]

    def get_cooldown_exercises_by_muscle(self, muscle_name):
        # Find muscle group ID
        mg_id = next((mg["id"] for mg in self.muscle_groups if mg["name"] == muscle_name), None)
        if not mg_id:
            return []

        # Get exercise IDs linked to this muscle group
        exercise_ids = [m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id]

        return [e["name"] for e in self.exercises if e["id"] in exercise_ids and "Cooldown" in (e.get("types") or [])]

    def get_general_cooldown_exercises(self):
        # Find category ID for "Cooldown"
        category_id = next((c["id"] for c in self.categories if c["name"].lower() == "cooldown"), None)
        if not category_id:
            return []

        # Get exercise IDs linked to this category
        exercise_ids = [m["exercise_id"] for m in self.category_mappings if m["category_id"] == category_id]

        return [e["name"] for e in self.exercises if e["id"] in exercise_ids]

    def generate(self, muscles):
        pool = []

        # Add muscle-specific cooldowns
        for muscle in muscles:
            pool.extend(self.get_cooldown_exercises_by_muscle(muscle))

        # Add general cooldowns
        pool.extend(self.get_general_cooldown_exercises())

        selected = random.sample(pool, min(10, len(pool)))

        cooldown_plan = [
            {"exercise": ex, "duration": COOLDOWN_DURATION, "transition": TRANSITION_TIME}
            for ex in selected
        ]

        return {
            "type": "Cooldown",
            "muscles": muscles,
            "time": TOTAL_COOLDOWN_TIME,
            "details": f"10-minute cooldown targeting {', '.join(muscles)}",
            "activities": cooldown_plan
        }
