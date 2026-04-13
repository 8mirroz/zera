import json
import os
from pathlib import Path
from datetime import datetime

class ProfileManager:
    """Manages the L1 Stateful Memory (User Persona)."""
    
    def __init__(self, profile_path):
        self.profile_path = Path(profile_path)
        self.profile = self.load()
        
    def load(self):
        if not self.profile_path.exists():
            return {}
        try:
            with open(self.profile_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
            
    def save(self):
        self.profile["last_synced"] = datetime.now().isoformat()
        with open(self.profile_path, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, indent=2, ensure_ascii=False)
            
    def update_preference(self, key, value):
        if "preferences" not in self.profile:
            self.profile["preferences"] = {}
        self.profile["preferences"][key] = value
        self.save()
        
    def add_learned_rule(self, rule):
        if "learned_rules" not in self.profile:
            self.profile["learned_rules"] = []
        if rule not in self.profile["learned_rules"]:
            self.profile["learned_rules"].append(rule)
            self.save()
            
    def get_summary_context(self):
        """Returns a string suitable for system prompt injection."""
        p = self.profile.get("preferences", {})
        c = self.profile.get("context_slots", {})
        rules = self.profile.get("learned_rules", [])
        
        summary = f"USER PERSONA (L1 Memory):\n"
        summary += f"- Name: {self.profile.get('name', 'User')}\n"
        summary += f"- Design Style: {', '.join(p.get('design_style', []))}\n"
        summary += f"- Tech Stack: {', '.join(p.get('tech_stack', []))}\n"
        summary += f"- Focus: {', '.join(c.get('active_focus', []))}\n"
        summary += f"- Recent Rules: {', '.join(rules[-5:]) if rules else 'None'}\n"
        return summary

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--update_rule", help="Add a new learned rule to profile")
    args = parser.parse_args()
    
    pm = ProfileManager("configs/orchestrator/user_profile.json")
    if args.update_rule:
        pm.add_learned_rule(args.update_rule)
        print(f"L1 Memory Updated: Added rule '{args.update_rule}'")
    else:
        print(pm.get_summary_context())
