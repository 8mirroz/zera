import yaml
import json
from pathlib import Path
from typing import List, Dict, Optional

class RetrievedResult:
    def __init__(self, content: str, source: str, confidence: float, metadata: dict = None):
        self.content = content
        self.source = source
        self.confidence = confidence
        self.metadata = metadata or {}

class MemoryRetriever:
    def __init__(self, config_path: str = None):
        if config_path is None:
            # Assume standard location in Zera workspace
            config_path = str(Path(__file__).parent.parent.parent / "memory" / "vault_config.yaml")
            
        with open(config_path, 'r') as f:
            self.cfg = yaml.safe_load(f)
        
        self.retrieval_cfg = self.cfg.get('retrieval', {})
        self.hybrid_cfg = self.retrieval_cfg.get('hybrid_search', {})

    def retrieve(self, query: str, top_k: int = None, filters: Dict = None) -> List[RetrievedResult]:
        top_k = top_k or self.retrieval_cfg.get('default_top_k', 8)
        top_k = min(top_k, self.retrieval_cfg.get('max_top_k', 24))
        
        # Mock retrieval
        results = [
            RetrievedResult("Content from Zera memory", "docs/zera_guide.md", 0.95, {"project_id": "zera_core"}),
            RetrievedResult("Hermes coordination notes", "vault/coordination.md", 0.88, {"project_id": "hermes"})
        ]
        
        if filters:
            results = [r for r in results if all(r.metadata.get(k) == v for k, v in filters.items())]
            
        return results

def search_memory(query: str, project_id: str = None, top_k: int = 8):
    retriever = MemoryRetriever()
    filters = {"project_id": project_id} if project_id else None
    return retriever.retrieve(query, top_k=top_k, filters=filters)
