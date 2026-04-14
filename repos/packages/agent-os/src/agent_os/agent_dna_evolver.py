import os
import re
import yaml
import json
from pathlib import Path
from typing import List, Dict

class AgentDNAEvolver:
    def __init__(self, 
                 quarantine_path: str = "wiki/_quarantine", 
                 agents_path: str = "configs/registry/agents"):
        self.quarantine_path = Path(quarantine_path)
        self.agents_path = Path(agents_path)

    def scan_failures(self) -> List[Dict]:
        failures = []
        if not self.quarantine_path.exists():
            return []
            
        for f in self.quarantine_path.glob("*.md"):
            content = f.read_text()
            # Extract basic info from markdown
            match_query = re.search(r"## Query:?\s*(.*)", content)
            match_agent = re.search(r"\*\*Agent\*\*:?\s*(.*)", content)
            
            if match_query and match_agent:
                failures.append({
                    "query": match_query.group(1).strip(),
                    "failed_agent": match_agent.group(1).strip(),
                    "file": f
                })
        return failures

    def propose_evolution(self):
        failures = self.scan_failures()
        if not failures:
            print("✨ No failures found in quarantine. Your swarm DNA is stable.")
            return

        print(f"🧬 Found {len(failures)} routing failures. Analyzing DNA optimization...")
        
        for fail in failures:
            print(f"\n--- Failure Analysis: '{fail['query']}' ---")
            print(f"Current selection was: {fail['failed_agent']}")
            
            # Suggestion logic (simplistic for Phase 5 initial): 
            # If a query clearly matches keywords of another agent, suggest adding them.
            # In a real v4.0, this would use a LLM to re-classify and suggest trigger diffs.
            
            # For this MVP, we just report that improvement is needed at the trigger level.
            print("💡 Suggestion: Review agent triggers for overlap.")
            print(f"Trace: Task quarantined at {fail['file']}")

if __name__ == "__main__":
    evolver = AgentDNAEvolver()
    evolver.propose_evolution()
