import os
import re
import yaml
import json
import argparse
import sys
from pathlib import Path

# Add src to path for observability
scripts_dir = Path(__file__).parent
src_dir = scripts_dir.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

try:
    from agent_os.observability import emit_event
except ImportError:
    def emit_event(*args, **kwargs): pass

def parse_skill(skill_path):
    with open(skill_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract YAML frontmatter
    match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if not match:
        return None
    
    try:
        metadata = yaml.safe_load(match.group(1))
        metadata['path'] = skill_path
        return metadata
    except Exception:
        return None

def score_skill(skill, task_text, mastery_db=None, task_type=None):
    score = 0
    task_text = task_text.lower()
    skill_name = skill.get('name', '')
    
    # 1. Trigger matches (High weight)
    triggers = skill.get('triggers', [])
    for trigger in triggers:
        if trigger.lower() in task_text:
            score += 10
            
    # 2. Description keyword matching (Medium weight)
    description = skill.get('description', '').lower()
    task_words = set(re.findall(r'\w+', task_text))
    desc_words = set(re.findall(r'\w+', description))
    overlap = task_words.intersection(desc_words)
    score += len(overlap) * 2
    
    # 3. Exact name match (Highest weight)
    if skill_name.lower() in task_text:
        score += 20
        
    # 4. Mastery Boost (Adaptive weight)
    if mastery_db and skill_name in mastery_db:
        m = mastery_db[skill_name]
        success = m.get('success', 0)
        failed = m.get('failed', 0)
        total = success + failed
        if total > 0:
            affinity = m.get('task_affinity', {}).get(task_type, 1.0) if task_type else 1.0
            boost = (success / total) * affinity * 5 # Max boost of +5
            score += boost
            
    return score

def main():
    parser = argparse.ArgumentParser(description='Smart Skill Matcher for Antigravity')
    parser.add_argument('task', help='Task description to match against')
    parser.add_argument('--skills_dir', default='.agents/skills', help='Directory containing skills')
    parser.add_argument('--limit', type=int, default=5, help='Limit number of results')
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    parser.add_argument('--run_id', help='Run ID for observability tracking')
    parser.add_argument('--task_type', help='Task type (T1-T7) for mastery affinity')
    
    args = parser.parse_args()
    
    # Load Mastery DB
    mastery_db = {}
    mastery_path = Path(__file__).parent / "mastery.json"
    if mastery_path.exists():
        try:
            with open(mastery_path, "r") as f:
                mastery_db = json.load(f)
        except Exception: pass

    skills = []
    for root, dirs, files in os.walk(args.skills_dir):
        if 'SKILL.md' in files:
            skill = parse_skill(os.path.join(root, 'SKILL.md'))
            if skill:
                skills.append(skill)
                
    results = []
    for skill in skills:
        score = score_skill(skill, args.task, mastery_db, args.task_type)
        if score > 0:
            results.append({
                'name': skill.get('name'),
                'score': score,
                'description': skill.get('description'),
                'path': skill.get('path')
            })
            
    results.sort(key=lambda x: x['score'], reverse=True)
    results = results[:args.limit]
    
    # Emit event for CSM tracking
    if args.run_id and results:
        emit_event("skill_selection_metadata", {
            "run_id": args.run_id,
            "task_type": args.task_type,
            "top_skill": results[0]["name"],
            "all_matches": [r["name"] for r in results],
            "scores": {r["name"]: r["score"] for r in results}
        })

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print(f"Top matches for task: '{args.task}'")
        for r in results:
            print(f"- {r['name']} (Score: {r['score']:.2f}): {r['description'][:100]}...")

if __name__ == "__main__":
    main()
