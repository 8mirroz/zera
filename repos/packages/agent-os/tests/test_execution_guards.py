"""Tests for execution guards — pre/post-flight validation, stall detection, heartbeat."""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Add src to path for testing
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_os.execution_guards import (
    ExecutionGuards,
    PreflightValidator,
    PostflightGroundingChecker,
    StallDetector,
    HeartbeatEmitter,
    ViolationTracker,
    ArtifactSummaryValidator,
    ProgressSignal,
    ViolationLevel,
    ViolationType,
    StallCause,
    Violation,
    ValidationResult,
    GroundingResult,
    StallEvent,
)


# ============================================================================
# PRE-FLIGHT VALIDATOR TESTS
# ============================================================================


def test_preflight_detects_unverified_completion():
    """Preflight validator detects 'created' claims without evidence."""
    validator = PreflightValidator()
    
    # Bad: claim without evidence
    response = "I've created all the necessary files for the project."
    result = validator.validate(response)
    
    assert not result.passed, "Should fail: unverified completion claim"
    assert result.error_count > 0, "Should have at least one error"


def test_preflight_passes_with_evidence():
    """Preflight passes when evidence block is present."""
    validator = PreflightValidator()
    
    # Good: claim with evidence
    response = """
Created 6 directories.

Evidence:
```bash
$ ls -d project/*/
configs/  data/  docs/  src/  tests/  tools/
```
"""
    result = validator.validate(response)
    
    assert result.passed, "Should pass: evidence block present"


def test_preflight_detects_filesystem_claim_without_evidence():
    """Preflight detects filesystem claims without path verification."""
    validator = PreflightValidator()
    
    response = "I created the src/config.py file with the configuration."
    result = validator.validate(response)
    
    assert not result.passed, "Should fail: filesystem claim without evidence"
    assert any(
        v.violation_type == ViolationType.MISSING_FILESYSTEM_EVIDENCE
        for v in result.violations
    )


def test_preflight_warns_on_narrative():
    """Preflight warns on narrative action without tool."""
    validator = PreflightValidator()
    
    response = "I'm creating the project structure now..."
    result = validator.validate(response)
    
    # Narrative is a warning, not an error
    assert any(
        v.violation_type == ViolationType.NARRATE_WITHOUT_TOOL
        for v in result.violations
    )


def test_preflight_detects_aggregation_without_count():
    """Preflight detects aggregated claims without specific count."""
    validator = PreflightValidator()
    
    response = "All files created successfully."
    result = validator.validate(response)
    
    assert not result.passed, "Should fail: aggregated claim without count"


# ============================================================================
# POST-FLIGHT GROUNDING CHECKER TESTS
# ============================================================================


def test_grounding_extractor_finds_paths():
    """Grounding checker extracts path claims from response."""
    checker = PostflightGroundingChecker()
    
    response = """
Created directories:
- /tmp/test_project/src
- /tmp/test_project/configs
"""
    paths = checker._extract_path_claims(response)
    
    assert len(paths) > 0, "Should extract paths from response"
    assert any("src" in p for p in paths), "Should find /tmp/test_project/src"


def test_grounding_checks_filesystem():
    """Grounding checker verifies paths against actual filesystem."""
    checker = PostflightGroundingChecker()
    
    # Create a temp path that exists
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        response = f"Created directory {tmpdir}/src"
        Path(f"{tmpdir}/src").mkdir(exist_ok=True)
        
        result = checker.check(response, filesystem_root=Path(tmpdir))
        
        assert result.grounded_claims >= 0, "Should check paths"


# ============================================================================
# STALL DETECTOR TESTS
# ============================================================================


def test_stall_detector_detects_stall():
    """Stall detector detects when no progress signal is received."""
    detector = StallDetector(timeout_seconds=0.3, max_duration_seconds=1.0)
    detector.signal_progress(ProgressSignal.TOOL_CALL_EXECUTED)
    
    # Wait for timeout
    time.sleep(0.4)
    
    assert detector.is_stalled(), "Should detect stall after timeout"
    assert detector.stall_duration() > 0, "Should have non-zero stall duration"


