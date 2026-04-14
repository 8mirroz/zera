import os
import yaml
import json
import subprocess
import argparse
from pathlib import Path

def run_matcher(task_text):
    # Smart skill matching was moved to the agent_os package
    # We use -m to run it as a module, assuming src is in PYTHONPATH
    # or we can point to the absolute path.
    # Given the existing structure, we'll point to the new location.
    cmd = [
        "python3", 
        "repos/packages/agent-os/src/agent_os/smart_skill_matching.py", 
        task_text, 
        "--json"
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error running matcher: {e}")
        return []

def run_benchmark(skills_dir):
    results = {
        "summary": {"total": 0, "passed": 0, "accuracy": 0.0},
        "details": []
    }
    
    skills_path = Path(skills_dir)
    for skill_path in skills_path.iterdir():
        if not skill_path.is_dir():
            continue
            
        eval_file = skill_path / "eval_cases.yaml"
        if not eval_file.exists():
            continue
            
        skill_name = skill_path.name
        with open(eval_file, "r") as f:
            data = yaml.safe_load(f)
            cases = data.get("cases", [])
            
        for case in cases:
            prompt = case.get("prompt")
            expected = case.get("expected_skill")
            results["summary"]["total"] += 1
            
            matches = run_matcher(prompt)
            top_match = matches[0]["name"] if matches else None
            
            passed = top_match == expected
            if passed:
                results["summary"]["passed"] += 1
            
            results["details"].append({
                "prompt": prompt,
                "expected": expected,
                "actual": top_match,
                "passed": passed,
                "rankings": [m["name"] for m in matches]
            })
            
    if results["summary"]["total"] > 0:
        results["summary"]["accuracy"] = results["summary"]["passed"] / results["summary"]["total"]
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Antigravity Skill Accuracy Benchmark')
    parser.add_argument('--skills_dir', default='.agent/skills', help='Directory containing skills')
    parser.add_argument('--output', help='Save results to JSON file')
    
    args = parser.parse_args()
    
    results = run_benchmark(args.skills_dir)
    
    print("\n=== SKILL ACCURACY BENCHMARK RESULT ===")
    print(f"Total Cases: {results['summary']['total']}")
    print(f"Passed:      {results['summary']['passed']}")
    print(f"Accuracy:    {results['summary']['accuracy']:.2%}")
    print("-" * 40)
    
    if results["summary"]["accuracy"] < 1.0:
        print("\nFailures:")
        for d in results["details"]:
            if not d["passed"]:
                print(f"❌ '{d['prompt']}' -> expected: {d['expected']}, actual: {d['actual']}")
    else:
        print("\n✅ All cases passed!")

    if args.output:
        with open(args.output, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.output}")

if __name__ == "__main__":
    main()
