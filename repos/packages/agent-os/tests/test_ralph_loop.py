"""Tests for Ralph Loop engine — algorithm correctness and edge cases."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for testing
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_os.ralph_loop import RalphLoopConfig, RalphLoopEngine


def test_basic_iteration():
    """Test that basic iteration works and scores are computed correctly."""
    config = RalphLoopConfig(max_iterations=3, min_iterations=1)
    engine = RalphLoopEngine(config)
    
    candidate = {'id': 'cand_1', 'code': 'test'}
    metrics = {
        'correctness': 0.8,
        'speed': 0.7,
        'code_quality': 0.75,
        'token_efficiency': 0.7,
        'tool_success_rate': 0.9,
    }
    
    events = engine.record_iteration(candidate, metrics=metrics)
    
    assert len(events) == 2  # started + scored
    assert engine.state.iteration == 1
    assert engine.state.best_score > 0
    assert not engine.state.stopped


def test_early_stop_threshold():
    """Test that loop stops when threshold is met after min_iterations."""
    config = RalphLoopConfig(
        max_iterations=7,
        min_iterations=2,
        min_acceptable_score=0.70,
    )
    engine = RalphLoopEngine(config)
    
    # First iteration - below threshold
    engine.record_iteration({'id': 'c1'}, metrics={
        'correctness': 0.6, 'speed': 0.6, 'code_quality': 0.6,
        'token_efficiency': 0.6, 'tool_success_rate': 0.6,
    })
    assert not engine.should_stop()  # min_iterations not met
    
    # Second iteration - above threshold, min_iterations met
    engine.record_iteration({'id': 'c2'}, metrics={
        'correctness': 0.8, 'speed': 0.8, 'code_quality': 0.8,
        'token_efficiency': 0.8, 'tool_success_rate': 0.8,
    })
    assert engine.should_stop()  # threshold met
    assert engine.state.stop_reason == "threshold_met"


def test_plateau_detection_fixed():
    """
    REGRESSION TEST: Plateau detection should NOT trigger on consistent small improvements.
    
    After fix: if improvements are steady (even small), the loop continues.
    Plateau only triggers when improvement ACTUALLY STOPS (delta <= 0).
    """
    config = RalphLoopConfig(
        max_iterations=7,
        min_iterations=3,
        min_acceptable_score=0.85,  # High threshold - won't be met
        min_score_delta=0.05,  # Plateau if delta <= 0
    )
    engine = RalphLoopEngine(config)
    
    # Simulate consistent small improvements (0.03 per iteration)
    # This should NOT trigger plateau - improvements are still happening!
    for i in range(1, 8):
        candidate = {'id': f'cand_{i}'}
        metrics = {
            'correctness': 0.65 + i * 0.03,
            'speed': 0.70 + i * 0.03,
            'code_quality': 0.60 + i * 0.03,
            'token_efficiency': 0.65 + i * 0.03,
            'tool_success_rate': 0.75 + i * 0.03,
        }
        engine.record_iteration(candidate, metrics=metrics)
        stopped = engine.should_stop()
        
        if stopped:
            print(f"Stopped at iteration {i} with reason: {engine.state.stop_reason}")
            print(f"Scores: {[round(s, 3) for s in engine.state.scores]}")
            print(f"Improvement streak: {engine.state.improvement_streak}")
            # Should only stop due to max_iterations, not plateau
            assert engine.state.stop_reason == "max_iterations_reached", \
                f"Still has bug: stopped with '{engine.state.stop_reason}' instead of continuing improvements"
            break
    
    # If we reach max_iterations with improvements, the fix works
    assert engine.state.stop_reason == "max_iterations_reached", \
        f"Expected max_iterations_reached, got {engine.state.stop_reason}"
    print(f"✓ Completed all {engine.state.iteration} iterations with consistent improvements")


def test_true_plateau():
    """Test that plateau correctly triggers when improvement STOPS."""
    config = RalphLoopConfig(
        max_iterations=7,
        min_iterations=3,
        min_acceptable_score=0.95,  # Very high - won't be met
        min_score_delta=0.05,
    )
    engine = RalphLoopEngine(config)
    
    # Iteration 1-2: improvement
    engine.record_iteration({'id': 'c1'}, metrics={
        'correctness': 0.7, 'speed': 0.7, 'code_quality': 0.7,
        'token_efficiency': 0.7, 'tool_success_rate': 0.7,
    })
    engine.record_iteration({'id': 'c2'}, metrics={
        'correctness': 0.8, 'speed': 0.8, 'code_quality': 0.8,
        'token_efficiency': 0.8, 'tool_success_rate': 0.8,
    })
    
    # Iteration 3-4: NO improvement (plateau)
    engine.record_iteration({'id': 'c3'}, metrics={
        'correctness': 0.80, 'speed': 0.80, 'code_quality': 0.80,
        'token_efficiency': 0.80, 'tool_success_rate': 0.80,
    })
    engine.record_iteration({'id': 'c4'}, metrics={
        'correctness': 0.80, 'speed': 0.80, 'code_quality': 0.80,
        'token_efficiency': 0.80, 'tool_success_rate': 0.80,
    })
    
    assert engine.should_stop()
    assert engine.state.stop_reason == "plateau_detected"


def test_max_iterations():
    """Test that loop always stops at max_iterations."""
    config = RalphLoopConfig(max_iterations=5, min_iterations=2)
    engine = RalphLoopEngine(config)
    
    # Use scores that gradually improve to avoid early plateau
    for i in range(1, 6):
        score = 0.5 + i * 0.01  # Small but consistent improvement
        engine.record_iteration({'id': f'c{i}'}, weighted_total=score)
        if engine.should_stop():
            break
    
    assert engine.state.stopped
    assert engine.state.stop_reason == "max_iterations_reached"
    assert engine.state.iteration == 5


def test_finalize_selects_best():
    """Test that finalize returns the best candidate."""
    config = RalphLoopConfig(
        max_iterations=5, 
        min_iterations=1,
        min_acceptable_score=0.95,  # High enough to not trigger early
    )
    engine = RalphLoopEngine(config)
    
    # Scores: gradual improvement to avoid plateau
    scores = [0.6, 0.7, 0.75, 0.8, 0.85]
    for i, score in enumerate(scores, 1):
        engine.record_iteration({'id': f'c{i}'}, weighted_total=score)
        engine.should_stop()
    
    decision = engine.finalize()
    
    assert decision.selected
    assert decision.best_score == 0.85
    assert decision.total_iterations == 5


if __name__ == "__main__":
    print("Running test_basic_iteration...")
    test_basic_iteration()
    print("✓ PASSED\n")
    
    print("Running test_early_stop_threshold...")
    test_early_stop_threshold()
    print("✓ PASSED\n")
    
    print("Running test_plateau_detection_fixed...")
    try:
        test_plateau_detection_fixed()
        print("✓ PASSED\n")
    except AssertionError as e:
        print(f"✗ FAILED: {e}\n")
    
    print("Running test_true_plateau...")
    test_true_plateau()
    print("✓ PASSED\n")
    
    print("Running test_max_iterations...")
    test_max_iterations()
    print("✓ PASSED\n")
    
    print("Running test_finalize_selects_best...")
    test_finalize_selects_best()
    print("✓ PASSED\n")
    
    print("\nAll tests completed!")
