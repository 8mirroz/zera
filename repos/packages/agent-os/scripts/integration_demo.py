"""
Integration Demo: Confidence, Tool Permissions, Escalation, and Ralph Loop Verification

This script demonstrates how the new components work together in the agent pipeline.
"""

from pathlib import Path
from agent_os import (
    ConfidenceScorer,
    ToolPermissionEngine,
    EscalationEngine,
    RalphLoopWithVerification,
    run_verification_checks,
)
from agent_os.ralph_loop import RalphLoopConfig

# Config paths
REPO_ROOT = Path("/Users/user/zera")


def demo_confidence_scorer():
    print("\n=== Confidence Scorer Demo ===")

    scorer = ConfidenceScorer(REPO_ROOT)

    # Normal evaluation
    decision = scorer.evaluate(
        action_type="file_edit",
        evidence_quality=0.9,
        source_reliability=0.85,
        historical_success=0.8,
        model_capability_match=0.9,
        risk_assessment=0.7,
        retry_count=0,
        tier="C3",
    )

    print(f"Action: {decision.action_type}")
    print(f"Confidence Score: {decision.confidence_score:.3f}")
    print(f"Confidence Level: {decision.confidence_level}")
    print(f"Autonomy Allowed: {decision.autonomy_allowed}")
    print(f"Action Class: {decision.action_class}")
    print(f"Requires Approval: {decision.requires_approval}")
    print(f"Escalate To: {decision.escalate_to}")
    print(f"Reason: {decision.reason}")

    # With retry (degradation)
    decision_retry = scorer.evaluate(
        action_type="file_edit",
        evidence_quality=0.9,
        source_reliability=0.85,
        historical_success=0.8,
        model_capability_match=0.9,
        risk_assessment=0.7,
        retry_count=2,
        tier="C3",
    )
    print(f"\nAfter 2 retries:")
    print(f"Confidence Score: {decision_retry.confidence_score:.3f}")
    print(f"Degradation Applied: {decision_retry.degradation_applied:.2f}")
    print(f"Requires Approval: {decision_retry.requires_approval}")


def demo_tool_permissions():
    print("\n=== Tool Permission Engine Demo ===")

    engine = ToolPermissionEngine(REPO_ROOT)

    # Check allowed tool
    allowed, reason = engine.is_allowed(
        "file_edit", role="engineer", sandbox_mode=False
    )
    print(f"file_edit for engineer: {allowed} - {reason}")

    # Check tool requiring approval
    allowed, reason = engine.is_allowed(
        "browser_action", role="engineer", sandbox_mode=False
    )
    print(f"browser_action for engineer: {allowed} - {reason}")

    # Check never autonomous
    allowed, reason = engine.is_allowed(
        "financial_transaction", role="engineer", sandbox_mode=False
    )
    print(f"financial_transaction for engineer: {allowed} - {reason}")

    # Get tools by role
    tools = engine.get_tools_by_role("orchestrator")
    print(f"\nTools for orchestrator: {len(tools)}")

    # Get high risk tools
    high_risk = engine.get_high_risk_tools(min_risk_level=4)
    print(f"High risk tools (>=4): {high_risk[:5]}...")


def demo_escalation():
    print("\n=== Escalation Engine Demo ===")

    engine = EscalationEngine(REPO_ROOT)

    # Confidence escalation
    decision = engine.check_confidence_escalation(
        confidence_score=0.55,
        tier_min=0.7,
        repeated_low_confidence=0,
    )
    print(f"Confidence check: triggered={decision.triggered}, level={decision.level}")
    print(f"  Action: {decision.action}, target: {decision.target}")
    print(f"  Reason: {decision.reason}")
    print(f"  Can Avoid: {decision.can_avoid}, strategy: {decision.avoidance_strategy}")

    # Risk escalation
    decision = engine.check_risk_escalation(risk_score=10)
    print(
        f"\nRisk check (score=10): triggered={decision.triggered}, level={decision.level}"
    )

    decision = engine.check_risk_escalation(risk_score=14)
    print(
        f"Risk check (score=14): triggered={decision.triggered}, level={decision.level}"
    )

    # Failure escalation
    decision = engine.check_failure_escalation(failure_count=2)
    print(f"\nFailure check (count=2): triggered={decision.triggered}")

    decision = engine.check_failure_escalation(
        failure_count=3, failure_type="same_failure"
    )
    print(
        f"Failure check (same x3): triggered={decision.triggered}, target={decision.target}"
    )


def demo_ralph_verification():
    print("\n=== Ralph Loop Verification Demo ===")

    config = RalphLoopConfig(
        max_iterations=3,
        min_iterations=2,
        min_acceptable_score=0.80,
    )

    ralph = RalphLoopWithVerification.from_config(config, REPO_ROOT)
    engine = ralph.get_engine()

    # Simulate iterations with verification
    for i in range(1, 4):
        candidate = {"id": f"candidate_{i}", "code": f"solution_{i}"}
        metrics = {
            "correctness": 0.8 + (i * 0.05),
            "speed": 0.7,
            "code_quality": 0.75,
            "token_efficiency": 0.8,
            "tool_success_rate": 0.9,
        }

        # Run verification checks
        verification_results = run_verification_checks(
            candidate,
            ["code_syntax", "test_pass", "no_regression"],
        )

        events = ralph.record_iteration_with_verification(
            candidate,
            metrics=metrics,
            verification_results=verification_results,
        )

        print(f"Iteration {i}:")
        for e in events:
            if e.event_type.startswith("ralph_"):
                print(f"  {e.event_type}: {e.message}")

        if ralph.should_stop():
            break

    # Get verification summary
    summary = ralph.get_verification_summary()
    print(f"\nVerification Summary: {summary}")
    print(f"Current Confidence: {ralph._current_confidence:.3f}")

    # Finalize
    decision = ralph.get_engine().finalize()
    print(f"\nFinal Decision:")
    print(f"  Selected: {decision.selected}")
    print(f"  Best Score: {decision.best_score:.4f}")
    print(f"  Iterations: {decision.total_iterations}")
    print(f"  Stop Reason: {decision.stop_reason}")


def main():
    print("=" * 60)
    print("Agent OS Integration Demo")
    print("Confidence + Tool Permissions + Escalation + Ralph Verification")
    print("=" * 60)

    demo_confidence_scorer()
    demo_tool_permissions()
    demo_escalation()
    demo_ralph_verification()

    print("\n" + "=" * 60)
    print("All demos completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
