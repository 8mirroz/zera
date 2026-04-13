"""RoutingVectorClassifier — compute C1-C5 complexity from routing-matrix.yaml dimensions.

Reads lane_thresholds from configs/tooling/routing-matrix.yaml and maps
a 9-dimensional task vector to a complexity tier.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml
from .config_loader import ModularConfigLoader


@dataclass
class RoutingVector:
    ambiguity: float = 0.0
    blast_radius: float = 0.0
    novelty: float = 0.0
    reversibility: float = 0.0          # 0=fully reversible, 1=irreversible
    external_dependency_risk: float = 0.0
    verification_cost: float = 0.0
    task_complexity: float = 0.0        # 0=trivial, 1=critical
    known_pattern_match: float = 1.0   # 1=known, 0=unknown
    uncertainty: float = 0.0

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "RoutingVector":
        def _f(key: str, default: float) -> float:
            v = d.get(key, default)
            if isinstance(v, bool):
                return 1.0 if v else 0.0
            return float(v)

        return cls(
            ambiguity=_f("ambiguity", 0.0),
            blast_radius=_f("blast_radius", 0.0),
            novelty=_f("novelty", 0.0),
            reversibility=_f("reversibility", 0.0),
            external_dependency_risk=_f("external_dependency_risk", 0.0),
            verification_cost=_f("verification_cost", 0.0),
            task_complexity=_f("task_complexity", 0.0),
            known_pattern_match=_f("known_pattern_match", 1.0),
            uncertainty=_f("uncertainty", 0.0),
        )

    @classmethod
    def from_intent(cls, repo_root: Path, intent_class: str) -> "RoutingVector":
        """Load a RoutingVector from a standardized intent class in the catalog."""
        loader = ModularConfigLoader(str(repo_root))
        catalog_path = "configs/orchestrator/routing_intent_catalog.yaml"
        catalog = loader.load_suite(catalog_path)
        profiles = catalog.get("intent_profiles", {})
        
        if intent_class not in profiles:
            # Fallback to generic defaults if intent not found
            return cls()
            
        profile = profiles[intent_class]
        dims = profile.get("dimensions", {})
        
        # Merge profile dimensions with defaults
        return cls.from_dict(dims)

    def to_dict(self) -> dict[str, float]:
        return {
            "ambiguity": self.ambiguity,
            "blast_radius": self.blast_radius,
            "novelty": self.novelty,
            "reversibility": self.reversibility,
            "external_dependency_risk": self.external_dependency_risk,
            "verification_cost": self.verification_cost,
            "task_complexity": self.task_complexity,
            "known_pattern_match": self.known_pattern_match,
            "uncertainty": self.uncertainty,
        }


@dataclass
class ClassificationResult:
    complexity: str
    score: float                        # 0.0–1.0 aggregate risk score
    lane: str                           # fast / quality / swarm
    reasons: list[str] = field(default_factory=list)
    vector: dict[str, float] = field(default_factory=dict)


# Dimension weights for aggregate risk score
_WEIGHTS: dict[str, float] = {
    "ambiguity": 0.20,
    "blast_radius": 0.20,
    "novelty": 0.15,
    "reversibility": 0.15,
    "external_dependency_risk": 0.10,
    "verification_cost": 0.08,
    "task_complexity": 0.07,
    "known_pattern_match": -0.10,   # negative: known pattern reduces risk
    "uncertainty": 0.05,
}

# Score → complexity mapping (thresholds)
_SCORE_TO_COMPLEXITY: list[tuple[float, str]] = [
    (0.02, "C1"),
    (0.15, "C2"),
    (0.32, "C3"),
    (0.52, "C4"),
    (1.01, "C5"),
]

# Score → lane mapping
_SCORE_TO_LANE: list[tuple[float, str]] = [
    (0.35, "fast"),
    (0.70, "quality"),
    (1.01, "swarm"),
]


class RoutingVectorClassifier:
    """Classify task complexity from a RoutingVector."""

    _MATRIX_PATH = "configs/tooling/routing-matrix.yaml"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self.loader = ModularConfigLoader(str(self.repo_root))
        self._thresholds = self._load_thresholds()

    def _load_thresholds(self) -> dict[str, Any]:
        path = self.repo_root / self._MATRIX_PATH
        if not path.exists():
            return {}
        try:
            from .yaml_compat import parse_simple_yaml
            data = parse_simple_yaml(path.read_text(encoding="utf-8")) or {}
            return data.get("lane_thresholds", {}) or {}
        except Exception:
            return {}

    def _aggregate_score(self, vec: RoutingVector) -> float:
        raw = {
            "ambiguity": vec.ambiguity,
            "blast_radius": vec.blast_radius,
            "novelty": vec.novelty,
            "reversibility": vec.reversibility,
            "external_dependency_risk": vec.external_dependency_risk,
            "verification_cost": vec.verification_cost,
            "task_complexity": vec.task_complexity,
            "known_pattern_match": vec.known_pattern_match,
            "uncertainty": vec.uncertainty,
        }
        score = sum(raw[k] * w for k, w in _WEIGHTS.items())
        return max(0.0, min(1.0, round(score, 4)))

    def _score_to_complexity(self, score: float) -> str:
        for threshold, tier in _SCORE_TO_COMPLEXITY:
            if score < threshold:
                return tier
        return "C5"

    def _score_to_lane(self, score: float) -> str:
        for threshold, lane in _SCORE_TO_LANE:
            if score < threshold:
                return lane
        return "swarm"

    def _build_reasons(self, vec: RoutingVector, score: float) -> list[str]:
        reasons: list[str] = []
        if vec.ambiguity > 0.6:
            reasons.append(f"high_ambiguity={vec.ambiguity:.2f}")
        if vec.blast_radius > 0.6:
            reasons.append(f"high_blast_radius={vec.blast_radius:.2f}")
        if vec.novelty > 0.6:
            reasons.append(f"high_novelty={vec.novelty:.2f}")
        if vec.reversibility > 0.7:
            reasons.append(f"irreversible={vec.reversibility:.2f}")
        if vec.external_dependency_risk > 0.5:
            reasons.append(f"external_risk={vec.external_dependency_risk:.2f}")
        if vec.known_pattern_match < 0.3:
            reasons.append("no_known_pattern")
        if not reasons:
            reasons.append(f"aggregate_score={score:.3f}")
        return reasons

    def classify(self, vec: RoutingVector) -> ClassificationResult:
        score = self._aggregate_score(vec)
        complexity = self._score_to_complexity(score)
        lane = self._score_to_lane(score)
        reasons = self._build_reasons(vec, score)
        return ClassificationResult(
            complexity=complexity,
            score=score,
            lane=lane,
            reasons=reasons,
            vector=vec.to_dict(),
        )

    def classify_dict(self, d: dict[str, Any]) -> ClassificationResult:
        return self.classify(RoutingVector.from_dict(d))
