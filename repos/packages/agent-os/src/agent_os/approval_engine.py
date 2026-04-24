from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


def _utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


@dataclass
class ApprovalTicket:
    id: str
    created_at: str
    status: str
    action_type: str
    risk_class: str
    summary: str
    run_id: str
    runtime_provider: str
    persona_id: str | None
    approval_policy: str | None
    proposal: dict[str, Any]
    resolved_at: str | None = None
    resolved_by: str | None = None
    resolution: str | None = None
    note: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "status": self.status,
            "action_type": self.action_type,
            "risk_class": self.risk_class,
            "summary": self.summary,
            "run_id": self.run_id,
            "runtime_provider": self.runtime_provider,
            "persona_id": self.persona_id,
            "approval_policy": self.approval_policy,
            "proposal": self.proposal,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "resolution": self.resolution,
            "note": self.note,
        }


class ApprovalEngine:
    """Persistent approval queue for gated autonomous actions."""

    def __init__(self, repo_root: Path, storage_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.storage_path = storage_path or (self.repo_root / ".agents/runtime/approvals.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.storage_path.exists():
            return {"tickets": [], "updated_at": _utc_now_iso()}
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return {"tickets": [], "updated_at": _utc_now_iso()}
        if not isinstance(data, dict):
            return {"tickets": [], "updated_at": _utc_now_iso()}
        data.setdefault("tickets", [])
        data.setdefault("updated_at", _utc_now_iso())
        return data

    def _save(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = _utc_now_iso()
        self.storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    @staticmethod
    def _row_to_ticket(row: dict[str, Any]) -> ApprovalTicket:
        return ApprovalTicket(
            id=str(row.get("id") or uuid4()),
            created_at=str(row.get("created_at") or _utc_now_iso()),
            status=str(row.get("status") or "pending"),
            action_type=str(row.get("action_type") or "unknown"),
            risk_class=str(row.get("risk_class") or "unknown"),
            summary=str(row.get("summary") or ""),
            run_id=str(row.get("run_id") or ""),
            runtime_provider=str(row.get("runtime_provider") or "unknown"),
            persona_id=str(row.get("persona_id") or "") or None,
            approval_policy=str(row.get("approval_policy") or "") or None,
            proposal=dict(row.get("proposal") or {}),
            resolved_at=str(row.get("resolved_at") or "") or None,
            resolved_by=str(row.get("resolved_by") or "") or None,
            resolution=str(row.get("resolution") or "") or None,
            note=str(row.get("note") or "") or None,
        )

    def list_tickets(self, *, status: str | None = None) -> list[ApprovalTicket]:
        rows = self._load().get("tickets", [])
        out: list[ApprovalTicket] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            ticket = self._row_to_ticket(row)
            if status and ticket.status != status:
                continue
            out.append(ticket)
        return out

    def create_ticket(
        self,
        *,
        action_type: str,
        risk_class: str,
        summary: str,
        run_id: str,
        runtime_provider: str,
        persona_id: str | None,
        approval_policy: str | None,
        proposal: dict[str, Any],
    ) -> ApprovalTicket:
        data = self._load()
        for row in data.get("tickets", []):
            if not isinstance(row, dict):
                continue
            if row.get("status") != "pending":
                continue
            if row.get("run_id") == run_id and row.get("action_type") == action_type and row.get("summary") == summary:
                return self._row_to_ticket(row)
        ticket = ApprovalTicket(
            id=str(uuid4()),
            created_at=_utc_now_iso(),
            status="pending",
            action_type=str(action_type or "unknown"),
            risk_class=str(risk_class or "unknown"),
            summary=str(summary or "").strip(),
            run_id=str(run_id or ""),
            runtime_provider=str(runtime_provider or "unknown"),
            persona_id=str(persona_id or "") or None,
            approval_policy=str(approval_policy or "") or None,
            proposal=dict(proposal or {}),
        )
        data["tickets"].append(ticket.to_dict())
        self._save(data)
        return ticket

    def resolve(
        self,
        ticket_id: str,
        *,
        resolution: str,
        resolved_by: str = "operator",
        note: str | None = None,
    ) -> ApprovalTicket | None:
        data = self._load()
        rows = data.get("tickets", [])
        if not isinstance(rows, list):
            return None
        for idx, row in enumerate(rows):
            if not isinstance(row, dict) or str(row.get("id")) != str(ticket_id):
                continue
            row = dict(row)
            row["status"] = "approved" if resolution == "approve" else "denied"
            row["resolved_at"] = _utc_now_iso()
            row["resolved_by"] = str(resolved_by or "operator")
            row["resolution"] = str(resolution or "deny")
            row["note"] = str(note or "") or None
            rows[idx] = row
            self._save(data)
            return self._row_to_ticket(row)
        return None
