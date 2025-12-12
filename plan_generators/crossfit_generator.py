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
from plan_generators.supabase_sync_function import sync_plan_to_supabase
from datetime import datetime, timedelta

class CrossFitPlanGenerator:
    def __init__(self, supabase, debug=False):
        self.supabase = supabase
        self.data = self._load_data()
        self.debug = debug

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


    def _estimate_total_time(self, plan: dict) -> int:
        """
        Sum known section times. Prefer structured 'time_cap_sec' in exercises,
        then section-level 'Estimated Time', else fall back to defaults.
        Returns minutes (int).
        """
        # Defaults (tweak to your preferences / program constraints)
        DEFAULTS = {
            "Warmup": 12,
            "Heavy": 20,
            "Olympic": 20,
            "Run": 30,        # If run generator doesn't provide time, assume mixed cardio
            "WOD": 18,        # Fallback if no cap provided
            "Benchmark": 25,
            "Light": 15,
            "Skill": 20,
            "Cooldown": 8,
        }
    
        def section_minutes(section_name: str, section_obj: dict) -> int:
            # 1) Try to read per-exercise time caps (complex WODs / interval formats)
            if isinstance(section_obj, dict) and "exercises" in section_obj:
                caps = []
                for ex in section_obj.get("exercises", []):
                    cap_sec = ex.get("time_cap_sec")
                    if isinstance(cap_sec, (int, float)) and cap_sec > 0:
                        caps.append(cap_sec)
                if caps:
                    # For most sections, the block time is the *max* cap (WOD) or the *sum* if clearly additive.
                    # WODs are cap-based, so take max. For Warmup/Cooldown/Light, generators usually don't set caps.
                    if section_name in ("WOD", "Benchmark"):
                        return int(max(caps) // 60)
                    # If ever you produce additive caps (rare), sum them:
                    # return int(sum(caps) // 60)
                    # Otherwise fall through to 'Estimated Time' or defaults.
    
            # 2) Try the section-level "Estimated Time"
            est = None
            if isinstance(section_obj, dict):
                est = section_obj.get("Estimated Time")
            elif isinstance(section_obj, str):
                # Some generators might return just text; try a very light parse
                est = section_obj
    
            if isinstance(est, str):
                # Extract a leading integer before 'min'
                # e.g., "18 min", "Time Cap: 30 min"
                import re
                m = re.search(r"(\d+)\s*min", est.lower())
                if m:
                    return int(m.group(1))
    
            # 3) Last resort: defaults
            return DEFAULTS.get(section_name, 0)
    
        total = 0
        for section_name, section_obj in plan.items():
            if section_name in ("Total Time", "Rest Day"):
                continue
            total += section_minutes(section_name, section_obj)
    
        # Edge case: if your Run generator returns distance only, estimate by pace
        # Example: add heuristic if 'Run' exists and has distance but no time:
        run = plan.get("Run")
        if isinstance(run, dict) and "exercises" in run:
            # If no section Minutes computed above, try to infer from distance
            # Assume 6:00 min/km (i.e., 10 km/h) for treadmill as default
            has_time = section_minutes("Run", run)
            if not has_time:
                dist_m = 0
                for ex in run["exercises"]:
                    if (ex.get("name", "").lower().find("treadmill run") >= 0) and ex.get("unit") == "m":
                        try:
                            dist_m += int(ex.get("reps", "0"))
                        except Exception:
                            pass
                if dist_m > 0:
                    pace_min_per_km = 6.0
                    total += int((dist_m / 1000.0) * pace_min_per_km)
    

    
    def fetch_skills(self):
        return self.supabase.table("skills").select("skill_name").execute().data
    
    

    
    def build_framework(self):
        framework = {}
        for week in range(1, 7):
            # Odd/even week switch
            is_odd = (week % 2 != 0)
    
            # ---- Assignments per your attachment ----
            # Odd week mapping
            odd_heavy = {
                "Mon": ["Shoulders"],
                "Tue": [],
                "Wed": ["Glutes/Hamstrings"],
                "Thu": [],
                "Fri": ["Chest"],
                "Sat": [],
            }
            odd_wod = {
                "Mon": ["Back"],
                "Tue": ["Core"],
                "Wed": ["Shoulders"],
                "Thu": [],
                "Fri": ["Glutes/Hamstrings"],
                "Sat": [],
            }
            odd_light = {
                "Mon": ["Quads"],
                "Tue": [],
                "Wed": ["Back"],
                "Thu": [],
                "Fri": ["Shoulders"],
                "Sat": ["Core"],
            }
    
            # Even week mapping
            even_heavy = {
                "Mon": ["Shoulders"],
                "Tue": [],
                "Wed": ["Quads"],
                "Thu": [],
                "Fri": ["Back"],
                "Sat": [],
            }
            even_wod = {
                "Mon": ["Chest"],
                "Tue": ["Core"],
                "Wed": ["Shoulders"],
                "Thu": [],
                "Fri": ["Quads"],
                "Sat": [],
            }
            even_light = {
                "Mon": ["Glutes/Hamstrings"],
                "Tue": [],
                "Wed": ["Chest"],
                "Thu": [],
                "Fri": ["Shoulders"],
                "Sat": ["Core"],
            }
    
            heavy_map = odd_heavy if is_odd else even_heavy
            wod_map   = odd_wod   if is_odd else even_wod
            light_map = odd_light if is_odd else even_light
    
            # Stimulus logic 
            mon_stim = random.choice(["VO2 Max", "Lactate Threshold"])
            tue_stim = random.choice(["VO2 Max", "Lactate Threshold"])
            wed_stim = random.choice(["VO2 Max", "Lactate Threshold"])
            fri_stim = random.choice(["VO2 Max", "Lactate Threshold"])
            sat_stim = "Girl/Hero" if is_odd else "Anaerobic"
    
            framework[week] = [
                {
                    "day": "Mon",
                    "heavy": heavy_map["Mon"],
                    "wod": wod_map["Mon"],
                    "stimulus": mon_stim,
                    "light": light_map["Mon"],
                    "olympic": False,
                    "skill": False,
                    "run": False,
                },
                {
                    "day": "Tue",
                    "heavy": heavy_map["Tue"],
                    "wod": wod_map["Tue"],
                    "stimulus": tue_stim,
                    "light": light_map["Tue"],
                    "olympic": True,
                    "skill": True,
                    "run": False,
                },
                {
                    "day": "Wed",
                    "heavy": heavy_map["Wed"],
                    "wod": wod_map["Wed"],
                    "stimulus": wed_stim,
                    "light": light_map["Wed"],
                    "olympic": False,
                    "skill": False,
                    "run": False,
                },
                {
                    "day": "Thu",
                    "heavy": heavy_map["Thu"],
                    "wod": wod_map["Thu"],
                    "stimulus": None,
                    "light": light_map["Thu"],
                    "olympic": False,
                    "skill": False,
                    "run": True,  # Your Thursday run
                },
                {
                    "day": "Fri",
                    "heavy": heavy_map["Fri"],
                    "wod": wod_map["Fri"],
                    "stimulus": fri_stim,
                    "light": light_map["Fri"],
                    "olympic": False,
                    "skill": False,
                    "run": False,
                },
                {
                    "day": "Sat",
                    "heavy": heavy_map["Sat"],
                    "wod": wod_map["Sat"],
                    "stimulus": sat_stim,
                    "light": light_map["Sat"],
                    "olympic": True,
                    "skill": False,
                    "run": False,
                           },
                None,  # Sunday rest
            ]


    def generate_daily_plan(self, config, week_number, skill_name=None):
        if config is None:
            return {"Rest Day": "No workout scheduled"}
        plan = {}
        muscles = list(set(config["heavy"] + config["wod"] + config["light"]))
        if not config["run"]:
            plan["Warmup"] = self.warmup_gen.generate(muscles)
        if config["heavy"]:
            plan["Heavy"] = self.heavy_gen.generate(config["heavy"])
        if config["olympic"]:
            plan["Olympic"] = self.olympic_gen.generate()
        if config["run"]:
            plan["Run"] = self.run_gen.generate()
        if config["wod"] and config["stimulus"]:
            plan["WOD"] = self.wod_gen.generate_complex_wod(target_muscle=config["wod"][0], stimulus=config["stimulus"])
        if config["stimulus"] == "Girl/Hero":
            plan["Benchmark"] = self.benchmark_gen.generate()
        if not config["skill"] and not config["run"]:
            light_target = "Core" if config["olympic"] else (config["light"][0] if config["light"] else "Core")
            plan["Light"] = self.light_gen.generate(target=light_target)
        if config["skill"]:
            plan["Skill"] = self.skill_gen.generate(skill_name, week_number)
        if not config["run"]:
            plan["Cooldown"] = self.cooldown_gen.generate(muscles)
        plan["Total Time"] = f"{self._estimate_total_time(plan)} min"
        return plan


    def generate_full_plan(self, start_date, skill="Handstand Push-Up"):
        if isinstance(start_date, str):
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        framework = self.build_framework()
        full_plan = {}
        day_offset = 0
        for week, days in framework.items():
            full_plan[f"Week {week}"] = {}
            for day_config in days:
                if day_config is None:
                    actual_date = start_date + timedelta(days=day_offset)
                    full_plan[f"Week {week}"]["Sun"] = {
                        "Rest": True,
                        "details": "Rest day",
                        "date": actual_date.isoformat()
                    }
                    day_offset += 1
                    continue
                actual_date = start_date + timedelta(days=day_offset)
                daily_plan = self.generate_daily_plan(day_config, week,skill)
                
                # ✅ Add focus muscles for each session
                for session_type, session_data in daily_plan.items():
                    if isinstance(session_data, dict):
                        if session_type == "Heavy":
                            session_data["focus_muscle"] = ", ".join(day_config["heavy"])
                        elif session_type == "WOD":
                            session_data["focus_muscle"] = ", ".join(day_config["wod"])
                        elif session_type == "Light":
                            session_data["focus_muscle"] = ", ".join(day_config["light"])
                        elif session_type == "Olympic":
                            session_data["focus_muscle"] = "Olympic Lifts"
                        elif session_type == "Run":
                            session_data["focus_muscle"] = "Cardio"
                        elif session_type == "Skill":
                            session_data["focus_muscle"] = "Skill Work"
                        elif session_type == "Warmup" or session_type == "Cooldown":
                            session_data["focus_muscle"] = "Full Body"

                full_plan[f"Week {week}"][day_config["day"]] = {
                    "date": actual_date.isoformat(),
                    "muscles": list(set(day_config["heavy"] + day_config["wod"] + day_config["light"])),
                    "stimulus": day_config["stimulus"],
                    "day_type": day_config["day"],
                    "plan": daily_plan,
                    "estimated_time": int(self._estimate_total_time(daily_plan) or 0)
                }
                day_offset += 1
        return full_plan


    def sync_plan_to_supabase(self, full_plan):
        return sync_plan_to_supabase(self.supabase, full_plan, self.data)
