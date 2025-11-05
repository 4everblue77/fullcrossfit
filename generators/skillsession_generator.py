class SkillSessionGenerator:
    def __init__(self, supabase,debug=False):
        """
        #supabase: Supabase client instance
        """
        self.data = data  # ✅ Store exercise dataset
        self.supabase = supabase
        self.debug = debug


    def get_skill_id(self, skill_name):
        response = self.supabase.table("skills").select("skill_id").eq("skill_name", skill_name).execute()
        if response.data:
            return response.data[0]["skill_id"]
        return None

    def get_session_plan(self, skill_id, week):
        response = self.supabase.table("skill_plans").select("*").eq("skill_id", skill_id).eq("week", week).execute()
        if response.data:
            return response.data[0]
        return None

    def generate(self, skill_name, week):
        skill_id = self.get_skill_id(skill_name)
        if not skill_id:
            return {
                "type": "Skill Session",
                "skill": skill_name,
                "week": week,
                "details": f"No skill found with name '{skill_name}'",
                "session": None,
                "exercises": []
            }
    
        session = self.get_session_plan(skill_id, week)
        if not session:
            return {
                "type": "Skill Session",
                "skill": skill_name,
                "week": week,
                "details": f"No session plan found for week {week}",
                "session": None,
                "exercises": []
            }
    
        # Parse session_plan into structured exercises
        # Assuming session["session_plan"] is a list of dicts like:
        # [{"name": "Wall Walk", "sets": 3, "reps": "5", "rest": 60, "notes": "Strict form"}]
        raw_plan = session.get("session_plan", [])
        exercises = []
        raw_plan = [item if isinstance(item, dict) else {"name": item} for item in raw_plan]
        for i, item in enumerate(raw_plan, start=1):
            

            ex_id = next((e["id"] for e in self.data["exercises"] if e["name"] == name), None)

            exercises.append({
                "name": item.get("name", f"Skill Move {i}"),
                "exercise_id": ex_id,
                "set": item.get("sets", 1),
                "reps": item.get("reps", ""),
                "intensity": item.get("intensity", "Skill Focus"),
                "rest": item.get("rest", 30),
                "notes": item.get("notes", ""),
                "exercise_order": i,
                "tempo": item.get("tempo", ""),
                "expected_weight": item.get("expected_weight", ""),
                "equipment": item.get("equipment", "")
            })
    
        return {
            "type": "Skill Session",
            "skill": skill_name,
            "week": week,
            "focus": session.get("focus", ""),
            "details": f"Week {week} skill session for {skill_name}",
            "session_plan": raw_plan,
            "exercises": exercises  # ✅ Enables syncing
        }
