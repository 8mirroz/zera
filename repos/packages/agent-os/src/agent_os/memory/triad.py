from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

@dataclass
class MemoryRecord:
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    importance: float = 1.0
    layer: str = "episodic"

class MemoryTriad:
    """
    Implementation of the 3-layer memory architecture:
    1. Episodic: Temporal/contextual events.
    2. Semantic: Facts and domain knowledge.
    3. Procedural: Policies and action patterns.
    """

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.layers_config = config.get("memory_layers", {})
        self.weights = config.get("retrieval_weights", {"episodic": 0.4, "semantic": 0.4, "procedural": 0.2})
        
        # In a real implementation, these would connect to VectorDB, Neo4j, etc.
        # For now, we implement the logic for scoring and retrieval.
        logger.info("MemoryTriad initialized with layers: %s", list(self.layers_config.keys()))

    def score_record(self, record: MemoryRecord, query_similarity: float) -> float:
        """
        Calculate importance score based on:
        Score = Similarity * (Decay ^ TimeDelta) * Importance
        """
        layer_cfg = self.layers_config.get(record.layer, {})
        decay_rate = layer_cfg.get("recency_decay", 0.995)
        
        # Calculate time decay (simple version: days since creation)
        delta = datetime.now(timezone.utc) - record.timestamp
        days_passed = delta.total_seconds() / 86400.0
        
        time_factor = pow(decay_rate, days_passed)
        
        return query_similarity * time_factor * record.importance

    def retrieve(self, query: str, top_k: int = 5) -> List[MemoryRecord]:
        """
        Performs hybrid retrieval across all layers.
        """
        results = []
        # Logic for searching across layers would go here.
        # This is a stub for the architectural pattern.
        logger.debug("Retrieving memory for query: %s", query)
        return results

    def memorize(self, content: str, layer: str = "episodic", importance: float = 1.0, metadata: Optional[Dict] = None):
        """
        Saves a record to the specified layer.
        """
        record = MemoryRecord(
            content=content,
            layer=layer,
            importance=importance,
            metadata=metadata or {}
        )
        # Logic for persisting to backends (Chroma, etc.)
        logger.info("Memorized record in layer %s: %s...", layer, content[:50])
        return record

# Helper function to load from yaml
def load_triad_from_config(config_path: str) -> MemoryTriad:
    import yaml
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return MemoryTriad(config)
