import random

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
        self.skill_gen = SkillSessionGenerator(self.data, self.supabase, debug=self.debug)

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
        for week in range(1, 7):  # Only 6 weeks now
            glutes_or_quads = "Glutes/Hamstrings" if week % 2 != 0 else "Quads"
            chest_or_back = "Chest" if week % 2 != 0 else "Back"
    
            # Randomly assign VO2 Max or Lactate Threshold
            mon_stim = random.choice(["VO2 Max", "Lactate Threshold"])
            tue_stim = random.choice(["VO2 Max", "Lactate Threshold"])
            wed_stim = random.choice(["VO2 Max", "Lactate Threshold"])
            fri_stim = random.choice(["VO2 Max", "Lactate Threshold"])
            sat_stim = "Girl/Hero" if week % 2 != 0 else "Anaerobic"
    
            framework[week] = [
                {"day": "Mon", "heavy": [glutes_or_quads], "wod": [chest_or_back], "stimulus": mon_stim, "light": ["Shoulders"], "olympic": False, "skill": False, "run": False},
                {"day": "Tue", "heavy": [], "wod": ["Core"], "stimulus": tue_stim, "light": [], "olympic": True, "skill": True, "run": False},
                {"day": "Wed", "heavy": ["Shoulders"], "wod": [glutes_or_quads], "stimulus": wed_stim, "light": [chest_or_back], "olympic": False, "skill": False, "run": False},
                {"day": "Thu", "heavy": [], "wod": [], "stimulus": None, "light": [], "olympic": False, "skill": False, "run": True},
                {"day": "Fri", "heavy": [chest_or_back], "wod": ["Shoulders"], "stimulus": fri_stim, "light": [glutes_or_quads], "olympic": False, "skill": False, "run": False},
                {"day": "Sat", "heavy": [], "wod": [], "stimulus": sat_stim, "light": [glutes_or_quads], "olympic": True, "skill": False, "run": False},
                None  # Sunday rest
            ]
        return framework


    def generate_daily_plan(self, config, week_number):
        if config is None:
            return {"Rest Day": "No workout scheduled"}

        plan = {}
        muscles = list(set(config["heavy"] + config["wod"] + config["light"]))

        # Skip Warmup on Thursday (Run day)
        if not config["run"]:
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

        # Light session: Skip on Tuesday (Skill day) and Thursday (Run day)
        if not config["skill"] and not config["run"]:
            light_target = "Core" if config["olympic"] else (config["light"][0] if config["light"] else "Core")
            plan["Light"] = self.light_gen.generate(target=light_target)

        # Skill only if flag is True
        if config["skill"]:
            plan["Skill"] = self.skill_gen.generate("Handstand Push-Up", week_number)

        # Skip Cooldown on Thursday (Run day)
        if not config["run"]:
            plan["Cooldown"] = self.cooldown_gen.generate(muscles)

        # Total time
        plan["Total Time"] = self._estimate_total_time(plan)  # numeric value

        return plan

    def generate_full_plan(self):
        framework = self.build_framework()
        full_plan = {}

        for week, days in framework.items():
            full_plan[f"Week {week}"] = {}
            for day_config in days:
                if day_config is None:
                    full_plan[f"Week {week}"]["Sun"] = {"Rest": True, "details": "Rest day"}
                    continue

                daily_plan = self.generate_daily_plan(day_config, week)
                full_plan[f"Week {week}"][day_config["day"]] = {
                    "muscles": list(set(day_config["heavy"] + day_config["wod"] + day_config["light"])),
                    "stimulus": day_config["stimulus"],
                    "day_type": day_config["day"],
                    "plan": daily_plan,
                    "estimated_time": self._estimate_total_time(daily_plan)
                }

        return full_plan
    
    def sync_plan_to_supabase(self, full_plan):
        # Clear previous plan safely (requires WHERE clause)
        self.supabase.table("plan_session_exercises").delete().gt("id", 0).execute()
        self.supabase.table("plan_sessions").delete().gt("id", 0).execute()
        self.supabase.table("plan_days").delete().gt("id", 0).execute()
        self.supabase.table("plan_weeks").delete().gt("id", 0).execute()
    
        for week_number, (week_label, week_data) in enumerate(full_plan.items(), start=1):
            # Insert week
            week_resp = self.supabase.table("plan_weeks").insert({
                "number": week_number,
                "notes": week_label
            }).execute()
            week_id = week_resp.data[0]["id"]
    
            for day_number, (day_label, day_data) in enumerate(week_data.items(), start=1):
                # Insert day
                day_resp = self.supabase.table("plan_days").insert({
                    "week_id": week_id,
                    "day_number": day_number,
                    "is_rest_day": day_data.get("Rest", False),
                    "total_time": day_data.get("estimated_time", 0)
                }).execute()
                day_id = day_resp.data[0]["id"]
    
                # Skip if it's a rest day
                if day_data.get("Rest") or "plan" not in day_data:
                    continue
    
                for session_type, session_data in day_data["plan"].items():
                    # Skip non-session entries
                    if session_type in ["Debug", "Total Time"]:
                        continue
                    if not isinstance(session_data, dict):
                        continue
    
                    # Insert session
                    session_resp = self.supabase.table("plan_sessions").insert({
                        "day_id": day_id,
                        "type": session_type,
                        "target_muscle": ", ".join(day_data.get("muscles", [])),
                        "duration": session_data.get("time", 0),
                        "details": session_data.get("details", ""),
                        "performance_targets": session_data.get("Performance Targets", {}
                    }).execute()
                    session_id = session_resp.data[0]["id"]
    
                    # Insert exercises if present
                    if "exercises" in session_data and isinstance(session_data["exercises"], list):
                        for i, ex in enumerate(session_data["exercises"], start=1):
                            exercise_id = next((e["id"] for e in self.data["exercises"] if e["name"] == ex["name"]), None)
                            self.supabase.table("plan_session_exercises").insert({
                                "session_id": session_id,
                                "exercise_name": ex["name"],
                                "exercise_id": exercise_id,
                                "set_number": ex.get("set", 1),
                                "reps": ex.get("reps", ""),
                                "intensity": ex.get("intensity", ""),
                                "rest": ex.get("rest", 0),
                                "notes": ex.get("notes", ""),
                                "exercise_order": i,  # ✅ Now i is defined
                                "completed": False,
                                "actual_reps": "",
                                "actual_weight": "",
                                "tempo": ex.get("tempo", ""),
                                "expected_weight": ex.get("expected_weight", ""),
                                "equipment": ex.get("equipment", "")
                            }).execute()
