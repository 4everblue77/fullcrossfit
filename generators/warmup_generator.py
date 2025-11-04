import random

class WarmupGenerator:
    def __init__(self, data):
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]

    def generate(self, muscles):
        # Use self.exercises and self.mappings instead of Supabase calls
        general_pool = [e["name"] for e in self.exercises]
        general_selected = random.sample(general_pool, min(8, len(general_pool)))

        specific_pool = []
        for muscle in muscles:
            mg_id = next((mg["id"] for mg in self.muscle_groups if mg["name"] == muscle), None)
            if mg_id:
                exercise_ids = [m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id]
                specific_pool.extend([e["name"] for e in self.exercises if e["id"] in exercise_ids])

        specific_selected = random.sample(specific_pool, min(8, len(specific_pool)))

        return {
            "type": "Warmup",
            "muscles": muscles,
            "time": 10,
            "details": "10-minute warmup split into general and specific components",
            "general": [{"exercise": ex, "duration": 30, "transition": 5} for ex in general_selected],
            "specific": [{"exercise": ex, "duration": 30, "transition": 5} for ex in specific_selected]
        }
