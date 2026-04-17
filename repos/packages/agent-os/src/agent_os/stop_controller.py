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
class StopSignal:
    id: str
    scope: str
    reason: str
    created_at: str
    expires_at: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scope": self.scope,
            "reason": self.reason,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
        }


class StopController:
    """Persistent stop signal registry for bounded autonomy."""

    def __init__(self, repo_root: Path, storage_path: Path | None = None) -> None:
        self.repo_root = Path(repo_root)
        self.storage_path = storage_path or (self.repo_root / ".agents/runtime/stop-signals.json")
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self.storage_path.exists():
            return {"signals": [], "updated_at": _utc_now_iso()}
        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return {"signals": [], "updated_at": _utc_now_iso()}
        if not isinstance(data, dict):
            return {"signals": [], "updated_at": _utc_now_iso()}
        data.setdefault("signals", [])
        data.setdefault("updated_at", _utc_now_iso())
        return data

    def _save(self, payload: dict[str, Any]) -> None:
        payload["updated_at"] = _utc_now_iso()
        self.storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def signal(self, *, scope: str = "global", reason: str = "operator_stop", minutes: int | None = None) -> StopSignal:
        data = self._load()
        expires_at = None
        if minutes is not None and int(minutes) > 0:
            expires_at = (_utc_now() + timedelta(minutes=int(minutes))).isoformat()
        signal = StopSignal(
            id=str(uuid4()),
            scope=str(scope or "global"),
            reason=str(reason or "operator_stop"),
            created_at=_utc_now_iso(),
            expires_at=expires_at,
        )
        data["signals"] = [row for row in data.get("signals", []) if not self._is_expired_row(row)]
        data["signals"].append(signal.to_dict())
        self._save(data)
        return signal

    def clear(self, *, scope: str | None = None) -> dict[str, Any]:
        data = self._load()
        signals = []
        for row in data.get("signals", []):
            if not isinstance(row, dict):
                continue
            if scope and str(row.get("scope") or "") == scope:
                continue
            if self._is_expired_row(row):
                continue
            signals.append(row)
        data["signals"] = signals
        self._save(data)
        return data

    def active_signals(self, *, scope: str | None = None) -> list[StopSignal]:
        data = self._load()
        out: list[StopSignal] = []
        for row in data.get("signals", []):
            if not isinstance(row, dict) or self._is_expired_row(row):
                continue
            if scope and str(row.get("scope") or "") not in {scope, "global"}:
                continue
            out.append(
                StopSignal(
                    id=str(row.get("id") or uuid4()),
                    scope=str(row.get("scope") or "global"),
                    reason=str(row.get("reason") or "operator_stop"),
                    created_at=str(row.get("created_at") or _utc_now_iso()),
                    expires_at=str(row.get("expires_at") or "") or None,
                )
            )
        return out

    def is_stopped(self, *, scope: str | None = None) -> bool:
        return bool(self.active_signals(scope=scope))

    @staticmethod
    def _is_expired_row(row: dict[str, Any]) -> bool:
        raw = row.get("expires_at")
        if not raw:
            return False
        try:
            expires_at = datetime.fromisoformat(str(raw))
        except Exception:
            return False
        return expires_at <= _utc_now()
