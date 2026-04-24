from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)


def _utc_now_iso() -> str:
    return _utc_now().isoformat()


@dataclass
class BackgroundQueueItem:
    id: str
    idempotency_key: str
    job_type: str
    objective: str
    runtime_provider: str
    runtime_profile: str | None
    persona_id: str | None
    scheduler_profile: str | None
    queued_at: str
    not_before: str
    attempts: int
    max_attempts: int
    budget_limit: dict[str, Any]
    stop_token: str | None
    quiet_hours_policy: str | None
    escalation_policy: str | None
    proof_of_action: dict[str, Any]
    approval_ticket_id: str | None
    dead_letter_reason: str | None
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "idempotency_key": self.idempotency_key,
            "job_type": self.job_type,
            "objective": self.objective,
            "runtime_provider": self.runtime_provider,
            "runtime_profile": self.runtime_profile,
            "persona_id": self.persona_id,
            "scheduler_profile": self.scheduler_profile,
            "queued_at": self.queued_at,
            "not_before": self.not_before,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "budget_limit": self.budget_limit,
            "stop_token": self.stop_token,
            "quiet_hours_policy": self.quiet_hours_policy,
            "escalation_policy": self.escalation_policy,
            "proof_of_action": self.proof_of_action,
            "approval_ticket_id": self.approval_ticket_id,
            "dead_letter_reason": self.dead_letter_reason,
            "payload": self.payload,
        }


