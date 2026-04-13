from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PersonaModeRouter:
    """Keyword-based mode router for persona-specific response shaping."""

    def __init__(self, repo_root: Path, config_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.config_path = config_path or (self.repo_root / "configs/tooling/zera_mode_router.json")
        self.config = self._load_config()
        self.default_mode = str(self.config.get("default_mode") or "plan")

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return {"default_mode": "plan", "rules": []}
        try:
            data = json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception:
            return {"default_mode": "plan", "rules": []}
        if not isinstance(data, dict):
            return {"default_mode": "plan", "rules": []}
        return data

    def select_mode(self, text: str, *, default_mode: str | None = None) -> str:
        """Select mode by scoring all rules and returning the highest-scoring match."""
        normalized = str(text or "").lower()
        rules = self.config.get("rules", [])
        best_mode: str | None = None
        best_score = 0
        if isinstance(rules, list):
            for row in rules:
                if not isinstance(row, dict):
                    continue
                mode = str(row.get("mode") or "").strip()
                keywords = row.get("keywords", [])
                if not mode or not isinstance(keywords, list):
                    continue
                score = sum(
                    1 for keyword in keywords
                    if str(keyword).strip().lower() and str(keyword).strip().lower() in normalized
                )
                if score > best_score:
                    best_score = score
                    best_mode = mode
        return best_mode if best_mode else str(default_mode or self.default_mode or "plan")

