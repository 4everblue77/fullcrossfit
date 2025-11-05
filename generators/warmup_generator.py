import random

EXERCISE_DURATION = 30  # seconds
TRANSITION_TIME = 5     # seconds
WARMUP_TIME = 10        # minutes

class WarmupGenerator:
    def __init__(self, data):
        """
        data: dict containing preloaded Supabase tables:
            - exercises
            - muscle_groups
            - mappings (exercise-muscle)
            - categories
            - category_mappings (exercise-category)
        """
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]
        self.categories = data["categories"]
        self.category_mappings = data["category_mappings"]

    def get_general_warmup(self):
        # Find category ID for "general warmup"
        category_id = next((c["id"] for c in self.categories if c["name"].lower() == "general warmup"), None)
        if not category_id:
            return []

        # Get exercise IDs linked to this category
        exercise_ids = [m["exercise_id"] for m in self.category_mappings if m["category_id"] == category_id]

        # Return exercise names
        return [e["name"] for e in self.exercises if e["id"] in exercise_ids]

    def get_exercises_by_muscle(self, muscle):
        # Find muscle group ID
        mg_id = next((mg["id"] for mg in self.muscle_groups if mg["name"] == muscle), None)
        if not mg_id:
            return []

        # Get exercise IDs linked to this muscle group
        exercise_ids = [m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id]

        # Return exercise names
        return [e["name"] for e in self.exercises if e["id"] in exercise_ids]

    def generate(self, muscles):
        # General warmup exercises
        general_pool = self.get_general_warmup()
        general_selected = random.sample(general_pool, min(8, len(general_pool)))

        # Specific warmup exercises
        specific_pool = []
        for muscle in muscles:
            specific_pool.extend(self.get_exercises_by_muscle(muscle))
        specific_selected = random.sample(specific_pool, min(8, len(specific_pool)))

# Combine general and specific into a unified exercises list
        combined_exercises = []

        for i, ex in enumerate(general_selected):
            combined_exercises.append({
                "name": ex,
                "set": 1,
                "reps": f"{EXERCISE_DURATION} sec",
                "intensity": "Low",
                "rest": TRANSITION_TIME,
                "notes": "General warmup"
            })

        for i, ex in enumerate(specific_selected):
            combined_exercises.append({
                "name": ex,
                "set": 1,
                "reps": f"{EXERCISE_DURATION} sec",
                "intensity": "Moderate",
                "rest": TRANSITION_TIME,
                "notes": "Specific warmup"
            })

        return {
            "type": "Warmup",
            "muscles": muscles,
            "time": WARMUP_TIME,
            "details": "10-minute warmup split into general and specific components",
            "general": [{"exercise": ex, "duration": EXERCISE_DURATION, "transition": TRANSITION_TIME} for ex in general_selected],
            "specific": [{"exercise": ex, "duration": EXERCISE_DURATION, "transition": TRANSITION_TIME} for ex in specific_selected],
            "exercises": combined_exercises  # ✅ This enables syncing
        }