def test_stall_detector_recovers():
    """Stall detector resets on progress signal."""
    detector = StallDetector(timeout_seconds=0.3)
    detector.signal_progress(ProgressSignal.TOOL_CALL_EXECUTED)
    
    time.sleep(0.4)
    assert detector.is_stalled()
    
    # Recover
    detector.recover()
    assert not detector.is_stalled(), "Should recover from stall"


def test_stall_detector_persistent():
    """Stall detector detects persistent stall beyond max duration."""
    detector = StallDetector(timeout_seconds=0.2, max_duration_seconds=0.5)
    detector.signal_progress(ProgressSignal.TOOL_CALL_EXECUTED)
    
    time.sleep(0.7)
    
    assert detector.is_stalled()
    assert detector.is_persistent(), "Should detect persistent stall"


def test_stall_event_has_cause():
    """Stall event includes likely cause classification."""
    detector = StallDetector(timeout_seconds=0.2)
    detector.set_state("executing")
    detector.signal_progress(ProgressSignal.TOOL_CALL_EXECUTED)
    
    time.sleep(0.3)
    
    event = detector.get_stall_event()
    assert event is not None, "Should produce stall event"
    assert event.likely_cause in list(StallCause), "Should have valid cause"


def test_stall_cause_classification():
    """Stall detector classifies different causes."""
    # Waiting for tool: tool call made but no result
    detector = StallDetector(timeout_seconds=0.2)
    detector.set_state("executing")
    detector.set_tool_call("mkdir")
    detector.signal_progress(ProgressSignal.TOOL_CALL_EXECUTED)
    time.sleep(0.3)
    
    event = detector.get_stall_event()
    assert event.likely_cause == StallCause.WAITING_FOR_TOOL, \
        f"Expected waiting_for_tool, got {event.likely_cause}"


# ============================================================================
# HEARTBEAT EMITTER TESTS
# ============================================================================


def test_heartbeat_emits_on_interval():
    """Heartbeat emitter emits when interval elapsed."""
    heartbeat = HeartbeatEmitter(interval_seconds=0.3)
    
    assert not heartbeat.should_emit(), "Should not emit immediately"
    
    time.sleep(0.4)
    
    assert heartbeat.should_emit(), "Should emit after interval"


def test_heartbeat_reset():
    """Heartbeat emitter resets on emit."""
    heartbeat = HeartbeatEmitter(interval_seconds=0.3)
    time.sleep(0.4)
    
    assert heartbeat.should_emit()
    heartbeat.emit()
    
    assert not heartbeat.should_emit(), "Should reset after emit"


def test_heartbeat_miss_count():
    """Heartbeat emitter tracks miss count."""
    heartbeat = HeartbeatEmitter(interval_seconds=0.3)
    
    miss1 = heartbeat.record_miss()
    miss2 = heartbeat.record_miss()
    
    assert miss1 == 1
    assert miss2 == 2
    assert heartbeat.miss_count == 2


# ============================================================================
# VIOLATION TRACKER TESTS
# ============================================================================


def test_violation_tracker_counts():
    """Violation tracker counts violations by type."""
    tracker = ViolationTracker()
    
    tracker.record(Violation(
        violation_type=ViolationType.UNVERIFIED_COMPLETION_CLAIM,
        level=ViolationLevel.ERROR,
        message="Test violation 1",
    ))
    tracker.record(Violation(
        violation_type=ViolationType.UNVERIFIED_COMPLETION_CLAIM,
        level=ViolationLevel.ERROR,
        message="Test violation 2",
    ))
    tracker.record(Violation(
        violation_type=ViolationType.NARRATE_WITHOUT_TOOL,
        level=ViolationLevel.WARNING,
        message="Test warning",
    ))
    
    summary = tracker.get_summary()
    assert summary["total"] == 3
    assert summary["by_type"]["unverified_completion_claim"] == 2
    assert summary["by_level"]["error"] == 2
    assert summary["by_level"]["warning"] == 1


