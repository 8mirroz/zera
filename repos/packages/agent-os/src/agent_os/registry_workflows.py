from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from .yaml_compat import parse_simple_yaml

try:  # pragma: no cover - optional dependency in some minimal environments
    import yaml
except Exception:  # pragma: no cover
    yaml = None

# ---------------------------------------------------------------------------
# Lazy-initialized structured trace emitter
# ---------------------------------------------------------------------------

_emitter: Any = None

def _get_emitter() -> Any:
    global _emitter
    if _emitter is None:
        from .trace_context import TraceSink, StructuredTraceEmitter
        _emitter = StructuredTraceEmitter(TraceSink(filename="agent_traces.jsonl"))
    return _emitter


class RegistryWorkflowResolver:
    """Resolve registry-backed workflow and orchestration skill metadata for a route."""

    _ROUTER_PATH = "configs/orchestrator/router.yaml"
    _WORKFLOW_DIR = "configs/registry/workflows"
    _SKILL_DIR = "configs/registry/skills"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self._router_cache: dict[str, Any] | None = None
        self._workflow_cache: dict[str, dict[str, Any]] = {}
        self._skill_cache: dict[str, dict[str, Any]] = {}

    def _load_yaml(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        text = path.read_text(encoding="utf-8")
        if yaml is not None:
            data = yaml.safe_load(text)
            return data if isinstance(data, dict) else {}
        data = parse_simple_yaml(text)
        return data if isinstance(data, dict) else {}

    @property
    def router_config(self) -> dict[str, Any]:
        if self._router_cache is None:
            self._router_cache = self._load_yaml(self.repo_root / self._ROUTER_PATH)
        return self._router_cache

    def _tier_row(self, complexity: str) -> dict[str, Any]:
        routing = self.router_config.get("routing") if isinstance(self.router_config, dict) else {}
        tiers = routing.get("tiers") if isinstance(routing, dict) else {}
        row = tiers.get(str(complexity or "").strip()) if isinstance(tiers, dict) else {}
        return row if isinstance(row, dict) else {}

    def workflow_path_for_complexity(self, complexity: str) -> str | None:
        row = self._tier_row(complexity)
        value = str(row.get("workflow") or "").strip()
        return value or None

    @staticmethod
    def workflow_ref_to_path_name(workflow_ref: str | None) -> str | None:
        raw = str(workflow_ref or "").strip()
        if not raw:
            return None
        stem = Path(raw).stem
        if stem.startswith("path-"):
            suffix = stem[len("path-") :]
            words = [part for part in suffix.split("-") if part]
            if words:
                return f"{' '.join(word.capitalize() for word in words)} Path"
        return None

    def load_workflow(self, rel_path: str) -> dict[str, Any]:
        key = str(rel_path or "").strip()
        if not key:
            return {}
        if key not in self._workflow_cache:
            self._workflow_cache[key] = self._load_yaml(self.repo_root / key)
        return self._workflow_cache[key]

    def load_skill(self, skill_id: str) -> dict[str, Any]:
        key = str(skill_id or "").strip()
        if not key:
            return {}
        # --- trace: skill loading ---
        t_start = time.perf_counter()
        from .trace_context import TraceContext
        skill_ctx = TraceContext.root(task_id=f"skill-{key}", tier="C2", component="registry_workflows")
        _get_emitter().task_start(skill_ctx, skill_id=key)
        # --- end trace ---

        if key not in self._skill_cache:
            path = self.repo_root / self._SKILL_DIR / f"{key}.yaml"
            self._skill_cache[key] = self._load_yaml(path)

        loaded = bool(self._skill_cache.get(key))
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        _get_emitter().task_end(skill_ctx, duration_ms=elapsed_ms, status="completed" if loaded else "not_found", skill_id=key, loaded=loaded)
        # --- end trace ---

        return self._skill_cache[key]

    def resolve(self, *, task_type: str, complexity: str, orchestration_path: str | None) -> dict[str, Any] | None:
        # --- trace: workflow resolution start ---
        t_start = time.perf_counter()
        from .trace_context import TraceContext
        ctx = TraceContext.root(
            task_id=f"resolve-{task_type}",
            tier=complexity,
            component="registry_workflows",
        )
        _get_emitter().task_start(ctx, workflow_resolution=True, task_type=task_type)
        # --- end trace ---

        workflow_path = self.workflow_path_for_complexity(complexity)
        if not workflow_path:
            _get_emitter().task_end(ctx, duration_ms=(time.perf_counter() - t_start) * 1000, status="no_workflow_found")
            return None
        workflow = self.load_workflow(workflow_path)
        if not workflow:
            _get_emitter().task_end(ctx, duration_ms=(time.perf_counter() - t_start) * 1000, status="workflow_empty")
            return None

        stages = workflow.get("stages") if isinstance(workflow.get("stages"), list) else []
        stage_ids = [str(stage.get("id")) for stage in stages if isinstance(stage, dict) and stage.get("id")]
        stage_agents = [str(stage.get("agent")) for stage in stages if isinstance(stage, dict) and stage.get("agent")]

        tier_row = self._tier_row(complexity)
        routing = self.router_config.get("routing") if isinstance(self.router_config, dict) else {}
        safeguards = routing.get("handoff_safeguards") if isinstance(routing, dict) else {}
        safeguards = safeguards if isinstance(safeguards, dict) else {}
        ralph_cfg = tier_row.get("ralph_loop") if isinstance(tier_row.get("ralph_loop"), dict) else {}

        handoff_skill_id = str(workflow.get("handoff_skill") or "dynamic-handoff").strip()
        iteration_skill_id = str(workflow.get("iteration_skill") or "ralph-loop-execute").strip()
        handoff_skill = self.load_skill(handoff_skill_id)
        iteration_skill = self.load_skill(iteration_skill_id)
        knowledge_policy = workflow.get("knowledge_policy") if isinstance(workflow.get("knowledge_policy"), dict) else {}
        effective_path = str(orchestration_path or self.workflow_ref_to_path_name(workflow_path) or "").strip() or None

        # --- trace: workflow resolution end ---
        elapsed_ms = (time.perf_counter() - t_start) * 1000
        _get_emitter().task_end(
            ctx,
            duration_ms=elapsed_ms,
            status="completed",
            workflow_path=workflow_path,
            resolved_name=workflow.get("name"),
            handoff_skill_id=handoff_skill_id,
            iteration_skill_id=iteration_skill_id,
        )
        # --- end trace ---

        return {
            "workflow_id": workflow.get("id"),
            "workflow_name": workflow.get("name"),
            "workflow_path": workflow_path,
            "task_type": task_type,
            "complexity": complexity,
            "orchestration_path": effective_path,
            "entry_agent": workflow.get("entry_agent"),
            "stage_ids": stage_ids,
            "stage_agents": stage_agents,
            "completion_criteria": list(workflow.get("completion_criteria") or []),
            "knowledge_policy": knowledge_policy,
            "handoff": {
                "skill_id": handoff_skill_id,
                "required": bool(safeguards.get("require_contract", False)),
                "max_depth": int(safeguards.get("max_chain_depth", 0) or 0),
                "forbid_cycles": bool(safeguards.get("forbid_cycles", False)),
                "schema": safeguards.get("contract_schema"),
                "outputs": list(handoff_skill.get("outputs") or []),
                "contract_fields": list(handoff_skill.get("contract_fields") or []),
                "knowledge_capture": handoff_skill.get("knowledge_capture") or {},
            },
            "iteration": {
                "skill_id": iteration_skill_id,
                "enabled": bool(ralph_cfg.get("enabled", False)),
                "iterations": int(ralph_cfg.get("iterations", 0) or 0),
                "outputs": list(iteration_skill.get("outputs") or []),
                "comparison_mode": iteration_skill.get("comparison_mode"),
                "verification_required": bool(iteration_skill.get("verification_required", False)),
            },
        }
