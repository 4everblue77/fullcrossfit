import random

class HeavyGenerator:
    def __init__(self, data):
        """
        data: dict containing preloaded Supabase tables:
            - exercises
            - muscle_groups
            - mappings (exercise-muscle)
        """
        self.exercises = data["exercises"]
        self.muscle_groups = data["muscle_groups"]
        self.mappings = data["mappings"]

    def get_exercises_by_muscle(self, muscle):
        mg_id = next((mg["id"] for mg in self.muscle_groups if mg["name"] == muscle), None)
        if not mg_id:
            return []
        exercise_ids = [m["exercise_id"] for m in self.mappings if m["musclegroup_id"] == mg_id]
        return [e["name"] for e in self.exercises if e["id"] in exercise_ids]

    def assign_exercise(self, target):
        pool = self.get_exercises_by_muscle(target)
        return random.choice(pool) if pool else "No exercise available"

    def generate(self, target, week):
        """
        target: muscle group or 'Olympic'
        week: current week number (1-6 for intensity cycle)
        """
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

        # Estimate total time
        def estimate_set_time(reps, rest):
            return (reps * 5 + rest) / 60  # convert to minutes

        total_time = sum(estimate_set_time(s["reps"], s["rest"]) for s in warmup_sets + working_sets)

        return {
            "type": "Heavy",
            "target": target,
            "week": week,
            "exercise": exercise,
            "time": round(total_time),
            "details": f"Progressive strength session for {target} using {exercise}",
            "sets": warmup_sets + working_sets
        }
