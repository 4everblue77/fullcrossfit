class SkillSessionGenerator:
    def __init__(self, supabase):
        """
        supabase: Supabase client instance
        """
        self.supabase = supabase

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
                "session": None
            }

        session = self.get_session_plan(skill_id, week)
        if not session:
            return {
                "type": "Skill Session",
                "skill": skill_name,
                "week": week,
                "details": f"No session plan found for week {week}",
                "session": None
            }

        return {
            "type": "Skill Session",
            "skill": skill_name,
            "week": week,
            "focus": session["focus"],
            "details": f"Week {week} skill session for {skill_name}",
            "session_plan": session["session_plan"]
        }
