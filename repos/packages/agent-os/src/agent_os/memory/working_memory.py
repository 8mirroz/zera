"""Session-scoped working memory with TTL and capacity limits."""
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional


@dataclass
class MemoryEntry:
    content: str
    created_at: str
    relevance: float = 0.5
    entry_type: str = "session_data"
    metadata: Optional[dict] = None


class WorkingMemory:
    """Session-scoped memory with capacity limits and relevance scoring."""

    MAX_ENTRIES = 50
    TTL_HOURS = 24

    def __init__(self, memory_path: Path):
        self.path = memory_path
        self.entries: list[MemoryEntry] = []
        self.session_id = datetime.now().isoformat()
        self.created_at = datetime.now().isoformat()
        if self.path.exists():
            self.load()

    def add(self, entry: MemoryEntry) -> None:
        """Add entry. If at capacity, evict lowest-relevance entry."""
        self.entries.append(entry)
        if len(self.entries) > self.MAX_ENTRIES:
            self.entries.sort(key=lambda e: e.relevance, reverse=True)
            self.entries = self.entries[:self.MAX_ENTRIES]

    def get_relevant(self, query: str, top_k: int = 5) -> list[MemoryEntry]:
        """Return top-k entries by relevance to query using token + substring scoring."""
        import re
        query_lower = query.lower()
        query_tokens = set(re.findall(r"[a-zA-Z0-9_]+", query_lower))
        scored = []
        for entry in self.entries:
            content_lower = entry.content.lower()
            score = entry.relevance
            # Substring hit bonus
            if query_lower in content_lower:
                score += 0.4
            # Token overlap bonus (each matching token adds 0.1, capped at 0.5)
            if query_tokens:
                content_tokens = set(re.findall(r"[a-zA-Z0-9_]+", content_lower))
                overlap = len(query_tokens & content_tokens)
                score += min(overlap * 0.1, 0.5)
            # Recency bonus for working_memory type
            if entry.entry_type in {"active_goal", "working_memory"}:
                score += 0.1
            scored.append((score, entry))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [e for _, e in scored[:top_k]]

    def clear_expired(self) -> int:
        """Remove entries older than TTL. Return count removed."""
        cutoff = datetime.now() - timedelta(hours=self.TTL_HOURS)
        initial_count = len(self.entries)
        self.entries = [
            e for e in self.entries
            if datetime.fromisoformat(e.created_at) > cutoff
        ]
        return initial_count - len(self.entries)

    def save(self) -> None:
        """Persist to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "max_entries": self.MAX_ENTRIES,
            "ttl_hours": self.TTL_HOURS,
            "entries": [asdict(e) for e in self.entries]
        }
        self.path.write_text(json.dumps(data, indent=2))

    def load(self) -> None:
        """Load from disk."""
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text())
        self.session_id = data.get("session_id", self.session_id)
        self.created_at = data.get("created_at", self.created_at)
        self.entries = [
            MemoryEntry(**e) for e in data.get("entries", [])
        ]
        self.clear_expired()
