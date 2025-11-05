class RunGenerator:
    def __init__(self, user_5k_time=24, debug=False):
        """
        user_5k_time: Current 5km time in minutes (default: 24)
        debug: Enable debug info
        """
        self.user_5k_time = user_5k_time
        self.debug = debug

    def generate(self, duration=60):
        # Calculate pace and Zone 2 target
        five_km_pace_per_km = self.user_5k_time / 5  # min/km
        zone2_percent = 0.70  # 70% of race pace
        zone2_pace = five_km_pace_per_km / zone2_percent
        zone2_kph = 60 / zone2_pace  # convert min/km to km/h

        result = {
            "type": "Run",
            "time": duration,
            "details": (
                f"{duration}-minute Zone 2 run. "
                f"Target pace: ~{round(zone2_percent * 100)}% of 5km race pace "
                f"(~{round(zone2_pace, 2)} min/km or ~{round(zone2_kph, 1)} kph)"
            )
        }

        if self.debug:
            result["debug"] = {
                "five_km_time": self.user_5k_time,
                "pace_per_km": round(five_km_pace_per_km, 2),
                "zone2_percent": zone2_percent,
                "zone2_pace": round(zone2_pace, 2),
                "zone2_kph": round(zone2_kph, 1)
            }

        return result
