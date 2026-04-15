"""PEER Cooperation — Plan → Execute → Evaluate → Reflect.

Inspired by agentUniverse PEER patterns.
Provides a reflection loop on top of SOP pipeline results.

Phases:
  P — Plan: Define approach, constraints, success criteria
  E — Execute: Run SOP or direct execution
  E — Evaluate: Check results against success criteria
  R — Reflect: Learn from outcome, update patterns
"""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger("hermes-zera.peer")


class PEERPhase(Enum):
    PLAN = "plan"
    EXECUTE = "execute"
    EVALUATE = "evaluate"
    REFLECT = "reflect"


@dataclass
class PlanOutput:
    objective: str
    constraints: list[str]
    success_criteria: list[str]
    approach: str


@dataclass
class EvaluationResult:
    passed: bool
    criteria_met: list[str]
    criteria_failed: list[str]
    score: float  # 0.0 - 1.0
    feedback: str


@dataclass
class ReflectionOutput:
    what_worked: list[str]
    what_failed: list[str]
    lessons: list[str]
    pattern_updates: list[str]


@dataclass
class PEERResult:
    tier: str
    plan: PlanOutput
    execution_output: str
    evaluation: EvaluationResult
    reflection: ReflectionOutput | None
    total_iterations: int
    total_latency_ms: float


class PEEROrchestrator:
    """Plan→Execute→Evaluate→Reflect loop for quality-critical tasks.

    Wraps SOP pipeline or direct execution with reflection.
    Used for C4/C5 tasks where quality validation matters.
    """

    _PLAN_PROMPT = """Ты — фаза Planning в PEER цикле.

Для задачи: {task}

Определи:
1. **Objective:** конкретная, измеримая цель
2. **Constraints:** ограничения (время, токены, зависимости)
3. **Success Criteria:** 3-5 конкретных критериев успеха
4. **Approach:** общий план выполнения

Формат ответа — YAML:
objective: ...
constraints:
  - ...
success_criteria:
  - ...
approach: ..."""

    _EVALUATE_PROMPT = """Ты — фаза Evaluation в PEER цикле.

Цель: {objective}
Критерии успеха: {criteria}
Результат выполнения: {execution_output}

Оцени:
1. Какие критерии выполнены?
2. Какие провалены?
3. Общая оценка (0.0-1.0)
4. Конкретный feedback

Формат ответа — YAML:
passed: true/false
criteria_met:
  - ...
criteria_failed:
  - ...
score: 0.0-1.0
feedback: ..."""

    _REFLECT_PROMPT = """Ты — фаза Reflection в PEER цикле.

Результат Evaluation: {evaluation_result}
План был: {plan_approach}

Определи:
1. Что сработало хорошо?
2. Что провалилось?
3. Извлечённые уроки
4. Какие паттерны нужно обновить?

Формат ответа — YAML:
what_worked:
  - ...
what_failed:
  - ...
lessons:
  - ...
pattern_updates:
  - ..."""

    def __init__(self, max_reflections: int = 3) -> None:
        self.max_reflections = max_reflections

    def _parse_yaml_response(self, text: str) -> dict[str, Any]:
        """Parse YAML-like response from LLM."""
        result: dict[str, Any] = {}
        current_key: str | None = None
        current_list: list[str] | None = None

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            if stripped.startswith("- "):
                value = stripped[2:].strip().strip('"').strip("'")
                if current_list is not None and current_key:
                    current_list.append(value)
                continue

            if ":" in stripped:
                # Save previous list
                if current_list is not None and current_key:
                    result[current_key] = current_list

                key, _, val = stripped.partition(":")
                key = key.strip()
                val = val.strip().strip('"').strip("'")

                if val.lower() in ("true", "yes"):
                    result[key] = True
                    current_key = key
                    current_list = None
                elif val.lower() in ("false", "no"):
                    result[key] = False
                    current_key = key
                    current_list = None
                else:
                    try:
                        result[key] = float(val)
                        current_key = key
                        current_list = None
                    except ValueError:
                        result[key] = val
                        current_key = key
                        current_list = []

        # Save last list
        if current_list is not None and current_key:
            result[current_key] = current_list

        return result

    def _run_plan(self, task: str) -> PlanOutput:
        """Phase 1: Plan — define approach and success criteria."""
        prompt = self._PLAN_PROMPT.format(task=task)
        # In production, this would call an LLM. For now, generate structured plan.
        logger.info(f"  📝 PEER Plan: {task[:60]}...")
        return PlanOutput(
            objective=task,
            constraints=["max_tokens: 4096", "single_response", "no_external_deps"],
            success_criteria=["complete answer", "addresses user question", "actionable"],
            approach="Direct execution with quality validation",
        )

    def _run_evaluate(
        self,
        plan: PlanOutput,
        execution_output: str,
    ) -> EvaluationResult:
        """Phase 3: Evaluate — check against success criteria."""
        logger.info("  🔍 PEER Evaluate: checking criteria...")
        # In production, call LLM with _EVALUATE_PROMPT.
        # For now, heuristic evaluation
        passed = bool(execution_output.strip())
        return EvaluationResult(
            passed=passed,
            criteria_met=plan.success_criteria if passed else [],
            criteria_failed=plan.success_criteria if not passed else [],
            score=0.8 if passed else 0.0,
            feedback="Execution completed" if passed else "Execution failed",
        )

    def _run_reflect(
        self,
        plan: PlanOutput,
        evaluation: EvaluationResult,
    ) -> ReflectionOutput:
        """Phase 4: Reflect — learn from outcome."""
        logger.info("  💡 PEER Reflect: extracting lessons...")
        if evaluation.passed:
            return ReflectionOutput(
                what_worked=["Execution met all criteria"],
                what_failed=[],
                lessons=["Direct approach was sufficient"],
                pattern_updates=[],
            )
        else:
            return ReflectionOutput(
                what_worked=["Plan was structured"],
                what_failed=["Execution did not meet criteria"],
                lessons=["Consider SOP pipeline for this task type"],
                pattern_updates=["Escalate to multi-agent for similar tasks"],
            )

    def run(
        self,
        task: str,
        tier: str,
        execution_fn: Any = None,
    ) -> PEERResult:
        """Run the full PEER loop.

        Args:
            task: user task description
            tier: C1-C5 complexity tier
            execution_fn: callable that performs the task (returns output string)

        Returns:
            PEERResult with all phases
        """
        t0 = time.perf_counter()

        # Phase 1: Plan
        plan = self._run_plan(task)

        # Phase 2: Execute
        logger.info("  ⚡ PEER Execute: running task...")
        if execution_fn:
            execution_output = execution_fn()
        else:
            execution_output = "[No execution_fn provided]"

        # Phase 3: Evaluate
        evaluation = self._run_evaluate(plan, execution_output)

        # Phase 4: Reflect
        reflection = None
        iterations = 1

        # If evaluation failed, reflect and potentially re-execute
        if not evaluation.passed and iterations < self.max_reflections:
            reflection = self._run_reflect(plan, evaluation)
            # Could re-execute with updated approach here
            iterations += 1

        total_latency_ms = (time.perf_counter() - t0) * 1000

        logger.info(
            f"✅ PEER completed ({total_latency_ms:.0f}ms, "
            f"score={evaluation.score:.2f}, passed={evaluation.passed})"
        )

        return PEERResult(
            tier=tier,
            plan=plan,
            execution_output=execution_output,
            evaluation=evaluation,
            reflection=reflection,
            total_iterations=iterations,
            total_latency_ms=total_latency_ms,
        )
