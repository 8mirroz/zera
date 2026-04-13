import logging
import os
from typing import List

logger = logging.getLogger(__name__)


class DNAInjector:
    def __init__(self, vault_paths: List[str] = None):
        self.vault_paths = vault_paths or [
            os.getenv("VAULT_PATH", "docs/vault"),
            "wiki/_logs",
            "wiki/_briefs",
        ]

    def get_dna(self, agent_id: str, task_keywords: List[str]) -> str:
        dna_notes = []
        patterns = [f"#{agent_id}", f"#[{agent_id}]", f"- {agent_id}"]

        for vault_dir in self.vault_paths:
            if not os.path.exists(vault_dir):
                continue
            for root, _, files in os.walk(vault_dir):
                for f in files:
                    if not f.endswith(".md"):
                        continue
                    path = os.path.join(root, f)
                    try:
                        with open(path, "r", encoding="utf-8") as file:
                            content = file.read()

                        # Anti-degeneration gate: skip quarantined records
                        if "status: quarantine" in content:
                            continue

                        match_found = any(p in content for p in patterns) or any(
                            kw.lower() in content.lower()
                            for kw in task_keywords
                            if len(kw) > 3
                        )
                        if match_found:
                            dna_notes.append(content[:500])
                    except Exception as exc:
                        logger.debug("Failed to read vault file %s: %s", path, exc)

        if not dna_notes:
            return ""

        dna_block = "\n<collective-wisdom>\n"
        dna_block += "Relevant insights from Living Memory Mesh:\n"
        for note in dna_notes[:3]:
            dna_block += f"- {note.strip()}\n"
        dna_block += "</collective-wisdom>\n"
        return dna_block
