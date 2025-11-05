import random

class WODGenerator:
    def __init__(self, data, debug=False):
        self.data = data
        self.debug = debug

        self.rep_ranges = {
            "Treadmill Run": (200, 400), "Pull-ups": (4, 6), "Deadlifts (100/70kg)": (4, 6),
            "Ring Rows": (6, 8), "Push-ups": (8, 12), "Bench Press (60/40kg)": (4, 6),
            "Burpees": (6, 8), "Handstand Push-ups": (3, 5), "Push Press (50/35kg)": (6, 8),
            "Wall Balls (9/6kg)": (8, 10), "Kettlebell Swings (24/16kg)": (8, 10),
            "Hip Thrusts (40/30kg)": (8, 10), "Box Step Overs (24/20\")": (6, 8),
            "Front Squats (60/40kg)": (4, 6), "Air Squats": (12, 15), "Lunges": (8, 10),
            "Double Unders": (15, 25), "Sit-ups": (10, 15), "Single Unders": (20, 30),
            "V-Ups": (10, 15), "Hollow Rocks": (10, 15), "Superman Holds": (20, 30),
            "Plank Holds": (20, 30), "Box Jumps (24/20\")": (6, 10), "Knees-to-Elbows": (6, 10),
            "Bear Crawl": (10, 20), "Mountain Climbers": (20, 30), "Tuck Ups": (10, 15),
            "Leg Raises": (10, 15), "Dragon Flags": (5, 10), "Farmer’s Carry": (20, 40),
            "Front Rack Carry": (20, 40), "Overhead Carry": (20, 40), "Rowing": (10, 15),
            "SkiErg": (10, 15), "Assault Bike": (10, 15)
        }

        self.stimulus_map = {
            "vo2 max": ["AMRAP", "Interval", "Alternating EMOM"],
            "lactate threshold": ["Chipper", "For Time", "Tabata"],
            "anaerobic": ["Ladder", "Death by", "EMOM"]
        }

        self.adjectives = ["Savage", "Blazing", "Iron", "Crimson", "Furious", "Relentless", "Vicious", "Explosive", "Brutal", "Wicked"]
        self.nouns = ["Storm", "Inferno", "Titan", "Crusher", "Blitz", "Rage", "Pulse", "Grind", "Surge", "Reaper"]
        self.actions = ["Charge", "Strike", "Burn", "Smash", "Blast", "Crush", "Rush", "Roar", "Clash", "Ignite"]

    def generate_wod_name(self):
        pattern = random.choice(["adj_noun", "noun_action", "adj_noun_action"])
        if pattern == "adj_noun":
            return f"{random.choice(self.adjectives)} {random.choice(self.nouns)}"
        elif pattern == "noun_action":
            return f"{random.choice(self.nouns)} {random.choice(self.actions)}"
        else:
            return f"{random.choice(self.adjectives)} {random.choice(self.nouns)} {random.choice(self.actions)}"

    def select_exercises(self, target_muscle, count):
        # Filter from exercise_pool by muscle group if available
        pool = [
            ex["exercise"] for ex in self.data["exercise_pool"]
            if target_muscle.lower() in (ex.get("muscle_group", "").lower() or "")
        ]
    
        # If no match, fallback to all exercises in exercise_pool
        if not pool:
            pool = [ex["exercise"] for ex in self.data["exercise_pool"]]
    
        return random.sample(pool, min(count, len(pool)))

    def format_exercise(self, ex, reps):
        if "Run" in ex or "Carry" in ex:
            return f"- {reps}m {ex}"
        elif "Hold" in ex:
            return f"- {reps}s {ex}"
        else:
            return f"- {reps} {ex}"

    def generate_targets(self, wod_type):
        targets = {
            "AMRAP": {"Beginner": "3-4 rounds", "Intermediate": "5-6 rounds", "Advanced": "7-8 rounds", "Elite": "9+ rounds"},
            "Chipper": {"Beginner": "Complete in 20+ min", "Intermediate": "Complete in 15-20 min", "Advanced": "Complete in 10-15 min", "Elite": "Complete in <10 min"},
            "Interval": {"Beginner": "1-2 rounds per interval", "Intermediate": "2-3 rounds per interval", "Advanced": "3-4 rounds per interval", "Elite": "4+ rounds per interval"},
            "Tabata": {"Beginner": "8-10 reps per round", "Intermediate": "11-13 reps per round", "Advanced": "14-16 reps per round", "Elite": "17+ reps per round"},
            "For Time": {"Beginner": "Complete in 20+ min", "Intermediate": "Complete in 15-20 min", "Advanced": "Complete in 10-15 min", "Elite": "Complete in <10 min"},
            "Ladder": {"Beginner": "Complete 3 rounds", "Intermediate": "Complete 4 rounds", "Advanced": "Complete 5 rounds", "Elite": "Complete all rounds unbroken"},
            "Death by": {"Beginner": "5-7 minutes", "Intermediate": "8-10 minutes", "Advanced": "11-13 minutes", "Elite": "14+ minutes"},
            "EMOM": {"Beginner": "Maintain for 6-8 minutes", "Intermediate": "Maintain for 9-12 minutes", "Advanced": "Maintain for 13-15 minutes", "Elite": "Maintain full duration unbroken"},
            "Alternating EMOM": {"Beginner": "Maintain for 6-8 minutes", "Intermediate": "Maintain for 9-12 minutes", "Advanced": "Maintain for 13-15 minutes", "Elite": "Maintain full duration unbroken"}
        }
        return targets.get(wod_type, {})

    def generate(self, target_muscle=None, stimulus="anaerobic"):
        stimulus = stimulus.lower()
        if stimulus not in self.stimulus_map:
            return {"error": "Invalid stimulus type. Choose from: vo2 max, lactate threshold, anaerobic."}

        wod_type = random.choice(self.stimulus_map[stimulus])
        name = self.generate_wod_name()
        duration = random.choice([12, 15, 20])
        exercises = self.select_exercises(target_muscle or "general", 2 if wod_type in ["EMOM", "Alternating EMOM"] else 3)

        if not exercises:
            return {
                "WOD Name": "No WOD Generated",
                "Type": "N/A",
                "Estimated Time": "0 min",
                "Description": "No exercises available for the selected muscle group.",
                "Performance Targets": {},
                "debug": {
                    "muscle": target_muscle,
                    "stimulus": stimulus,
                    "selected_exercises": []
                } if self.debug else {}
            }

        description = f"{wod_type} for {duration} minutes\n"
        if wod_type == "AMRAP":
            description += "Complete as many rounds as possible:\n"
            for ex in exercises:
                reps = random.randint(*self.rep_ranges.get(ex, (10, 15)))
                description += self.format_exercise(ex, reps) + "\n"
        elif wod_type == "Chipper":
            description += "Work through the following:\n"
            for ex in exercises:
                base, top = self.rep_ranges.get(ex, (10, 15))
                reps = random.randint(base * 3, top * 3)
                description += self.format_exercise(ex, reps) + "\n"
        elif wod_type == "Interval":
            work = random.choice([3, 4])
            rest = random.choice([1, 2])
            description += f"Work {work} min / Rest {rest} min:\n"
            for ex in exercises:
                reps = random.randint(*self.rep_ranges.get(ex, (10, 15)))
                description += self.format_exercise(ex, reps) + "\n"
        elif wod_type == "Tabata":
            description += "8 rounds of 20s work / 10s rest per movement:\n"
            for ex in exercises:
                description += f"- {ex}\n"
        elif wod_type == "For Time":
            rounds = random.choice([2, 3])
            description += f"Complete {rounds} rounds:\n"
            for ex in exercises:
                reps = random.randint(*self.rep_ranges.get(ex, (10, 15)))
                description += self.format_exercise(ex, reps) + "\n"
        elif wod_type == "Ladder":
            base = random.choice([3, 5])
            rounds = 5
            description += f"Increase reps each round: {', '.join(str(base * i) for i in range(1, rounds + 1))}\n"
            for ex in exercises:
                description += f"- {ex}\n"
        elif wod_type == "Death by":
            description += "Start with 1 rep in minute 1, 2 reps in minute 2, etc. Continue until failure:\n"
            for ex in exercises:
                description += f"- {ex}\n"
        elif wod_type == "EMOM":
            reps = random.randint(*self.rep_ranges.get(exercises[0], (10, 15)))
            description += f"Each minute:\n{self.format_exercise(exercises[0], reps)}"
        elif wod_type == "Alternating EMOM":
            description += "Alternate each minute:\n"
            for i, ex in enumerate(exercises):
                reps = random.randint(*self.rep_ranges.get(ex, (10, 15)))
                description += f"Minute {'Odd' if i == 0 else 'Even'}: {self.format_exercise(ex, reps)}\n"

        
        # Build structured exercise list for syncing
        structured_exercises = []
        for ex in exercises:
            reps = random.randint(*self.rep_ranges.get(ex, (10, 15)))
            structured_exercises.append({
                "name": ex,
                "set": 1,
                "reps": str(reps),
                "intensity": "High",
                "rest": 30,
                "notes": f"{wod_type} format"
            })



        return {
            "WOD Name": name,
            "Type": wod_type,
            "Estimated Time": f"{duration} min",
            "details": description.strip(),
            "Performance Targets": self.generate_targets(wod_type),
            "exercises": structured_exercises,  # ✅ Enables syncing
            "debug": {
                "muscle": target_muscle,
                "stimulus": stimulus,
                "selected_exercises": exercises
            } if self.debug else {}
        }

