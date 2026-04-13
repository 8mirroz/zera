from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from uuid import uuid4

from .contracts import MemoryStoreInput, MemoryStoreOutput

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)
_EGGENT_NAMESPACES = {"runs", "escalation", "design"}


def _parse_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _short_error(exc: Exception) -> str:
    message = f"{exc.__class__.__name__}: {exc}"
    return message[:200]


class _JsonlMemoryBackend:
    """JSONL-backed memory adapter for MVP."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        env_path = os.getenv("MEMORY_FILE_PATH", ".agent/memory/memory.jsonl")
        path = Path(env_path)
        if not path.is_absolute():
            path = self.repo_root / path
        self.memory_file_path = path
        self.memory_file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.memory_file_path.exists():
            self.memory_file_path.write_text("", encoding="utf-8")

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(tz=timezone.utc)

    @classmethod
    def _utc_now_iso(cls) -> str:
        return cls._utc_now().isoformat()

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return [token for token in re.findall(r"[a-zA-Z0-9_]+", text.lower()) if token]

    def _serialize_payload(self, payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)

    def _row_digest(self, key: str, payload: dict[str, Any]) -> str:
        return sha256(f"{key}\n{self._serialize_payload(payload)}".encode("utf-8")).hexdigest()

    def _compute_expiry(self, memory_input: MemoryStoreInput) -> str | None:
        options = memory_input.options if isinstance(memory_input.options, dict) else {}
        ttl_seconds = options.get("ttl_seconds")
        if ttl_seconds in (None, "", 0, "0"):
            return None
        try:
            ttl = int(ttl_seconds)
        except Exception:
            return None
        if ttl <= 0:
            return None
        return (self._utc_now() + timedelta(seconds=ttl)).isoformat()

    def operate(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        op = memory_input.op.lower()
        if op == "write":
            return self.write(memory_input)
        if op == "read":
            return self.read(memory_input)
        if op == "search":
            return self.search(memory_input)
        raise ValueError(f"Unsupported memory op: {memory_input.op}")

    def write(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        payload = dict(memory_input.payload or {})
        digest = self._row_digest(memory_input.key, payload)
        options = memory_input.options if isinstance(memory_input.options, dict) else {}
        existing = self._load_rows(include_expired=True)
        for row in existing:
            if row.get("key") == memory_input.key and row.get("digest") == digest and not self._is_expired(row):
                return MemoryStoreOutput(result=row, memory_ids=[str(row["id"])], confidence=float(row.get("confidence", 1.0)))

        mem_id = str(uuid4())
        row: dict[str, Any] = {
            "id": mem_id,
            "key": memory_input.key,
            "payload": payload,
            "digest": digest,
            "created_at": self._utc_now_iso(),
            "expires_at": self._compute_expiry(memory_input),
            "memory_class": str(options.get("memory_class") or "general"),
            "confidence": float(options.get("confidence", 1.0)),
            "source_confidence": float(options.get("source_confidence", options.get("confidence", 1.0))),
            "promotion_state": str(options.get("promotion_state") or "session_only"),
            "decay_score": float(options.get("decay_score", 0.0)),
            "user_scope": str(options.get("user_scope") or "default"),
            "evidence_refs": list(options.get("evidence_refs") or []),
            "correlation_id": memory_input.correlation_id,
        }
        with self.memory_file_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return MemoryStoreOutput(result=row, memory_ids=[mem_id], confidence=float(row["confidence"]))

    def read(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        matched = self.read_rows(memory_input.key)
        return MemoryStoreOutput(
            result={"items": matched, "count": len(matched)},
            memory_ids=[str(r["id"]) for r in matched],
            confidence=1.0,
        )

    def search(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        start = time.perf_counter()
        matched = self.search_rows(memory_input.key)
        retrieval_ms = int((time.perf_counter() - start) * 1000)
        event_payload = {
            "component": "memory",
            "run_id": memory_input.correlation_id or str(uuid4()),
            "status": "ok",
            "message": f"Memory retrieval scored for query '{memory_input.key[:60]}'",
            "data": {
                "query": memory_input.key,
                "hits": len(matched),
                "memory_ids": [str(r["id"]) for r in matched],
                "retrieval_ms": retrieval_ms,
            },
        }
        try:
            from .observability import emit_event

            emit_event("memory_retrieval_scored", event_payload)
        except Exception as exc:
            logger.debug("Failed to emit memory_retrieval_scored event: %s", exc)
        return MemoryStoreOutput(
            result={"items": matched, "count": len(matched)},
            memory_ids=[str(r["id"]) for r in matched],
            confidence=0.8 if matched else 0.0,
        )

    def read_rows(self, key: str) -> list[dict[str, Any]]:
        all_rows = self._load_rows()
        return [r for r in all_rows if r.get("key") == key]

    def search_rows(self, needle_raw: str) -> list[dict[str, Any]]:
        needle = needle_raw.lower().strip()
        rows = self._load_rows()
        if not needle:
            return rows[:10]
        query_tokens = self._tokenize(needle)
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in rows:
            haystack = f"{row.get('key', '')} {self._serialize_payload(row.get('payload', {}))}".lower()
            token_hits = sum(1 for token in query_tokens if token in haystack)
            substring_hit = 1 if needle in haystack else 0
            recency_bonus = 0.1 if row.get("memory_class") in {"active_goal", "working_memory"} else 0.0
            confidence = float(row.get("confidence", 1.0))
            score = (token_hits * 1.0) + (substring_hit * 0.5) + recency_bonus + confidence * 0.2
            if score > 0:
                row_copy = dict(row)
                row_copy["search_score"] = round(score, 4)
                scored.append((score, row_copy))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [row for _, row in scored[:10]]

    def _is_expired(self, row: dict[str, Any]) -> bool:
        raw = row.get("expires_at")
        if not raw:
            return False
        try:
            expires_at = datetime.fromisoformat(str(raw))
        except Exception:
            return False
        return expires_at <= self._utc_now()

    def _load_rows(self, *, include_expired: bool = False) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for line in self.memory_file_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except Exception:
                continue
            if isinstance(parsed, dict):
                if not include_expired and self._is_expired(parsed):
                    continue
                confidence = parsed.get("confidence")
                if confidence is not None:
                    age_hours = self._age_hours(parsed)
                    parsed["confidence"] = round(max(0.1, float(confidence) - (age_hours / 720.0)), 4)
                rows.append(parsed)
        return rows

    def _age_hours(self, row: dict[str, Any]) -> float:
        created_at = row.get("created_at")
        if not created_at:
            return 0.0
        try:
            created = datetime.fromisoformat(str(created_at))
        except Exception:
            return 0.0
        age_seconds = max(0.0, (self._utc_now() - created).total_seconds())
        return age_seconds / 3600.0


class _MemUCloudClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        user_id: str,
        agent_id: str,
        timeout_seconds: float,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.user_id = user_id
        self.agent_id = agent_id
        self.timeout_seconds = timeout_seconds

    def memorize_record(self, record_text: str) -> dict[str, Any]:
        payload = {
            "conversation": [{"role": "user", "content": record_text}],
            "user_id": self.user_id,
            "agent_id": self.agent_id,
        }
        return self._post_json("/api/v3/memory/memorize", payload)

    def retrieve(self, query: str) -> dict[str, Any]:
        payload = {
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "query": query,
        }
        return self._post_json("/api/v3/memory/retrieve", payload)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.base_url}{path}"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib_request.Request(
            url=url,
            data=data,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib_request.urlopen(req, timeout=self.timeout_seconds) as response:
                status = int(getattr(response, "status", 200))
                body = response.read()
        except urllib_error.HTTPError as exc:
            body = b""
            try:
                body = exc.read()
            except Exception:
                pass  # best-effort body read; ignore if unavailable
            body_text = body.decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"memU HTTP {exc.code}: {body_text}") from exc
        except urllib_error.URLError as exc:
            raise RuntimeError(f"memU network error: {exc.reason}") from exc
        except Exception as exc:
            raise RuntimeError(f"memU request error: {exc}") from exc

        if status >= 400:
            body_text = body.decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"memU HTTP {status}: {body_text}")

        if not body:
            return {}
        try:
            parsed = json.loads(body.decode("utf-8"))
        except Exception as exc:
            raise RuntimeError("memU returned non-JSON response") from exc
        if not isinstance(parsed, dict):
            raise RuntimeError("memU returned unexpected response shape")
        return parsed


class _MemUCloudHybridBackend:
    def __init__(self, local_backend: _JsonlMemoryBackend, cloud_client: _MemUCloudClient, *, fail_open: bool) -> None:
        self.local_backend = local_backend
        self.cloud_client = cloud_client
        self.fail_open = fail_open

    def operate(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        op = memory_input.op.lower()
        if op == "write":
            return self._write(memory_input)
        if op == "read":
            return self._read(memory_input)
        if op == "search":
            return self._search(memory_input)
        raise ValueError(f"Unsupported memory op: {memory_input.op}")

    def _write(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        local_out = self.local_backend.write(memory_input)
        row = local_out.result
        row["_backend"] = "memu_cloud_hybrid"

        record_text = self._serialize_record(row)
        try:
            cloud_result = self.cloud_client.memorize_record(record_text)
        except Exception as exc:
            row["_memu"] = {
                "status": "failed",
                "error": _short_error(exc),
            }
            logger.warning("memU cloud write failed; keeping local write (fail-open): %s", _short_error(exc))
            return local_out

        memu_meta: dict[str, Any] = {"status": "submitted"}
        task_id = cloud_result.get("task_id")
        if task_id:
            memu_meta["task_id"] = task_id
        elif cloud_result:
            memu_meta["response"] = cloud_result
        row["_memu"] = memu_meta
        return local_out

    def _read(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        return self.local_backend.read(memory_input)

    def _search(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        local_rows = self.local_backend.search_rows(memory_input.key)
        local_items = [{**row, "_source": "jsonl_local"} for row in local_rows]
        local_ids = [str(row["id"]) for row in local_rows if "id" in row]

        result: dict[str, Any] = {
            "items": local_items,
            "_backend": "memu_cloud_hybrid",
        }
        try:
            cloud_response = self.cloud_client.retrieve(memory_input.key)
        except Exception as exc:
            if not self.fail_open:
                raise RuntimeError(f"memU cloud search failed: {_short_error(exc)}") from exc
            result["_memu"] = {"status": "failed", "error": _short_error(exc)}
            logger.warning("memU cloud search failed; returning local results only: %s", _short_error(exc))
            return MemoryStoreOutput(result=result, memory_ids=local_ids, confidence=0.8)

        memu_items, memu_ids, memu_raw = self._normalize_cloud_hits(cloud_response)
        result["items"] = local_items + memu_items
        result["_memu"] = {"status": "ok", "hit_count": len(memu_items)}
        if memu_raw is not None:
            result["_memu_raw"] = memu_raw
        return MemoryStoreOutput(result=result, memory_ids=local_ids + memu_ids, confidence=0.9)

    def _serialize_record(self, row: dict[str, Any]) -> str:
        payload_json = json.dumps(row.get("payload", {}), ensure_ascii=False, sort_keys=True)
        return (
            "AGENT_OS_MEMORY_RECORD_V1\n"
            f"id={row.get('id', '')}\n"
            f"key={row.get('key', '')}\n"
            f"payload_json={payload_json}"
        )

    def _normalize_cloud_hits(
        self,
        cloud_response: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[str], dict[str, Any] | None]:
        raw_hits = cloud_response.get("items")
        if not isinstance(raw_hits, list):
            raw_hits = cloud_response.get("memories")
        if not isinstance(raw_hits, list):
            return [], [], cloud_response

        items: list[dict[str, Any]] = []
        ids: list[str] = []
        for idx, raw in enumerate(raw_hits):
            raw_item = raw if isinstance(raw, dict) else {"value": raw}
            raw_id = raw_item.get("id")
            mem_id = str(raw_id) if raw_id not in (None, "") else f"memu:{idx}"
            raw_key = raw_item.get("key")
            key = raw_key if isinstance(raw_key, str) and raw_key else "__memu__"
            if not isinstance(key, str):
                key = str(key)
            items.append(
                {
                    "id": mem_id,
                    "key": key,
                    "payload": {"memu": raw_item},
                    "_source": "memu_cloud",
                }
            )
            ids.append(mem_id)
        return items, ids, None


class MemoryStore:
    """MemoryStore facade with pluggable backends (default JSONL, optional memU Cloud hybrid)."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self._local_backend = _JsonlMemoryBackend(self.repo_root)
        self._backend = self._select_backend()

    def _select_backend(self) -> Any:
        backend_name = (os.getenv("MEMORY_BACKEND", "jsonl") or "jsonl").strip().lower()
        if backend_name == "jsonl":
            logger.info("MemoryStore backend selected: jsonl")
            return self._local_backend

        if backend_name != "memu_cloud":
            raise ValueError(f"Unsupported MEMORY_BACKEND={backend_name!r}; expected 'jsonl' or 'memu_cloud'")

        fail_open = _parse_bool_env("MEMU_FAIL_OPEN", False)
        if fail_open:
            logger.warning("MEMU_FAIL_OPEN is explicitly enabled — memory store will silently fall back on errors")
        try:
            client = self._build_memu_cloud_client()
        except Exception as exc:
            if fail_open:
                logger.warning(
                    "memU cloud backend init failed; falling back to jsonl backend (MEMU_FAIL_OPEN=true): %s",
                    _short_error(exc),
                )
                return self._local_backend
            raise

        logger.info("MemoryStore backend selected: memu_cloud_hybrid")
        return _MemUCloudHybridBackend(self._local_backend, client, fail_open=fail_open)

    def _build_memu_cloud_client(self) -> _MemUCloudClient:
        api_key = (os.getenv("MEMU_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("MEMU_API_KEY is required when MEMORY_BACKEND=memu_cloud")

        base_url = (os.getenv("MEMU_BASE_URL") or "https://api.memu.so").strip()
        parsed = urllib_parse.urlparse(base_url)
        if not base_url or not parsed.scheme or not parsed.netloc:
            raise ValueError("MEMU_BASE_URL must be a valid absolute URL")

        timeout_raw = (os.getenv("MEMU_HTTP_TIMEOUT_SECONDS") or "5").strip()
        try:
            timeout_seconds = float(timeout_raw)
        except ValueError as exc:
            raise ValueError("MEMU_HTTP_TIMEOUT_SECONDS must be a positive number") from exc
        if timeout_seconds <= 0:
            raise ValueError("MEMU_HTTP_TIMEOUT_SECONDS must be a positive number")

        user_id = (os.getenv("MEMU_USER_ID") or "antigravity-core").strip() or "antigravity-core"
        agent_id = (os.getenv("MEMU_AGENT_ID") or "agent-os-memory-store").strip() or "agent-os-memory-store"

        return _MemUCloudClient(
            base_url=base_url,
            api_key=api_key,
            user_id=user_id,
            agent_id=agent_id,
            timeout_seconds=timeout_seconds,
        )

    def operate(self, memory_input: MemoryStoreInput) -> MemoryStoreOutput:
        return self._backend.operate(memory_input)

    def eggent_key(self, namespace: str, task_id: str, *, suffix: str | None = None) -> str:
        ns = str(namespace).strip().lower()
        if ns not in _EGGENT_NAMESPACES:
            allowed = ", ".join(sorted(_EGGENT_NAMESPACES))
            raise ValueError(f"Unsupported Eggent namespace: {namespace!r}. Allowed: {allowed}")
        tid = str(task_id).strip()
        if not tid:
            raise ValueError("task_id must be non-empty")
        if suffix is None or str(suffix).strip() == "":
            return f"eggent:{ns}:{tid}"
        return f"eggent:{ns}:{tid}:{str(suffix).strip()}"

    def record_eggent_snapshot(
        self,
        namespace: str,
        task_id: str,
        payload: dict[str, Any],
        *,
        suffix: str | None = None,
    ) -> MemoryStoreOutput:
        key = self.eggent_key(namespace, task_id, suffix=suffix)
        return self.operate(MemoryStoreInput(op="write", key=key, payload=dict(payload)))
