#!/usr/bin/env python3
"""
Ralph Loop Demo CLI — Demonstrates Ralph Loop Engine usage.

This CLI shows how to:
1. Initialize the engine with configuration
2. Record iterations with candidates and scores
3. Check stop conditions
4. Emit events (to stdout or trace file)
5. Finalize and get the best candidate

Usage:
    python3 ralph_loop_demo.py [--trace-file PATH] [--scenario SCENARIO]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_os.ralph_loop import RalphLoopConfig, RalphLoopEngine, RalphEvent


def emit_event_to_stdout(event: RalphEvent) -> None:
    """Emit event to stdout as JSON line."""
    print(json.dumps(event.to_dict(), ensure_ascii=False))


def emit_event_to_trace_file(event: RalphEvent, trace_path: Path) -> None:
    """Emit event to trace file (JSONL format)."""
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with trace_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")


def run_scenario_plateau(trace_path: Path | None = None) -> None:
    """
    Scenario 1: Plateau Detection
    
    Demonstrates stop when score improvement drops below min_score_delta.
    """
    print("# Scenario: Plateau Detection")
    print("# Scores: 0.75 → 0.76 → 0.765 (delta < 0.05, plateau)")
    print()

    config = RalphLoopConfig(
        max_iterations=7,
        min_iterations=3,
        min_acceptable_score=0.90,  # Keep threshold above demo scores so plateau is the trigger
        min_score_delta=0.05,
        run_id="demo-plateau-001",
        task_type="T3",
        complexity="C3",
    )
    engine = RalphLoopEngine(config)

    # Simulated scores showing plateau
    scores = [0.75, 0.76, 0.765]

    for i, score in enumerate(scores):
        candidate = {"id": f"candidate_{i+1}", "description": f"Iteration {i+1}"}

        # Record iteration and get events
        events = engine.record_iteration(candidate, weighted_total=score)

        # Emit events
        for event in events:
            if trace_path:
                emit_event_to_trace_file(event, trace_path)
            else:
                emit_event_to_stdout(event)

        # Check stop condition
        if engine.should_stop():
            print(f"# Stopped at iteration {engine.state.iteration}: {engine.state.stop_reason}")
            break

    # Finalize
    decision = engine.finalize()
    print(f"# Best candidate: {decision.best_candidate['id']} (score: {decision.best_score})")
    print(f"# Total iterations: {decision.total_iterations}")
    print(f"# Stop reason: {decision.stop_reason}")
    print()

    # Emit finalization events
    for event in engine.pop_events():
        if trace_path:
            emit_event_to_trace_file(event, trace_path)
        else:
            emit_event_to_stdout(event)


def run_scenario_threshold(trace_path: Path | None = None) -> None:
    """
    Scenario 2: Threshold Met
    
    Demonstrates early stop when score exceeds min_acceptable_score.
    """
    print("# Scenario: Threshold Met")
    print("# Scores: 0.50 → 0.65 → 0.85 (threshold 0.70 exceeded)")
    print()

    config = RalphLoopConfig(
        max_iterations=7,
        min_iterations=3,
        min_acceptable_score=0.70,
        min_score_delta=0.05,
        run_id="demo-threshold-001",
        task_type="T4",
        complexity="C4",
    )
    engine = RalphLoopEngine(config)

    scores = [0.50, 0.65, 0.85]

    for i, score in enumerate(scores):
        candidate = {"id": f"candidate_{i+1}", "description": f"Iteration {i+1}"}
        events = engine.record_iteration(candidate, weighted_total=score)

        for event in events:
            if trace_path:
                emit_event_to_trace_file(event, trace_path)
            else:
                emit_event_to_stdout(event)

        if engine.should_stop():
            print(f"# Stopped at iteration {engine.state.iteration}: {engine.state.stop_reason}")
            break

    decision = engine.finalize()
    print(f"# Best candidate: {decision.best_candidate['id']} (score: {decision.best_score})")
    print(f"# Total iterations: {decision.total_iterations}")
    print()

    for event in engine.pop_events():
        if trace_path:
            emit_event_to_trace_file(event, trace_path)
        else:
            emit_event_to_stdout(event)


def run_scenario_max_iterations(trace_path: Path | None = None) -> None:
    """
    Scenario 3: Max Iterations
    
    Demonstrates forced stop when max_iterations is reached.
    """
    print("# Scenario: Max Iterations Reached")
    print("# Max iterations: 5, scores keep improving but no stop condition met")
    print()

    config = RalphLoopConfig(
        max_iterations=5,
        min_iterations=1,
        min_acceptable_score=0.99,  # Very high threshold
        min_score_delta=0.01,  # Small delta
        run_id="demo-max-001",
        task_type="T5",
        complexity="C5",
    )
    engine = RalphLoopEngine(config)

    # Scores that keep improving but never reach threshold
    scores = [0.60, 0.70, 0.78, 0.84, 0.88]

    for i, score in enumerate(scores):
        candidate = {"id": f"candidate_{i+1}", "description": f"Iteration {i+1}"}
        events = engine.record_iteration(candidate, weighted_total=score)

        for event in events:
            if trace_path:
                emit_event_to_trace_file(event, trace_path)
            else:
                emit_event_to_stdout(event)

        if engine.should_stop():
            print(f"# Stopped at iteration {engine.state.iteration}: {engine.state.stop_reason}")
            break

    decision = engine.finalize()
    print(f"# Best candidate: {decision.best_candidate['id']} (score: {decision.best_score})")
    print(f"# Total iterations: {decision.total_iterations}")
    print(f"# Stop reason: {decision.stop_reason}")
    print()

    for event in engine.pop_events():
        if trace_path:
            emit_event_to_trace_file(event, trace_path)
        else:
            emit_event_to_stdout(event)


def run_scenario_with_metrics(trace_path: Path | None = None) -> None:
    """
    Scenario 4: Full Metrics
    
    Demonstrates scoring with full metrics breakdown.
    """
    print("# Scenario: Full Metrics Scoring")
    print("# Shows per-metric scores and weighted total calculation")
    print()

    config = RalphLoopConfig(
        max_iterations=3,
        min_iterations=1,
        min_acceptable_score=0.70,
        run_id="demo-metrics-001",
    )
    engine = RalphLoopEngine(config)

    # Full metrics for each iteration
    iterations = [
        {
            "candidate": {"id": "balanced", "description": "Balanced solution"},
            "metrics": {
                "correctness": 0.9,
                "speed": 0.7,
                "code_quality": 0.8,
                "token_efficiency": 0.7,
                "tool_success_rate": 1.0,
            },
        },
        {
            "candidate": {"id": "fast", "description": "Optimized for speed"},
            "metrics": {
                "correctness": 0.85,
                "speed": 0.95,
                "code_quality": 0.7,
                "token_efficiency": 0.8,
                "tool_success_rate": 0.9,
            },
        },
        {
            "candidate": {"id": "clean", "description": "Clean code focus"},
            "metrics": {
                "correctness": 0.95,
                "speed": 0.6,
                "code_quality": 0.95,
                "token_efficiency": 0.6,
                "tool_success_rate": 1.0,
            },
        },
    ]

    for i, item in enumerate(iterations):
        events = engine.record_iteration(
            item["candidate"],
            metrics=item["metrics"],
        )

        for event in events:
            if trace_path:
                emit_event_to_trace_file(event, trace_path)
            else:
                emit_event_to_stdout(event)

        if engine.should_stop():
            print(f"# Stopped at iteration {engine.state.iteration}: {engine.state.stop_reason}")
            break

    decision = engine.finalize()
    print(f"# Best candidate: {decision.best_candidate['id']}")
    print(f"# Best score: {decision.best_score}")
    print(f"# All scores: {decision.all_scores}")
    print(f"# Improvement history: {decision.improvement_history}")
    print()

    for event in engine.pop_events():
        if trace_path:
            emit_event_to_trace_file(event, trace_path)
        else:
            emit_event_to_stdout(event)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Ralph Loop Demo CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--trace-file",
        type=Path,
        help="Write events to trace file (JSONL) instead of stdout",
    )
    parser.add_argument(
        "--scenario",
        choices=["plateau", "threshold", "max_iterations", "metrics", "all"],
        default="all",
        help="Scenario to run (default: all)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress scenario descriptions (only emit events)",
    )

    args = parser.parse_args()

    if not args.quiet:
        print("=" * 60)
        print("Ralph Loop Engine Demo")
        print("=" * 60)
        print()

    scenarios = {
        "plateau": run_scenario_plateau,
        "threshold": run_scenario_threshold,
        "max_iterations": run_scenario_max_iterations,
        "metrics": run_scenario_with_metrics,
    }

    if args.scenario == "all":
        for scenario_fn in scenarios.values():
            scenario_fn(args.trace_file)
    else:
        scenarios[args.scenario](args.trace_file)

    if not args.quiet:
        print("=" * 60)
        print("Demo complete")
        if args.trace_file:
            print(f"Events written to: {args.trace_file}")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
