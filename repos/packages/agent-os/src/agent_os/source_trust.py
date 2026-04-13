from __future__ import annotations

from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


def load_source_trust_policy(repo_root: Path) -> dict[str, Any]:
    path = Path(repo_root) / "configs/tooling/source_trust_policy.yaml"
    if not path.exists():
        return {
            "default_tier": "Tier C",
            "tiers": {
                "Tier A": {"allowed_for_capability_promotion": True},
                "Tier B": {"allowed_for_capability_promotion": True},
                "Tier C": {"allowed_for_capability_promotion": False},
            },
        }
    parsed = parse_simple_yaml(path.read_text(encoding="utf-8"))
    return parsed if isinstance(parsed, dict) else {}


def evaluate_source_tier_policy(
    source_policy: dict[str, Any],
    *,
    source_tier: str | None,
    requests_capability_promotion: bool,
) -> dict[str, Any]:
    default_tier = str(source_policy.get("default_tier") or "Tier C")
    tiers = source_policy.get("tiers", {})
    if not isinstance(tiers, dict):
        tiers = {}
    tier_name = str(source_tier or default_tier)
    tier_row = tiers.get(tier_name, {})
    if not isinstance(tier_row, dict):
        tier_row = {}
    allowed_for_promotion = bool(tier_row.get("allowed_for_capability_promotion", False))
    blocked = bool(requests_capability_promotion and not allowed_for_promotion)
    if blocked:
        reason = f"source tier {tier_name} does not allow capability promotion"
    elif requests_capability_promotion:
        reason = f"source tier {tier_name} allows capability promotion"
    else:
        reason = f"source tier {tier_name} accepted"
    return {
        "source_tier": tier_name,
        "requests_capability_promotion": bool(requests_capability_promotion),
        "allowed_for_capability_promotion": allowed_for_promotion,
        "blocked": blocked,
        "reason": reason,
    }
