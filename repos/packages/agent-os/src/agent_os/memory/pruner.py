"""Memory pruning with TTL, relevance decay, and retention policies."""
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class RetentionPolicy(Enum):
    PERMANENT = "permanent"        # Never auto-deleted (ki_captures, ADRs)
    LONG_TERM = "long_term"        # 90 days (patterns, retros)
    MEDIUM_TERM = "medium_term"    # 30 days (task traces)
    SHORT_TERM = "short_term"      # 7 days (session data)


@dataclass
class PruningConfig:
    default_ttl_days: int = 30
    half_life_days: int = 7        # For temporal decay scoring
    min_relevance_score: float = 0.3
    archive_before_delete: bool = True
    archive_path: str = ".agent/memory/archive/"


class MemoryPruner:
    """Prunes memory entries based on TTL, relevance decay, and retention policy."""

    TTL_MAP = {
        RetentionPolicy.PERMANENT: None,
        RetentionPolicy.LONG_TERM: 90,
        RetentionPolicy.MEDIUM_TERM: 30,
        RetentionPolicy.SHORT_TERM: 7,
    }

    def __init__(self, config: PruningConfig):
        self.config = config

    def compute_relevance(self, entry: dict, current_time: float) -> float:
        """
        Score = base_relevance * temporal_decay
        temporal_decay = 0.5 ^ (age_days / half_life_days)
        """
        base_relevance = entry.get("relevance", 0.5)
        created_str = entry.get("created_at") or entry.get("created", "")
        if not created_str:
            return base_relevance
        
        try:
            created = datetime.fromisoformat(created_str)
            age_days = (datetime.now() - created).days
            temporal_decay = 0.5 ** (age_days / self.config.half_life_days)
            return base_relevance * temporal_decay
        except (ValueError, TypeError):
            return base_relevance

    def classify_retention(self, entry: dict) -> RetentionPolicy:
        """Determine retention policy based on entry type."""
        type_map = {
            "ki_capture": RetentionPolicy.PERMANENT,
            "adr": RetentionPolicy.PERMANENT,
            "pattern": RetentionPolicy.LONG_TERM,
            "retro": RetentionPolicy.LONG_TERM,
            "task_trace": RetentionPolicy.MEDIUM_TERM,
            "session_data": RetentionPolicy.SHORT_TERM,
        }
        entry_type = entry.get("type") or entry.get("entry_type", "")
        return type_map.get(entry_type, RetentionPolicy.MEDIUM_TERM)

    def prune(self, entries: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        Returns (kept_entries, pruned_entries).
        Pruned entries are archived if config.archive_before_delete is True.
        """
        kept = []
        pruned = []
        current_time = datetime.now().timestamp()

        for entry in entries:
            policy = self.classify_retention(entry)
            
            # Permanent entries never pruned
            if policy == RetentionPolicy.PERMANENT:
                kept.append(entry)
                continue
            
            # Check TTL
            ttl_days = self.TTL_MAP.get(policy, self.config.default_ttl_days)
            created_str = entry.get("created_at") or entry.get("created", "")
            
            if created_str:
                try:
                    created = datetime.fromisoformat(created_str)
                    age = datetime.now() - created
                    if age > timedelta(days=ttl_days):
                        pruned.append(entry)
                        continue
                except (ValueError, TypeError) as exc:
                    logger.debug("Failed to parse entry timestamp for TTL check: %s", exc)
            
            # Check relevance score
            relevance = self.compute_relevance(entry, current_time)
            if relevance < self.config.min_relevance_score:
                pruned.append(entry)
                continue
            
            kept.append(entry)

        if self.config.archive_before_delete and pruned:
            self.archive(pruned)

        return kept, pruned

    def archive(self, entries: list[dict]) -> None:
        """Save pruned entries to archive directory."""
        archive_dir = Path(self.config.archive_path)
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = archive_dir / f"pruned_{timestamp}.json"
        
        archive_file.write_text(json.dumps(entries, indent=2))
