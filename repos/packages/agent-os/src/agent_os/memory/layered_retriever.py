from __future__ import annotations

"""LayeredMemoryRetriever — unified retrieval across all memory layers.

Implements the 4-layer model from configs/global/memory_policy.yaml:
  retrieval_priority: [session, project, workspace, user_preferences]

Each layer is searched with BM25. Results are merged and re-ranked by:
  layer_priority_score * bm25_score
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .retriever import BM25Retriever
from ..yaml_compat import parse_simple_yaml


# Layer priority weights (higher = more authoritative)
_LAYER_WEIGHTS: dict[str, float] = {
    "session": 1.0,
    "project": 0.85,
    "workspace": 0.70,
    "user_preferences": 0.60,
}

_DEFAULT_LAYER_PATHS: dict[str, str] = {
    "session": ".agents/memory/session/",
    "project": ".agents/memory/projects/",
    "workspace": ".agents/memory/build-library/global/",
    "user_preferences": ".agents/memory/build-library/global/",
}


@dataclass
class LayeredResult:
    content: str
    source_layer: str
    source_file: str
    bm25_score: float
    final_score: float
    metadata: dict[str, Any]


class LayeredMemoryRetriever:
    """Search all memory layers and return merged, re-ranked results."""

    _POLICY_PATH = "configs/global/memory_policy.yaml"

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)
        self._layer_paths = self._load_layer_paths()

    def _load_layer_paths(self) -> dict[str, Path]:
        policy_path = self.repo_root / self._POLICY_PATH
        paths: dict[str, Path] = {}
        if policy_path.exists():
            data = parse_simple_yaml(policy_path.read_text(encoding="utf-8")) or {}
            layers = data.get("memory_layers", {}) or {}
            for layer_name, cfg in layers.items():
                if isinstance(cfg, dict) and cfg.get("path"):
                    paths[layer_name] = self.repo_root / str(cfg["path"])
        # Fill missing layers with defaults
        for layer, default in _DEFAULT_LAYER_PATHS.items():
            if layer not in paths:
                paths[layer] = self.repo_root / default
        return paths

    def _load_jsonl(self, path: Path) -> list[dict[str, Any]]:
        """Load all .jsonl files under a directory path."""
        entries: list[dict[str, Any]] = []
        if not path.exists():
            return entries
        targets = list(path.glob("**/*.jsonl")) + list(path.glob("**/*.json"))
        for f in targets:
            try:
                text = f.read_text(encoding="utf-8")
                # Try JSONL first
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        if isinstance(obj, dict):
                            obj.setdefault("_source_file", str(f))
                            entries.append(obj)
                    except Exception:
                        continue
            except Exception:
                continue
        return entries

    def _search_layer(
        self, layer: str, query: str, top_k: int, min_score: float
    ) -> list[LayeredResult]:
        layer_path = self._layer_paths.get(layer)
        if not layer_path:
            return []

        entries = self._load_jsonl(layer_path)
        if not entries:
            return []

        retriever = BM25Retriever(layer_path / ".index")
        try:
            retriever.build_index(entries, text_fields=["content", "observations", "value", "text"])
        except ImportError:
            # rank-bm25 not installed — fall back to substring match
            return self._fallback_search(layer, entries, query, top_k, min_score)

        raw = retriever.retrieve(query, top_k=top_k, min_score=min_score)
        weight = _LAYER_WEIGHTS.get(layer, 0.5)
        results: list[LayeredResult] = []
        for item in raw:
            bm25_score = float(item.get("_score", 0.0))
            content = str(item.get("content") or item.get("value") or item.get("text") or json.dumps(item))
            results.append(LayeredResult(
                content=content,
                source_layer=layer,
                source_file=str(item.get("_source_file", "")),
                bm25_score=bm25_score,
                final_score=round(bm25_score * weight, 4),
                metadata={k: v for k, v in item.items() if not k.startswith("_") and k != "content"},
            ))
        return results

    @staticmethod
    def _fallback_search(
        layer: str, entries: list[dict], query: str, top_k: int, min_score: float
    ) -> list[LayeredResult]:
        """Simple substring fallback when rank-bm25 is unavailable."""
        query_lower = query.lower()
        weight = _LAYER_WEIGHTS.get(layer, 0.5)
        results: list[LayeredResult] = []
        for item in entries:
            content = str(item.get("content") or item.get("value") or item.get("text") or "")
            if query_lower in content.lower():
                score = 0.7 * weight
                results.append(LayeredResult(
                    content=content,
                    source_layer=layer,
                    source_file=str(item.get("_source_file", "")),
                    bm25_score=0.7,
                    final_score=round(score, 4),
                    metadata={},
                ))
        results.sort(key=lambda r: r.final_score, reverse=True)
        return results[:top_k]

    def retrieve(
        self,
        query: str,
        top_k: int = 10,
        min_score: float = 0.3,
        layers: list[str] | None = None,
    ) -> list[LayeredResult]:
        """Search all (or specified) layers, merge and re-rank results.

        Args:
            query: search query string
            top_k: max results to return across all layers
            min_score: minimum BM25 score threshold per layer
            layers: restrict to specific layers; None = all layers in priority order

        Returns:
            Merged list sorted by final_score descending.
        """
        search_layers = layers or list(_LAYER_WEIGHTS.keys())
        all_results: list[LayeredResult] = []

        for layer in search_layers:
            layer_results = self._search_layer(layer, query, top_k=top_k, min_score=min_score)
            all_results.extend(layer_results)

        # Deduplicate by content hash, keeping highest final_score
        seen: dict[str, LayeredResult] = {}
        for r in all_results:
            key = r.content[:120]  # content prefix as dedup key
            if key not in seen or r.final_score > seen[key].final_score:
                seen[key] = r

        merged = sorted(seen.values(), key=lambda r: r.final_score, reverse=True)
        return merged[:top_k]

    def retrieve_from_layer(self, layer: str, query: str, top_k: int = 5) -> list[LayeredResult]:
        """Convenience: search a single layer."""
        return self._search_layer(layer, query, top_k=top_k, min_score=0.3)
