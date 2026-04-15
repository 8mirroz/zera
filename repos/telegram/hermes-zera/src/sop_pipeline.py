"""SOP Pipeline — MetaGPT-style phased multi-agent execution.

Phases:
  1. Orchestrator — task decomposition and role assignment
  2. Architect — system design and tradeoff analysis
  3. Engineer — implementation and testing
  4. Reviewer — adversarial validation and critique

Each phase produces structured output that feeds into the next.
The final result is a synthesized response combining all phases.
"""
from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from agent_executor import execute, ExecutionResult

logger = logging.getLogger("hermes-zera.sop")


class Phase(Enum):
    ORCHESTRATOR = "orchestrator"
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    REVIEWER = "reviewer"


@dataclass
class PhaseResult:
    """Output from a single SOP phase."""
    phase: Phase
    model: str
    output: str
    latency_ms: float
    status: str  # "completed" | "failed" | "skipped"
    error: str | None = None


@dataclass
class SOPResult:
    """Final result of the full SOP pipeline."""
    task: str
    tier: str
    phases_executed: list[str]
    final_response: str
    total_latency_ms: float
    phase_results: dict[str, PhaseResult] = field(default_factory=dict)


# System prompts for each phase
_PHASE_SYSTEM_PROMPTS = {
    Phase.ORCHESTRATOR: """Ты — Orchestrator в мульти-агентной системе Antigravity Core.

Твоя задача:
1. Проанализировать запрос пользователя
2. Декомпозировать его на подзадачи
3. Назначить роли (Architect, Engineer, Reviewer)
4. Определить план выполнения

Формат ответа:
- **Декомпозиция:** список подзадач
- **Роли:** кто что делает
- **План:** шаги выполнения
- **Риски:** потенциальные проблемы""",

    Phase.ARCHITECT: """Ты — Architect в мульти-агентной системе Antigravity Core.

Учитывая анализ Orchestrator, твоя задача:
1. Предложить архитектурное решение
2. Описать trade-offs (плюсы/минусы)
3. Определить зависимости и интеграции
4. Предложить план миграции (если нужно)

Формат ответа:
- **Архитектура:** описание решения
- **Trade-offs:** анализ вариантов
- **Зависимости:** что с чем связано
- **Миграция:** план внедрения""",

    Phase.ENGINEER: """Ты — Engineer в мульти-агентной системе Antigravity Core.

Учитывая план Orchestrator и архитекту Architect, твоя задача:
1. Предложить конкретную реализацию
2. Описать ключевые компоненты
3. Предложить тесты и валидацию
4. Документировать решение

Формат ответа:
- **Реализация:** код / конфигурация / описание
- **Компоненты:** ключевые части системы
- **Тесты:** что и как проверять
- **Документация:** важные заметки""",

    Phase.REVIEWER: """Ты — Reviewer в мульти-агентной системе Antigravity Core.

Учитывая весь контекст (Orchestrator → Architect → Engineer), твоя задача:
1. Найти слабые места в решении
2. Проверить качество кода и архитектуры
3. Оценить безопасность и надёжность
4. Дать финальную рекомендацию

Формат ответа:
- **Критика:** найденные проблемы
- **Качество:** оценка кода/архитектуры
- **Безопасность:** потенциальные риски
- **Рекомендация:** approve / revise / reject""",
}

# Model selection per phase (aligned with Antigravity Core models.yaml)
_PHASE_MODELS = {
    Phase.ORCHESTRATOR: "kc/deepseek/deepseek-v3.2",
    Phase.ARCHITECT: "antigravity/claude-opus-4-6-thinking",
    Phase.ENGINEER: "qw/qwen3-coder-plus",
    Phase.REVIEWER: "antigravity/claude-opus-4-6-thinking",
}

# Tiers that activate SOP
_SOP_TIERS = {"C3", "C4", "C5"}

# Phases per tier
_PHASES_PER_TIER = {
    "C3": [Phase.ORCHESTRATOR, Phase.ENGINEER, Phase.REVIEWER],
    "C4": [Phase.ORCHESTRATOR, Phase.ARCHITECT, Phase.ENGINEER, Phase.REVIEWER],
    "C5": [Phase.ORCHESTRATOR, Phase.ARCHITECT, Phase.ENGINEER, Phase.REVIEWER],
}


