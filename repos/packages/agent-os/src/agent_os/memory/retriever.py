from __future__ import annotations

"""BM25 keyword-based retrieval for agent memory."""

import json
import pickle
from pathlib import Path
from typing import Optional

try:
    from rank_bm25 import BM25Okapi, BM25Plus
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False


class BM25Retriever:
    """BM25 keyword-based retrieval for agent memory."""

    def __init__(self, index_path: Path):
        self.index_path = index_path
        self.corpus: list[dict] = []
        self.bm25: Optional[BM25Okapi] = None
        self.tokenized_corpus: list[list[str]] = []

    def _tokenize(self, text: str) -> list[str]:
        """Simple tokenization: lowercase and split on whitespace."""
        return text.lower().split()

    def build_index(self, entries: list[dict], text_fields: Optional[list[str]] = None) -> None:
        """
        Build BM25 index from memory entries.
        text_fields: which fields to index (default: ["content", "observations"])
        """
        if not BM25_AVAILABLE:
            raise ImportError("rank-bm25 not installed. Run: pip install rank-bm25")
        
        if text_fields is None:
            text_fields = ["content", "observations"]
        
        self.corpus = entries
        self.tokenized_corpus = []
        
        for entry in entries:
            text_parts = []
            for field in text_fields:
                value = entry.get(field, "")
                if value:
                    text_parts.append(str(value))
            combined_text = " ".join(text_parts)
            self.tokenized_corpus.append(self._tokenize(combined_text))
        
        # BM25Plus avoids zero-IDF problem in small corpora (N<=2)
        self.bm25 = BM25Plus(self.tokenized_corpus)
        self.warm_up()

    def retrieve(self, query: str, top_k: int = 5, min_score: float = 0.6) -> list[dict]:
        """
        Retrieve top-k entries matching query.
        Returns entries with added '_score' field.
        """
        if not self.bm25:
            return []

        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)

        max_score = float(scores.max())
        normalized_scores = scores / max_score if max_score > 0 else scores

        results = [
            {**self.corpus[idx], "_score": float(score)}
            for idx, score in enumerate(normalized_scores)
            if score >= min_score
        ]
        results.sort(key=lambda x: x["_score"], reverse=True)
        return results[:top_k]

    def warm_up(self) -> None:
        """Pre-warm BM25 scoring to avoid first-call latency spike."""
        if self.bm25 and self.tokenized_corpus:
            self.bm25.get_scores(["warm"])



    def retrieve_by_key(self, key: str) -> dict | None:
        """Direct key-based lookup by entry 'key' field."""
        for entry in self.corpus:
            if entry.get("key") == key:
                return entry
        return None

    def retrieve_by_topic(self, topic: str, top_k: int = 10) -> list[dict]:
        """Retrieve entries related to a specific topic."""
        return self.retrieve(topic, top_k=top_k, min_score=0.6)

    def save_index(self) -> None:
        """Persist BM25 index to disk for faster reload."""
        self.index_path.mkdir(parents=True, exist_ok=True)
        
        index_file = self.index_path / "bm25_index.pkl"
        corpus_file = self.index_path / "corpus.json"
        
        with open(index_file, "wb") as f:
            pickle.dump({
                "bm25": self.bm25,
                "tokenized_corpus": self.tokenized_corpus
            }, f)
        
        corpus_file.write_text(json.dumps(self.corpus, indent=2))

    def load_index(self) -> bool:
        """Load persisted index. Returns True if loaded, False if needs rebuild."""
        index_file = self.index_path / "bm25_index.pkl"
        corpus_file = self.index_path / "corpus.json"
        
        if not index_file.exists() or not corpus_file.exists():
            return False
        
        try:
            with open(index_file, "rb") as f:
                data = pickle.load(f)
                self.bm25 = data["bm25"]
                self.tokenized_corpus = data["tokenized_corpus"]
            
            self.corpus = json.loads(corpus_file.read_text())
            return True
        except (pickle.PickleError, json.JSONDecodeError, KeyError):
            return False
