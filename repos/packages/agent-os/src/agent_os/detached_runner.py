from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


CLI_COMMANDS: dict[str, list[str]] = {
    "qwen": ["qwen", "-y"],
    "codex": ["codex", "exec", "--full-auto"],
    "kiro": ["kiro-cli", "run"],
    "claude": ["claude"],
    "opencode": ["opencode"],
}


class DetachedRunner:
    """
    Запускает CLI-агента как detached process.
    Статус пишется в .agents/tasks/<task_id>/status.json.
    Поддерживает on_complete цепочки (передаёт task_id следующему шагу).
    """

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self.tasks_dir = self.repo_root / ".agent" / "tasks"
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        *,
        prompt: str,
        cli: str = "qwen",
        task_id: str | None = None,
        on_complete: str | None = None,
        on_complete_prompt: str | None = None,
        session_id: str | None = None,
        policy: str | None = None,
        runner: str = "local",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task_id = task_id or str(uuid4())
        task_dir = self.tasks_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)

        status = {
            "task_id": task_id,
            "cli": cli,
            "prompt": prompt,
            "status": "pending",
            "created_at": _utc_now(),
            "started_at": None,
            "completed_at": None,
            "exit_code": None,
            "on_complete": on_complete,
            "on_complete_prompt": on_complete_prompt,
            "session_id": session_id,
            "policy": policy,
            "runner": runner,
            "metadata": metadata or {},
        }
        self._write_status(task_dir, status)

        script = self._build_wrapper_script(
            task_id=task_id,
            task_dir=task_dir,
            cli=cli,
            prompt=prompt,
            session_id=session_id,
        )
        script_path = task_dir / "run.sh"
        script_path.write_text(script, encoding="utf-8")
        script_path.chmod(0o755)

        proc = subprocess.Popen(
            ["/bin/bash", str(script_path)],
            stdout=open(task_dir / "stdout.log", "w"),
            stderr=open(task_dir / "stderr.log", "w"),
            start_new_session=True,
            close_fds=True,
        )

        status["status"] = "running"
        status["started_at"] = _utc_now()
        status["pid"] = proc.pid
        self._write_status(task_dir, status)

        return {"task_id": task_id, "pid": proc.pid, "status": "running", "task_dir": str(task_dir)}

    def get_status(self, task_id: str) -> dict[str, Any] | None:
        path = self.tasks_dir / task_id / "status.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def signal_complete(self, task_id: str, *, result: dict[str, Any] | None = None) -> dict[str, Any]:
        """Агент вызывает это когда шаг готов — триггерит on_complete цепочку."""
        status = self.get_status(task_id)
        if not status:
            return {"error": f"task {task_id} not found"}

        task_dir = self.tasks_dir / task_id
        status["status"] = "completed"
        status["completed_at"] = _utc_now()
        status["result"] = result or {}
        self._write_status(task_dir, status)

        # Запускаем следующий шаг если есть on_complete
        next_task: dict[str, Any] | None = None
        if status.get("on_complete") and status.get("on_complete_prompt"):
            next_task = self.run(
                prompt=status["on_complete_prompt"],
                cli=status.get("cli", "qwen"),
                on_complete=None,
                session_id=result.get("session_id") if result else None,
                metadata={"triggered_by": task_id},
            )

        return {"task_id": task_id, "status": "completed", "next_task": next_task}

    def bounce_back(self, task_id: str, *, reason: str, max_bounces: int = 3) -> dict[str, Any]:
        """Возвращает задачу на предыдущий шаг с причиной — аналог Request Changes."""
        status = self.get_status(task_id)
        if not status:
            return {"error": f"task {task_id} not found"}

        bounces = status.get("bounce_count", 0) + 1
        if bounces > max_bounces:
            return {"error": f"max_bounces ({max_bounces}) exceeded", "task_id": task_id}

        task_dir = self.tasks_dir / task_id
        status["status"] = "bounced"
        status["bounce_count"] = bounces
        status["bounce_reason"] = reason
        status["bounced_at"] = _utc_now()
        self._write_status(task_dir, status)

        # Перезапускаем с добавленным контекстом об ошибке
        enriched_prompt = f"{status['prompt']}\n\n[BOUNCE BACK #{bounces}]: {reason}"
        return self.run(
            prompt=enriched_prompt,
            cli=status.get("cli", "qwen"),
            task_id=f"{task_id}-bounce-{bounces}",
            session_id=status.get("session_id"),
            policy=status.get("policy"),
            metadata={**status.get("metadata", {}), "bounced_from": task_id, "bounce_count": bounces},
        )

    def list_tasks(self, *, status_filter: str | None = None) -> list[dict[str, Any]]:
        tasks = []
        for task_dir in sorted(self.tasks_dir.iterdir()):
            if not task_dir.is_dir():
                continue
            s = self.get_status(task_dir.name)
            if s and (status_filter is None or s.get("status") == status_filter):
                tasks.append(s)
        return tasks

    def _build_wrapper_script(
        self,
        *,
        task_id: str,
        task_dir: Path,
        cli: str,
        prompt: str,
        session_id: str | None,
    ) -> str:
        cmd_parts = CLI_COMMANDS.get(cli, [cli])
        cmd = " ".join(cmd_parts)
        escaped_prompt = prompt.replace('"', '\\"')
        session_flag = f'--session "{session_id}"' if session_id else ""
        status_path = task_dir / "status.json"

        return f"""#!/bin/bash
set -euo pipefail
TASK_ID="{task_id}"
STATUS_PATH="{status_path}"

# Обновляем статус через python inline
update_status() {{
  python3 -c "
import json, sys
p = '{status_path}'
try:
    d = json.loads(open(p).read())
except:
    d = {{}}
d['status'] = sys.argv[1]
open(p, 'w').write(json.dumps(d, indent=2))
" "$1"
}}

update_status "running"
{cmd} {session_flag} "{escaped_prompt}"
EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
  update_status "completed"
else
  update_status "failed"
fi

exit $EXIT_CODE
"""

    @staticmethod
    def _write_status(task_dir: Path, status: dict[str, Any]) -> None:
        (task_dir / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8"
        )
