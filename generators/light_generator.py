
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
        """
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]
        self.categories = data["categories"]
        self.category_mappings = data["category_mappings"]

        # Opposing muscle group map for supersets
        self.opposing_map = {
            "Chest": "Back",
            "Back": "Chest",
            "Quads": "Glutes/Hamstrings",
            "Glutes/Hamstrings": "Quads",
            "Shoulders": "Core",
            "Core": "Shoulders"
        }

        # Get category ID for "Muscular Endurance"
        self.light_category_id = next(
            (c["id"] for c in self.categories if c["name"].lower() == "muscular endurance"), None
        )

    def get_light_exercises_by_muscle(self, muscle_name):
        """Return exercises for a muscle group filtered by 'Muscular Endurance' category."""
        mg_id = next((mg["id"] for mg in self.muscle_groups if mg["name"] == muscle_name), None)
        if not mg_id or not self.light_category_id:
            return []

        # Get exercise IDs mapped to both muscle group and category
        muscle_ex_ids = {m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id}
        category_ex_ids = {m["exercise_id"] for m in self.category_mappings if m["category_id"] == self.light_category_id}

        valid_ex_ids = muscle_ex_ids & category_ex_ids
        return [ex for ex in self.exercises if ex["id"] in valid_ex_ids]

    def generate(self, target):
        """Generate a light session with 3 supersets of 2 exercises (primary + opposing)."""
        primary_pool = self.get_light_exercises_by_muscle(target)
        opposing_group = self.opposing_map.get(target, target)
        opposing_pool = self.get_light_exercises_by_muscle(opposing_group)

        
        # ✅ Pick two exercises ONCE
        ex1 = random.choice(primary_pool) if primary_pool else {"name": f"No match for {target}", "id": None}
        ex2 = random.choice(opposing_pool) if opposing_pool else {"name": f"No match for {opposing_group}", "id": None}


        supersets = []
        exercises = []


        supersets.append({
            "Superset": f"{ex1['name']} + {ex2['name']}",
            "Sets": LIGHT_SETS,
            "Reps": LIGHT_REPS
        })

        # ✅ Add each set for both exercises
        for set_num in range(1, LIGHT_SETS + 1):
            exercises.append({
                "exercise_name": ex1["name"],
                "exercise_id": ex1["id"],
                "set_number": set_num,
                "reps": LIGHT_REPS,
                "intensity": "<60% 1RM",
                "rest": 30,
                "notes": f"Set {set_num} - Primary ({target})"
                "exercise_order": len(exercises) + 1,
                "tempo": "2010",
                "expected_weight": "",
                "equipment": ""
            })

        for set_num in range(1, LIGHT_SETS + 1):
            exercises.append({
                "exercise_name": ex2["name"],
                "exercise_id": ex2["id"],
                "set_number": set_num,
                "reps": LIGHT_REPS,
                "intensity": "<60% 1RM",
                "rest": 30,
                "notes": f"Superset {i} - Opposing ({opposing_group})",
                "exercise_order": len(exercises) + 1,
                "tempo": "2010",
                "expected_weight": "",
                "equipment": ""
            })

        return {
            "type": "Light",
            "target": target,
            "time": LIGHT_TIME,
            "details": f"3 supersets targeting {target} with opposing muscle activation",
            "supersets": supersets,
            "exercises": exercises  # ✅ Each set is its own row for Supabase sync
        }
