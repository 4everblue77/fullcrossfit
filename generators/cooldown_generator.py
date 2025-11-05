import random

COOLDOWN_DURATION = 55  # seconds per exercise
TRANSITION_TIME = 5     # seconds
TOTAL_COOLDOWN_TIME = 10  # minutes
MAX_EXERCISES = 10

class CooldownGenerator:
    def __init__(self, data):
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]
        self.categories = data["categories"]
        self.category_mappings = data["category_mappings"]

        self.cooldown_category_id = next(
            (c["id"] for c in self.categories if c["name"].lower() == "cooldown"), None
        )

    def get_muscle_specific_cooldowns(self, muscles):
        mg_ids = [mg["id"] for mg in self.muscle_groups if mg["name"] in muscles]
        muscle_ex_ids = {m["exercise_id"] for m in self.mappings if m["musclegroup_id"] in mg_ids}
        category_ex_ids = {m["exercise_id"] for m in self.category_mappings if m["category_id"] == self.cooldown_category_id}
        valid_ex_ids = muscle_ex_ids & category_ex_ids

        return [ex for ex in self.exercises if ex["id"] in valid_ex_ids]

    def get_general_cooldowns(self):
        if not self.cooldown_category_id:
            return []
        category_ex_ids = {m["exercise_id"] for m in self.category_mappings if m["category_id"] == self.cooldown_category_id}
        return [ex for ex in self.exercises if ex["id"] in category_ex_ids]

      def generate(self, muscles):
        muscle_specific_pool = self.get_muscle_specific_cooldowns(muscles)
        general_pool = self.get_general_cooldowns()
    
        # Remove duplicates across pools
        general_pool = [ex for ex in general_pool if ex["id"] not in {e["id"] for e in muscle_specific_pool}]
    
        # Shuffle pools to randomize selection
        random.shuffle(muscle_specific_pool)
        random.shuffle(general_pool)
    
        selected = []
        used_ids = set()
    
        # Select up to half from muscle-specific pool
        for ex in muscle_specific_pool:
            if len(selected) >= MAX_EXERCISES // 2:
                break
            if ex["id"] not in used_ids:
                selected.append((ex, "Targeted"))
                used_ids.add(ex["id"])
    
        # Fill remaining slots from general pool
        for ex in general_pool:
            if len(selected) >= MAX_EXERCISES:
                break
            if ex["id"] not in used_ids:
                selected.append((ex, "General"))
                used_ids.add(ex["id"])
    
        cooldown_plan = [
            {
                "exercise": ex["name"],
                "duration": COOLDOWN_DURATION,
                "transition": TRANSITION_TIME,
                "focus": focus
            }
            for ex, focus in selected
        ]
    
        # ✅ Structured exercises for Supabase syncing
        exercises = [
            {
                "name": item["exercise"],
                "set": i + 1,
                "reps": f"{item['duration']} sec",
                "intensity": "Recovery",
                "rest": item["transition"],
                "notes": f"{item['focus']} cooldown"
            }
            for i, item in enumerate(cooldown_plan)
        ]
    
        return {
            "type": "Cooldown",
            "muscles": muscles,
            "time": TOTAL_COOLDOWN_TIME,
            "details": f"10-minute cooldown targeting {', '.join(muscles)}",
            "activities": cooldown_plan,
            "exercises": exercises  # ✅ Enables syncing
        }
