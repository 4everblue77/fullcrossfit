class PlanGenerator:
    def __init__(self, supabase):
        self.supabase = supabase
        self.data = self._load_data()
        self.warmup_gen = WarmupGenerator(self.data)

    def _load_data(self):
        return {
            "exercises": self.supabase.table("md_exercises").select("*").execute().data,
            "muscle_groups": self.supabase.table("md_muscle_groups").select("*").execute().data,
            "mappings": self.supabase.table("md_map_exercise_muscle_groups").select("*").execute().data,
            "categories": self.supabase.table("md_categories").select("*").execute().data,
            "category_mappings": self.supabase.table("md_map_exercise_categories").select("*").execute().data
        }

    def generate_daily_plan(self, muscles):
        return {
            "Warmup": self.warmup_gen.generate(muscles)
        }
