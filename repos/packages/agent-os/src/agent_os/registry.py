import json
import logging
import math
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Lazy-initialized trace emitter
_emitter: Any = None


def _get_emitter() -> Any:
    global _emitter
    if _emitter is None:
        from .trace_context import TraceSink, StructuredTraceEmitter
        _emitter = StructuredTraceEmitter(TraceSink(filename="agent_traces.jsonl"))
    return _emitter

class TfIdfScorer:
    """Lightweight TF-IDF search on pure Python."""
    
    def __init__(self, documents: List[Dict[str, Any]], fields: List[str]):
        self.documents = documents
        self.fields = fields
        self.vocab = {}
        self.idf = {}
        self.doc_term_freqs = []
        self._build_index()
        
    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r'\w+', text.lower())
        
    def _build_index(self):
        doc_counts = {}
        total_docs = len(self.documents)
        
        for doc in self.documents:
            term_freq = {}
            # Combine content from specified fields
            text = " ".join([str(doc.get(f, "")) for f in self.fields])
            tokens = self._tokenize(text)
            
            for token in tokens:
                term_freq[token] = term_freq.get(token, 0) + 1
            
            self.doc_term_freqs.append(term_freq)
            
            for token in term_freq:
                doc_counts[token] = doc_counts.get(token, 0) + 1
                
        for token, count in doc_counts.items():
            # Smoothed IDF to avoid zero for terms in only one doc when N is low
            self.idf[token] = math.log((total_docs + 1) / (count + 0.5)) + 1.0
            
    def score(self, query: str) -> List[float]:
        query_tokens = self._tokenize(query)
        scores = []
        
        for doc_tf in self.doc_term_freqs:
            score = 0.0
            for token in query_tokens:
                if token in doc_tf:
                    # TF * IDF
                    score += doc_tf[token] * self.idf.get(token, 0)
            scores.append(score)
        return scores

