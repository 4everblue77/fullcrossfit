import random

LIGHT_SETS = 3
LIGHT_REPS = "15–20 reps each @ <60% 1RM"
LIGHT_TIME = 15  # minutes

class LightGenerator:
    def __init__(self, data):
        """
        data: dict containing preloaded Supabase tables:
            - exercises
            - muscle_groups
            - mappings (exercise-muscle)
            - categories
            - category_mappings (exercise-category)
            - exercise_pool (custom pool with type tags)
        """
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]
        self.exercise_pool = data["exercise_pool"]

        # Define opposing muscle group logic
        self.opposing_map = {
            "Chest": "Back",
            "Back": "Chest",
            "Quads": "Glutes_Hamstrings",
            "Glutes_Hamstrings": "Quads",
            "Shoulders": "Core",
            "Core": "Shoulders"
        }

    def get_light_exercises(self, group_name):
        # Filter pool by group and type
        return [
            ex["name"] for ex in self.exercise_pool
            if ex.get("muscle_group") == group_name and "Light" in ex.get("types", [])
        ]

    def generate(self, target):
        primary_pool = self.get_light_exercises(target)
        opposing_group = self.opposing_map.get(target, target)
        opposing_pool = self.get_light_exercises(opposing_group)

        supersets = []
        for _ in range(3):
            ex1 = random.choice(primary_pool) if primary_pool else "Placeholder"
            ex2 = random.choice(opposing_pool) if opposing_pool else "Placeholder"
            supersets.append({
                "Superset": f"{ex1} + {ex2}",
                "Sets": LIGHT_SETS,
                "Reps": LIGHT_REPS
            })

        return {
            "type": "Light",
            "target": target,
            "time": LIGHT_TIME,
            "details": f"3 supersets targeting {target} with opposing muscle activation",
            "supersets": supersets
        }
