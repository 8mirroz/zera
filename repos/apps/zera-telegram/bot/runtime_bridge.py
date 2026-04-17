from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[4]
SWARMCTL = REPO_ROOT / "repos/packages/agent-os/scripts/swarmctl.py"
_LAST_REQUEST_TS: dict[int, float] = {}


def repo_root() -> Path:
    override = os.getenv("AGENT_OS_REPO_ROOT")
    if override:
        return Path(override).resolve()
    return REPO_ROOT


def allowed_chat_ids() -> set[int]:
    raw = str(os.getenv("TG_ALLOWED_CHAT_IDS") or "").strip()
    if not raw:
        return set()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except Exception:
            continue
    return out


def is_chat_allowed(chat_id: int) -> bool:
    allow = allowed_chat_ids()
    return not allow or chat_id in allow


def admin_chat_ids() -> set[int]:
    raw = str(os.getenv("TG_ADMIN_CHAT_IDS") or "").strip()
    if not raw:
        return allowed_chat_ids()
    out: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except Exception:
            continue
    return out


def is_admin_chat(chat_id: int) -> bool:
    admins = admin_chat_ids()
    return not admins or chat_id in admins


def rate_limit_seconds() -> float:
    raw = str(os.getenv("TG_RATE_LIMIT_SECONDS") or "3").strip()
    try:
        return max(0.0, float(raw))
    except Exception:
        return 3.0


def is_rate_limited(chat_id: int) -> bool:
    now = time.monotonic()
    prev = _LAST_REQUEST_TS.get(chat_id)
    limit = rate_limit_seconds()
    if prev is not None and (now - prev) < limit:
        return True
    _LAST_REQUEST_TS[chat_id] = now
    return False


