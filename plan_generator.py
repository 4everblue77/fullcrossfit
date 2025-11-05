
from generators.warmup_generator import WarmupGenerator
from generators.heavy_generator import HeavyGenerator
from generators.olympic_generator import OlympicGenerator
from generators.run_generator import RunGenerator
from generators.wod_generator import WODGenerator
from generators.benchmark_generator import BenchmarkGenerator
from generators.light_generator import LightGenerator
from generators.cooldown_generator import CooldownGenerator
from generators.skillsession_generator import SkillSessionGenerator

class PlanGenerator:
    def __init__(self, supabase, debug=False):
        self.supabase = supabase
        self.data = self._load_data()
        self.debug = debug

        # Initialize generators
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
        return {
            "exercises": self.supabase.table("md_exercises").select("*").execute().data,
            "muscle_groups": self.supabase.table("md_muscle_groups").select("*").execute().data,
            "mappings": self.supabase.table("md_map_exercise_muscle_groups").select("*").execute().data,
            "categories": self.supabase.table("md_categories").select("*").execute().data,
            "category_mappings": self.supabase.table("md_map_exercise_categories").select("*").execute().data,
            "exercise_pool": self.supabase.table("exercise_pool").select("*").execute().data
        }

    def _estimate_total_time(self, daily_plan):
        total = 0
        for block in daily_plan.values():
            if isinstance(block, dict) and "time" in block:
                total += block["time"]
        return total

    def build_framework(self):
        framework = {}
        for week in range(1, 13):
            # Alternating logic
            if week <= 6:
                glutes_or_quads = "Glutes_Hamstrings" if week % 2 != 0 else "Quads"
                chest_or_back = "Chest" if week % 2 != 0 else "Back"
            else:
                glutes_or_quads = "Quads" if week % 2 != 0 else "Glutes_Hamstrings"
                chest_or_back = "Back" if week % 2 != 0 else "Chest"
    
            # Stimulus
            mon_stim = "VO2 Max"
            tue_stim = "Lactate Threshold"
            wed_stim = "VO2 Max"
            thu_stim = None
            fri_stim = "VO2 Max"
            sat_stim = "Girl/Hero" if week % 2 != 0 else "Anaerobic"
    
            framework[week] = [
                # Monday
                {"day": "Mon", "heavy": [glutes_or_quads], "wod": [chest_or_back], "stimulus": mon_stim, "light": ["Shoulders"], "olympic": False, "skill": False, "run": False},
                # Tuesday
                {"day": "Tue", "heavy": [], "wod": ["Core"], "stimulus": tue_stim, "light": [], "olympic": True, "skill": True, "run": False},
                # Wednesday
                {"day": "Wed", "heavy": ["Shoulders"], "wod": [glutes_or_quads], "stimulus": wed_stim, "light": [chest_or_back], "olympic": False, "skill": False, "run": False},
                # Thursday
                {"day": "Thu", "heavy": [], "wod": [], "stimulus": thu_stim, "light": [], "olympic": False, "skill": False, "run": True},
                # Friday
                {"day": "Fri", "heavy": [chest_or_back], "wod": ["Shoulders"], "stimulus": fri_stim, "light": [glutes_or_quads], "olympic": False, "skill": False, "run": False},
                # Saturday
                {"day": "Sat", "heavy": [], "wod": [], "stimulus": sat_stim, "light": [glutes_or_quads], "olympic": True, "skill": False, "run": False},
                # Sunday
                None
            ]
        return framework

    def generate_daily_plan(self, config, week_number):
        if config is None:
            return {"Rest Day": "No workout scheduled"}
    
        plan = {}
        muscles = list(set(config["heavy"] + config["wod"] + config["light"]))
    
        # Always Warmup
        plan["Warmup"] = self.warmup_gen.generate(muscles)
    
        # Heavy only if heavy list is not empty
        if config["heavy"]:
            plan["Heavy"] = self.heavy_gen.generate(config["heavy"])
    
        # Olympic only if flag is True
        if config["olympic"]:
            plan["Olympic"] = self.olympic_gen.generate()
    
        # Run only if flag is True
        if config["run"]:
            plan["Run"] = self.run_gen.generate()
    
        # WOD only if wod list and stimulus exist
        if config["wod"] and config["stimulus"]:
            plan["WOD"] = self.wod_gen.generate(target_muscle=config["wod"][0], stimulus=config["stimulus"])
    
        # Benchmark only if stimulus is Girl/Hero
        if config["stimulus"] == "Girl/Hero":
            plan["Benchmark"] = self.benchmark_gen.generate()
    
        # Light session: Core if Olympic day else config["light"]
        light_target = "Core" if config["olympic"] else (config["light"][0] if config["light"] else "Core")
        plan["Light"] = self.light_gen.generate(target=light_target)
    
        # Skill only if flag is True
        if config["skill"]:
            plan["Skill"] = self.skill_gen.generate("Handstand Push-Up", week_number)
    
        # Always Cooldown
        plan["Cooldown"] = self.cooldown_gen.generate(muscles)
    
        # Total time
        plan["Total Time"] = f"{self._estimate_total_time(plan)} min"
    
        return plan

    def generate_full_plan(self):
        framework = self.build_framework()
        full_plan = {}
    
        for week, days in framework.items():
            full_plan[f"Week {week}"] = {}
            for day_config in days:
                if day_config is None:
                    full_plan[f"Week {week}"][day_config] = {"Rest": True, "details": "Rest day"}
                    continue
    
                daily_plan = self.generate_daily_plan(day_config, week)
                full_plan[f"Week {week}"][day_config["day"]] = daily_plan
    
        return full_plan
