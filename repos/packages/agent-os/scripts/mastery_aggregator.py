import json
import os
from pathlib import Path
from collections import defaultdict

def aggregate_mastery(log_path, mastery_path):
    if not os.path.exists(log_path):
        print(f"Log file not found: {log_path}")
        return
        
    # 1. Load existing mastery
    mastery = {}
    if os.path.exists(mastery_path):
        with open(mastery_path, "r") as f:
            mastery = json.load(f)
            
    # 2. Scrape traces for correlations
    selections = {} # run_id -> selection_data
    outcomes = {}   # run_id -> success/fail
    
    with open(log_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            try:
                event = json.loads(line)
                run_id = event.get("run_id")
                if not run_id: continue
                
                event_type = event.get("event_type")
                
                if event_type == "skill_selection_metadata":
                    selections[run_id] = event.get("data")
                    
                # Support multiple outcome event types
                if event_type in ["benchmark_run_completed", "eggent_auto_flow", "agent_run_completed"]:
                    data = event.get("data", {})
                    passed = data.get("passed") if "passed" in data else (event.get("status") == "ok")
                    outcomes[run_id] = passed
            except Exception: continue
            
    # 3. Correlate and Update
    updated_skills = set()
    for run_id, sel in selections.items():
        if run_id in outcomes:
            skill_name = sel.get("top_skill")
            task_type = sel.get("task_type") or "unknown"
            passed = outcomes[run_id]
            
            if skill_name not in mastery:
                mastery[skill_name] = {"success": 0, "failed": 0, "task_affinity": {}}
                
            if passed:
                mastery[skill_name]["success"] += 1
                affinity = mastery[skill_name]["task_affinity"].get(task_type, 1.0)
                mastery[skill_name]["task_affinity"][task_type] = min(2.0, affinity + 0.1)
            else:
                mastery[skill_name]["failed"] += 1
                affinity = mastery[skill_name]["task_affinity"].get(task_type, 1.0)
                mastery[skill_name]["task_affinity"][task_type] = max(0.1, affinity - 0.2)
                
            updated_skills.add(skill_name)
            
    # 4. Save updated mastery
    with open(mastery_path, "w") as f:
        json.dump(mastery, f, indent=2)
        
    print(f"Mastery aggregation complete. Updated skills: {', '.join(updated_skills)}")
    return mastery

def main():
    log_path = "logs/agent_traces.jsonl"
    mastery_path = Path(__file__).parent / "mastery.json"
    aggregate_mastery(log_path, mastery_path)

if __name__ == "__main__":
    main()
