
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
            if week <= 6:
                glutes_or_quads = "Glutes/Hamstrings" if week % 2 != 0 else "Quads"
                chest_or_back = "Chest" if week % 2 != 0 else "Back"
            else:
                glutes_or_quads = "Quads" if week % 2 != 0 else "Glutes/Hamstrings"
                chest_or_back = "Back" if week % 2 != 0 else "Chest"

            mon_stim = "VO2 Max"
            tue_stim = "Lactate Threshold"
            wed_stim = "VO2 Max"
            fri_stim = "Lactate Threshold"
            sat_stim = "Girl/Hero" if week % 2 != 0 else "Anaerobic"

            framework[week] = [
                (glutes_or_quads, chest_or_back, "Shoulders", mon_stim),
                ("Olympic", "Core", "Skill/Weakness", tue_stim),
                ("Shoulders", glutes_or_quads, chest_or_back, wed_stim),
                ("Run", None, None, "Run"),
                (chest_or_back, "Shoulders", glutes_or_quads, fri_stim),
                ("Olympic", "Any", "Core", sat_stim),
                None  # Rest day
            ]
        return framework

    def generate_daily_plan(self, muscles, stimulus="anaerobic", day_type=None):
        """
        day_type: str or None (e.g., 'Run', 'Olympic', 'Skill/Weakness')
        """
        plan = {}
    
        # Always include Warmup
        plan["Warmup"] = self.warmup_gen.generate(muscles)
    
        # Heavy only if day_type is not Run or Olympic
        if day_type not in ["Run", "Olympic", "Skill/Weakness"]:
            plan["Heavy"] = self.heavy_gen.generate(muscles)
    
        # Olympic only if day_type == 'Olympic'
        if day_type == "Olympic":
            plan["Olympic"] = self.olympic_gen.generate()
    
        # Run only if day_type == 'Run'
        if day_type == "Run":
            plan["Run"] = self.run_gen.generate()
    
        # WOD only if stimulus is Girl/Hero or Anaerobic
        if stimulus in ["Girl/Hero", "Anaerobic"]:
            plan["WOD"] = self.wod_gen.generate(target_muscle=muscles[0] if muscles else None, stimulus=stimulus)
    
        # Benchmark WOD only on Saturday or special stimulus
        if stimulus == "Girl/Hero":
            plan["Benchmark"] = self.benchmark_gen.generate()
    
        # Light session: Core if Olympic day, else first muscle
        light_target = "Core" if day_type == "Olympic" else (muscles[0] if muscles else "Core")
        plan["Light"] = self.light_gen.generate(target=light_target)
    
        # Always include Cooldown
        plan["Cooldown"] = self.cooldown_gen.generate(muscles)
    
        # Debug info
        if self.debug:
            plan["Debug"] = {k: v.get("debug", {}) for k, v in plan.items() if isinstance(v, dict)}
    
        return plan

    def generate_full_plan(self):
        framework = self.build_framework()
        full_plan = {}
    
        for week, days in framework.items():
            full_plan[f"Week {week}"] = {}
            for day_index, day_targets in enumerate(days, start=1):
                day_key = f"Day {day_index}"
    
                if day_targets is None:
                    full_plan[f"Week {week}"][day_key] = {"Rest": True, "details": "Rest day"}
                    continue
    
                muscles = [m for m in day_targets[:3] if m and m != "Any"]
                stimulus = day_targets[3]
                day_type = day_targets[0]  # First element indicates primary focus (Run/Olympic/etc.)
    
                daily_plan = self.generate_daily_plan(muscles=muscles, stimulus=stimulus, day_type=day_type)
                full_plan[f"Week {week}"][day_key] = {
                    "muscles": muscles,
                    "stimulus": stimulus,
                    "day_type": day_type,
                    "plan": daily_plan,
                    "estimated_time": self._estimate_total_time(daily_plan)
                }
    
        return full_plan
