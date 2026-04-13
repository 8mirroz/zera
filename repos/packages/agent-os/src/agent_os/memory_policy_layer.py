"""MemoryPolicyLayer — слоевая память поверх MemoryStore.

Читает configs/global/memory_policy.yaml.
Добавляет scope (session/project/workspace/user_preferences),
TTL, write_rules и retrieval_priority поверх существующего MemoryStore.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import MemoryStoreInput, MemoryStoreOutput
from .memory_store import MemoryStore
from .yaml_compat import parse_simple_yaml
from .config_loader import ModularConfigLoader, ConfigNode

_SCOPE_TTL_HOURS = {
    "session": 24,
    "project": 180 * 24,
    "workspace": 365 * 24,
    "user_preferences": 365 * 24,
}

_NEVER_WRITE_KEYWORDS = {
    "temporary_credentials",
    "transient_debugging",
    "unverified_claims",
    "credential",
    "secret",
    "token",
}


class MemoryPolicyLayer:
    """Scoped memory facade: session / project / workspace / user_preferences.

    Wraps MemoryStore and enforces write_rules from memory_policy.yaml.
    """

    _POLICY_PATH = "configs/global/memory_policy.yaml"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self._store = MemoryStore(repo_root)
        self.loader = ModularConfigLoader(str(self.repo_root))
        self._policy: dict[str, Any] = {}
        self._load_policy()

    def _load_policy(self) -> None:
        try:
            self._policy = self.loader.load_suite(self._POLICY_PATH)
        except Exception:
            self._policy = {}

    def _scope_ttl_seconds(self, scope: str) -> int | None:
        lifecycle = ModularConfigLoader.get_component(self._policy, "memory_lifecycle")
        if lifecycle:
            layers = lifecycle.get("memory_layers", {})
            if isinstance(layers, ConfigNode) and scope in layers._data:
                layer = layers._data[scope]
                if isinstance(layer, dict):
                    if "ttl_hours" in layer:
                        return int(layer["ttl_hours"]) * 3600
                    if "ttl_days" in layer:
                        return int(layer["ttl_days"]) * 86400
        
        # Fallback to hardcoded defaults
        hours = _SCOPE_TTL_HOURS.get(scope)
        return hours * 3600 if hours else None

    def _is_never_write(self, key: str, payload: dict[str, Any]) -> bool:
        combined = f"{key} {json.dumps(payload, ensure_ascii=False)}".lower()
        return any(kw in combined for kw in _NEVER_WRITE_KEYWORDS)

    def _scoped_key(self, scope: str, key: str) -> str:
        return f"{scope}:{key}"

    def write(
        self,
        key: str,
        payload: dict[str, Any],
        *,
        scope: str = "session",
        require_confirmation: bool = False,
    ) -> MemoryStoreOutput | None:
        """Write to memory with scope enforcement.

        Returns None if write_rules block the write.
        """
        if self._is_never_write(key, payload):
            return None

        if require_confirmation:
            # In production this would queue for human approval;
            # here we skip the write and return a sentinel.
            return MemoryStoreOutput(
                result={"status": "pending_confirmation", "key": key, "scope": scope},
                memory_ids=[],
                confidence=0.0,
            )

        ttl = self._scope_ttl_seconds(scope)
        options: dict[str, Any] = {"memory_class": scope}
        if ttl:
            options["ttl_seconds"] = ttl

        scoped_key = self._scoped_key(scope, key)
        return self._store.operate(
            MemoryStoreInput(
                op="write",
                key=scoped_key,
                payload={**payload, "_scope": scope},
                options=options,
            )
        )

    def read(self, key: str, *, scope: str = "session") -> MemoryStoreOutput:
        return self._store.operate(
            MemoryStoreInput(op="read", key=self._scoped_key(scope, key), payload={})
        )

    def search(
        self,
        query: str,
        *,
        scopes: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Search across scopes in retrieval_priority order."""
        priority = self._retrieval_priority()
        target_scopes = scopes if scopes else priority

        all_items: list[dict[str, Any]] = []
        seen_ids: set[str] = set()

        for scope in target_scopes:
            result = self._store.operate(
                MemoryStoreInput(op="search", key=query, payload={})
            )
            for item in result.result.get("items", []):
                if not isinstance(item, dict):
                    continue
                item_scope = item.get("payload", {}).get("_scope", "")
                if item_scope and item_scope != scope:
                    continue
                item_id = str(item.get("id", ""))
                if item_id and item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                all_items.append(item)

        return all_items

    def _retrieval_priority(self) -> list[str]:
        raw = self._policy.get("retrieval_priority", [])
        if isinstance(raw, list) and raw:
            return [str(s) for s in raw]
        return ["session", "project", "workspace", "user_preferences"]
