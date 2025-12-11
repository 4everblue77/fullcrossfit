
import random
from typing import Any, Dict, List, Optional, Sequence, Union


class WODGenerator:
    """
    Table-driven WOD generator.

    Expected data:
      data["exercise_pool"]: list[dict] rows with at least:
        {
          "id": int,
          "musclegroup_id": int,
          "exercise": str,           # normalized name
          "unit": str,               # 'reps' | 'meters' | 'seconds'
          "range_min": int,
          "range_max": int,
          "rx_male_kg": float | None,
          "rx_female_kg": float | None,
          "equipment": list[str] | None,
          "tags": list[str] | None,
          "skill_level": int | None,
          "is_unilateral": bool | None,
          "notes": str | None
        }

      data["muscle_groups"]: optional list[dict] -> [{"id": 1, "name": "Back"}, ...]
      data["exercises"]:     optional legacy lookup [{"id": <int>, "name": <str>}]
    """

    def __init__(self, data: Dict[str, Any], debug: bool = False, seed: Optional[int] = None) -> None:
        self.data = data or {}
        self.debug = debug
        if seed is not None:
            random.seed(seed)

        # Stimulus -> WOD types
        self.stimulus_map = {
            "vo2 max": ["AMRAP", "Interval", "Alternating EMOM"],
            "lactate threshold": ["Chipper", "For Time", "Tabata"],
            "anaerobic": ["Ladder", "Death by", "EMOM"],
        }

        # Name generator parts
        self.adjectives = [
            "Savage", "Blazing", "Iron", "Crimson", "Furious",
            "Relentless", "Vicious", "Explosive", "Brutal", "Wicked",
        ]
        self.nouns = [
            "Storm", "Inferno", "Titan", "Crusher", "Blitz",
            "Rage", "Pulse", "Grind", "Surge", "Reaper",
        ]
        self.actions = [
            "Charge", "Strike", "Burn", "Smash", "Blast",
            "Crush", "Rush", "Roar", "Clash", "Ignite",
        ]

    # ----------------------------
    # --------- Utilities --------
    # ----------------------------

    @staticmethod
    def _lower_list(x: Optional[Sequence[str]]) -> List[str]:
        return [s.lower() for s in (x or [])]

    def generate_wod_name(self) -> str:
        pattern = random.choice(["adj_noun", "noun_action", "adj_noun_action"])
        if pattern == "adj_noun":
            return f"{random.choice(self.adjectives)} {random.choice(self.nouns)}"
        elif pattern == "noun_action":
            return f"{random.choice(self.nouns)} {random.choice(self.actions)}"
        else:
            return f"{random.choice(self.adjectives)} {random.choice(self.nouns)} {random.choice(self.actions)}"

    def _muscle_id_from_name(self, name: str) -> Optional[int]:
        groups = self.data.get("muscle_groups") or []
        lookup = {g["name"].lower(): g["id"] for g in groups if "id" in g and "name" in g}
        return lookup.get(name.lower())

    def _filter_pool(
        self,
        target_muscle: Optional[Union[int, str]],
        equipment_available: Optional[Sequence[str]] = None,
        include_tags: Optional[Sequence[str]] = None,
        exclude_tags: Optional[Sequence[str]] = None,
        max_skill_level: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        pool: List[Dict[str, Any]] = list(self.data.get("exercise_pool") or [])

        # Muscle group filtering
        if isinstance(target_muscle, int):
            pool = [ex for ex in pool if ex.get("musclegroup_id") == target_muscle]
        elif isinstance(target_muscle, str) and target_muscle.strip():
            mg_id = self._muscle_id_from_name(target_muscle)
            if mg_id is not None:
                pool = [ex for ex in pool if ex.get("musclegroup_id") == mg_id]
            else:
                # fallback: search by exercise name/tags containing the term
                key = target_muscle.lower()
                pool = [
                    ex for ex in pool
                    if key in (ex.get("exercise", "") or "").lower()
                    or key in " ".join(self._lower_list(ex.get("tags")))
                ]

        # Equipment filter: keep if needs no equipment OR is subset of available
        if equipment_available:
            avail = set(self._lower_list(equipment_available))
            filtered = []
            for ex in pool:
                eq = set(self._lower_list(ex.get("equipment") or []))
                if not eq or eq.issubset(avail):
                    filtered.append(ex)
            pool = filtered

        # Tag filters
        if include_tags or exclude_tags:
            incl = set(self._lower_list(include_tags))
            excl = set(self._lower_list(exclude_tags))
            out = []
            for ex in pool:
                tags = set(self._lower_list(ex.get("tags") or []))
                if incl and not (tags & incl):
                    continue
                if excl and (tags & excl):
                    continue
                out.append(ex)
            pool = out

        # Skill level
        if max_skill_level is not None:
            out = []
            for ex in pool:
                level = ex.get("skill_level")
                level = 1 if level is None else int(level)
                if level <= int(max_skill_level):
                    out.append(ex)
            pool = out

        # Fallback if filters empty the pool
        if not pool:
            pool = list(self.data.get("exercise_pool") or [])
        return pool

    def _pick_exercises(
        self,
        target_muscle: Optional[Union[int, str]],
        count: int,
        equipment_available: Optional[Sequence[str]] = None,
        include_tags: Optional[Sequence[str]] = None,
        exclude_tags: Optional[Sequence[str]] = None,
        max_skill_level: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        pool = self._filter_pool(
            target_muscle=target_muscle,
            equipment_available=equipment_available,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            max_skill_level=max_skill_level,
        )
        count = max(1, min(count, len(pool)))
        return random.sample(pool, count)

    @staticmethod
    def _rand_between(low: Optional[int], high: Optional[int]) -> int:
        low = 10 if low is None else int(low)
        high = 15 if high is None else int(high)
        if low > high:
            low, high = high, low
        return random.randint(max(1, low), max(1, high))

    def _pick_qty(self, ex: Dict[str, Any], multiplier: float = 1.0) -> int:
        base = self._rand_between(ex.get("range_min"), ex.get("range_max"))
        qty = int(round(base * multiplier))
        return max(1, qty)

    @staticmethod
    def _format_line(ex: Dict[str, Any], qty: int) -> str:
        unit = (ex.get("unit") or "reps").lower()
        name = ex.get("exercise") or "Unknown"
        suffix = ""
        rx_m = ex.get("rx_male_kg")
        rx_f = ex.get("rx_female_kg")
        if rx_m or rx_f:
            if rx_m and rx_f:
                suffix = f" ({rx_m}/{rx_f}kg)"
            else:
                suffix = f" ({rx_m or rx_f}kg)"

        if unit == "meters":
            return f"- {qty}m {name}{suffix}"
        elif unit == "seconds":
            return f"- {qty}s {name}{suffix}"
        else:
            return f"- {qty} {name}{suffix}"

    def _structured_item(self, ex: Dict[str, Any], order: int, qty: int, wod_type: str, duration_min: int) -> Dict[str, Any]:
        # Try legacy lookup first; otherwise use exercise_pool.id
        ex_id = next(
            (e.get("id") for e in self.data.get("exercises", []) if e.get("name") == ex.get("exercise")),
            ex.get("id"),
        )

        expected_weight = ""
        rx_m = ex.get("rx_male_kg")
        rx_f = ex.get("rx_female_kg")
        if rx_m or rx_f:
            expected_weight = f"{rx_m}/{rx_f}kg" if rx_m and rx_f else f"{rx_m or rx_f}kg"

        return {
            "name": ex.get("exercise"),
            "exercise_id": ex_id,
            "set": 1,
            "reps": str(qty),  # quantity as string for compatibility
            "intensity": "High",
            "rest": 30,
            "notes": f"{wod_type} format",
            "exercise_order": order,
            "tempo": "",
            "expected_weight": expected_weight,
            "equipment": ", ".join(ex.get("equipment") or []),
            # non-breaking extras
            "unit": (ex.get("unit") or "reps").lower(),
            "time_cap_sec": int(duration_min) * 60 if isinstance(duration_min, int) else 0,
            "protocol": wod_type,
        }

    def generate_targets(self, wod_type: str) -> Dict[str, str]:
        return {
            "AMRAP": {"Beginner": "3-4 rounds", "Intermediate": "5-6 rounds", "Advanced": "7-8 rounds", "Elite": "9+ rounds"},
            "Chipper": {"Beginner": "Complete in 20+ min", "Intermediate": "15-20 min", "Advanced": "10-15 min", "Elite": "<10 min"},
            "Interval": {"Beginner": "1-2 rounds/interval", "Intermediate": "2-3 rounds/interval", "Advanced": "3-4 rounds/interval", "Elite": "4+ rounds/interval"},
            "Tabata": {"Beginner": "8-10 reps per round", "Intermediate": "11-13 reps per round", "Advanced": "14-16 reps per round", "Elite": "17+ reps per round"},
            "For Time": {"Beginner": "Complete in 20+ min", "Intermediate": "15-20 min", "Advanced": "10-15 min", "Elite": "<10 min"},
            "Ladder": {"Beginner": "Complete 3 rounds", "Intermediate": "Complete 4 rounds", "Advanced": "Complete 5 rounds", "Elite": "Complete all rounds unbroken"},
            "Death by": {"Beginner": "5-7 minutes", "Intermediate": "8-10 minutes", "Advanced": "11-13 minutes", "Elite": "14+ minutes"},
            "EMOM": {"Beginner": "Maintain for 6-8 minutes", "Intermediate": "9-12 minutes", "Advanced": "13-15 minutes", "Elite": "Maintain full duration unbroken"},
            "Alternating EMOM": {"Beginner": "Maintain for 6-8 minutes", "Intermediate": "9-12 minutes", "Advanced": "13-15 minutes", "Elite": "Maintain full duration unbroken"},
        }.get(wod_type, {})

    # ----------------------------
    # --------- Generate ---------
    # ----------------------------

    def generate(
        self,
        target_muscle: Optional[Union[int, str]] = None,
        stimulus: str = "anaerobic",
        duration_options: Sequence[int] = (12, 15, 20),
        equipment_available: Optional[Sequence[str]] = None,
        include_tags: Optional[Sequence[str]] = None,
        exclude_tags: Optional[Sequence[str]] = None,
        max_skill_level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Simple WOD generator (AMRAP/Chipper/Interval/Tabata/For Time/Ladder/Death by/EMOM/Alternating EMOM)
        using table-driven exercise data.
        """
        stimulus = (stimulus or "").lower()
        if stimulus not in self.stimulus_map:
            return {"error": "Invalid stimulus type. Choose from: vo2 max, lactate threshold, anaerobic."}

        wod_type = random.choice(self.stimulus_map[stimulus])
        name = self.generate_wod_name()
        duration = random.choice(list(duration_options))

        # Exercise count per format
        count = 1 if wod_type == "EMOM" else (2 if wod_type == "Alternating EMOM" else 3)

        exercises = self._pick_exercises(
            target_muscle=target_muscle or "General",
            count=count,
            equipment_available=equipment_available,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
            max_skill_level=max_skill_level,
        )

        if not exercises:
            return {
                "WOD Name": "No WOD Generated",
                "Type": "N/A",
                "Estimated Time": "0 min",
                "details": "No exercises available for the selected muscle group/filters.",
                "Performance Targets": {},
                "exercises": [],
                "debug": {"muscle": target_muscle, "stimulus": stimulus, "selected_exercises": []} if self.debug else {},
            }

        lines: List[str] = [f"{wod_type} for {duration} minutes"]

        # Build description per format
        if wod_type == "AMRAP":
            lines.append("Complete as many rounds as possible:")
            for ex in exercises:
                qty = self._pick_qty(ex)
                lines.append(self._format_line(ex, qty))

        elif wod_type == "Chipper":
            lines.append("Work through the following:")
            for ex in exercises:
                qty = self._pick_qty(ex, multiplier=3.0)  # increased volume
                lines.append(self._format_line(ex, qty))

        elif wod_type == "Interval":
            work = random.choice([3, 4])
            rest = random.choice([1, 2])
            lines.append(f"Work {work} min / Rest {rest} min:")
            for ex in exercises:
                qty = self._pick_qty(ex)
                lines.append(self._format_line(ex, qty))

        elif wod_type == "Tabata":
            lines.append("8 rounds of 20s work / 10s rest per movement:")
            for ex in exercises:
                lines.append(f"- {ex.get('exercise')}")

        elif wod_type == "For Time":
            rounds = random.choice([2, 3])
            lines.append(f"Complete {rounds} rounds:")
            for ex in exercises:
                qty = self._pick_qty(ex)
                lines.append(self._format_line(ex, qty))

        elif wod_type == "Ladder":
            base = random.choice([3, 5])
            rounds = 5
            ladder = ", ".join(str(base * i) for i in range(1, rounds + 1))
            lines.append(f"Increase reps each round: {ladder}")
            for ex in exercises:
                lines.append(f"- {ex.get('exercise')}")

        elif wod_type == "Death by":
            lines.append("Start with 1 rep in minute 1, 2 reps in minute 2, etc. Continue until failure:")
            for ex in exercises:
                lines.append(f"- {ex.get('exercise')}")

        elif wod_type == "EMOM":
            qty = self._pick_qty(exercises[0])
            lines.append("Each minute:")
            lines.append(self._format_line(exercises[0], qty))

        elif wod_type == "Alternating EMOM":
            lines.append("Alternate each minute:")
            for i, ex in enumerate(exercises):
                qty = self._pick_qty(ex)
                lines.append(f"Minute {'Odd' if i == 0 else 'Even'}: {self._format_line(ex, qty)}")

        # Structured output for syncing/logging
        structured: List[Dict[str, Any]] = []
        for order, ex in enumerate(exercises, start=1):
            qty = self._pick_qty(ex)
            structured.append(self._structured_item(ex, order, qty, wod_type, duration))

        return {
            "WOD Name": name,
            "Type": wod_type,
            "Estimated Time": f"{duration} min",
            "estimated_time": int(duration), # <-- always numeric
            "details": "\n".join(lines),
            "Performance Targets": self.generate_targets(wod_type),
            "exercises": structured,
            "debug": {
                "muscle": target_muscle,
                "stimulus": stimulus,
                "selected_exercises": [ex.get("exercise") for ex in exercises],
            } if self.debug else {},
        }

    # --------------------------------------------
    # --- Optional richer templates (table-driven)
    # --------------------------------------------
    def generate_complex_wod(
        self,
        target_muscle: Optional[Union[int, str]] = None,
        stimulus: str = "anaerobic",
        level: str = "Intermediate",
        equipment_available: Optional[Sequence[str]] = None,
        include_tags: Optional[Sequence[str]] = None,
        exclude_tags: Optional[Sequence[str]] = None,
        max_skill_level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Richer generator using templates, still table-driven (no hard-coded ranges).
        """
        stimulus = (stimulus or "").lower()
        if stimulus not in self.stimulus_map:
            return {"error": "Invalid stimulus type. Choose from: vo2 max, lactate threshold, anaerobic."}

        wod_type = random.choice(self.stimulus_map[stimulus])
        name = self.generate_wod_name()

        templates_by_type = {
            "For Time": ["ladder_desc", "bookend_run", "chipper_linear", "rft_fixed", "overlay_every_x_sec"],
            "AMRAP": ["amrap_couplet", "amrap_triplet", "amrap_buyin"],
            "Interval": ["interval_blocks"],
            "EMOM": ["emom_single", "emom_alternating"],
            "Alternating EMOM": ["emom_alternating"],
            "Tabata": ["tabata_multi"],
            "Ladder": ["ladder_desc"],
        }
        template = random.choice(templates_by_type.get(wod_type, ["rft_fixed"]))

        def pick_ex(count: int) -> List[Dict[str, Any]]:
            return self._pick_exercises(
                target_muscle=target_muscle or "General",
                count=count,
                equipment_available=equipment_available,
                include_tags=include_tags,
                exclude_tags=exclude_tags,
                max_skill_level=max_skill_level,
            )

        # sensible caps
        def time_cap_for(wt: str) -> int:
            if wt in ["For Time", "Chipper", "Ladder"]:
                return random.choice([15, 18, 20, 22, 30])
            if wt in ["AMRAP"]:
                return random.choice([12, 15, 18, 20])
            if wt in ["EMOM", "Alternating EMOM", "Interval"]:
                return random.choice([10, 12, 15, 18])
            if wt in ["Tabata"]:
                return 8
            return random.choice([12, 15, 20])

        duration = time_cap_for(wod_type)
        lines: List[str] = []
        structured: List[Dict[str, Any]] = []

        ladder_schemes = [[21, 15, 9], [21, 15, 9, 6, 3], [10, 8, 6, 4, 2]]

        if wod_type == "For Time" and template == "ladder_desc":
            moves = pick_ex(random.choice([2, 3]))
            scheme = random.choice(ladder_schemes)
            lines.append(f"For Time – {duration} min cap")
            lines.append(f"{'-'.join(str(s) for s in scheme)} reps of:")
            for ex in moves:
                lines.append(f"- {ex.get('exercise')}")
            for i, ex in enumerate(moves, start=1):
                structured.append(self._structured_item(ex, i, scheme[0], wod_type, duration))

        elif wod_type == "For Time" and template == "bookend_run":
            mid = pick_ex(2)
            scheme = random.choice([[10, 8, 6, 4, 2], [12, 9, 6, 3]])
            lines.append("For Time")
            # Pick a run movement from pool (unit = meters)
            run_candidates = [ex for ex in self._filter_pool(target_muscle, equipment_available, include_tags, exclude_tags, max_skill_level) if (ex.get("unit") or "").lower() == "meters"]
            run_move = run_candidates[0] if run_candidates else {"exercise": "Treadmill Run", "unit": "meters", "range_min": 200, "range_max": 400, "id": None, "equipment": ["treadmill"]}
            run_dist = 2000
            lines.append(f"- {run_dist}m {run_move.get('exercise')}")
            lines.append(f"{'-'.join(str(s) for s in scheme)} reps of:")
            for ex in mid:
                lines.append(f"- {ex.get('exercise')}")
            lines.append(f"- {run_dist}m {run_move.get('exercise')}")
            structured.append(self._structured_item(run_move, 1, run_dist, wod_type, duration))
            for i, ex in enumerate(mid, start=2):
                structured.append(self._structured_item(ex, i, scheme[0], wod_type, duration))
            structured.append(self._structured_item(run_move, len(mid) + 2, run_dist, wod_type, duration))

        elif wod_type == "For Time" and template == "chipper_linear":
            blocks = random.choice([[100, 200, 300, 400], [200, 150, 100, 50]])
            moves = pick_ex(4)
            lines.append(f"For Time – {duration} min cap")
            for i, ex in enumerate(moves):
                val = blocks[i]
                lines.append(self._format_line(ex, val))
                structured.append(self._structured_item(ex, i + 1, val, wod_type, duration))
            # optional short run if no meters unit present
            if all((ex.get("unit") or "").lower() != "meters" for ex in moves):
                tail = random.choice([400, 800])
                # choose a run movement
                run_candidates = [ex for ex in self._filter_pool(target_muscle, equipment_available, include_tags, exclude_tags, max_skill_level) if (ex.get("unit") or "").lower() == "meters"]
                run_move = run_candidates[0] if run_candidates else {"exercise": "Treadmill Run", "unit": "meters", "range_min": 200, "range_max": 400, "id": None, "equipment": ["treadmill"]}
                lines.append(self._format_line(run_move, tail))
                structured.append(self._structured_item(run_move, len(moves) + 1, tail, wod_type, duration))

        elif wod_type == "For Time" and template == "rft_fixed":
            rounds = random.choice([3, 4, 5, 6])
            moves = pick_ex(random.choice([3, 4, 5]))
            reps = random.choice([7, 10, 12, 15])
            lines.append(f"For Time – Time Cap: {duration} min")
            lines.append(f"{rounds} Rounds of:")
            for ex in moves:
                lines.append(self._format_line(ex, reps))
            for i, ex in enumerate(moves, start=1):
                structured.append(self._structured_item(ex, i, reps, wod_type, duration))

        elif wod_type == "For Time" and template == "overlay_every_x_sec":
            primary = pick_ex(1)[0]
            overlay = pick_ex(1)[0]
            primary_total = random.choice([60, 70, 90])
            overlay_sec = random.choice([60, 75, 90])
            lines.append(f"For Time – {duration} min cap")
            lines.append(self._format_line(primary, primary_total))
            lines.append(f"Every {overlay_sec}s perform {overlay.get('exercise')}")
            structured.append(self._structured_item(primary, 1, primary_total, wod_type, duration))
            structured.append(self._structured_item(overlay, 2, 1, wod_type, duration))

        elif wod_type == "AMRAP" and template in ["amrap_couplet", "amrap_triplet"]:
            duration = random.choice([18, 20])
            moves = pick_ex(2 if template == "amrap_couplet" else 3)
            lines.append(f"{duration} Min AMRAP")
            for i, ex in enumerate(moves, start=1):
                reps = self._pick_qty(ex)
                lines.append(self._format_line(ex, reps))
                structured.append(self._structured_item(ex, i, reps, "AMRAP", duration))

        elif wod_type == "AMRAP" and template == "amrap_buyin":
            duration = random.choice([16, 18, 20])
            buyin = pick_ex(1)[0]
            loop = pick_ex(2)
            # choose a buy-in value compatible with its unit
            if (buyin.get("unit") or "reps").lower() == "meters":
                buyin_val = random.choice([400, 800, 1000])
            elif (buyin.get("unit") or "reps").lower() == "seconds":
                buyin_val = random.choice([30, 45, 60])
            else:
                buyin_val = random.choice([10, 20, 30])
            lines.append(f"{duration} Min AMRAP")
            lines.append(f"Buy-in: {self._format_line(buyin, buyin_val)[2:]}")
            lines.append("Then, as many rounds as possible of:")
            structured.append(self._structured_item(buyin, 1, buyin_val, "AMRAP", duration))
            for i, ex in enumerate(loop, start=2):
                reps = self._pick_qty(ex)
                lines.append(self._format_line(ex, reps))
                structured.append(self._structured_item(ex, i, reps, "AMRAP", duration))

        elif wod_type in ["EMOM", "Alternating EMOM"] and template in ["emom_single", "emom_alternating"]:
            duration = random.choice([10, 12, 15])
            if template == "emom_single":
                ex = pick_ex(1)[0]
                reps = self._pick_qty(ex)
                lines.append(f"EMOM {duration} minutes:")
                lines.append(f"- {reps} {ex.get('exercise')} each minute" if (ex.get("unit") or "reps") == "reps"
                            else self._format_line(ex, reps) + " each minute")
                structured.append(self._structured_item(ex, 1, reps, wod_type, duration))
            else:
                moves = pick_ex(2)
                lines.append(f"Alternating EMOM {duration} minutes:")
                for i, ex in enumerate(moves, start=1):
                    reps = self._pick_qty(ex)
                    lines.append(f"- Minute {'Odd' if i == 1 else 'Even'}: {self._format_line(ex, reps)[2:]}")
                    structured.append(self._structured_item(ex, i, reps, "Alternating EMOM", duration))

        elif wod_type == "Interval" and template == "interval_blocks":
            duration = random.choice([16, 20])
            work = random.choice([2, 3, 4])
            rest = random.choice([1, 2])
            moves = pick_ex(random.choice([2, 3]))
            lines.append(f"Work {work} min / Rest {rest} min for {duration} minutes total:")
            for i, ex in enumerate(moves, start=1):
                reps = self._pick_qty(ex)
                lines.append(self._format_line(ex, reps))
                structured.append(self._structured_item(ex, i, reps, "Interval", duration))

        elif wod_type == "Tabata" and template == "tabata_multi":
            duration = 8  # protocol rounds (display only)
            moves = pick_ex(random.choice([2, 3]))
            lines.append("Tabata: 8 rounds of 20s work / 10s rest per movement:")
            for i, ex in enumerate(moves, start=1):
                lines.append(f"- {ex.get('exercise')}")
                structured.append(self._structured_item(ex, i, 20, "Tabata", duration))

        else:
            # Fallback simple For Time triplet
            moves = pick_ex(3)
            lines.append(f"For Time – {duration} min cap")
            for i, ex in enumerate(moves, start=1):
                reps = self._pick_qty(ex)
                lines.append(self._format_line(ex, reps))
                structured.append(self._structured_item(ex, i, reps, "For Time", duration))

        details = "\n".join(lines).strip()
        return {
            "WOD Name": name,
            "Type": wod_type,
            "Estimated Time": f"{duration} min",
            "estimated_time": int(duration), # <-- always numeric
            "details": details,
            "Performance Targets": self.generate_targets(wod_type),
            "exercises": structured,
            "debug": {"muscle": target_muscle, "stimulus": stimulus, "template": template} if self.debug else {},
        }



