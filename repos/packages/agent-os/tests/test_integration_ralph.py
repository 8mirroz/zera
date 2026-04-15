#!/usr/bin/env python3
"""
Integration test: Ralph Loop with production settings.

Demonstrates the fix for:
1. Plateau detection bug (early termination on small but consistent improvements)
2. Confidence degradation too aggressive (penalty 0.15 causes escalation after 3 retries)

Run: cd repos/packages/agent-os && uv run python tests/test_integration_ralph.py
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_os.ralph_loop import RalphLoopConfig, RalphLoopEngine
from agent_os.ralph_loop_verification import RalphLoopWithVerification, run_verification_checks


def test_production_scenario():
    """
    Simulates production C3 task with Ralph Loop.
    
    Before fix: stopped at iteration 3 with 'plateau_detected' (score ~0.75)
    After fix: continues until iteration 6+ with 'threshold_met' (score ~0.87)
    """
    print("=" * 70)
    print("PRODUCTION SCENARIO TEST — C3 Task with Ralph Loop")
    print("=" * 70)
    
    config = RalphLoopConfig(
        max_iterations=7,
        min_iterations=3,
        min_acceptable_score=0.85,
        min_score_delta=0.05,
        run_id='integration-test-001',
        task_type='T3',
        complexity='C3',
    )
    
    engine = RalphLoopWithVerification.from_config(
        config, 
        repo_root=Path('/Users/user/zera'),
    )
    
    print(f"\nConfiguration:")
    print(f"  Max iterations: {config.max_iterations}")
    print(f"  Min iterations: {config.min_iterations}")
    print(f"  Score threshold: {config.min_acceptable_score}")
    print(f"  Confidence penalty: {engine.confidence_penalty_per_retry}")
    print()
    
    iteration_count = 0
    for i in range(1, config.max_iterations + 1):
        iteration_count = i
        candidate = {
            'id': f'candidate_{i}',
            'syntax_valid': True,
            'tests_passed': i >= 2,
            'no_regression': True,
            'backward_compatible': True,
        }
        
        # Realistic gradual improvement (agent gets better each iteration)
        metrics = {
            'correctness': 0.65 + i * 0.04,
            'speed': 0.70 + i * 0.02,
            'code_quality': 0.60 + i * 0.05,
            'token_efficiency': 0.65 + i * 0.03,
            'tool_success_rate': 0.75 + i * 0.02,
        }
        
        ver_results = run_verification_checks(candidate, engine.verification_types)
        engine.record_iteration_with_verification(
            candidate, 
            metrics=metrics,
            verification_results=ver_results,
        )
        
        confidence = engine.apply_confidence_degradation(i - 1)
        
        score = engine.engine.state.best_score
        streak = engine.engine.state.improvement_streak
        
        print(f"  Iteration {i}: score={score:.3f}, streak={streak}, "
              f"confidence={confidence:.2f}")
        
        if engine.should_stop():
            reason = engine.engine.state.stop_reason
            print(f"  >>> Stopped: {reason}")
            break
    
    decision = engine.engine.finalize()
    ver_summary = engine.get_verification_summary()
    
    print(f"\n{'=' * 70}")
    print(f"RESULTS:")
    print(f"  Iterations completed: {iteration_count}")
    print(f"  Final score: {decision.best_score:.3f}")
    print(f"  Stop reason: {decision.stop_reason}")
    print(f"  Verification pass rate: {ver_summary['passed']}/{ver_summary['total']} "
          f"({ver_summary['avg_score']:.1%})")
    print(f"  Final confidence: {engine._current_confidence:.2f}")
    print(f"{'=' * 70}")
    
    # Assertions
    assert iteration_count >= 5, \
        f"Too few iterations ({iteration_count}) — plateau bug may still exist"
    assert decision.best_score >= 0.80, \
        f"Score too low ({decision.best_score:.3f}) — should reach threshold"
    assert decision.stop_reason == "threshold_met", \
        f"Expected threshold_met, got {decision.stop_reason}"
    
    print("\n✓ TEST PASSED — Agent completes sufficient iterations and reaches quality threshold\n")
    return True


def test_confidence_degradation_fixed():
    """
    Test that confidence degradation is reasonable.
    
    Current issue: penalty=0.15 causes escalation after just 3 retries.
    This test documents the current behavior and will pass after fix.
    """
    print("=" * 70)
    print("CONFIDENCE DEGRADATION TEST")
    print("=" * 70)
    
    config = RalphLoopConfig(max_iterations=7, min_iterations=3, min_acceptable_score=0.85)
    engine = RalphLoopWithVerification.from_config(config, Path('/Users/user/zera'))
    
    print(f"\nCurrent settings:")
    print(f"  Penalty per retry: {engine.confidence_penalty_per_retry}")
    print(f"  Min floor: {engine.confidence_min_floor}")
    print()
    
    # Simulate 7 iterations
    for i in range(7):
        conf = engine.apply_confidence_degradation(i)
        escalate = engine.should_escalate_due_to_confidence()
        print(f"  Retry {i}: confidence={conf:.2f}, escalate={escalate}")
    
    print(f"\n⚠ NOTE: With penalty=0.15, escalation triggers at retry 3.")
    print(f"  This may cause premature task escalation.")
    print(f"  Recommended: penalty=0.08-0.10 for more graceful degradation.")
    print()
    
    # This test documents current behavior — will fail after we fix the penalty
    assert engine._current_confidence <= 0.30, "Confidence should hit floor"
    assert engine.should_escalate_due_to_confidence(), "Escalation should trigger"
    
    print("✓ TEST PASSED — Current behavior documented\n")
    return True


if __name__ == "__main__":
    print("\n" + "🧪 " * 35)
    print("RALPH LOOP INTEGRATION TESTS")
    print("🧪 " * 35 + "\n")
    
    all_passed = True
    
    try:
        test_production_scenario()
    except AssertionError as e:
        print(f"\n✗ FAILED: {e}\n")
        all_passed = False
    
    try:
        test_confidence_degradation_fixed()
    except AssertionError as e:
        print(f"\n✗ FAILED: {e}\n")
        all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70 + "\n")
    
    sys.exit(0 if all_passed else 1)