def response_chunks(text: str, *, limit: int = 3500) -> list[str]:
    normalized = str(text or "").strip() or "No response produced."
    if len(normalized) <= limit:
        return [normalized]
    chunks: list[str] = []
    current = normalized
    while len(current) > limit:
        split_at = current.rfind("\n", 0, limit)
        if split_at < max(1000, limit // 2):
            split_at = current.rfind(" ", 0, limit)
        if split_at < max(1000, limit // 2):
            split_at = limit
        chunks.append(current[:split_at].rstrip())
        current = current[split_at:].lstrip()
    if current:
        chunks.append(current)
    return chunks


def queue_summary() -> dict[str, Any]:
    queue_path = repo_root() / ".agents/runtime/background-jobs.json"
    if not queue_path.exists():
        return {"queued": 0, "completed": 0, "failed": 0, "queue_file": str(queue_path)}
    try:
        data = json.loads(queue_path.read_text(encoding="utf-8"))
    except Exception:
        return {"queued": 0, "completed": 0, "failed": 0, "queue_file": str(queue_path), "status": "invalid"}
    return {
        "queued": len(data.get("queued", [])) if isinstance(data.get("queued"), list) else 0,
        "completed": len(data.get("completed", [])) if isinstance(data.get("completed"), list) else 0,
        "failed": len(data.get("failed", [])) if isinstance(data.get("failed"), list) else 0,
        "queue_file": str(queue_path),
        "updated_at": data.get("updated_at"),
    }


def health_text() -> str:
    summary = queue_summary()
    runtime_provider = os.getenv("AG_RUNTIME_PROVIDER", "zeroclaw")
    runtime_profile = os.getenv("AG_RUNTIME_PROFILE", "zera-telegram-prod")
    native_mode = str(os.getenv("ZEROCLAW_USE_NATIVE_BIN") or "false").lower()
    return (
        "Zera runtime health\n"
        f"provider: {runtime_provider}\n"
        f"profile: {runtime_profile}\n"
        f"native_mode: {native_mode}\n"
        f"queued_jobs: {summary['queued']}\n"
        f"completed_jobs: {summary['completed']}\n"
        f"failed_jobs: {summary['failed']}"
    )


def mode_text() -> str:
    return (
        "Zera runtime mode\n"
        f"bot_mode: {os.getenv('TG_BOT_MODE', 'polling')}\n"
        f"runtime_provider: {os.getenv('AG_RUNTIME_PROVIDER', 'zeroclaw')}\n"
        f"runtime_profile: {os.getenv('AG_RUNTIME_PROFILE', 'zera-telegram-prod')}\n"
        f"native_mode: {str(os.getenv('ZEROCLAW_USE_NATIVE_BIN') or 'false').lower()}\n"
        f"webhook_path: {os.getenv('TG_WEBHOOK_PATH', '/telegram/webhook')}"
    )


def _run_swarmctl_command(args: list[str], *, timeout_seconds: int = 60) -> str:
    env = dict(os.environ)
    env.setdefault("ENABLE_ZEROCLAW_ADAPTER", "true")
    env.setdefault("AGENT_OS_REPO_ROOT", str(repo_root()))
    proc = subprocess.run(
        [sys.executable, str(SWARMCTL), *args],
        capture_output=True,
        text=True,
        cwd=repo_root(),
        env=env,
        timeout=timeout_seconds,
        check=False,
    )
    if proc.returncode != 0:
        return f"Command error: {(proc.stderr or proc.stdout).strip()[:400]}"
    return proc.stdout.strip()


def background_status_text() -> str:
    return _run_swarmctl_command(["background-status"], timeout_seconds=30)


def background_drain_text(limit: int = 10) -> str:
    return _run_swarmctl_command(["background-daemon", "--limit", str(limit)], timeout_seconds=120)


def pause_background_text(minutes: int) -> str:
    return _run_swarmctl_command(["background-pause", "--minutes", str(minutes)], timeout_seconds=30)


def resume_background_text() -> str:
    return _run_swarmctl_command(["background-resume"], timeout_seconds=30)


def approval_list_text() -> str:
    return _run_swarmctl_command(["approval-list"], timeout_seconds=30)


def approval_resolve_text(ticket_id: str, decision: str) -> str:
    return _run_swarmctl_command(["approval-resolve", ticket_id, decision], timeout_seconds=30)


def goal_stack_text() -> str:
    return _run_swarmctl_command(["goal-stack"], timeout_seconds=30)


def budget_status_text() -> str:
    return _run_swarmctl_command(["budget-status"], timeout_seconds=30)


def incident_report_text() -> str:
    return _run_swarmctl_command(["incident-report"], timeout_seconds=30)


def stop_signal_text(minutes: int = 30, scope: str = "global") -> str:
    return _run_swarmctl_command(["stop-signal", "--scope", scope, "--minutes", str(minutes)], timeout_seconds=30)


def stop_clear_text(scope: str = "global") -> str:
    return _run_swarmctl_command(["stop-clear", "--scope", scope], timeout_seconds=30)


def run_companion_flow(text: str) -> str:
    runtime_provider = os.getenv("AG_RUNTIME_PROVIDER", "zeroclaw")
    runtime_profile = os.getenv("AG_RUNTIME_PROFILE", "zera-telegram-prod")
    task_type = os.getenv("AG_TASK_TYPE", "T7")
    complexity = os.getenv("AG_COMPLEXITY", "C2")
    timeout_raw = os.getenv("TG_RUNTIME_TIMEOUT_SECONDS", "60")
    try:
        timeout_seconds = max(10, int(timeout_raw))
    except Exception:
        timeout_seconds = 60

    stdout = _run_swarmctl_command(
        [
            "run",
            text,
            "--task-type",
            task_type,
            "--complexity",
            complexity,
            "--runtime-provider",
            runtime_provider,
            "--runtime-profile",
            runtime_profile,
        ],
        timeout_seconds=timeout_seconds,
    )
    try:
        payload = json.loads(stdout)
    except Exception:
        return stdout[:1000]
    agent = payload.get("agent", {})
    if isinstance(agent, dict):
        return str(agent.get("response_text") or agent.get("diff_summary") or "No response produced.")
    return "No response produced."
