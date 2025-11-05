from generators.warmup_generator import WarmupGenerator
from generators.heavy_generator import HeavyGenerator
from generators.olympic_generator import OlympicGenerator
from generators.run_generator import RunGenerator
from generators.wod_generator import WODGenerator
from generators.benchmark_generator import BenchmarkGenerator
from generators.light_generator import LightGenerator
from generators.cooldown_generator import CooldownGenerator
from generators.skill_session_generator import SkillSessionGenerator



class PlanGenerator:
    def __init__(self, supabase, debug=False):
        self.supabase = supabase
        self.data = self._load_data()
        self.debug = debug

        # Initialize generators with preloaded data
        self.warmup_gen = WarmupGenerator(self.data)
        self.heavy_gen = HeavyGenerator(self.data, debug=debug)
        self.olympic_gen = OlympicGenerator(self.data, debug=debug)
        self.run_gen = RunGenerator(user_5k_time=24, debug=debug)
        self.wod_gen = WODGenerator(self.data, debug=debug)
        self.benchmark_gen = BenchmarkGenerator(supabase)
        self.light_gen = LightGenerator(self.data)
        self.cooldown_gen = CooldownGenerator(self.data)
        self.skill_gen = SkillSessionGenerator(supabase)


    def _load_data(self):
        """Fetch all required tables from Supabase once."""
        return {
            "exercises": self.supabase.table("md_exercises").select("*").execute().data,
            "muscle_groups": self.supabase.table("md_muscle_groups").select("*").execute().data,
            "mappings": self.supabase.table("md_map_exercise_muscle_groups").select("*").execute().data,
            "categories": self.supabase.table("md_categories").select("*").execute().data,
            "category_mappings": self.supabase.table("md_map_exercise_categories").select("*").execute().data,
            "exercise_pool": self.supabase.table("exercise_pool").select("*").execute().data
        }

    def generate_daily_plan(self, muscles, stimulus="anaerobic"):
        """Build a daily plan using all generators."""
        heavy_session = self.heavy_gen.generate(muscles)
        olympic_session = self.olympic_gen.generate()
        run_session = self.run_gen.generate()
        wod_session = self.wod_gen.generate(target_muscle=muscles[0] if muscles else None,  stimulus=stimulus)
        benchmark_session = self.benchmark_gen.generate()
        light_session = self.light_gen.generate(target=muscles[0] if muscles else "Core")
        skill_session = self.skill_gen.generate(skill_name="Handstand Push-Up", week=3)
        cooldown_session = self.cooldown_gen.generate(muscles)


        return {
            "Warmup": self.warmup_gen.generate(muscles),

            "Heavy": heavy_session,
            "Olympic": olympic_session,
            "Run": run_session,  
            "WOD": wod_session,
            "Benchmark": benchmark_session,
            "Light": light_session,
            "Cooldown": cooldown_session,
            "Debug": {
                

                "Heavy": heavy_session.get("debug", {}),
                "Olympic": olympic_session.get("debug", {}),
                "Run": run_session.get("debug", {}),
                "WOD": wod_session.get("debug", {}),
                "Benchmark": benchmark_wod if self.debug else {}
            } if self.debug else {}

            # "WOD": self.wod_gen.generate(muscles),
            # "Light": self.light_gen.generate(muscles),
            # "Cooldown": self.cooldown_gen.generate(muscles)
        }
