import os
import yaml
import json
import subprocess
import argparse
from pathlib import Path

def run_benchmark():
    cmd = [
        "python3", 
        "repos/packages/agent-os/scripts/skill_accuracy_benchmark.py", 
        "--output", "tmp/benchmark_results.json"
    ]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        with open("tmp/benchmark_results.json", "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error running benchmark: {e}")
        return None

def analyze_failure(failure):
    prompt = failure["prompt"]
    expected = failure["expected"]
    actual = failure["actual"]
    
    print(f"\n--- Analyzing failure: '{prompt}' ---")
    print(f"Expected: {expected}")
    print(f"Actual:   {actual}")
    
    # Read skill files
    expected_path = Path(f".agent/skills/{expected}/SKILL.md")
    actual_path = Path(f".agent/skills/{actual}/SKILL.md") if actual else None
    
    expected_content = expected_path.read_text() if expected_path.exists() else ""
    actual_content = actual_path.read_text() if actual_path and actual_path.exists() else ""
    
    # Generate evolution request
    evolution_query = f"""
    The routing system incorrectly chose '{actual}' instead of '{expected}' for the prompt: '{prompt}'.
    
    Current '{expected}' skill:
    ```markdown
    {expected_content[:500]}...
    ```
    
    Current '{actual}' skill:
    ```markdown
    {actual_content[:500]}...
    ```
    
    TASK: Propose an updated YAML frontmatter for '{expected}' (specifically ‘triggers’ and ‘description’) so that it is more likely to be chosen for this prompt, while still being accurate for its domain. 
    Also, identify if any triggers in '{actual}' are too broad and causing the mismatch.
    """
    
    print("\n[Self-Healing Prompt generated]")
    return evolution_query

def analyze_mastery_failure(skill_name, mastery):
    success = mastery.get("success", 0)
    failed = mastery.get("failed", 0)
    affinity = mastery.get("task_affinity", {})
    
    print(f"\n--- Analyzing behavior failure for skill: '{skill_name}' ---")
    print(f"Success: {success}, Failed: {failed}")
    
    skill_path = Path(f".agent/skills/{skill_name}/SKILL.md")
    content = skill_path.read_text() if skill_path.exists() else ""
    
    evolution_query = f"""
    The skill '{skill_name}' has a poor success rate ({success}/{success+failed}).
    Current affinity: {json.dumps(affinity, indent=2)}
    
    Skill Content:
    ```markdown
    {content[:1000]}
    ```
    
    TASK: Analyze why this skill might be failing. Is the 'description' or 'Use when...' section too broad, leading to its selection in inappropriate contexts? 
    Propose refinements to make it more specialized and effective.
    """
    return evolution_query

def main():
    parser = argparse.ArgumentParser(description='Antigravity Skill Evolution Loop')
    parser.add_argument('--run', action='store_true', help='Run the evolution loop')
    parser.add_argument('--behavior', action='store_true', help='Include behavior (mastery) analysis')
    
    args = parser.parse_args()
    
    # 1. Accuracy Evolution
    results = run_benchmark()
    if results:
        accuracy = results["summary"]["accuracy"]
        print(f"Current System Routing Accuracy: {accuracy:.2%}")
        
        failures = [d for d in results["details"] if not d["passed"]]
        if failures:
            print(f"Found {len(failures)} routing failures. Starting evolution cycle...")
            for failure in failures:
                query = analyze_failure(failure)
                print("-" * 50)
                print("ROUTING EVOLUTION PROMPT:")
                print(query)
                print("-" * 50)

    # 2. Behavior Evolution
    if args.behavior:
        mastery_path = Path(__file__).parent / "mastery.json"
        if mastery_path.exists():
            with open(mastery_path, "r") as f:
                mastery_db = json.load(f)
            
            for skill_name, m in mastery_db.items():
                total = m.get("success", 0) + m.get("failed", 0)
                if total > 5 and (m.get("success", 0) / total) < 0.7:
                    query = analyze_mastery_failure(skill_name, m)
                    print("-" * 50)
                    print("BEHAVIOR EVOLUTION PROMPT:")
                    print(query)
                    print("-" * 50)

if __name__ == "__main__":
    # Ensure tmp directory exists
    os.makedirs("tmp", exist_ok=True)
    main()
