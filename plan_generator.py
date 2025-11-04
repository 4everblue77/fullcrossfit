from generators.warmup_generator import WarmupGenerator

class PlanGenerator:
    def __init__(self, supabase):
        self.supabase = supabase
        self.warmup_gen = WarmupGenerator(supabase)
        # Future: add heavy_gen, light_gen, wod_gen, cooldown_gen

    def generate_daily_plan(self, muscles):
        return {
            "Warmup": self.warmup_gen.generate(muscles),
            # "Heavy": self.heavy_gen.generate(...),
            # "WOD": self.wod_gen.generate(...),
            # "Cooldown": self.cooldown_gen.generate(...)
        }
