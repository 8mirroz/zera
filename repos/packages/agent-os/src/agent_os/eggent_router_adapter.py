from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import ModelRouteInput, ModelRouteOutput
from .eggent_contracts import EggentRouteDecisionV1, TaskSpecV1
from .eggent_profile_loader import EggentProfileLoader
from .model_router import ModelRouter


_COMPLEXITY_ORDER = ["C1", "C2", "C3", "C4", "C5"]


def _max_complexity(a: str, b: str) -> str:
    ia = _COMPLEXITY_ORDER.index(a)
    ib = _COMPLEXITY_ORDER.index(b)
    return _COMPLEXITY_ORDER[max(ia, ib)]


def _bump_complexity(c: str, times: int = 1) -> str:
    idx = _COMPLEXITY_ORDER.index(c)
    return _COMPLEXITY_ORDER[min(len(_COMPLEXITY_ORDER) - 1, idx + max(0, times))]


@dataclass
class EggentMappingResult:
    task_type: str
    complexity_tier: str
    execution_role: str
    reasons: list[str]


class EggentRouterAdapter:
    """Deterministic TaskSpec -> ModelRouter adapter for Eggent compatibility."""

    def __init__(self, repo_root: Path, pack_root: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.profile_loader = EggentProfileLoader(self.repo_root, pack_root)
        self.profile = self.profile_loader.load()
        from .model_router import UnifiedRouter
        self.model_router = UnifiedRouter(repo_root=self.repo_root)

    def route_task(
        self,
        task_spec_raw: dict[str, Any] | TaskSpecV1,
        *,
        token_budget: int | None = None,
        cost_budget: float | None = None,
        preferred_models: list[str] | None = None,
        mode: str | None = None,
        unavailable_models: set[str] | None = None,
    ) -> EggentRouteDecisionV1:
        task_spec = task_spec_raw if isinstance(task_spec_raw, TaskSpecV1) else TaskSpecV1.from_dict(task_spec_raw)
        mapped = self._map_task(task_spec)
        budget_token, budget_cost = self._default_budgets(mapped.complexity_tier)

        route_output_dict = self.model_router.route(
            routing_topic=mapped.task_type,
            complexity_or_context=mapped.complexity_tier,
            context={
                "token_budget": int(token_budget) if token_budget is not None else int(budget_token),
                "cost_budget": float(cost_budget) if cost_budget is not None else float(budget_cost),
                "preferred_models": list(preferred_models or []),
                "mode": mode,
                "unavailable_models": list(unavailable_models or []),
                "complexity": mapped.complexity_tier,
                "execution_channel": "api_router",
            }
        )
        # Convert dict response to ModelRouteOutput for downstream compatibility
        from .contracts import ModelRouteOutput
        route_output = ModelRouteOutput(
            task_type=route_output_dict["task_type"],
            complexity=route_output_dict["complexity"],
            model_tier=route_output_dict["model_tier"],
            primary_model=route_output_dict["primary_model"],
            fallback_chain=route_output_dict["fallback_chain"],
            route_reason=route_output_dict["route_reason"],
            # Fill mandatory fields with v4 route payload (or safe defaults).
            max_input_tokens=int(route_output_dict.get("max_input_tokens", 0)),
            max_output_tokens=int(route_output_dict.get("max_output_tokens", 0)),
            provider_topology=str(route_output_dict.get("provider_topology", "hybrid")),
            routing_source=str(route_output_dict.get("routing_source", "v4")),
            orchestration_path=str(route_output_dict.get("orchestration_path", "")) or None,
            telemetry=dict(route_output_dict.get("telemetry", {})) if isinstance(route_output_dict.get("telemetry"), dict) else {},
        )

        route_reason_parts = list(mapped.reasons)
        route_reason_parts.append(route_output.route_reason)
        route_reason = "; ".join(route_reason_parts)

        decision = EggentRouteDecisionV1(
            task_id=task_spec.task_id,
            task_type=mapped.task_type,
            complexity_tier=mapped.complexity_tier,
            execution_role=mapped.execution_role,
            primary_model=route_output.primary_model,
            fallback_chain=list(route_output.fallback_chain),
            escalation_policy=self._build_escalation_policy(),
            design_contour=mapped.task_type == "T6",
            route_reason=route_reason,
            routing_source=route_output.routing_source,
            telemetry={
                "orchestration_path": route_output.orchestration_path,
                "provider_topology": route_output.provider_topology,
                "model_tier": route_output.model_tier,
                "router_telemetry": route_output.telemetry,
            },
        )
        return decision

    def _default_budgets(self, complexity: str) -> tuple[int, float]:
        providers_path = self.repo_root / "configs/tooling/model_providers.json"
        providers = json.loads(providers_path.read_text(encoding="utf-8"))
        row = providers.get("budgets", {}).get("per_complexity", {}).get(complexity, {})
        return int(row.get("max_total_tokens", 20000)), float(row.get("max_cost_usd", 0.3))

    def _build_escalation_policy(self) -> dict[str, Any]:
        rules = self.profile.escalation_rules
        failure_tracking = rules.get("failure_tracking", {})
        signals = rules.get("signals", {})
        supervisor_usage = rules.get("supervisor_usage", {})
        return {
            "max_worker_attempts": int(failure_tracking.get("max_worker_attempts", 3)),
            "max_specialist_attempts": int(failure_tracking.get("max_specialist_attempts", 2)),
            "signals": signals,
            "supervisor_usage": supervisor_usage,
        }

    def _map_task(self, task_spec: TaskSpecV1) -> EggentMappingResult:
        reasons: list[str] = []

        task_type = self._map_task_type(task_spec, reasons)
        complexity_tier = self._map_complexity_tier(task_spec, reasons)
        execution_role = self._select_execution_role(task_spec, task_type, complexity_tier, reasons)

        return EggentMappingResult(
            task_type=task_type,
            complexity_tier=complexity_tier,
            execution_role=execution_role,
            reasons=reasons,
        )

    def _map_task_type(self, task_spec: TaskSpecV1, reasons: list[str]) -> str:
        if task_spec.area in {"ui", "animation"}:
            reasons.append(f"area={task_spec.area} -> task_type=T6")
            return "T6"
        if task_spec.area == "tests":
            reasons.append("area=tests -> task_type=T2")
            return "T2"
        if task_spec.area == "backend":
            reasons.append("area=backend -> task_type=T3")
            return "T3"
        if task_spec.area == "infra" and task_spec.scope == "system_wide":
            reasons.append("area=infra + scope=system_wide -> task_type=T4")
            return "T4"
        if task_spec.area == "infra":
            reasons.append("area=infra -> task_type=T1")
            return "T1"

        reasons.append("fallback task_type=T3")
        return "T3"

    def _map_complexity_tier(self, task_spec: TaskSpecV1, reasons: list[str]) -> str:
        base = {
            "trivial": "C1",
            "normal": "C2",
            "hard": "C4",
        }[task_spec.complexity]
        reasons.append(f"complexity={task_spec.complexity} -> {base}")

        tier = base
        if task_spec.scope == "multi_file":
            tier = _max_complexity(tier, "C3")
            reasons.append("scope=multi_file -> min C3")
        elif task_spec.scope == "system_wide":
            tier = _max_complexity(tier, "C4")
            reasons.append("scope=system_wide -> min C4")

        if task_spec.risk == "high":
            tier = _max_complexity(tier, "C4")
            reasons.append("risk=high -> min C4")

        if task_spec.requires_reasoning:
            tier = _bump_complexity(tier, 1)
            reasons.append("requires_reasoning=true -> bump +1")

        if task_spec.requires_accuracy and task_spec.risk == "high":
            tier = _bump_complexity(tier, 1)
            reasons.append("requires_accuracy=true + risk=high -> bump +1")

        return tier

    def _select_execution_role(
        self,
        task_spec: TaskSpecV1,
        task_type: str,
        complexity_tier: str,
        reasons: list[str],
    ) -> str:
        if task_spec.scope == "system_wide":
            reasons.append("scope=system_wide -> execution_role=supervisor")
            return "supervisor"
        if task_spec.risk == "high" and task_spec.requires_reasoning:
            reasons.append("risk=high + requires_reasoning=true -> execution_role=supervisor")
            return "supervisor"

        if task_type == "T6" and complexity_tier in {"C1", "C2", "C3"}:
            reasons.append("ui/design fast path -> execution_role=worker")
            return "worker"

        if complexity_tier in {"C1", "C2"}:
            reasons.append("complexity in C1/C2 -> execution_role=worker")
            return "worker"
        if complexity_tier == "C3":
            reasons.append("complexity=C3 -> execution_role=specialist")
            return "specialist"

        reasons.append("complexity in C4/C5 -> execution_role=supervisor")
        return "supervisor"


def route_to_output(route_output: ModelRouteOutput) -> dict[str, Any]:
    return {
        "task_type": route_output.task_type,
        "complexity": route_output.complexity,
        "model_tier": route_output.model_tier,
        "primary_model": route_output.primary_model,
        "fallback_chain": list(route_output.fallback_chain),
        "route_reason": route_output.route_reason,
        "routing_source": route_output.routing_source,
        "orchestration_path": route_output.orchestration_path,
        "telemetry": route_output.telemetry,
    }
