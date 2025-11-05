from generators.warmup_generator import WarmupGenerator
# Future imports:
# from generators.heavy_generator import HeavyGenerator
# from generators.cooldown_generator import CooldownGenerator
# from generators.wod_generator import WODGenerator
# from generators.light_generator import LightGenerator

class PlanGenerator:
    def __init__(self, supabase):
        self.supabase = supabase
        self.data = self._load_data()

        # Initialize generators with preloaded data
        self.warmup_gen = WarmupGenerator(self.data)
        self.heavy_gen = HeavyGenerator(self.data)
        # self.cooldown_gen = CooldownGenerator(self.data)
        # self.wod_gen = WODGenerator(self.data)
        # self.light_gen = LightGenerator(self.data)

    def _load_data(self):
        """Fetch all required tables from Supabase once."""
        return {
            "exercises": self.supabase.table("md_exercises").select("*").execute().data,
            "muscle_groups": self.supabase.table("md_muscle_groups").select("*").execute().data,
            "mappings": self.supabase.table("md_map_exercise_muscle_groups").select("*").execute().data,
            "categories": self.supabase.table("md_categories").select("*").execute().data,
            "category_mappings": self.supabase.table("md_map_exercise_categories").select("*").execute().data
        }

    def generate_daily_plan(self, muscles):
        """Build a daily plan using all generators."""
        return {
            "Warmup": self.warmup_gen.generate(muscles),
            "Heavy": self.heavy_gen.generate(muscles),
            # "WOD": self.wod_gen.generate(muscles),
            # "Light": self.light_gen.generate(muscles),
            # "Cooldown": self.cooldown_gen.generate(muscles)
        }
