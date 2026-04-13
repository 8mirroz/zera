from __future__ import annotations

import time
from pathlib import Path
from typing import Iterable

from .contracts import RetrieverInput, RetrieverOutput


class Retriever:
    """Minimal local retrieval over workspace files."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = Path(repo_root)

    def query(self, retriever_input: RetrieverInput) -> RetrieverOutput:
        start = time.perf_counter()

        chunks: list[dict[str, str | int]] = []
        citations: list[str] = []
        needle = retriever_input.query.lower().strip()
        if not needle:
            return RetrieverOutput(chunks=[], citations=[], retrieval_ms=0)

        sources = retriever_input.sources or ["docs", "configs"]
        for source_name in sources:
            if len(chunks) >= retriever_input.max_chunks:
                break
            if str(source_name).strip() == "wiki_core":
                self._append_wiki_core_results(
                    needle,
                    max_chunks=retriever_input.max_chunks,
                    chunks=chunks,
                    citations=citations,
                )
                continue

            source = self.repo_root / str(source_name)
            if not source.exists():
                continue
            for path in self._iter_text_files(source):
                try:
                    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
                except Exception:
                    continue

                for idx, line in enumerate(lines, start=1):
                    if needle in line.lower():
                        rel = path.relative_to(self.repo_root)
                        citations.append(f"{rel}:{idx}")
                        chunks.append(
                            {
                                "source": str(rel),
                                "line": idx,
                                "content": line.strip(),
                            }
                        )
                        if len(chunks) >= retriever_input.max_chunks:
                            elapsed_ms = int((time.perf_counter() - start) * 1000)
                            return RetrieverOutput(chunks=chunks, citations=citations, retrieval_ms=elapsed_ms)

        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return RetrieverOutput(chunks=chunks, citations=citations, retrieval_ms=elapsed_ms)

    def _append_wiki_core_results(
        self,
        query: str,
        *,
        max_chunks: int,
        chunks: list[dict[str, str | int]],
        citations: list[str],
    ) -> None:
        try:
            from .wiki_core import WikiCore

            config_path = self.repo_root / "configs/tooling/wiki_core.yaml"
            if not config_path.exists():
                return
            result = WikiCore(self.repo_root, config_path=config_path).query(query, limit=max_chunks - len(chunks))
            for row in result.get("results", []):
                path = str(row.get("path") or "wiki-core")
                rel = path
                path_obj = Path(path)
                if path and path_obj.is_absolute():
                    try:
                        rel = str(path_obj.relative_to(self.repo_root))
                    except ValueError:
                        rel = path
                citations.append(f"{rel}:wiki")
                chunks.append(
                    {
                        "source": rel,
                        "line": 1,
                        "content": str(row.get("snippet") or row.get("title") or "")[:500],
                    }
                )
                if len(chunks) >= max_chunks:
                    break
        except Exception:
            return

    @staticmethod
    def _iter_text_files(root: Path) -> Iterable[Path]:
        skip = {".git", "node_modules", "__pycache__", ".pytest_cache", "test_venv", ".venv", ".next", "dist", "build"}
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in skip for part in path.parts):
                continue
            suffix = path.suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".pyc", ".zip", ".pkl", ".gz", ".tar", ".bin"}:
                continue
            yield path
