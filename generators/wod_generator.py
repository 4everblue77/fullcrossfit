
import random

class WODGenerator:
    def __init__(self, data, debug=False):
        self.data = data
        self.debug = debug

        # Base ranges used when we need a quick default per movement.
        # Values represent *counts*; formatting below maps counts to appropriate units.
        self.rep_ranges = {
            "Treadmill Run": (200, 400),
            "Pull-ups": (4, 6),
            "Deadlifts (100/70kg)": (4, 6),
            "Ring Rows": (6, 8),
            "Push-ups": (8, 12),
            "Bench Press (60/40kg)": (4, 6),
            "Burpees": (6, 8),
            "Handstand Push-ups": (3, 5),
            "Push Press (50/35kg)": (6, 8),
            "Wall Balls (9/6kg)": (8, 10),
            "Kettlebell Swings (24/16kg)": (8, 10),
            "Hip Thrusts (40/30kg)": (8, 10),
            "Box Step Overs (24/20\")": (6, 8),
            "Front Squats (60/40kg)": (4, 6),
            "Air Squats": (12, 15),
            "Lunges": (8, 10),
            "Double Unders": (15, 25),
            "Sit-ups": (10, 15),
            "Single Unders": (20, 30),
            "V-Ups": (10, 15),
            "Hollow Rocks": (10, 15),
            "Superman Holds": (20, 30),
            "Plank Holds": (20, 30),
            "Box Jumps (24/20\")": (6, 10),
            "Knees-to-Elbows": (6, 10),
            "Bear Crawl": (10, 20),
            "Mountain Climbers": (20, 30),
            "Tuck Ups": (10, 15),
            "Leg Raises": (10, 15),
            "Dragon Flags": (5, 10),
            "Farmer’s Carry": (20, 40),
            "Front Rack Carry": (20, 40),
            "Overhead Carry": (20, 40),

            # Erg work: use calories by default (you can switch to meters if you prefer)
            "Rowing": (10, 20),
            "SkiErg": (10, 20),
            "Assault Bike": (10, 20),
        }

        # Stimulus to WOD-type mapping (unchanged)
        self.stimulus_map = {
            "vo2 max": ["AMRAP", "Interval", "Alternating EMOM"],
            "lactate threshold": ["Chipper", "For Time", "Tabata"],
            "anaerobic": ["Ladder", "Death by", "EMOM"]
        }

        # Name generator lists (unchanged)
        self.adjectives = ["Savage", "Blazing", "Iron", "Crimson", "Furious", "Relentless", "Vicious", "Explosive", "Brutal", "Wicked"]
        self.nouns = ["Storm", "Inferno", "Titan", "Crusher", "Blitz", "Rage", "Pulse", "Grind", "Surge", "Reaper"]
        self.actions = ["Charge", "Strike", "Burn", "Smash", "Blast", "Crush", "Rush", "Roar", "Clash", "Ignite"]

    # ---------- Helpers for units & formatting ----------

    def _exercise_unit(self, name: str) -> str:
        """
        Infer a unit for an exercise name:
        - 'm'   : meters (Run, Carries)
        - 'sec' : seconds (Holds, Plank, Superman)
        - 'cal' : calories (Rowing, SkiErg, Assault Bike)
        - 'reps': everything else
        """
        nl = name.lower()
        if "run" in nl or "carry" in nl:
            return "m"
        if "hold" in nl or "plank" in nl or "superman" in nl:
            return "sec"
        if "row" in nl or "skierg" in nl or "assault bike" in nl or "bike" in nl:
            return "cal"
        return "reps"

    def _format_value(self, ex: str, value: int) -> str:
        """Format a line item with appropriate unit suffix."""
        unit = self._exercise_unit(ex)
        if unit == "m":
            return f"- {value}m {ex}"
        if unit == "sec":
            return f"- {value}s {ex}"
        if unit == "cal":
            return f"- {value} cal {ex}"
        return f"- {value} {ex}"

    def _pick_time_cap(self, wod_type: str) -> int:
        """Choose a sensible time cap (minutes) for each WOD type."""
        if wod_type in ["For Time", "Chipper", "Ladder"]:
            return random.choice([15, 18, 20, 22, 30])  # allow longer caps as needed
        if wod_type in ["AMRAP"]:
            return random.choice([12, 15, 18, 20])
        if wod_type in ["EMOM", "Alternating EMOM", "Interval"]:
            return random.choice([10, 12, 15, 18])
        if wod_type in ["Tabata"]:
            # Tabata is protocol-based (20s on/10s off); we still return a nominal "minutes" for display
            return 8
        return random.choice([12, 15, 20])

    def _structured_item(self, ex: str, order: int, value: int, wod_type: str, duration_min: int) -> dict:
        """Build structured item compatible with your schema; add unit/time cap for timer/UI."""
        ex_id = next((e["id"] for e in self.data["exercises"] if e["name"] == ex), None)
        unit = self._exercise_unit(ex)
        return {
            "name": ex,
            "exercise_id": ex_id,
            "set": 1,
            "reps": str(value),              # keep string for backward compatibility
            "intensity": "High",
            "rest": 30,
            "notes": f"{wod_type} format",
            "exercise_order": order,
            "tempo": "",
            "expected_weight": "",
            "equipment": "",
            # New (non-breaking) fields:
            "unit": unit,
            "time_cap_sec": int(duration_min) * 60 if isinstance(duration_min, int) else 0,
            "protocol": wod_type
        }

    # ---------- Existing name generator ----------

    def generate_wod_name(self):
        pattern = random.choice(["adj_noun", "noun_action", "adj_noun_action"])
        if pattern == "adj_noun":
            return f"{random.choice(self.adjectives)} {random.choice(self.nouns)}"
        elif pattern == "noun_action":
            return f"{random.choice(self.nouns)} {random.choice(self.actions)}"
        else:
            return f"{random.choice(self.adjectives)} {random.choice(self.nouns)} {random.choice(self.actions)}"

    # ---------- Existing exercise selector (preserves muscle-group focus) ----------

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

    # ---------- Existing formatter (now routed to unit-aware helper) ----------

    def format_exercise(self, ex, reps):
        # Keep legacy signature, but use precise unit formatting
        return self._format_value(ex, reps)

    # ---------- Existing performance targets ----------

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

    # ---------- Existing simple generator (unchanged behavior; now unit-aware) ----------

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
        for i, ex in enumerate(exercises):
            reps = random.randint(*self.rep_ranges.get(ex, (10, 15)))
            structured_exercises.append(self._structured_item(ex, i + 1, reps, wod_type, duration))

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

    # ---------- NEW: Rich template-driven generator (no hero/benchmark names) ----------

    def generate_complex_wod(self, target_muscle=None, stimulus="anaerobic", level="Intermediate"):
        """
        Richer WOD generation with multiple templates:
          - Descending ladder (21-15-9, 10-8-6-4-2)
          - Bookend run (run -> ladder -> run)
          - Linear chipper (large blocks, optional short run at end)
          - RFT with fixed reps and 3–5 movements
          - AMRAP with buy-in
          - EMOM / Alternating EMOM
          - Interval blocks
          - Tabata multi-movement

        Preserves muscle-group filtering via select_exercises().
        Avoids named hero/benchmark WODs (structure only).
        """
        stimulus = stimulus.lower()
        if stimulus not in self.stimulus_map:
            return {"error": "Invalid stimulus type. Choose from: vo2 max, lactate threshold, anaerobic."}

        # Choose a WOD type consistent with stimulus
        wod_type = random.choice(self.stimulus_map[stimulus])
        name = self.generate_wod_name()

        # Template choices per type
        templates_by_type = {
            "For Time": ["ladder_desc", "bookend_run", "chipper_linear", "rft_fixed", "overlay_every_x_sec"],
            "AMRAP": ["amrap_couplet", "amrap_triplet", "amrap_buyin"],
            "Interval": ["interval_blocks"],
            "EMOM": ["emom_single", "emom_alternating"],
            "Alternating EMOM": ["emom_alternating"],
            "Tabata": ["tabata_multi"],
            "Ladder": ["ladder_desc"]
        }
        template = random.choice(templates_by_type.get(wod_type, ["rft_fixed"]))
        duration = self._pick_time_cap(wod_type)

        # Helper to get exercises while preserving muscle-group filter
        def pick_ex(count):
            return self.select_exercises(target_muscle or "general", count)

        description_lines = []
        structured_exercises = []

        ladder_schemes = [[21, 15, 9], [21, 15, 9, 6, 3], [10, 8, 6, 4, 2]]

        # ----- Templates -----

        if wod_type == "For Time" and template == "ladder_desc":
            moves = pick_ex(random.choice([2, 3]))
            scheme = random.choice(ladder_schemes)
            description_lines.append(f"For Time - {duration} Minutes Time Cap")
            desc_scheme = "-".join(str(s) for s in scheme)
            description_lines.append(f"{desc_scheme} reps of:")
            for ex in moves:
                description_lines.append(f"- {ex}")
            # seed structured with first ladder value
            order = 1
            for ex in moves:
                structured_exercises.append(self._structured_item(ex, order, scheme[0], wod_type, duration))
                order += 1

        elif wod_type == "For Time" and template == "bookend_run":
            middle_moves = pick_ex(2)
            scheme = random.choice([[10, 8, 6, 4, 2], [12, 9, 6, 3]])
            description_lines.append("For Time")
            description_lines.append("2000m Treadmill Run")
            description_lines.append(f"{'-'.join(str(s) for s in scheme)} reps of:")
            for ex in middle_moves:
                description_lines.append(f"- {ex}")
            description_lines.append("2000m Treadmill Run")
            order = 1
            structured_exercises.append(self._structured_item("Treadmill Run", order, 2000, wod_type, duration)); order += 1
            for ex in middle_moves:
                structured_exercises.append(self._structured_item(ex, order, scheme[0], wod_type, duration)); order += 1
            structured_exercises.append(self._structured_item("Treadmill Run", order, 2000, wod_type, duration))

        elif wod_type == "For Time" and template == "chipper_linear":
            blocks = random.choice([[100, 200, 300, 400], [200, 150, 100, 50]])
            moves = pick_ex(4)
            description_lines.append(f"For Time - {duration} Minutes Time Cap")
            for i, ex in enumerate(moves):
                val = blocks[i]
                description_lines.append(self._format_value(ex, val))
                structured_exercises.append(self._structured_item(ex, i + 1, val, wod_type, duration))
            # optional short run if no run present
            if all("run" not in m.lower() for m in moves):
                tail_run = random.choice([400, 800])
                description_lines.append(self._format_value("Treadmill Run", tail_run))
                structured_exercises.append(self._structured_item("Treadmill Run", len(moves) + 1, tail_run, wod_type, duration))

        elif wod_type == "For Time" and template == "rft_fixed":
            rounds = random.choice([3, 4, 5, 6])
            moves = pick_ex(random.choice([3, 4, 5]))
            reps = random.choice([7, 10, 12, 15])
            description_lines.append(f"For Time - Time Cap: {duration} min")
            description_lines.append(f"{rounds} Rounds of:")
            for ex in moves:
                description_lines.append(self._format_value(ex, reps))
            order = 1
            for ex in moves:
                structured_exercises.append(self._structured_item(ex, order, reps, wod_type, duration))
                order += 1

        elif wod_type == "For Time" and template == "overlay_every_x_sec":
            primary = pick_ex(1)[0]
            overlay = pick_ex(1)[0]
            primary_total = random.choice([60, 70, 90])
            overlay_sec = random.choice([60, 75, 90])
            description_lines.append(f"For Time - {duration} Minutes Time Cap")
            description_lines.append(self._format_value(primary, primary_total))
            description_lines.append(f"Every {overlay_sec} sec perform {overlay}")
            structured_exercises.append(self._structured_item(primary, 1, primary_total, wod_type, duration))
            structured_exercises.append(self._structured_item(overlay, 2, 1, wod_type, duration))

        elif wod_type == "AMRAP" and template in ["amrap_couplet", "amrap_triplet"]:
            duration = random.choice([18, 20])
            moves = pick_ex(2 if template == "amrap_couplet" else 3)
            description_lines.append(f"{duration} Min AMRAP")
            order = 1
            for ex in moves:
                base, top = self.rep_ranges.get(ex, (10, 15))
                reps = random.randint(base, top)
                description_lines.append(self._format_value(ex, reps))
                structured_exercises.append(self._structured_item(ex, order, reps, "AMRAP", duration))
                order += 1

        elif wod_type == "AMRAP" and template == "amrap_buyin":
            duration = random.choice([16, 18, 20])
            buyin = pick_ex(1)[0]
            loop = pick_ex(2)
            buyin_val = random.choice([400, 800, 1000]) if self._exercise_unit(buyin) == "m" else random.choice([10, 20, 30])
            description_lines.append(f"{duration} Min AMRAP")
            description_lines.append(f"Buy-in: {self._format_value(buyin, buyin_val).replace('- ', '')}")
            description_lines.append("Then, as many rounds as possible of:")
            order = 1
            structured_exercises.append(self._structured_item(buyin, order, buyin_val, "AMRAP", duration)); order += 1
            for ex in loop:
                base, top = self.rep_ranges.get(ex, (8, 12))
                reps = random.randint(base, top)
                description_lines.append(self._format_value(ex, reps))
                structured_exercises.append(self._structured_item(ex, order, reps, "AMRAP", duration)); order += 1

        elif wod_type in ["EMOM", "Alternating EMOM"] and template in ["emom_single", "emom_alternating"]:
            duration = random.choice([10, 12, 15])
            if template == "emom_single":
                ex = pick_ex(1)[0]
                base, top = self.rep_ranges.get(ex, (8, 12))
                reps = random.randint(base, top)
                description_lines.append(f"EMOM {duration} minutes:")
                description_lines.append(f"- {reps} {ex} each minute")
                structured_exercises.append(self._structured_item(ex, 1, reps, wod_type, duration))
            else:
                moves = pick_ex(2)
                description_lines.append(f"Alternating EMOM {duration} minutes:")
                for i, ex in enumerate(moves):
                    base, top = self.rep_ranges.get(ex, (8, 12))
                    reps = random.randint(base, top)
                    description_lines.append(f"- Minute {'Odd' if i == 0 else 'Even'}: {reps} {ex}")
                    structured_exercises.append(self._structured_item(ex, i + 1, reps, "Alternating EMOM", duration))

        elif wod_type == "Interval" and template == "interval_blocks":
            duration = random.choice([16, 20])
            work = random.choice([2, 3, 4])
            rest = random.choice([1, 2])
            moves = pick_ex(random.choice([2, 3]))
            description_lines.append(f"Work {work} min / Rest {rest} min for {duration} minutes total:")
            for ex in moves:
                base, top = self.rep_ranges.get(ex, (8, 12))
                reps = random.randint(base, top)
                description_lines.append(self._format_value(ex, reps))
                structured_exercises.append(self._structured_item(ex, len(structured_exercises) + 1, reps, "Interval", duration))

        elif wod_type == "Tabata" and template == "tabata_multi":
            duration = 8  # protocol rounds (display only)
            moves = pick_ex(random.choice([2, 3]))
            description_lines.append("Tabata: 8 rounds of 20s work / 10s rest per movement:")
            for ex in moves:
                description_lines.append(f"- {ex}")
                structured_exercises.append(self._structured_item(ex, len(structured_exercises) + 1, 20, "Tabata", duration))

        else:
            # Fallback: simple For Time triplet with cap
            moves = pick_ex(3)
            description_lines.append(f"For Time - {duration} Minutes Time Cap")
            for ex in moves:
                base, top = self.rep_ranges.get(ex, (10, 15))
                reps = random.randint(base, top)
                description_lines.append(self._format_value(ex, reps))
                structured_exercises.append(self._structured_item(ex, len(structured_exercises) + 1, reps, "For Time", duration))

        details = "\n".join(description_lines).strip()
        return {
            "WOD Name": name,
            "Type": wod_type,
            "Estimated Time": f"{duration} min" if isinstance(duration, int) else str(duration),
            "details": details,
            "Performance Targets": self.generate_targets(wod_type),
            "exercises": structured_exercises,
            "debug": {
                "muscle": target_muscle,
                "stimulus": stimulus,
                "template": template
            } if self.debug else {}
        }