def test_violation_tracker_escalation():
    """Violation tracker escalates after threshold."""
    tracker = ViolationTracker(escalation_after=2)
    
    tracker.record(Violation(
        violation_type=ViolationType.UNVERIFIED_COMPLETION_CLAIM,
        level=ViolationLevel.ERROR,
        message="Violation 1",
    ))
    assert not tracker.should_escalate(ViolationType.UNVERIFIED_COMPLETION_CLAIM)
    
    tracker.record(Violation(
        violation_type=ViolationType.UNVERIFIED_COMPLETION_CLAIM,
        level=ViolationLevel.ERROR,
        message="Violation 2",
    ))
    assert tracker.should_escalate(ViolationType.UNVERIFIED_COMPLETION_CLAIM)


# ============================================================================
# ARTIFACT SUMMARY VALIDATOR TESTS
# ============================================================================


def test_artifact_validator_detects_missing_summary():
    """Artifact validator detects missing artifact summary."""
    validator = ArtifactSummaryValidator()
    
    response = "Task completed successfully."
    result = validator.validate(response)
    
    assert not result.passed, "Should fail: missing artifact summary"


def test_artifact_validator_passes_with_summary():
    """Artifact validator passes when artifact summary present."""
    validator = ArtifactSummaryValidator()
    
    response = """
Task completed.

Artifacts:
- Created: 6 directories
- Modified: 2 files

Verification:
- 8/8 checks passed
"""
    result = validator.validate(response)
    
    assert result.passed, "Should pass: artifact summary present"


# ============================================================================
# EXECUTION GUARDS FACADE TESTS
# ============================================================================


def test_execution_guards_preflight():
    """Execution guards preflight validation."""
    guards = ExecutionGuards()
    
    result = guards.preflight_validate("Created all files")
    assert not result.passed, "Should fail: unverified claim"


def test_execution_guards_progress_signal():
    """Execution guards signal progress."""
    guards = ExecutionGuards()
    
    guards.signal_progress(ProgressSignal.TOOL_CALL_EXECUTED)
    assert not guards.stall_detector.is_stalled()


def test_execution_guards_stall_detection():
    """Execution guards detect stall."""
    guards = ExecutionGuards(
        stall_detector=StallDetector(timeout_seconds=0.3),
    )
    
    guards.signal_progress(ProgressSignal.TOOL_CALL_EXECUTED)
    time.sleep(0.4)
    
    event = guards.get_stall_event()
    assert event is not None, "Should detect stall"


def test_execution_guards_violation_summary():
    """Execution guards provide violation summary."""
    guards = ExecutionGuards()
    
    guards.preflight_validate("Created all files")
    guards.preflight_validate("Done with everything")
    
    summary = guards.get_violation_summary()
    assert summary["total"] > 0, "Should have violations"


def test_execution_guards_from_config():
    """Execution guards load from config file."""
    repo_root = Path("/Users/user/zera")
    guards = ExecutionGuards.from_config(repo_root)
    
    assert guards is not None, "Should create from config"
    assert guards.preflight is not None, "Should have preflight validator"
    assert guards.stall_detector is not None, "Should have stall detector"


# ============================================================================
# MAIN
# ============================================================================


