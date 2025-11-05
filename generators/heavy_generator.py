import random
import streamlit as st

def debug_info(label, data):
    st.text(f"{label}: {data}")


EXERCISE_DURATION = 30  # seconds per rep estimate for time calculation
TRANSITION_TIME = 5     # seconds between exercises

class HeavyGenerator:
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

    def normalize_name(self, value):
        """Normalize name field to lowercase string."""

        # Unwrap list if needed
        if isinstance(value, list):
            value = value[0]
    
        # Unwrap dict if needed
        if isinstance(value, dict):
            value = value.get("text", "")
    
        # Ensure it's a string before lowering
        return str(value).lower()


    def safe_normalize_compare(self, value, target):
        try:
            normalized = self.normalize_name(value)
            return normalized == target.lower()
        except Exception as e:
            print(f"Normalization error for value: {value} — {e}")
            return False


    def get_exercises_by_muscle_and_type(self, muscle, category_name):
        """Return exercises matching both muscle group and category."""
        


        
        
        mg_id = next(
            (
                mg["id"]
                for mg in self.muscle_groups
                if self.safe_normalize_compare(mg["name"], muscle)
            ),
            None
        )
        
        #mg_id = next((mg["id"] for mg in self.muscle_groups if self.normalize_name(mg["name"]) == muscle.lower()), None)
        if not mg_id:
            return []

        cat_id = next((c["id"] for c in self.categories if self.normalize_name(c["name"]) == category_name.lower()), None)
        if not cat_id:
            return []

        muscle_ex_ids = {m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id}
        category_ex_ids = {m["exercise_id"] for m in self.category_mappings if m["category_id"] == cat_id}

        exercise_ids = muscle_ex_ids.intersection(category_ex_ids)
        pool = [e["name"] for e in self.exercises if e["id"] in exercise_ids]


        debug_info.update({
            "muscle_ex_ids": muscle_ex_ids,
            "category_ex_ids": category_ex_ids,
            "intersection": exercise_ids
        })




        # Fallback if no match found
        if not pool:
            pool = [e["name"] for e in self.exercises]
        return pool, debug_info

    def assign_exercise(self, target):
        pool = self.get_exercises_by_muscle_and_type(target, "Heavy")
        return random.choice(pool) if pool else "No exercise available"

    def generate(self, target, week=1):
        """
        Generate heavy session for a muscle group.
        target: muscle group name
        week: current week number (1-6 for intensity cycle)
        """

        if isinstance(target, list):
            target = target[0]
    
        pool, debug_info = self.get_exercises_by_muscle_and_type(target, "Heavy")

        
        # Intensity progression schedule
        intensity_schedule = {
            1: [60, 65, 70],
            2: [65, 70, 75],
            3: [70, 75, 80],
            4: [75, 80, 85],
            5: [80, 85, 90],
            6: [60, 65, 70]  # deload
        }

        working_intensities = intensity_schedule.get(week, [65, 70, 75])
        warmup_intensities = [
            (0.5 * working_intensities[0], 8),
            (0.7 * working_intensities[0], 6),
            (0.85 * working_intensities[0], 3)
        ]

        warmup_sets = [
            {"set": i + 1, "type": "Warmup", "intensity": round(intensity, 1), "reps": reps, "rest": 60}
            for i, (intensity, reps) in enumerate(warmup_intensities)
        ]

        working_sets = [
            {"set": i + 1, "type": "Working", "intensity": intensity, "reps": 5, "rest": 180}
            for i, intensity in enumerate(working_intensities)
        ]

        exercise = self.assign_exercise(target)

        # Estimate total time (add buffer for transitions)
        def estimate_set_time(reps, rest):
            return (reps * 5 + rest) / 60  # convert to minutes

        total_time = sum(estimate_set_time(s["reps"], s["rest"]) for s in warmup_sets + working_sets)
        total_time = max(20, round(total_time))  # Ensure minimum 20 min session

        return {
            "type": "Heavy",
            "target": target,
            "week": week,
            "exercise": exercise,
            "time": total_time,
            "details": f"Progressive strength session for {target} using {exercise}",
            "sets": warmup_sets + working_sets,
            "debug": debug_info  # ✅ Add debug info here
        }