class BackgroundJobQueue:
    """Small JSON-backed queue for bounded background automation."""

    def __init__(self, repo_root: Path, queue_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.queue_path = queue_path or (self.repo_root / ".agents/runtime/background-jobs.json")
        self.control_path = self.repo_root / ".agents/runtime/background-control.json"
        self.queue_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.queue_path.exists():
            return {"queued": [], "completed": [], "failed": [], "updated_at": _utc_now_iso()}
        try:
            data = json.loads(self.queue_path.read_text(encoding="utf-8"))
        except Exception:
            return {"queued": [], "completed": [], "failed": [], "updated_at": _utc_now_iso()}
        if not isinstance(data, dict):
            return {"queued": [], "completed": [], "failed": [], "updated_at": _utc_now_iso()}
        data.setdefault("queued", [])
        data.setdefault("completed", [])
        data.setdefault("failed", [])
        data.setdefault("updated_at", _utc_now_iso())
        return data

    def _save(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = _utc_now_iso()
        self.queue_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def enqueue(
        self,
        *,
        job_type: str,
        objective: str,
        runtime_provider: str,
        runtime_profile: str | None,
        persona_id: str | None,
        scheduler_profile: str | None,
        idempotency_key: str,
        payload: dict[str, Any] | None = None,
        delay_seconds: int = 0,
        max_attempts: int = 3,
        budget_limit: dict[str, Any] | None = None,
        stop_token: str | None = None,
        quiet_hours_policy: str | None = None,
        escalation_policy: str | None = None,
        proof_of_action: dict[str, Any] | None = None,
        approval_ticket_id: str | None = None,
    ) -> tuple[BackgroundQueueItem, bool]:
        data = self._load()
        known = data.get("queued", []) + data.get("completed", []) + data.get("failed", [])
        for row in known:
            if isinstance(row, dict) and row.get("idempotency_key") == idempotency_key:
                return self._row_to_item(row), False
        item = BackgroundQueueItem(
            id=str(uuid4()),
            idempotency_key=idempotency_key,
            job_type=str(job_type).strip(),
            objective=str(objective).strip(),
            runtime_provider=str(runtime_provider).strip(),
            runtime_profile=str(runtime_profile).strip() or None if runtime_profile is not None else None,
            persona_id=str(persona_id).strip() or None if persona_id is not None else None,
            scheduler_profile=str(scheduler_profile).strip() or None if scheduler_profile is not None else None,
            queued_at=_utc_now_iso(),
            not_before=(_utc_now() + timedelta(seconds=max(0, int(delay_seconds)))).isoformat(),
            attempts=0,
            max_attempts=max(1, int(max_attempts)),
            budget_limit=dict(budget_limit or {}),
            stop_token=str(stop_token).strip() or None if stop_token is not None else None,
            quiet_hours_policy=str(quiet_hours_policy).strip() or None if quiet_hours_policy is not None else None,
            escalation_policy=str(escalation_policy).strip() or None if escalation_policy is not None else None,
            proof_of_action=dict(proof_of_action or {}),
            approval_ticket_id=str(approval_ticket_id).strip() or None if approval_ticket_id is not None else None,
            dead_letter_reason=None,
            payload=dict(payload or {}),
        )
        data["queued"].append(item.to_dict())
        self._save(data)
        return item, True

    def queued_items(self) -> list[BackgroundQueueItem]:
        return [self._row_to_item(row) for row in self._load().get("queued", []) if isinstance(row, dict)]

    def claim_due(self, *, limit: int = 10) -> list[BackgroundQueueItem]:
        data = self._load()
        now = _utc_now()
        claimed: list[BackgroundQueueItem] = []
        still_queued: list[dict[str, Any]] = []
        for row in data.get("queued", []):
            if not isinstance(row, dict):
                continue
            item = self._row_to_item(row)
            if len(claimed) >= limit:
                still_queued.append(item.to_dict())
                continue
            try:
                not_before = datetime.fromisoformat(item.not_before)
            except Exception:
                not_before = now
            if not_before <= now:
                claimed.append(item)
            else:
                still_queued.append(item.to_dict())
        data["queued"] = still_queued
        self._save(data)
        return claimed

    def mark_completed(self, item: BackgroundQueueItem, *, result: dict[str, Any] | None = None) -> None:
        data = self._load()
        row = item.to_dict()
        row["completed_at"] = _utc_now_iso()
        row["result"] = dict(result or {})
        if not row.get("proof_of_action"):
            row["proof_of_action"] = {
                "recorded_at": row["completed_at"],
                "objective": row.get("objective"),
                "job_type": row.get("job_type"),
            }
        data["completed"].append(row)
        self._save(data)

    def mark_failed(self, item: BackgroundQueueItem, *, error: str) -> None:
        data = self._load()
        row = item.to_dict()
        row["attempts"] = item.attempts + 1
        row["failed_at"] = _utc_now_iso()
        row["error"] = error
        if row["attempts"] < row["max_attempts"]:
            row["not_before"] = (_utc_now() + timedelta(seconds=30)).isoformat()
            data["queued"].append(row)
        else:
            row["dead_letter_reason"] = error
            data["failed"].append(row)
        self._save(data)

    def defer(self, item: BackgroundQueueItem, *, not_before: datetime, reason: str) -> None:
        data = self._load()
        row = item.to_dict()
        row["not_before"] = not_before.isoformat()
        payload = dict(row.get("payload") or {})
        payload["defer_reason"] = reason
        row["payload"] = payload
        data["queued"].append(row)
        self._save(data)

    def load_control(self) -> dict[str, Any]:
        if not self.control_path.exists():
            return {"paused_until": None, "updated_at": _utc_now_iso()}
        try:
            data = json.loads(self.control_path.read_text(encoding="utf-8"))
        except Exception:
            return {"paused_until": None, "updated_at": _utc_now_iso()}
        if not isinstance(data, dict):
            return {"paused_until": None, "updated_at": _utc_now_iso()}
        data.setdefault("paused_until", None)
        data.setdefault("updated_at", _utc_now_iso())
        return data

    def save_control(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = _utc_now_iso()
        self.control_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def pause_for(self, *, minutes: int) -> dict[str, Any]:
        until = (_utc_now() + timedelta(minutes=max(1, int(minutes)))).isoformat()
        payload = self.load_control()
        payload["paused_until"] = until
        self.save_control(payload)
        return payload

    def resume(self) -> dict[str, Any]:
        payload = self.load_control()
        payload["paused_until"] = None
        self.save_control(payload)
        return payload

    def paused_until(self) -> datetime | None:
        payload = self.load_control()
        raw = payload.get("paused_until")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(str(raw))
        except Exception:
            return None

    def is_paused(self, *, now: datetime | None = None) -> bool:
        pause_until = self.paused_until()
        if pause_until is None:
            return False
        return pause_until > (now or _utc_now())

    @staticmethod
    def _row_to_item(row: dict[str, Any]) -> BackgroundQueueItem:
        return BackgroundQueueItem(
            id=str(row.get("id") or uuid4()),
            idempotency_key=str(row.get("idempotency_key") or ""),
            job_type=str(row.get("job_type") or "unknown"),
            objective=str(row.get("objective") or ""),
            runtime_provider=str(row.get("runtime_provider") or "agent_os_python"),
            runtime_profile=str(row.get("runtime_profile") or "") or None,
            persona_id=str(row.get("persona_id") or "") or None,
            scheduler_profile=str(row.get("scheduler_profile") or "") or None,
            queued_at=str(row.get("queued_at") or _utc_now_iso()),
            not_before=str(row.get("not_before") or _utc_now_iso()),
            attempts=int(row.get("attempts", 0)),
            max_attempts=int(row.get("max_attempts", 3)),
            budget_limit=dict(row.get("budget_limit") or {}),
            stop_token=str(row.get("stop_token") or "") or None,
            quiet_hours_policy=str(row.get("quiet_hours_policy") or "") or None,
            escalation_policy=str(row.get("escalation_policy") or "") or None,
            proof_of_action=dict(row.get("proof_of_action") or {}),
            approval_ticket_id=str(row.get("approval_ticket_id") or "") or None,
            dead_letter_reason=str(row.get("dead_letter_reason") or "") or None,
            payload=dict(row.get("payload") or {}),
        )
