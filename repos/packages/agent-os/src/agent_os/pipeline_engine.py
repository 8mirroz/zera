from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from .detached_runner import DetachedRunner


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class PipelineEngine:
    """
    Event-driven pipeline — шаги запускаются демоном по триггерам,
    оркестратор не блокируется на ожидании.

    Триггеры:
      on_complete      — старт после конкретного шага
      on_complete_all  — fan-in, ждём группу шагов
      on_file          — реагируем на появление файла
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self.pipelines_dir = self.repo_root / ".agent" / "pipelines"
        self.pipelines_dir.mkdir(parents=True, exist_ok=True)
        self.runner = DetachedRunner(repo_root)

    def create(self, *, name: str, steps: list[dict[str, Any]]) -> dict[str, Any]:
        """
        steps пример:
        [
          {"name": "research", "prompt": "...", "cli": "qwen"},
          {"name": "backend",  "prompt": "...", "on_complete": "research"},
          {"name": "frontend", "prompt": "...", "on_complete": "research"},
          {"name": "deploy",   "prompt": "...", "on_complete_all": ["backend", "frontend"]},
        ]
        """
        pipeline_id = str(uuid4())
        pipeline = {
            "pipeline_id": pipeline_id,
            "name": name,
            "status": "pending",
            "created_at": _utc_now(),
            "steps": {s["name"]: self._init_step(s) for s in steps},
            "step_order": [s["name"] for s in steps],
        }
        self._save(pipeline_id, pipeline)

        # Запускаем шаги без зависимостей сразу
        for step_name, step in pipeline["steps"].items():
            if not step.get("on_complete") and not step.get("on_complete_all") and not step.get("on_file"):
                self._launch_step(pipeline, step_name)

        pipeline["status"] = "running"
        self._save(pipeline_id, pipeline)
        return {"pipeline_id": pipeline_id, "name": name, "status": "running"}

    def signal_step_complete(
        self, pipeline_id: str, step_name: str, *, result: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Агент вызывает это когда шаг готов."""
        pipeline = self._load(pipeline_id)
        if not pipeline:
            return {"error": f"pipeline {pipeline_id} not found"}

        step = pipeline["steps"].get(step_name)
        if not step:
            return {"error": f"step {step_name} not found"}

        step["status"] = "completed"
        step["completed_at"] = _utc_now()
        step["result"] = result or {}

        triggered = self._check_triggers(pipeline, completed_step=step_name)
        self._update_pipeline_status(pipeline)
        self._save(pipeline_id, pipeline)

        return {"pipeline_id": pipeline_id, "step": step_name, "triggered": triggered}

    def bounce_step(self, pipeline_id: str, step_name: str, *, reason: str) -> dict[str, Any]:
        """Возврат шага на доработку — аналог Request Changes."""
        pipeline = self._load(pipeline_id)
        if not pipeline:
            return {"error": f"pipeline {pipeline_id} not found"}

        step = pipeline["steps"].get(step_name)
        if not step:
            return {"error": f"step {step_name} not found"}

        max_bounces = pipeline.get("max_bounces", 3)
        bounces = step.get("bounce_count", 0) + 1

        if bounces > max_bounces:
            # fail-fast: отменяем весь pipeline
            pipeline["status"] = "failed"
            pipeline["failed_reason"] = f"step '{step_name}' exceeded max_bounces={max_bounces}: {reason}"
            self._save(pipeline_id, pipeline)
            return {"error": "max_bounces exceeded", "pipeline_status": "failed"}

        step["status"] = "bounced"
        step["bounce_count"] = bounces
        step["bounce_reason"] = reason

        # Перезапускаем шаг с контекстом
        enriched = f"{step['prompt']}\n\n[BOUNCE #{bounces}]: {reason}"
        task = self.runner.run(prompt=enriched, cli=step.get("cli", "qwen"), metadata={"pipeline_id": pipeline_id, "step": step_name})
        step["task_id"] = task["task_id"]
        step["status"] = "running"

        self._save(pipeline_id, pipeline)
        return {"pipeline_id": pipeline_id, "step": step_name, "bounce": bounces, "task_id": task["task_id"]}

    def get_status(self, pipeline_id: str) -> dict[str, Any] | None:
        return self._load(pipeline_id)

    def list_pipelines(self) -> list[dict[str, Any]]:
        result = []
        for f in sorted(self.pipelines_dir.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                result.append({"pipeline_id": data["pipeline_id"], "name": data["name"], "status": data["status"], "created_at": data["created_at"]})
            except Exception:
                pass
        return result

    # ── internal ──────────────────────────────────────────────────────────────

    def _check_triggers(self, pipeline: dict[str, Any], *, completed_step: str) -> list[str]:
        triggered = []
        for step_name, step in pipeline["steps"].items():
            if step["status"] not in ("pending", "waiting"):
                continue

            # on_complete — один предшественник
            if step.get("on_complete") == completed_step:
                self._launch_step(pipeline, step_name)
                triggered.append(step_name)

            # on_complete_all — fan-in
            elif deps := step.get("on_complete_all"):
                if all(pipeline["steps"].get(d, {}).get("status") == "completed" for d in deps):
                    # Собираем session_id из последнего завершённого шага
                    last_result = pipeline["steps"].get(deps[-1], {}).get("result", {})
                    step["inherited_session_id"] = last_result.get("session_id")
                    self._launch_step(pipeline, step_name)
                    triggered.append(step_name)

        return triggered

    def _launch_step(self, pipeline: dict[str, Any], step_name: str) -> None:
        step = pipeline["steps"][step_name]
        session_id = step.get("inherited_session_id") or step.get("session_id")
        task = self.runner.run(
            prompt=step["prompt"],
            cli=step.get("cli", "qwen"),
            session_id=session_id,
            policy=step.get("policy"),
            metadata={"pipeline_id": pipeline["pipeline_id"], "step": step_name},
        )
        step["task_id"] = task["task_id"]
        step["status"] = "running"
        step["started_at"] = _utc_now()

    def _update_pipeline_status(self, pipeline: dict[str, Any]) -> None:
        statuses = [s["status"] for s in pipeline["steps"].values()]
        if any(s == "failed" for s in statuses):
            pipeline["status"] = "failed"
        elif all(s == "completed" for s in statuses):
            pipeline["status"] = "completed"
            pipeline["completed_at"] = _utc_now()

    def _init_step(self, step_def: dict[str, Any]) -> dict[str, Any]:
        has_dep = any(k in step_def for k in ("on_complete", "on_complete_all", "on_file"))
        return {
            "name": step_def["name"],
            "prompt": step_def["prompt"],
            "cli": step_def.get("cli", "qwen"),
            "policy": step_def.get("policy"),
            "session_id": step_def.get("session_id"),
            "inherited_session_id": None,
            "on_complete": step_def.get("on_complete"),
            "on_complete_all": step_def.get("on_complete_all"),
            "on_file": step_def.get("on_file"),
            "group": step_def.get("group"),
            "count": step_def.get("count", 1),
            "status": "waiting" if has_dep else "pending",
            "task_id": None,
            "started_at": None,
            "completed_at": None,
            "bounce_count": 0,
            "bounce_reason": None,
            "result": {},
        }

    def _save(self, pipeline_id: str, data: dict[str, Any]) -> None:
        path = self.pipelines_dir / f"{pipeline_id}.json"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _load(self, pipeline_id: str) -> dict[str, Any] | None:
        path = self.pipelines_dir / f"{pipeline_id}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None
