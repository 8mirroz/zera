from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml


@dataclass
class ConfidenceFactors:
    evidence_quality: float = 0.5
    source_reliability: float = 0.5
    historical_success: float = 0.5
    model_capability_match: float = 0.5
    risk_assessment: float = 0.5


@dataclass
class ConfidenceScore:
    level: int
    score: float
    autonomy_allowed: bool
    action_class: str
    factors: ConfidenceFactors
    requires_approval: bool
    description: str


@dataclass
class ConfidenceDecision:
    action_type: str
    confidence_score: float
    confidence_level: int
    autonomy_allowed: bool
    action_class: str
    requires_approval: bool
    escalate_to: str | None
    reason: str
    degradation_applied: float = 0.0


class ConfidenceScorer:
    WEIGHTS = {
        "evidence_quality": 0.25,
        "source_reliability": 0.20,
        "historical_success": 0.20,
        "model_capability_match": 0.15,
        "risk_assessment": 0.20,
    }

    def __init__(self, repo_root: Path, config_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.config_path = config_path or (
            self.repo_root / "configs/tooling/confidence_thresholds.yaml"
        )
        self.config = self._load_config()

    def _load_config(self) -> dict[str, Any]:
        if not self.config_path.exists():
            return self._default_config()
        return parse_simple_yaml(self.config_path.read_text(encoding="utf-8"))

    def _default_config(self) -> dict[str, Any]:
        return {
            "version": "1.0",
            "confidence_levels": {
                "level_1": {
                    "score_min": 0.0,
                    "score_max": 0.4,
                    "autonomy_allowed": False,
                },
                "level_2": {
                    "score_min": 0.4,
                    "score_max": 0.6,
                    "autonomy_allowed": False,
                },
                "level_3": {
                    "score_min": 0.6,
                    "score_max": 0.75,
                    "autonomy_allowed": True,
                },
                "level_4": {
                    "score_min": 0.75,
                    "score_max": 0.85,
                    "autonomy_allowed": True,
                },
                "level_5": {
                    "score_min": 0.85,
                    "score_max": 0.95,
                    "autonomy_allowed": True,
                },
                "level_6": {
                    "score_min": 0.95,
                    "score_max": 1.0,
                    "autonomy_allowed": True,
                },
            },
            "confidence_factors": self.WEIGHTS,
            "degradation_rules": {
                "enabled": True,
                "confidence_penalty_per_failure": 0.15,
                "min_confidence_floor": 0.3,
            },
        }

    def compute_confidence(
        self,
        evidence_quality: float = 0.5,
        source_reliability: float = 0.5,
        historical_success: float = 0.5,
        model_capability_match: float = 0.5,
        risk_assessment: float = 0.5,
        retry_count: int = 0,
    ) -> float:
        factors = ConfidenceFactors(
            evidence_quality=evidence_quality,
            source_reliability=source_reliability,
            historical_success=historical_success,
            model_capability_match=model_capability_match,
            risk_assessment=risk_assessment,
        )

        weighted = (
            factors.evidence_quality * self.WEIGHTS["evidence_quality"]
            + factors.source_reliability * self.WEIGHTS["source_reliability"]
            + factors.historical_success * self.WEIGHTS["historical_success"]
            + factors.model_capability_match * self.WEIGHTS["model_capability_match"]
            + factors.risk_assessment * self.WEIGHTS["risk_assessment"]
        )

        degradation_rules = self.config.get("degradation_rules", {})
        if degradation_rules.get("enabled"):
            penalty = degradation_rules.get("confidence_penalty_per_failure", 0.15)
            floor = degradation_rules.get("min_confidence_floor", 0.3)
            degradation = penalty * retry_count
            weighted = max(floor, weighted - degradation)

        return round(weighted, 3)

    def get_confidence_level(self, score: float) -> ConfidenceScore:
        levels = self.config.get("confidence_levels", {})

        for level_num in range(1, 7):
            level_key = f"level_{level_num}"
            if level_key not in levels:
                continue
            level_config = levels[level_key]
            if level_config["score_min"] <= score < level_config["score_max"]:
                return ConfidenceScore(
                    level=level_num,
                    score=score,
                    autonomy_allowed=level_config.get("autonomy_allowed", False),
                    action_class=level_config.get("action_class", "observe"),
                    factors=ConfidenceFactors(),
                    requires_approval=level_config.get(
                        "require_approval",
                        not level_config.get("autonomy_allowed", False),
                    ),
                    description=level_config.get("description", ""),
                )

        return ConfidenceScore(
            level=0,
            score=score,
            autonomy_allowed=False,
            action_class="observe",
            factors=ConfidenceFactors(),
            requires_approval=True,
            description="Unknown level",
        )

    def evaluate(
        self,
        action_type: str,
        evidence_quality: float = 0.5,
        source_reliability: float = 0.5,
        historical_success: float = 0.5,
        model_capability_match: float = 0.5,
        risk_assessment: float = 0.5,
        retry_count: int = 0,
        tier: str = "C3",
    ) -> ConfidenceDecision:
        score = self.compute_confidence(
            evidence_quality=evidence_quality,
            source_reliability=source_reliability,
            historical_success=historical_success,
            model_capability_match=model_capability_match,
            risk_assessment=risk_assessment,
            retry_count=retry_count,
        )

        confidence_level = self.get_confidence_level(score)

        tiered_thresholds = self.config.get("tiered_thresholds", {})
        tier_config = tiered_thresholds.get(tier, {})
        min_conf = tier_config.get("min_confidence", 0.7)
        approval_above = tier_config.get("approval_above", 0.85)

        if score < min_conf:
            escalate_to = "planner"
            requires_approval = True
        elif score >= approval_above:
            escalate_to = None
            requires_approval = False
        else:
            escalate_to = None
            requires_approval = confidence_level.requires_approval

        degradation_applied = retry_count * self.config.get(
            "degradation_rules", {}
        ).get("confidence_penalty_per_failure", 0.15)

        return ConfidenceDecision(
            action_type=action_type,
            confidence_score=score,
            confidence_level=confidence_level.level,
            autonomy_allowed=confidence_level.autonomy_allowed and score >= min_conf,
            action_class=confidence_level.action_class,
            requires_approval=requires_approval,
            escalate_to=escalate_to,
            reason=f"Confidence {score:.2f} (level {confidence_level.level}): {confidence_level.description}",
            degradation_applied=degradation_applied,
        )

    def get_min_confidence_for_tier(self, tier: str) -> float:
        tiered_thresholds = self.config.get("tiered_thresholds", {})
        return tiered_thresholds.get(tier, {}).get("min_confidence", 0.7)

    def should_escalate(self, decision: ConfidenceDecision) -> bool:
        return decision.escalate_to is not None
