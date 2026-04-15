#!/usr/bin/env python3
"""
query_experience.py — Query historical wisdom from the Obsidian vault.
Matches skills and tasks to past decisions, patterns, and session outcomes.
"""

import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_experience(skill_name: str, vault: str, limit: int = 3, context: str = "") -> List[Dict[str, Any]]:
    """
    Search the vault for experiences related to a skill or context.
    
    Args:
        skill_name: Name of the skill to search for.
        vault: Path to the Obsidian vault or repo root.
        limit: Max number of results.
        context: Additional task context for better matching.
        
    Returns:
        List of dictionaries containing experience snippets.
    """
    vault_path = Path(vault).expanduser()
    if not vault_path.exists():
        # Try to find vault relative to repo root if path is relative
        # Or look for common locations
        common_locations = [
            vault_path,
            vault_path / "antigravity-vault",
            Path.home() / "antigravity-vault"
        ]
        found = False
        for loc in common_locations:
            if loc.exists() and (loc / "memory").exists():
                vault_path = loc
                found = True
                break
        if not found:
            return []

    search_dirs = [
        vault_path / "memory" / "patterns",
        vault_path / "memory" / "sessions",
        vault_path / "memory" / "decisions",
        vault_path / "knowledge" / "ki"
    ]
    
    results = []
    seen_files = set()
    
    # Simple keyword matching for now, can be improved with TF-IDF or semantic search
    query_terms = set(re.findall(r'\w+', f"{skill_name} {context}".lower()))
    
    for sdir in search_dirs:
        if not sdir.exists():
            continue
            
        for f in sdir.glob("*.md"):
            if f in seen_files:
                continue
                
            content = f.read_text(errors="ignore")
            content_lower = content.lower()
            
            # Simple scoring
            score = 0
            for term in query_terms:
                if term in content_lower:
                    score += 1
            
            if score > 0:
                # Extract a meaningful snippet
                # Try to find the skill name or some context terms
                # For now, just take the first 200 chars or first paragraph
                lines = content.split('\n')
                snippet = ""
                for line in lines:
                    if line.strip() and not line.startswith('---'):
                        snippet = line.strip()
                        break
                
                results.append({
                    "title": f.name,
                    "source": str(f.relative_to(vault_path)),
                    "snippet": snippet[:300],
                    "score": score,
                    "full_path": str(f)
                })
                seen_files.add(f)

    # Sort by score and return top results
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]


def main():
    parser = argparse.ArgumentParser(description="Query experience from Obsidian vault")
    parser.add_argument("skill", help="Skill name or query")
    parser.add_argument("--vault", default="~/antigravity-vault", help="Vault path")
    parser.add_argument("--limit", type=int, default=3, help="Max results")
    parser.add_argument("--context", default="", help="Additional context")
    
    args = parser.parse_args()
    
    experiences = get_experience(args.skill, args.vault, args.limit, args.context)
    print(json.dumps(experiences, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
