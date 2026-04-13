from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256


def make_dedupe_key(*, user_id: int, action: str, payload: str) -> str:
    digest = sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"{user_id}:{action}:{digest}"


@dataclass
class MemoryIdempotencyStore:
    _keys: set[str] = field(default_factory=set)

    def seen(self, key: str) -> bool:
        if key in self._keys:
            return True
        self._keys.add(key)
        return False
