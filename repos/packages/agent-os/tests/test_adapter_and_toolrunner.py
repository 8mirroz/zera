"""Additional coverage tests for EggentRouterAdapter branches and ToolRunner."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

ROOT = Path(__file__).resolve().parents[4]
SRC = ROOT / "repos/packages/agent-os/src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_os.eggent_router_adapter import EggentRouterAdapter, _max_complexity, _bump_complexity
from agent_os.eggent_contracts import TaskSpecV1
from agent_os.tool_runner import ToolRunner
from agent_os.contracts import ToolInput
from agent_os.exceptions import ToolNotFoundError, PermissionDeniedError


# ---------------------------------------------------------------------------
# EggentRouterAdapter — uncovered branches
# ---------------------------------------------------------------------------

class TestEggentAdapterBranches:
    def setup_method(self):
        self.adapter = EggentRouterAdapter(ROOT)

    def _spec(self, **kwargs) -> dict:
        base = {
            "task_id": "test-1",
            "area": "backend",
            "risk": "low",
            "scope": "single_file",
            "complexity": "trivial",
            "requires_reasoning": False,
            "requires_accuracy": False,
        }
        base.update(kwargs)
        return base

    def test_area_tests_maps_to_t2(self):
        decision = self.adapter.route_task(self._spec(area="tests"))
        assert decision.task_type == "T2"

    def test_area_animation_maps_to_t6(self):
        decision = self.adapter.route_task(self._spec(area="animation"))
        assert decision.task_type == "T6"

    def test_area_infra_single_file_maps_to_t1(self):
        decision = self.adapter.route_task(self._spec(area="infra", scope="single_file"))
        assert decision.task_type == "T1"

    def test_area_infra_system_wide_maps_to_t4(self):
        decision = self.adapter.route_task(self._spec(
            area="infra", scope="system_wide", complexity="hard"
        ))
        assert decision.task_type == "T4"

    def test_high_risk_requires_reasoning_gives_supervisor(self):
        decision = self.adapter.route_task(self._spec(
            risk="high", requires_reasoning=True, complexity="normal"
        ))
        assert decision.execution_role == "supervisor"

    def test_system_wide_scope_gives_supervisor(self):
        decision = self.adapter.route_task(self._spec(
            scope="system_wide", complexity="hard"
        ))
        assert decision.execution_role == "supervisor"

    def test_c3_complexity_gives_specialist(self):
        decision = self.adapter.route_task(self._spec(
            scope="multi_file", complexity="normal"
        ))
        assert decision.execution_role == "specialist"

    def test_requires_reasoning_bumps_complexity(self):
        decision = self.adapter.route_task(self._spec(
            complexity="trivial", requires_reasoning=True
        ))
        # C1 + bump = C2
        assert decision.complexity_tier == "C2"

    def test_requires_accuracy_high_risk_bumps_complexity(self):
        decision = self.adapter.route_task(self._spec(
            complexity="normal", risk="high",
            requires_reasoning=False, requires_accuracy=True
        ))
        # normal=C2, risk=high -> min C4, accuracy+high -> bump -> C5
        assert decision.complexity_tier in {"C4", "C5"}

    def test_design_contour_true_for_t6(self):
        decision = self.adapter.route_task(self._spec(area="ui"))
        assert decision.design_contour is True

    def test_design_contour_false_for_non_t6(self):
        decision = self.adapter.route_task(self._spec(area="backend"))
        assert decision.design_contour is False

    def test_escalation_policy_has_required_keys(self):
        decision = self.adapter.route_task(self._spec())
        policy = decision.escalation_policy
        assert "max_worker_attempts" in policy
        assert "max_specialist_attempts" in policy

    def test_task_spec_v1_passed_directly(self):
        spec = TaskSpecV1(
            task_id="direct-1",
            area="backend",
            risk="low",
            scope="single_file",
            complexity="trivial",
            requires_reasoning=False,
            requires_accuracy=False,
        )
        decision = self.adapter.route_task(spec)
        assert decision.task_id == "direct-1"


class TestComplexityHelpers:
    def test_max_complexity(self):
        assert _max_complexity("C1", "C3") == "C3"
        assert _max_complexity("C4", "C2") == "C4"
        assert _max_complexity("C3", "C3") == "C3"

    def test_bump_complexity_caps_at_c5(self):
        assert _bump_complexity("C5", 1) == "C5"
        assert _bump_complexity("C4", 2) == "C5"

    def test_bump_complexity_zero_times(self):
        assert _bump_complexity("C2", 0) == "C2"


# ---------------------------------------------------------------------------
# ToolRunner — uncovered branches
# ---------------------------------------------------------------------------

class TestToolRunnerBranches:
    def setup_method(self):
        self.runner = ToolRunner()

    def test_invalid_mode_raises_permission_denied(self):
        tool_input = ToolInput(
            tool_name="echo",
            args=["hello"],
            mode="execute",  # invalid
            correlation_id="test-1",
        )
        with pytest.raises(PermissionDeniedError):
            self.runner.run(tool_input)

    def test_tool_not_found_raises(self):
        tool_input = ToolInput(
            tool_name="nonexistent_tool_xyz_12345",
            args=[],
            mode="read",
            correlation_id="test-2",
        )
        with pytest.raises(ToolNotFoundError):
            self.runner.run(tool_input)

    def test_write_mode_no_retry(self, tmp_path):
        # write mode: retries=0, so a failing tool returns error output (not raises)
        tool_input = ToolInput(
            tool_name="bash",
            args=["-c", "exit 1"],
            mode="write",
            correlation_id="test-3",
        )
        result = self.runner.run(tool_input)
        assert result.status == "error"
        assert result.exit_code == 1

    def test_read_mode_success(self, tmp_path):
        tool_input = ToolInput(
            tool_name="echo",
            args=["hello"],
            mode="read",
            correlation_id="test-4",
        )
        result = self.runner.run(tool_input)
        assert result.status == "ok"
        assert "hello" in result.stdout

    def test_to_json_returns_valid_json(self, tmp_path):
        import json
        tool_input = ToolInput(
            tool_name="echo",
            args=["test"],
            mode="read",
            correlation_id="test-5",
        )
        result = self.runner.run(tool_input)
        parsed = json.loads(ToolRunner.to_json(result))
        assert parsed["status"] == "ok"

    def test_timeout_for_test_tool(self):
        runner = ToolRunner(default_timeout_seconds=30, test_timeout_seconds=120)
        assert runner._timeout_for("run_tests") == 120
        assert runner._timeout_for("echo") == 30
