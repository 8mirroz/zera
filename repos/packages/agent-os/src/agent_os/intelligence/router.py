import logging
import os
import re
import yaml
import json
import urllib.request
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class VectorEngine:
    def __init__(self, model: str = "all-minilm", host: str = "http://localhost:11434"):
        self.model = model
        self.host = host
        self.cache_path = ".agents/memory/router_embeddings.json"
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r") as f:
                    return json.load(f)
            except Exception as exc:
                logger.debug("Failed to load embedding cache: %s", exc)
        return {}

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w") as f:
                json.dump(self._cache, f)
        except Exception as exc:
            logger.debug("Failed to save embedding cache: %s", exc)

    def get_embedding(self, text: str) -> Optional[List[float]]:
        if text in self._cache:
            return self._cache[text]
        try:
            data = json.dumps({"model": self.model, "prompt": text}).encode()
            req = urllib.request.Request(f"{self.host}/api/embeddings", data=data)
            with urllib.request.urlopen(req, timeout=2) as res:
                embedding = json.loads(res.read().decode())["embedding"]
                self._cache[text] = embedding
                self._save_cache()
                return embedding
        except Exception as exc:
            logger.debug("Embedding request failed for model=%s: %s", self.model, exc)
        return None

    @staticmethod
    def similarity(v1: List[float], v2: List[float]) -> float:
        if not v1 or not v2:
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(a * a for a in v2) ** 0.5
        return dot / (norm1 * norm2) if norm1 * norm2 > 0 else 0.0


class SemanticRouter:
    def __init__(self, registry_path: str = "configs/registry/agents"):
        self.registry_path = registry_path
        self.WEIGHT_VECTOR = 0.7
        self.WEIGHT_KEYWORD = 0.3
        self.vector_engine = VectorEngine()

    def _get_agents(self) -> List[Dict]:
        agents = []
        for root, _, files in os.walk(self.registry_path):
            for f in files:
                if not f.endswith(".md"):
                    continue
                path = os.path.join(root, f)
                try:
                    with open(path, "r", encoding="utf-8") as file:
                        content = file.read()
                    yaml_match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                    if yaml_match:
                        data = yaml.safe_load(yaml_match.group(1))
                        if isinstance(data, dict):
                            agents.append({
                                "id": data.get("id") or f.replace(".md", ""),
                                "desc": data.get("description", ""),
                                "skills": data.get("skills", []),
                                "path": path,
                            })
                except Exception as exc:
                    logger.debug("Failed to parse agent file %s: %s", path, exc)
        return agents

    def route(self, query: str) -> Optional[Dict]:
        agents = self._get_agents()
        query_vec = self.vector_engine.get_embedding(query)

        best_match = None
        max_score = -1.0

        for agent in agents:
            kw_score = 0.0
            query_lower = query.lower()
            for skill in agent["skills"]:
                if skill.lower() in query_lower:
                    kw_score += 1.0
            kw_score = min(kw_score / 2.0, 1.0)

            agent_text = f"{agent['id']} {agent['desc']} {' '.join(agent['skills'])}"
            agent_vec = self.vector_engine.get_embedding(agent_text)
            vec_score = (
                self.vector_engine.similarity(query_vec, agent_vec)
                if query_vec and agent_vec
                else 0.0
            )

            if query_vec:
                total_score = (self.WEIGHT_VECTOR * vec_score) + (self.WEIGHT_KEYWORD * kw_score)
            else:
                total_score = kw_score

            # Domain safeguards
            if "frontend" in query_lower and "backend" in agent["id"].lower():
                total_score -= 0.5
            if "backend" in query_lower and "frontend" in agent["id"].lower():
                total_score -= 0.5

            if total_score > max_score:
                max_score = total_score
                best_match = agent

        if best_match and max_score > 0.1:
            return {
                "agent_id": best_match["id"],
                "score": round(max_score, 4),
                "method": "hybrid" if query_vec else "keyword",
            }
        return None