class SOPPipeline:
    """Phased multi-agent execution pipeline."""

    def __init__(
        self,
        system_prompt: str,
        conversation_history: list[dict[str, str]],
        tier: str,
        max_output_tokens: int = 4096,
        fallback_chains: dict[str, list[str]] | None = None,
    ) -> None:
        self.system_prompt = system_prompt
        self.history = conversation_history
        self.tier = tier
        self.max_output_tokens = max_output_tokens
        self.fallback_chains = fallback_chains or {}
        self.phase_results: dict[str, PhaseResult] = {}

    def should_run_sop(self) -> bool:
        """Check if SOP pipeline should run for this tier."""
        return self.tier in _SOP_TIERS

    def _get_phases(self) -> list[Phase]:
        return _PHASES_PER_TIER.get(self.tier, [Phase.ORCHESTRATOR])

    def _build_phase_prompt(self, phase: Phase) -> str:
        """Build system prompt for a phase, incorporating previous results."""
        base = _PHASE_SYSTEM_PROMPTS[phase]

        # Add previous phase results as context
        context_parts = []
        if phase == Phase.ARCHITECT and Phase.ORCHESTRATOR.value in self.phase_results:
            r = self.phase_results[Phase.ORCHESTRATOR.value]
            context_parts.append(f"## Анализ Orchestrator\n{r.output}")

        if phase == Phase.ENGINEER:
            if Phase.ORCHESTRATOR.value in self.phase_results:
                r = self.phase_results[Phase.ORCHESTRATOR.value]
                context_parts.append(f"## План Orchestrator\n{r.output}")
            if Phase.ARCHITECT.value in self.phase_results:
                r = self.phase_results[Phase.ARCHITECT.value]
                context_parts.append(f"## Архитектура Architect\n{r.output}")

        if phase == Phase.REVIEWER:
            for p in [Phase.ORCHESTRATOR, Phase.ARCHITECT, Phase.ENGINEER]:
                if p.value in self.phase_results:
                    r = self.phase_results[p.value]
                    context_parts.append(f"## Результат {p.value.capitalize()}\n{r.output}")

        if context_parts:
            return f"{base}\n\n---\n\n## Контекст из предыдущих фаз\n\n" + "\n\n".join(context_parts)
        return base

    def _build_phase_messages(self, phase: Phase) -> list[dict[str, str]]:
        """Build messages list for a phase execution."""
        # Add user's original request
        messages = list(self.history)

        # If there's a final user message, it's the task
        if messages and messages[-1].get("role") == "user":
            task = messages[-1]["content"]
            phase_prompt = f"Задача: {task}\n\nВыполни свою фазу ({phase.value})."
            messages.append({"role": "user", "content": phase_prompt})
        else:
            messages.append({"role": "user", "content": f"Выполни фазу {phase.value} для текущего контекста."})

        return messages

    def _execute_phase(self, phase: Phase) -> PhaseResult:
        """Execute a single phase with the selected model."""
        model = _PHASE_MODELS.get(phase, "qwen/qwen3-coder")
        system_prompt = self._build_phase_prompt(phase)
        messages = self._build_phase_messages(phase)
        fallback = self.fallback_chains.get(model, [])

        t0 = time.perf_counter()
        result = execute(
            model=model,
            system=system_prompt,
            messages=messages,
            max_tokens=self.max_output_tokens,
            fallback_chain=fallback_chain,
        )
        latency_ms = (time.perf_counter() - t0) * 1000

        if result.error:
            logger.warning(f"Phase {phase.value} failed: {result.error}")
            return PhaseResult(
                phase=phase,
                model=model,
                output="",
                latency_ms=latency_ms,
                status="failed",
                error=result.error,
            )

        return PhaseResult(
            phase=phase,
            model=model,
            output=result.response,
            latency_ms=latency_ms,
            status="completed",
        )

    def _synthesize_response(self) -> str:
        """Combine all phase results into a final response."""
        parts = []

        orchestrator = self.phase_results.get(Phase.ORCHESTRATOR.value)
        if orchestrator and orchestrator.status == "completed":
            parts.append(f"## 📋 План\n{orchestrator.output}")

        architect = self.phase_results.get(Phase.ARCHITECT.value)
        if architect and architect.status == "completed":
            parts.append(f"\n## 🏗️ Архитектура\n{architect.output}")

        engineer = self.phase_results.get(Phase.ENGINEER.value)
        if engineer and engineer.status == "completed":
            parts.append(f"\n## 🔧 Реализация\n{engineer.output}")

        reviewer = self.phase_results.get(Phase.REVIEWER.value)
        if reviewer and reviewer.status == "completed":
            parts.append(f"\n## 🔍 Рецензия\n{reviewer.output}")

        if not parts:
            return "SOP pipeline failed — no phase completed"

        return "\n".join(parts)

    def run(self) -> SOPResult:
        """Execute the full SOP pipeline."""
        if not self.should_run_sop():
            return SOPResult(
                task="",
                tier=self.tier,
                phases_executed=[],
                final_response="",
                total_latency_ms=0,
            )

        phases = self._get_phases()
        t0 = time.perf_counter()
        logger.info(f"🔄 SOP Pipeline starting for tier {self.tier}, phases: {[p.value for p in phases]}")

        for phase in phases:
            logger.info(f"  ▶ Phase: {phase.value}")
            result = self._execute_phase(phase)
            self.phase_results[phase.value] = result
            status_icon = "✅" if result.status == "completed" else "❌"
            logger.info(f"  {status_icon} {phase.value} completed ({result.latency_ms:.0f}ms)")

            # If architect fails, skip downstream phases
            if result.status == "failed" and phase == Phase.ARCHITECT:
                logger.warning(f"Architect failed, skipping downstream phases")
                break

        total_latency_ms = (time.perf_counter() - t0) * 1000
        final_response = self._synthesize_response()
        phases_executed = list(self.phase_results.keys())

        logger.info(f"✅ SOP Pipeline completed ({total_latency_ms:.0f}ms, {len(phases_executed)} phases)")

        return SOPResult(
            task="",
            tier=self.tier,
            phases_executed=phases_executed,
            final_response=final_response,
            total_latency_ms=total_latency_ms,
            phase_results={k: v for k, v in self.phase_results.items()},
        )