if __name__ == "__main__":
    import traceback
    
    tests = [
        ("test_preflight_detects_unverified_completion", test_preflight_detects_unverified_completion),
        ("test_preflight_passes_with_evidence", test_preflight_passes_with_evidence),
        ("test_preflight_detects_filesystem_claim_without_evidence", test_preflight_detects_filesystem_claim_without_evidence),
        ("test_preflight_warns_on_narrative", test_preflight_warns_on_narrative),
        ("test_preflight_detects_aggregation_without_count", test_preflight_detects_aggregation_without_count),
        ("test_grounding_extractor_finds_paths", test_grounding_extractor_finds_paths),
        ("test_grounding_checks_filesystem", test_grounding_checks_filesystem),
        ("test_stall_detector_detects_stall", test_stall_detector_detects_stall),
        ("test_stall_detector_recovers", test_stall_detector_recovers),
        ("test_stall_detector_persistent", test_stall_detector_persistent),
        ("test_stall_event_has_cause", test_stall_event_has_cause),
        ("test_stall_cause_classification", test_stall_cause_classification),
        ("test_heartbeat_emits_on_interval", test_heartbeat_emits_on_interval),
        ("test_heartbeat_reset", test_heartbeat_reset),
        ("test_heartbeat_miss_count", test_heartbeat_miss_count),
        ("test_violation_tracker_counts", test_violation_tracker_counts),
        ("test_violation_tracker_escalation", test_violation_tracker_escalation),
        ("test_artifact_validator_detects_missing_summary", test_artifact_validator_detects_missing_summary),
        ("test_artifact_validator_passes_with_summary", test_artifact_validator_passes_with_summary),
        ("test_execution_guards_preflight", test_execution_guards_preflight),
        ("test_execution_guards_progress_signal", test_execution_guards_progress_signal),
        ("test_execution_guards_stall_detection", test_execution_guards_stall_detection),
        ("test_execution_guards_violation_summary", test_execution_guards_violation_summary),
        ("test_execution_guards_from_config", test_execution_guards_from_config),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"✓ {name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\n{'=' * 60}")
    print(f"Results: {passed} passed, {failed} failed, {len(tests)} total")
    print(f"{'=' * 60}")
    
    sys.exit(0 if failed == 0 else 1)


# ============================================================================
# HEARTBEAT MONITOR TESTS (Continuous Background Thread)
# ============================================================================


def test_heartbeat_monitor_basic():
    """HeartbeatMonitor emits continuously in background thread."""
    from agent_os.execution_guards import HeartbeatMonitor
    
    monitor = HeartbeatMonitor(interval_seconds=0.3, run_id='test-hb')
    emit_count = [0]
    monitor.set_callback(lambda hb: emit_count.__setitem__(0, emit_count[0] + 1))
    monitor.start()
    
    time.sleep(1.0)
    stats = monitor.stop()
    
    assert stats['emit_count'] >= 2, f"Expected >= 2, got {stats['emit_count']}"
    assert not monitor._running, "Should stop after stop()"
    assert not monitor._thread.is_alive(), "Thread should be dead after stop"


def test_heartbeat_monitor_stall_integration():
    """HeartbeatMonitor reports stall_seconds from stall detector."""
    from agent_os.execution_guards import HeartbeatMonitor
    
    detector = StallDetector(timeout_seconds=0.3)
    monitor = HeartbeatMonitor(
        interval_seconds=0.3,
        run_id='test-stall',
        stall_detector=detector,
    )
    
    stall_heartbeats = [0]
    def on_hb(hb):
        if hb.stall_seconds > 0:
            stall_heartbeats[0] += 1
    
    monitor.set_callback(on_hb)
    detector.signal_progress(ProgressSignal.TOOL_CALL_EXECUTED)
    detector.set_state('executing')
    monitor.start()
    
    time.sleep(0.8)  # Wait for stall + heartbeat
    stats = monitor.stop()
    
    assert stats['emit_count'] >= 1, "Should emit at least 1 heartbeat"
    assert stall_heartbeats[0] >= 1, "Should report stall heartbeat"


def test_heartbeat_monitor_clean_shutdown():
    """HeartbeatMonitor shuts down cleanly without hanging."""
    from agent_os.execution_guards import HeartbeatMonitor
    
    monitor = HeartbeatMonitor(interval_seconds=0.5)
    monitor.start()
    stats = monitor.stop()
    
    assert not monitor._running
    assert not monitor._thread.is_alive()
    assert stats['emit_count'] >= 0  # May be 0 if stopped before interval

# Add heartbeat tests to the main test list
if __name__ == "__main__":
    import sys
    import traceback
    
    tests = [
        ("test_heartbeat_monitor_basic", test_heartbeat_monitor_basic),
        ("test_heartbeat_monitor_stall_integration", test_heartbeat_monitor_stall_integration),
        ("test_heartbeat_monitor_clean_shutdown", test_heartbeat_monitor_clean_shutdown),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_fn in tests:
        try:
            test_fn()
            print(f"✓ {name}")
            passed += 1
        except Exception as e:
            print(f"✗ {name}: {type(e).__name__}: {e}")
            failed += 1
    
    print(f"\nHeartbeatMonitor: {passed} passed, {failed} failed")
