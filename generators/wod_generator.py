
import random
from typing import Any, Dict, List, Optional, Sequence, Union


class WODGenerator:
    """
    Table-driven WOD generator.

    Pass in a data dict containing:
      - data["exercise_pool"]: list[dict] of rows from your exercise_pool table
      - data["muscle_groups"]: optional list[dict] of {"id": int, "name": str}
      - data["exercises"]: optional legacy list for id lookups ({"id": int, "name": str})

    Example:
        data = {
            "muscle_groups": [
                {"id": 1, "name": "Back"}, {"id": 3, "name": "Chest"}, {"id": 7, "name": "Shoulders"},
                {"id": 5, "name": "Glutes/Hamstrings"}, {"id": 6, "name": "Quads"}, {"id": 8, "name": "General"}
            ],
            "exercise_pool": [ ... rows from DB ... ]
        }

        wg = WODGenerator(data, debug=True, seed=42)
        wod = wg.generate(
            target_muscle="Shoulders",
            stimulus="anaerobic",
            equipment_available=["barbell", "dumbbell", "treadmill"],
            include_tags=None,
            exclude_tags=["advanced"],    # optional
            max_skill_level=3             # optional
        )
        print(wod["details"])
    """

    def __init__(
        self,
        data: Dict[str, Any],
        debug: bool = False,
        seed: Optional[int] = None
    ) -> None:
        self.data = data or {}
        self.debug = debug
        if seed is not None:
            random.seed(seed)

        # Workout stimulus -> formats
        self.stimulus_map = {
            "vo2 max": ["AMRAP", "Interval", "Alternating EMOM"],
            "lactate threshold": ["Chipper", "For Time", "Tabata"],
            "anaerobic": ["Ladder", "Death by", "EMOM"]
        }

        # Name generator parts
        self.adjectives = [
            "Savage", "Blazing", "Iron", "Crimson", "Furious",
            "Relentless", "Vicious", "Explosive", "Brutal", "Wicked"
        ]
        self.nouns = [
            "Storm", "Inferno", "Titan", "Crusher", "Blitz",
            "Rage", "Pulse", "Grind", "Surge", "Reaper"
        ]
        self.actions = [
            "Charge", "Strike", "Burn", "Smash", "Blast",
            "Crush", "Rush", "Roar", "Clash", "Ignite"
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

    def _filter_by_equipment(
        self, pool: List[Dict[str, Any]], equipment_available: Optional[Sequence[str]]
    ) -> List[Dict[str, Any]]:
        if not equipment_available:
            return pool
        avail = set(self._lower_list(equipment_available))
        filtered = []
        for ex in pool:
            eq = set(self._lower_list(ex.get("equipment") or []))
            # keep if exercise needs no equipment OR is subset of available
            if not eq or eq.issubset(avail):
                filtered.append(ex)
        return filtered

    def _filter_by_tags(
        self,
        pool: List[Dict[str, Any]],
        include_tags: Optional[Sequence[str]],
        exclude_tags: Optional[Sequence[str]]
    ) -> List[Dict[str, Any]]:
        if not include_tags and not exclude_tags:
            return pool
        incl = set(self._lower_list(include_tags))
        excl = set(self._lower_list(exclude_tags))
        out = []
        for ex in pool:
            tags = set(self._lower_list(ex.get("tags") or []))
            if incl and not (tags & incl):
                continue  # none of the include tags present
            if excl and (tags & excl):
                continue  # any excluded tag present
            out.append(ex)
        return out

    def _filter_by_skill_level(
        self, pool: List[Dict[str, Any]], max_skill_level: Optional[int]
    ) -> List[Dict[str, Any]]:
        if not max_skill_level:
            return pool
        out = []
        for ex in pool:
            level = ex.get("skill_level")
            # If no skill_level, treat as easy (1)
            level = 1 if level is None else int(level)
            if level <= max_skill_level:
                out.append(ex)
        return out

    def _filter_pool(
        self,
        target_muscle: Optional[Union[int, str]],
        equipment_available: Optional[Sequence[str]],
        include_tags: Optional[Sequence[str]],
        exclude_tags: Optional[Sequence[str]],
        max_skill_level: Optional[int],
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
                # fallback: filter by name/tags containing the word
                key = target_muscle.lower()
                pool = [
                    ex for ex in pool
                    if key in (ex.get("exercise", "") or "").lower()
                    or key in " ".join(self._lower_list(ex.get("tags")))
                ]

        # Additional filters
        pool = self._filter_by_equipment(pool, equipment_available)
        pool = self._filter_by_tags(pool, include_tags, exclude_tags)
        pool = self._filter_by_skill_level(pool, max_skill_level)

        # If filtering nuked the pool, fall back to the entire set
        if not pool:
            pool = list(self.data.get("exercise_pool") or [])
        return pool

    def _pick_exercises(
        self,
        target_muscle: Optional[Union[int, str]],
        count: int,
        equipment_available: Optional[Sequence[str]],
        include_tags: Optional[Sequence[str]],
        exclude_tags: Optional[Sequence[str]],
        max_skill_level: Optional[int],
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

    # ----------------------------
    # ---- Quantity & Formatting -
    # ----------------------------

    @staticmethod
    def _format_line(ex: Dict[str, Any], qty: int) -> str:
        unit = (ex.get("unit") or "reps").lower()
        name = ex.get("exercise") or "Unknown"
        suffix = ""

        rx_m = ex.get("rx_male_kg")
        rx_f = ex.get("rx_female_kg")
        if rx_m or rx_f:
            # Show both if present, otherwise a single value
            if rx_m and rx_f:
                suffix = f" ({int(rx_m) if rx_m == int(rx_m) else rx_m}/{int(rx_f) if rx_f == int(rx_f) else rx_f}kg)"
            else:
                val = rx_m if rx_m is not None else rx_f
                suffix = f" ({int(val) if val == int(val) else val}kg)"

        if unit == "meters":
            return f"- {qty}m {name}{suffix}"
        elif unit == "seconds":
            return f"- {qty}s {name}{suffix}"
        else:
            return f"- {qty} {name}{suffix}"

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

    # ----------------------------
    # ---- Targets & Formats -----
    # ----------------------------

    def generate_targets(self, wod_type: str) -> Dict[str, str]:
        return {
            "AMRAP": {
                "Beginner": "3-4 rounds",
                "Intermediate": "5-6 rounds",
                "Advanced": "7-8 rounds",
                "Elite": "9+ rounds",
            },
            "Chipper": {
                "Beginner": "Complete in 20+ min",
                "Intermediate": "15-20 min",
                "Advanced": "10-15 min",
                "Elite": "< 10 min",
            },
            "Interval": {
                "Beginner": "1-2 rounds/interval",
                "Intermediate": "2-3 rounds/interval",
                "Advanced": "3-4 rounds/interval",
                "Elite": "4+ rounds/interval",
            },
            "Tabata": {
                "Beginner": "8-10 reps per 20s",
                "Intermediate": "11-13 reps per 20s",
                "Advanced": "14-16 reps per 20s",
                "Elite": "17+ reps per 20s",
            },
            "For Time": {
                "Beginner": "20+ min",
                "Intermediate": "15-20 min",
                "Advanced": "10-15 min",
                "Elite": "< 10 min",
            },
            "Ladder": {
                "Beginner": "Complete 3 rounds",
                "Intermediate": "Complete 4 rounds",
                "Advanced": "Complete 5 rounds",
                "Elite": "All rounds unbroken",
            },
            "Death by": {
                "Beginner": "5-7 minutes",
                "Intermediate": "8-10 minutes",
                "Advanced": "11-13 minutes",
                "Elite": "14+ minutes",
            },
            "EMOM": {
                "Beginner": "6-8 minutes",
                "Intermediate": "9-12 minutes",
                "Advanced": "13-15 minutes",
                "Elite": "Full duration unbroken",
            },
            "Alternating EMOM": {
                "Beginner": "6-8 minutes",
                "Intermediate": "9-12 minutes",
                "Advanced": "13-15 minutes",
                "Elite": "Full duration unbroken",
            },
        }.get(wod_type, {})

    # ----------------------------
    # --------- Generate ---------
    # ----------------------------

    def generate(
        self,
        target_muscle: Optional[Union[int, str]] = None,
        stimulus: str = "anaerobic",
        duration_options: Sequence[int] = (12, 15, 20),
        # Selection constraints
        equipment_available: Optional[Sequence[str]] = None,
        include_tags: Optional[Sequence[str]] = None,
        exclude_tags: Optional[Sequence[str]] = None,
        max_skill_level: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Build a WOD dictionary with string details and a structured exercise list.
        """
        stimulus = (stimulus or "").lower()
        if stimulus not in self.stimulus_map:
            return {"error": "Invalid stimulus type. Choose from: vo2 max, lactate threshold, anaerobic."}

        wod_type = random.choice(self.stimulus_map[stimulus])
        name = self.generate_wod_name()
        duration = random.choice(list(duration_options))

        # Exercise count per format
        if wod_type == "EMOM":
            count = 1
        elif wod_type == "Alternating EMOM":
            count = 2
        else:
            count = 3

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
                "debug": {
                    "muscle": target_muscle,
                    "stimulus": stimulus,
                    "selected_exercises": [],
                } if self.debug else {},
            }

        lines: List[str] = [f"{wod_type} for {duration} minutes"]

        # ---- Build description by format ----
        if wod_type == "AMRAP":
            lines.append("Complete as many rounds as possible:")
            for ex in exercises:
                qty = self._pick_qty(ex)
                lines.append(self._format_line(ex, qty))

        elif wod_type == "Chipper":
            lines.append("Work through the following:")
            for ex in exercises:
                qty = self._pick_qty(ex, multiplier=3.0)  # higher volume
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

        # ---- Structured exercises for syncing/logging ----
        structured: List[Dict[str, Any]] = []
        for order, ex in enumerate(exercises, start=1):
            qty = self._pick_qty(ex)
            # If you still keep a legacy `exercises` mapping, try it first; else fall back to exercise_pool id
            ex_id = next(
                (e.get("id") for e in self.data.get("exercises", []) if e.get("name") == ex.get("exercise")),
                ex.get("id"),
            )

            # Optionally surface sex-specific RX; here we include a neutral text
            expected_weight = ""
            rx_m = ex.get("rx_male_kg")
            rx_f = ex.get("rx_female_kg")
            if rx_m or rx_f:
                if rx_m and rx_f:
                    expected_weight = f"{rx_m}/{rx_f}kg"
                else:
                    expected_weight = f"{rx_m or rx_f}kg"

            structured.append({
                "name": ex.get("exercise"),
                "exercise_id": ex_id,
                "set": 1,
                "reps": str(qty),                 # quantity formatted as reps/meters/seconds in details
                "intensity": "High",
                "rest": 30,
                "notes": f"{wod_type} format",
                "exercise_order": order,
                "tempo": "",
                "expected_weight": expected_weight,
                "equipment": ", ".join(ex.get("equipment") or []),
            })

        return {
            "WOD Name": self.generate_wod_name(),
            "Type": wod_type,
            "Estimated Time": f"{duration} min",
            "details": "\n".join(lines),
            "Performance Targets": self.generate_targets(wod_type),
            "exercises": structured,
            "debug": {
                "muscle": target_muscle,
                "stimulus": stimulus,
                "selected_exercises": [ex.get("exercise") for ex in exercises],
            } if self.debug else {},
        }


