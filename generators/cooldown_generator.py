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

        num_muscle_ex = min(len(muscle_specific_pool), MAX_EXERCISES // 2)
        num_general_ex = MAX_EXERCISES - num_muscle_ex

        selected_muscle = random.sample(muscle_specific_pool, num_muscle_ex) if muscle_specific_pool else []
        selected_general = random.sample(general_pool, num_general_ex) if general_pool else []

        selected = selected_muscle + selected_general
        random.shuffle(selected)

        # Annotate each exercise with whether it's muscle-focused
        focused_ids = {ex["id"] for ex in selected_muscle}
        cooldown_plan = [
            {
                "exercise": ex["name"],
                "duration": COOLDOWN_DURATION,
                "transition": TRANSITION_TIME,
                "focus": "Targeted" if ex["id"] in focused_ids else "General"
            }
            for ex in selected
        ]

        return {
            "type": "Cooldown",
            "muscles": muscles,
            "time": TOTAL_COOLDOWN_TIME,
            "details": f"10-minute cooldown targeting {', '.join(muscles)}",
            "activities": cooldown_plan
        }
