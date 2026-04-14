from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ralph_loop import RalphLoopConfig, RalphLoopState, RalphLoopEngine, RalphEvent
from .yaml_compat import parse_simple_yaml
from pathlib import Path


RALPH_VERIFICATION_DEFAULT = {
    "verification": {
        "enabled": True,
        "verify_each_iteration": True,
        "pass_threshold": 0.85,
        "fail_on_verification_failure": True,
        "verification_types": [
            "code_syntax",
            "test_pass",
            "no_regression",
            "backward_compatibility",
        ],
    },
    "confidence": {
        "degradation_enabled": True,
        "penalty_per_retry": 0.15,
        "min_floor": 0.3,
        "escalate_on_degradation": True,
    },
}


@dataclass
class VerificationResult:
    passed: bool
    verification_type: str
    score: float
    details: str
    errors: list[str] = field(default_factory=list)


@dataclass
class RalphLoopWithVerification:
    engine: RalphLoopEngine
    verification_enabled: bool
    verify_each_iteration: bool
    pass_threshold: float
    fail_on_verification_failure: bool
    verification_types: list[str]
    confidence_degradation_enabled: bool
    confidence_penalty_per_retry: float
    confidence_min_floor: float
    escalate_on_degradation: bool

    _verification_results: list[VerificationResult] = field(default_factory=list)
    _current_confidence: float = 1.0

    @classmethod
    def from_config(
        cls,
        config: RalphLoopConfig,
        repo_root: Path,
        router_config_path: Path | None = None,
    ) -> "RalphLoopWithVerification":
        router_path = router_config_path or (
            repo_root / "configs/orchestrator/router.yaml"
        )

        verification_config = RALPH_VERIFICATION_DEFAULT
        if router_path.exists():
            try:
                router_cfg = parse_simple_yaml(router_path.read_text(encoding="utf-8"))
                ralph_loop_cfg = router_cfg.get("ralph_loop", {})
                verification_config = ralph_loop_cfg
            except Exception:
                pass

        ver_cfg = verification_config.get("verification", {})
        conf_cfg = verification_config.get("confidence", {})

        return cls(
            engine=RalphLoopEngine(config),
            verification_enabled=ver_cfg.get("enabled", True),
            verify_each_iteration=ver_cfg.get("verify_each_iteration", True),
            pass_threshold=ver_cfg.get("pass_threshold", 0.85),
            fail_on_verification_failure=ver_cfg.get(
                "fail_on_verification_failure", True
            ),
            verification_types=ver_cfg.get(
                "verification_types", ["code_syntax", "test_pass"]
            ),
            confidence_degradation_enabled=conf_cfg.get("degradation_enabled", True),
            confidence_penalty_per_retry=conf_cfg.get("penalty_per_retry", 0.15),
            confidence_min_floor=conf_cfg.get("min_floor", 0.3),
            escalate_on_degradation=conf_cfg.get("escalate_on_degradation", True),
        )

    def record_iteration_with_verification(
        self,
        candidate: dict[str, Any],
        metrics: dict[str, float] | None = None,
        weighted_total: float | None = None,
        verification_results: list[VerificationResult] | None = None,
    ) -> list[RalphEvent]:
        events = self.engine.record_iteration(candidate, metrics, weighted_total)

        if verification_results:
            self._verification_results.extend(verification_results)

            all_passed = all(v.passed for v in verification_results)
            avg_score = (
                sum(v.score for v in verification_results) / len(verification_results)
                if verification_results
                else 0.0
            )

            if self.verify_each_iteration:
                if not all_passed and self.fail_on_verification_failure:
                    fail_event = RalphEvent(
                        ts=events[0].ts if events else "",
                        run_id=self.engine.config.run_id,
                        event_type="ralph_verification_failed",
                        status="error",
                        message=f"Verification failed: {len([v for v in verification_results if not v.passed])} failed",
                        data={
                            "verification_results": [
                                {
                                    "type": v.verification_type,
                                    "passed": v.passed,
                                    "score": v.score,
                                }
                                for v in verification_results
                            ],
                            "avg_score": avg_score,
                        },
                    )
                    events.append(fail_event)
                elif avg_score >= self.pass_threshold:
                    pass_event = RalphEvent(
                        ts=events[0].ts if events else "",
                        run_id=self.engine.config.run_id,
                        event_type="ralph_verification_passed",
                        status="ok",
                        message=f"Verification passed (avg: {avg_score:.2f})",
                        data={
                            "verification_results": [
                                {
                                    "type": v.verification_type,
                                    "passed": v.passed,
                                    "score": v.score,
                                }
                                for v in verification_results
                            ],
                            "avg_score": avg_score,
                        },
                    )
                    events.append(pass_event)

        return events

    def apply_confidence_degradation(self, retry_count: int) -> float:
        if not self.confidence_degradation_enabled:
            return 1.0

        degradation = self.confidence_penalty_per_retry * retry_count
        self._current_confidence = max(
            self.confidence_min_floor,
            self._current_confidence - degradation,
        )
        return self._current_confidence

    def should_escalate_due_to_confidence(self) -> bool:
        if not self.escalate_on_degradation:
            return False
        return self._current_confidence <= self.confidence_min_floor

    def should_stop(self) -> bool:
        return self.engine.should_stop()

    def get_verification_summary(self) -> dict[str, Any]:
        if not self._verification_results:
            return {"total": 0, "passed": 0, "failed": 0, "avg_score": 0.0}

        passed = sum(1 for v in self._verification_results if v.passed)
        failed = len(self._verification_results) - passed
        avg_score = sum(v.score for v in self._verification_results) / len(
            self._verification_results
        )

        return {
            "total": len(self._verification_results),
            "passed": passed,
            "failed": failed,
            "avg_score": round(avg_score, 3),
            "current_confidence": round(self._current_confidence, 3),
        }

    def get_engine(self) -> RalphLoopEngine:
        return self.engine


def run_verification_checks(
    candidate: dict[str, Any],
    verification_types: list[str],
) -> list[VerificationResult]:
    results = []

    for vtype in verification_types:
        if vtype == "code_syntax":
            passed = candidate.get("syntax_valid", True)
            score = 1.0 if passed else 0.0
            results.append(
                VerificationResult(
                    passed=passed,
                    verification_type="code_syntax",
                    score=score,
                    details="Syntax validation",
                    errors=candidate.get("syntax_errors", []),
                )
            )

        elif vtype == "test_pass":
            passed = candidate.get("tests_passed", True)
            score = 1.0 if passed else 0.0
            results.append(
                VerificationResult(
                    passed=passed,
                    verification_type="test_pass",
                    score=score,
                    details="Test execution",
                    errors=candidate.get("test_errors", []),
                )
            )

        elif vtype == "no_regression":
            passed = candidate.get("no_regression", True)
            score = 1.0 if passed else 0.0
            results.append(
                VerificationResult(
                    passed=passed,
                    verification_type="no_regression",
                    score=score,
                    details="Regression check",
                    errors=candidate.get("regression_errors", []),
                )
            )

        elif vtype == "backward_compatibility":
            passed = candidate.get("backward_compatible", True)
            score = 1.0 if passed else 0.0
            results.append(
                VerificationResult(
                    passed=passed,
                    verification_type="backward_compatibility",
                    score=score,
                    details="Backward compatibility check",
                    errors=candidate.get("compatibility_errors", []),
                )
            )

    return results
