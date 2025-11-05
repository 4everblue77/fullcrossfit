
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
                glutes_or_quads = "Glutes_Hamstrings" if week % 2 != 0 else "Quads"
                chest_or_back = "Chest" if week % 2 != 0 else "Back"
            else:
                glutes_or_quads = "Quads" if week % 2 != 0 else "Glutes_Hamstrings"
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

    def generate_daily_plan(self, muscles, stimulus="anaerobic"):
        heavy_session = self.heavy_gen.generate(muscles)
        olympic_session = self.olympic_gen.generate()
        run_session = self.run_gen.generate()
        wod_session = self.wod_gen.generate(target_muscle=muscles[0] if muscles else None, stimulus=stimulus)
        benchmark_session = self.benchmark_gen.generate()
        light_session = self.light_gen.generate(target=muscles[0] if muscles else "Core")
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
                "Benchmark": benchmark_session if self.debug else {},
                "Light": light_session if self.debug else {},
                "Cooldown": cooldown_session if self.debug else {}
            } if self.debug else {}
        }

    def generate_full_plan(self):
        framework = self.build_framework()
        full_plan = {}

        for week, days in framework.items():
            full_plan[f"Week {week}"] = {}
            for day_index, day_targets in enumerate(days, start=1):
                day_key = f"Day {day_index}"

                if day_targets is None:
                    full_plan[f"Week {week}"][day_key] = {
                        "Rest": True,
                        "details": "Rest day"
                    }
                    continue

                muscles = [m for m in day_targets[:3] if m and m != "Any"]
                stimulus = day_targets[3]

                daily_plan = self.generate_daily_plan(muscles=muscles, stimulus=stimulus)
                full_plan[f"Week {week}"][day_key] = {
                    "muscles": muscles,
                    "stimulus": stimulus,
                    "plan": daily_plan,
                    "estimated_time": self._estimate_total_time(daily_plan)
                }

        return full_plan