class AssetRegistry:
    """Registry logic for Antigravity Atlas v2 (Adaptive Semantic Engine)."""
    
    def __init__(self, catalog_path: Path, mastery_path: Optional[Path] = None):
        self.catalog_path = catalog_path
        self.mastery_path = mastery_path
        self.catalog = self.load_catalog()
        self.mastery = self.load_mastery()
        self._init_scorers()
        
    def load_catalog(self) -> Dict[str, Any]:
        if not self.catalog_path.exists():
            return {"skills": [], "rules": [], "workflows": [], "configs": []}
        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"skills": [], "rules": [], "workflows": [], "configs": []}
            
    def load_mastery(self) -> Dict[str, Any]:
        if self.mastery_path and self.mastery_path.exists():
            try:
                with open(self.mastery_path, "r") as f:
                    return json.load(f)
            except Exception as exc:
                logger.debug("Failed to load mastery file %s: %s", self.mastery_path, exc)
        return {}

    def _init_scorers(self):
        self.scorers = {}
        self._scorer_configs = {
            "skills": ["name", "description", "triggers"],
            "workflows": ["name", "description"],
            "rules": ["name"],
            "docs": ["name", "title", "description", "status", "path"]
        }

    def get_scorer(self, category: str):
        """Lazy initialization of scorers to save startup time and bulk registration overhead."""
        if category not in self.scorers and category in self._scorer_configs:
            assets = self.catalog.get(category, [])
            if assets:
                self.scorers[category] = TfIdfScorer(assets, self._scorer_configs[category])
        return self.scorers.get(category)

    def discover_assets(self, query: str, category: str = "skills", limit: int = 5) -> List[Dict[str, Any]]:
        """Adaptive semantic search combining TF-IDF and Mastery."""
        scorer = self.get_scorer(category)
        assets = self.catalog.get(category, [])
        if not scorer:
            # Fallback to simple matching if scorer not available/applicable
            return [i for i in assets if query.lower() in str(i).lower()][:limit]
            
        scores = scorer.score(query)
        
        results = []
        for i, asset in enumerate(assets):
            semantic_score = scores[i]
            if semantic_score <= 0: continue
            
            # Mastery Boost (30% weight)
            mastery_score = 0.0
            name = asset.get("name", "")
            if name in self.mastery:
                m = self.mastery[name]
                success = m.get("success", 0)
                total = success + m.get("failed", 0)
                if total > 0:
                    mastery_score = (success / total) * 10 # Scale to 0-10
            
            final_score = (semantic_score * 0.7) + (mastery_score * 0.3)
            
            results.append({
                **asset,
                "score": final_score,
                "semantic_score": semantic_score,
                "mastery_score": mastery_score
            })
            
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def generate_context_pack(self, task: str) -> Dict[str, Any]:
        """Synthesizes a full context pack (Rules + Skills + Workflow + Experience)."""
        skills = self.discover_assets(task, "skills", limit=2)
        doc_refs = self.discover_assets(task, "docs", limit=3)
        repo_root = self.catalog_path.parent.parent.parent

        # New: Experience Retrieval from Obsidian
        historical_wisdom = []
        try:
            import sys
            scripts_dir = str(repo_root / "scripts")
            if scripts_dir not in sys.path:
                sys.path.append(scripts_dir)
            import query_experience
            for skill in skills:
                name = skill.get("name")
                desc = skill.get("description", "")
                if name:
                    experiences = query_experience.get_experience(name, vault=str(repo_root), limit=3, context=desc)
                    historical_wisdom.extend(experiences)
        except Exception as exc:
            logger.debug("Failed to read experience history: %s", exc)

        wiki_core: Dict[str, Any] = {"status": "disabled", "backend": None, "results": []}
        try:
            config_path = repo_root / "configs/tooling/wiki_core.yaml"
            if config_path.exists():
                from agent_os.wiki_core import WikiCore

                query_result = WikiCore(repo_root, config_path=config_path).query(task, limit=3)
                wiki_core = {
                    "status": query_result.get("status", "ok"),
                    "backend": query_result.get("backend"),
                    "results": query_result.get("results", []),
                }
        except Exception as exc:
            wiki_core = {"status": "error", "backend": None, "results": [], "error": str(exc)}

        return {
            "primary_skills": skills,
            "relevant_rules": self.discover_assets(task, "rules", limit=3),
            "recommended_workflow": self.discover_assets(task, "workflows", limit=1),
            "doc_refs": doc_refs,
            "wiki_core": wiki_core,
            "historical_wisdom": historical_wisdom[:3],
            "generated_at": str(Path(__file__).stat().st_mtime)
        }

    # ------------------------------------------------------------------
    # Backward-compatible API used by existing tests and integrations.
    # ------------------------------------------------------------------
    def find_rule(self, query: str) -> List[Dict[str, Any]]:
        query_l = str(query or "").lower()
        return [r for r in self.catalog.get("rules", []) if query_l in str(r.get("name", "")).lower()]

    def find_workflow(self, query: str) -> List[Dict[str, Any]]:
        query_l = str(query or "").lower()
        return [
            w
            for w in self.catalog.get("workflows", [])
            if query_l in str(w.get("name", "")).lower() or query_l in str(w.get("description", "")).lower()
        ]

    def find_skill(self, query: str) -> List[Dict[str, Any]]:
        query_l = str(query or "").lower()
        results: List[Dict[str, Any]] = []
        for s in self.catalog.get("skills", []):
            if query_l in str(s.get("name", "")).lower():
                results.append(s)
                continue
            triggers = s.get("triggers", [])
            if isinstance(triggers, list) and any(query_l in str(t).lower() for t in triggers):
                results.append(s)
        return results

    def get_asset_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        emitter = _get_emitter()
        from .trace_context import TraceContext
        ctx = TraceContext.root(task_id=f"resolve_asset:{name}", tier="C1", component="asset_registry")
        t0 = time.perf_counter()
        emitter.task_start(ctx, asset_id=name)

        try:
            target = str(name or "").lower()
            result = None
            for category in self.catalog.values():
                if not isinstance(category, list):
                    continue
                for asset in category:
                    if isinstance(asset, dict) and str(asset.get("name", "")).lower() == target:
                        result = asset
                        break
                if result is not None:
                    break

            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                             asset_id=name, resolved=result is not None)
            return result
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_error(ctx, error_type=type(exc).__name__, error_message=str(exc))
            raise

    def register_asset(self, category: str, asset: Dict[str, Any]) -> None:
        emitter = _get_emitter()
        from .trace_context import TraceContext
        asset_id = str(asset.get("name", "unknown"))
        ctx = TraceContext.root(task_id=f"register_asset:{asset_id}", tier="C1", component="asset_registry")
        t0 = time.perf_counter()
        emitter.task_start(ctx, asset_id=asset_id, asset_type=category)

        try:
            key = str(category or "").strip()
            if key not in self.catalog or not isinstance(self.catalog.get(key), list):
                self.catalog[key] = []
            self.catalog[key].append(dict(asset))
            # Invalidate existing scorer to force re-init on next use
            if key in self.scorers:
                del self.scorers[key]

            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_end(ctx, duration_ms=duration_ms, status="completed",
                             asset_id=asset_id, asset_type=category)
        except Exception as exc:
            duration_ms = (time.perf_counter() - t0) * 1000
            emitter.task_error(ctx, error_type=type(exc).__name__, error_message=str(exc))
            raise

    def list_by_category(self, category: str) -> List[Dict[str, Any]]:
        key = str(category or "").strip()
        values = self.catalog.get(key, [])
        return list(values) if isinstance(values, list) else []

    def save_catalog(self) -> None:
        self.catalog_path.parent.mkdir(parents=True, exist_ok=True)
        with self.catalog_path.open("w", encoding="utf-8") as f:
            json.dump(self.catalog, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    import sys
    # For standalone testing
    repo_root = Path.cwd()
    reg = AssetRegistry(
        repo_root / "configs/orchestrator/catalog.json",
        repo_root / "repos/packages/agent-os/scripts/mastery.json"
    )
    
    if len(sys.argv) > 1:
        task = " ".join(sys.argv[1:])
        pack = reg.generate_context_pack(task)
        print(json.dumps(pack, indent=2, ensure_ascii=False))
    else:
        print(f"Registry v2 loaded with {sum(len(v) for v in reg.catalog.values() if isinstance(v, list))} assets.")
