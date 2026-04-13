"""Tests for RoutingVectorClassifier."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.routing_vector import RoutingVector, RoutingVectorClassifier, ClassificationResult


def _classifier(tmp_path: Path) -> RoutingVectorClassifier:
    (tmp_path / "configs/tooling").mkdir(parents=True)
    (tmp_path / "configs/tooling/routing-matrix.yaml").write_text(
        "version: '2026-03-11'\nlane_thresholds:\n  fast:\n    ambiguity_max: 0.35\n"
    )
    return RoutingVectorClassifier(tmp_path)


class TestRoutingVectorFromDict:
    def test_from_dict_defaults(self):
        vec = RoutingVector.from_dict({})
        assert vec.ambiguity == 0.0
        assert vec.known_pattern_match == 1.0

    def test_from_dict_bool_known_pattern(self):
        vec = RoutingVector.from_dict({"known_pattern_match": False})
        assert vec.known_pattern_match == 0.0

    def test_from_dict_partial(self):
        vec = RoutingVector.from_dict({"ambiguity": 0.8, "blast_radius": 0.7})
        assert vec.ambiguity == 0.8
        assert vec.blast_radius == 0.7
        assert vec.novelty == 0.0


class TestRoutingVectorClassifier:
    def test_trivial_task_is_c1(self, tmp_path):
        clf = _classifier(tmp_path)
        result = clf.classify(RoutingVector(
            ambiguity=0.05, blast_radius=0.05, novelty=0.05,
            reversibility=0.0, known_pattern_match=1.0,
        ))
        assert result.complexity == "C1"
        assert result.lane == "fast"

    def test_simple_task_is_c2(self, tmp_path):
        clf = _classifier(tmp_path)
        result = clf.classify(RoutingVector(
            ambiguity=0.2, blast_radius=0.2, novelty=0.15,
            reversibility=0.1, known_pattern_match=0.8,
        ))
        assert result.complexity == "C2"

    def test_medium_task_is_c3(self, tmp_path):
        clf = _classifier(tmp_path)
        result = clf.classify(RoutingVector(
            ambiguity=0.5, blast_radius=0.45, novelty=0.4,
            reversibility=0.3, known_pattern_match=0.5,
            verification_cost=0.4,
        ))
        assert result.complexity == "C3"

    def test_complex_task_is_c4(self, tmp_path):
        clf = _classifier(tmp_path)
        result = clf.classify(RoutingVector(
            ambiguity=0.7, blast_radius=0.7, novelty=0.65,
            reversibility=0.6, known_pattern_match=0.2,
            external_dependency_risk=0.6, verification_cost=0.6,
        ))
        assert result.complexity in {"C4", "C5"}

    def test_critical_task_is_c5(self, tmp_path):
        clf = _classifier(tmp_path)
        result = clf.classify(RoutingVector(
            ambiguity=0.95, blast_radius=0.95, novelty=0.9,
            reversibility=1.0, known_pattern_match=0.0,
            external_dependency_risk=0.9, verification_cost=0.9,
            task_complexity=1.0, uncertainty=0.9,
        ))
        assert result.complexity == "C5"
        assert result.lane == "swarm"

    def test_known_pattern_reduces_complexity(self, tmp_path):
        clf = _classifier(tmp_path)
        without_pattern = clf.classify(RoutingVector(
            ambiguity=0.4, blast_radius=0.4, known_pattern_match=0.0,
        ))
        with_pattern = clf.classify(RoutingVector(
            ambiguity=0.4, blast_radius=0.4, known_pattern_match=1.0,
        ))
        assert with_pattern.score < without_pattern.score

    def test_classify_dict(self, tmp_path):
        clf = _classifier(tmp_path)
        result = clf.classify_dict({"ambiguity": 0.1, "blast_radius": 0.1})
        assert isinstance(result, ClassificationResult)
        assert result.complexity in {"C1", "C2", "C3", "C4", "C5"}

    def test_result_has_reasons(self, tmp_path):
        clf = _classifier(tmp_path)
        result = clf.classify(RoutingVector(ambiguity=0.9, blast_radius=0.9))
        assert len(result.reasons) > 0

    def test_result_vector_matches_input(self, tmp_path):
        clf = _classifier(tmp_path)
        vec = RoutingVector(ambiguity=0.42, blast_radius=0.33)
        result = clf.classify(vec)
        assert result.vector["ambiguity"] == 0.42
        assert result.vector["blast_radius"] == 0.33

    def test_score_bounded_0_1(self, tmp_path):
        clf = _classifier(tmp_path)
        for vec in [
            RoutingVector(),
            RoutingVector(ambiguity=1.0, blast_radius=1.0, novelty=1.0, reversibility=1.0,
                          external_dependency_risk=1.0, verification_cost=1.0,
                          task_complexity=1.0, known_pattern_match=0.0, uncertainty=1.0),
        ]:
            result = clf.classify(vec)
            assert 0.0 <= result.score <= 1.0
