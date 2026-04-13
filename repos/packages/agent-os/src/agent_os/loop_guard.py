from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


@dataclass
class LoopGuardDecision:
    allowed: bool
    blocked: bool
    reason: str
    signature: str
    duplicate_count: int
    budget_limit_hit: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "blocked": self.blocked,
            "reason": self.reason,
            "signature": self.signature,
            "duplicate_count": self.duplicate_count,
            "budget_limit_hit": self.budget_limit_hit,
        }


def load_budget_profile(repo_root: Path, profile_name: str | None) -> dict[str, Any]:
    path = Path(repo_root) / "configs/tooling/budget_policy.yaml"
    if not path.exists():
        return {}
    data = parse_simple_yaml(path.read_text(encoding="utf-8"))
    profiles = data.get("profiles", {})
    if not isinstance(profiles, dict):
        return {}
    row = profiles.get(str(profile_name or "").strip(), {})
    return dict(row) if isinstance(row, dict) else {}


class LoopGuard:
    """Detect repeated initiative chains and budget overruns before execution."""

    def __init__(self, repo_root: Path, *, budget_profile: str | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.budget_profile = str(budget_profile or "").strip() or None
        self.profile = load_budget_profile(self.repo_root, self.budget_profile)

    @staticmethod
    def signature_for(proposal: dict[str, Any]) -> str:
        title = str(proposal.get("title") or "").strip().lower()
        action_type = str(proposal.get("action_type") or "unknown").strip().lower()
        return json.dumps({"action_type": action_type, "title": title}, sort_keys=True, ensure_ascii=False)

    def decide(
        self,
        proposal: dict[str, Any],
        *,
        signatures_seen: dict[str, int],
        total_actions_seen: int,
        max_actions: int | None = None,
    ) -> LoopGuardDecision:
        signature = self.signature_for(proposal)
        duplicate_count = int(signatures_seen.get(signature, 0))
        configured_max_actions = max_actions
        if configured_max_actions is None:
            raw = self.profile.get("max_recursive_depth")
            configured_max_actions = int(raw) if raw not in (None, "") else 4
        budget_limit_hit = total_actions_seen >= max(1, int(configured_max_actions))
        if budget_limit_hit:
            return LoopGuardDecision(
                allowed=False,
                blocked=True,
                reason=f"Action chain exceeds max_actions={configured_max_actions}",
                signature=signature,
                duplicate_count=duplicate_count,
                budget_limit_hit=True,
            )
        if duplicate_count >= 1:
            return LoopGuardDecision(
                allowed=False,
                blocked=True,
                reason="Repeated proposal signature detected",
                signature=signature,
                duplicate_count=duplicate_count,
                budget_limit_hit=False,
            )
        return LoopGuardDecision(
            allowed=True,
            blocked=False,
            reason="Proposal passed loop guard",
            signature=signature,
            duplicate_count=duplicate_count,
            budget_limit_hit=False,
        )
