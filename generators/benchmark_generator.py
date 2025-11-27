import random

class BenchmarkGenerator:
    def __init__(self, supabase):
        """
        supabase: Supabase client instance
        """
        self.supabase = supabase
        self.wods = self._load_benchmark_wods()

    def _load_benchmark_wods(self):
        response = self.supabase.table("benchmark_wods").select("*").execute()
        return response.data if response.data else []

    def generate(self):
        if not self.wods:
            return {
                "type": "Benchmark",
                "details": "No benchmark WODs available in database.",
                "name": None,
                "description": None,
                "estimated_time": None,
                "levels": {},
                "url": None
            }

        wod = random.choice(self.wods)

        return {
            "type": "Benchmark",
            "name": wod["name"],
            "description": wod["description"],
            "estimated_time": wod["estimated_time"],
            "workout_type": wod["workout_type"],
            "levels": {
                "beginner": wod["beginner"],
                "intermediate": wod["intermediate"],
                "advanced": wod["advanced"],
                "elite": wod["elite"]
            },
            "url": wod["wodwell_url"],
            "details": wod['id']}"
        }
