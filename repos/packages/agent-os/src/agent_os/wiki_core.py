from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from agent_os.yaml_compat import parse_simple_yaml


@dataclass(frozen=True)
class WikiCorePaths:
    root: Path
    raw: Path
    wiki: Path
    manifests: Path
    skills: Path
    local_skill_target: Path
    search: Path


class WikiCore:
    """Karpathy-style raw -> wiki -> search -> skills -> writeback service."""

    def __init__(
        self,
        repo_root: Path,
        config_path: Path | str | None = None,
        *,
        qmd_which: Callable[[str], str | None] | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.config_path = self._resolve_path(config_path or "configs/tooling/wiki_core.yaml")
        self.config = self._load_config(self.config_path)
        self.paths = self._load_paths(self.config)
        self._qmd_which = qmd_which or shutil.which
        self._runner = runner or subprocess.run

    def doctor(self) -> dict[str, Any]:
        required = {
            "root": self.paths.root,
            "raw": self.paths.raw,
            "wiki": self.paths.wiki,
            "manifests": self.paths.manifests,
            "skills": self.paths.skills,
        }
        path_checks = {name: {"path": str(path), "exists": path.exists()} for name, path in required.items()}
        qmd_available = self.qmd_available()
        missing_required = [name for name, row in path_checks.items() if not row["exists"]]
        active_backend = "qmd" if qmd_available else str(self._search_config().get("fallback_backend") or "tfidf")
        return {
            "status": "ok" if qmd_available and not missing_required else "warn",
            "config_path": str(self.config_path),
            "paths": path_checks,
            "search": {
                "primary_backend": self._search_config().get("primary_backend", "qmd"),
                "fallback_backend": self._search_config().get("fallback_backend", "tfidf"),
                "active_backend": active_backend,
                "qmd_available": qmd_available,
                "qmd_command": self.qmd_command(),
            },
            "missing_required_paths": missing_required,
        }

    def qmd_command(self) -> list[str]:
        qmd = self._qmd_config()
        raw_command = qmd.get("command", "qmd")
        if isinstance(raw_command, list):
            return [str(part) for part in raw_command if str(part).strip()]
        return [part for part in str(raw_command).split() if part]

    def qmd_available(self) -> bool:
        command = self.qmd_command()
        return bool(command and self._qmd_which(command[0]))

    def ingest_source(self, source: Path | str, *, dry_run: bool = False) -> dict[str, Any]:
        source_path = self._resolve_path(source)
        if not source_path.exists():
            raise FileNotFoundError(str(source_path))
        if not source_path.is_file():
            raise ValueError(f"source must be a file: {source_path}")
        if not self._is_relative_to(source_path, self.paths.raw):
            raise ValueError(f"source must be under immutable raw root: {self.paths.raw}")

        source_hash = self._sha256(source_path)
        manifest_path = self.paths.manifests / "sources.csv"
        existing = self._read_manifest(manifest_path)
        duplicate = next((row for row in existing if row.get("sha256") == source_hash), None)
        if duplicate:
            return {
                "status": "duplicate",
                "source_path": str(source_path),
                "sha256": source_hash,
                "wiki_path": str(self._resolve_path(duplicate.get("wiki_path") or "")),
            }

        title = self._title_from_markdown(source_path.read_text(encoding="utf-8", errors="replace")) or source_path.stem
        wiki_path = self.paths.wiki / "_briefs" / f"{self._slugify(source_path.stem)}.md"
        result = {
            "status": "dry_run" if dry_run else "ok",
            "source_path": str(source_path),
            "sha256": source_hash,
            "wiki_path": str(wiki_path),
            "title": title,
        }
        if dry_run:
            return result

        self._ensure_structure()
        wiki_path.parent.mkdir(parents=True, exist_ok=True)
        wiki_path.write_text(self._render_ingest_page(source_path, title, source_hash), encoding="utf-8")
        self._append_manifest(
            manifest_path,
            {
                "source_path": str(source_path.relative_to(self.repo_root)) if self._is_relative_to(source_path, self.repo_root) else str(source_path),
                "sha256": source_hash,
                "ingested_at": self._now(),
                "wiki_path": str(wiki_path.relative_to(self.repo_root)) if self._is_relative_to(wiki_path, self.repo_root) else str(wiki_path),
                "title": title,
            },
        )
        self._append_log(f"- {self._now()} ingested `{source_path}` -> `{wiki_path}` sha256={source_hash}\n")
        return result

    def writeback_answer(
        self,
        title: str,
        body: str,
        *,
        page_type: str = "brief",
        target: str | Path | None = None,
        tags: Iterable[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        normalized_type = str(page_type or "brief").strip().lower()
        allowed = self._allowed_page_types()
        if normalized_type not in allowed:
            raise ValueError(f"unsupported wiki page_type {normalized_type!r}; allowed={sorted(allowed)}")
        target_path = self._writeback_target(title, normalized_type, target)
        payload = self._render_writeback_page(title, body, normalized_type, tags or [])
        result = {"status": "dry_run" if dry_run else "ok", "path": str(target_path), "page_type": normalized_type}
        if dry_run:
            return result
        self._ensure_structure()
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(payload, encoding="utf-8")
        self._append_log(f"- {self._now()} writeback `{normalized_type}` -> `{target_path}`\n")
        return result

    def query(self, query: str, *, limit: int = 5) -> dict[str, Any]:
        if self.qmd_available():
            qmd_result = self._query_qmd(query, limit=limit)
            if qmd_result.get("status") == "ok":
                return qmd_result
        return self._query_local(query, limit=limit)

    def reindex(self, *, dry_run: bool = False) -> dict[str, Any]:
        command = self.qmd_command()
        if dry_run:
            return {
                "status": "dry_run",
                "backend": "qmd" if self.qmd_available() else self._search_config().get("fallback_backend", "tfidf"),
                "qmd_available": self.qmd_available(),
                "command": command,
                "wiki_path": str(self.paths.wiki),
            }
        if not self.qmd_available():
            return {"status": "skipped", "backend": "tfidf", "reason": "qmd_unavailable", "wiki_path": str(self.paths.wiki)}
        args = self._format_args(self._qmd_config().get("reindex_args", ["index", "{wiki_path}"]), query="", limit=0)
        completed = self._runner(command + args, capture_output=True, text=True, check=False, cwd=str(self.repo_root))
        return {
            "status": "ok" if completed.returncode == 0 else "error",
            "backend": "qmd",
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }

    def lint(self, *, dry_run: bool = False) -> dict[str, Any]:
        issues: list[dict[str, Any]] = []
        if not self.paths.raw.exists():
            issues.append({"severity": "warn", "code": "raw_missing", "path": str(self.paths.raw)})
        if not self.paths.wiki.exists():
            issues.append({"severity": "warn", "code": "wiki_missing", "path": str(self.paths.wiki)})
        if self.paths.wiki.exists():
            for page in sorted(self.paths.wiki.rglob("*.md")):
                text = page.read_text(encoding="utf-8", errors="replace")
                if text.startswith("---"):
                    continue
                if page.name.startswith("_"):
                    continue
                issues.append({"severity": "warn", "code": "missing_frontmatter", "path": str(page)})
        return {"status": "ok" if not issues else "warn", "dry_run": dry_run, "issues": issues}

    def publish_skills(self, *, mode: str = "copy", global_target: Path | str | None = None) -> dict[str, Any]:
        targets = [self.paths.local_skill_target]
        if global_target:
            targets.append(self._resolve_path(global_target))
        published: list[dict[str, Any]] = []
        if not self.paths.skills.exists():
            return {"status": "warn", "published": published, "reason": "skills_source_missing", "skills_path": str(self.paths.skills)}
        for skill_dir in sorted(p for p in self.paths.skills.iterdir() if p.is_dir() and (p / "SKILL.md").exists()):
            name = f"wiki-{skill_dir.name}"
            for target_root in targets:
                target_dir = target_root / name
                target_root.mkdir(parents=True, exist_ok=True)
                if mode == "symlink":
                    if not target_dir.exists():
                        target_dir.symlink_to(skill_dir, target_is_directory=True)
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    for item in skill_dir.iterdir():
                        if item.is_file():
                            shutil.copy2(item, target_dir / item.name)
                published.append({"name": name, "source": str(skill_dir), "target": str(target_dir), "mode": mode})
        return {"status": "ok", "published": published}

    def _query_qmd(self, query: str, *, limit: int) -> dict[str, Any]:
        command = self.qmd_command()
        args = self._format_args(self._qmd_config().get("query_args", ["search", "{query}", "--limit", "{limit}", "--format", "json"]), query=query, limit=limit)
        completed = self._runner(command + args, capture_output=True, text=True, check=False, cwd=str(self.repo_root))
        if completed.returncode != 0:
            return {"status": "error", "backend": "qmd", "error": completed.stderr[-1000:]}
        results = self._parse_qmd_results(completed.stdout, limit=limit)
        return {"status": "ok", "backend": "qmd", "results": results, "raw_stdout": completed.stdout[:4000]}

    def _query_local(self, query: str, *, limit: int) -> dict[str, Any]:
        docs: list[dict[str, Any]] = []
        for base in [self.paths.wiki]:
            if not base.exists():
                continue
            for page in sorted(base.rglob("*.md")):
                text = page.read_text(encoding="utf-8", errors="replace")
                score = self._score(query, text)
                if score <= 0:
                    continue
                docs.append(
                    {
                        "path": str(page),
                        "title": self._title_from_markdown(text) or page.stem,
                        "score": score,
                        "snippet": self._snippet(text),
                    }
                )
        docs.sort(key=lambda row: row["score"], reverse=True)
        return {"status": "ok", "backend": str(self._search_config().get("fallback_backend") or "tfidf"), "results": docs[:limit]}

    def _load_config(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(str(path))
        text = path.read_text(encoding="utf-8")
        try:
            import yaml  # type: ignore

            data = yaml.safe_load(text) or {}
        except Exception:
            data = parse_simple_yaml(text)
        if not isinstance(data, dict):
            raise ValueError(f"wiki-core config must be a mapping: {path}")
        return data

    def _load_paths(self, config: dict[str, Any]) -> WikiCorePaths:
        paths = config.get("paths") if isinstance(config.get("paths"), dict) else {}
        root = self._resolve_path(paths.get("root", "repos/data/knowledge/wiki-core"))
        return WikiCorePaths(
            root=root,
            raw=self._resolve_path(paths.get("raw", root / "raw")),
            wiki=self._resolve_path(paths.get("wiki", root / "wiki")),
            manifests=self._resolve_path(paths.get("manifests", root / "manifests")),
            skills=self._resolve_path(paths.get("skills", root / ".skills")),
            local_skill_target=self._resolve_path(paths.get("local_skill_target", ".agents/skills")),
            search=self._resolve_path(paths.get("search", root / "search/qmd")),
        )

    def _resolve_path(self, path: Path | str) -> Path:
        p = Path(path)
        return p.resolve() if p.is_absolute() else (self.repo_root / p).resolve()

    def _ensure_structure(self) -> None:
        for path in [self.paths.root, self.paths.raw, self.paths.wiki, self.paths.manifests, self.paths.skills, self.paths.search]:
            path.mkdir(parents=True, exist_ok=True)
        for subdir in ["_briefs", "_entities", "_concepts", "_projects", "_comparisons", "_logs"]:
            (self.paths.wiki / subdir).mkdir(parents=True, exist_ok=True)

    def _writeback_target(self, title: str, page_type: str, target: str | Path | None) -> Path:
        if target:
            target_path = self._resolve_wiki_relative_target(target)
            if target_path.suffix.lower() != ".md":
                target_path = target_path / f"{self._slugify(title)}.md"
        else:
            default_target = str((self.config.get("writeback") or {}).get("default_target") or "wiki/_briefs")
            target_root = self._resolve_wiki_relative_target(default_target)
            target_path = target_root / f"{self._slugify(title)}.md"
        if self._is_relative_to(target_path, self.paths.raw):
            raise ValueError(f"writeback target cannot be under raw/: {target_path}")
        if not self._is_relative_to(target_path, self.paths.wiki):
            raise ValueError(f"writeback target must be under wiki/: {self.paths.wiki}")
        return target_path

    def _resolve_wiki_relative_target(self, target: str | Path) -> Path:
        raw = Path(target)
        if raw.is_absolute():
            return raw.resolve()
        text = str(target)
        if text == "raw" or text.startswith("raw/"):
            return (self.paths.root / text).resolve()
        if text == "wiki" or text.startswith("wiki/"):
            return (self.paths.root / text).resolve()
        return (self.paths.wiki / raw).resolve()

    def _allowed_page_types(self) -> set[str]:
        wb = self.config.get("writeback") if isinstance(self.config.get("writeback"), dict) else {}
        raw = wb.get("allowed_page_types", ["brief", "entity", "concept", "project", "comparison", "decision", "log"])
        if isinstance(raw, str):
            if raw.startswith("[") and raw.endswith("]"):
                raw = [part.strip().strip("'\"") for part in raw[1:-1].split(",") if part.strip()]
            else:
                raw = [part.strip() for part in raw.split(",") if part.strip()]
        return {str(item).strip().lower() for item in raw if str(item).strip()}

    def _search_config(self) -> dict[str, Any]:
        return self.config.get("search") if isinstance(self.config.get("search"), dict) else {}

    def _qmd_config(self) -> dict[str, Any]:
        search = self._search_config()
        return search.get("qmd") if isinstance(search.get("qmd"), dict) else {}

    def _format_args(self, args: Any, *, query: str, limit: int) -> list[str]:
        if isinstance(args, str):
            args = args.split()
        formatted = []
        for arg in list(args or []):
            formatted.append(str(arg).format(query=query, limit=limit, wiki_path=str(self.paths.wiki), search_path=str(self.paths.search)))
        return formatted

    def _parse_qmd_results(self, stdout: str, *, limit: int) -> list[dict[str, Any]]:
        text = stdout.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                values = parsed.get("results", [])
            else:
                values = parsed
            if isinstance(values, list):
                return [self._normalize_result(row) for row in values[:limit] if isinstance(row, dict)]
        except Exception:
            pass
        results = []
        for idx, line in enumerate(text.splitlines()[:limit]):
            results.append({"title": line[:120], "path": "", "score": max(0, limit - idx), "snippet": line})
        return results

    def _normalize_result(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": str(row.get("title") or row.get("name") or row.get("path") or "result"),
            "path": str(row.get("path") or row.get("file") or ""),
            "score": float(row.get("score") or row.get("rank") or 0),
            "snippet": str(row.get("snippet") or row.get("text") or row.get("content") or "")[:500],
        }

    def _render_ingest_page(self, source_path: Path, title: str, source_hash: str) -> str:
        text = source_path.read_text(encoding="utf-8", errors="replace")
        rel_source = str(source_path.relative_to(self.repo_root)) if self._is_relative_to(source_path, self.repo_root) else str(source_path)
        return (
            "---\n"
            f"title: {self._yaml_scalar(title)}\n"
            "page_type: brief\n"
            f"source_path: {self._yaml_scalar(rel_source)}\n"
            f"source_sha256: {source_hash}\n"
            f"created_at: {self._now()}\n"
            "source: wiki-core-ingest\n"
            "---\n\n"
            f"# {title}\n\n"
            "## Summary\n"
            f"{self._snippet(text, limit=1200)}\n\n"
            "## Provenance\n"
            f"- Raw source: `{rel_source}`\n"
            f"- SHA256: `{source_hash}`\n"
        )

    def _render_writeback_page(self, title: str, body: str, page_type: str, tags: Iterable[str]) -> str:
        tag_values = [str(tag).strip() for tag in tags if str(tag).strip()]
        tag_line = "[" + ", ".join(tag_values) + "]"
        return (
            "---\n"
            f"title: {self._yaml_scalar(title)}\n"
            f"page_type: {page_type}\n"
            f"created_at: {self._now()}\n"
            "source: wiki-core-writeback\n"
            f"tags: {tag_line}\n"
            "---\n\n"
            f"# {title}\n\n"
            f"{body.rstrip()}\n"
        )

    def _read_manifest(self, path: Path) -> list[dict[str, str]]:
        if not path.exists():
            return []
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    def _append_manifest(self, path: Path, row: dict[str, str]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        exists = path.exists()
        fields = ["source_path", "sha256", "ingested_at", "wiki_path", "title"]
        with path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            if not exists:
                writer.writeheader()
            writer.writerow({key: row.get(key, "") for key in fields})

    def _append_log(self, text: str) -> None:
        self.paths.manifests.mkdir(parents=True, exist_ok=True)
        log_path = self.paths.manifests / "ingest-log.md"
        if not log_path.exists():
            log_path.write_text("# Wiki-Core Ingest Log\n\n", encoding="utf-8")
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(text)

    def _score(self, query: str, text: str) -> float:
        haystack = set(re.findall(r"\w+", text.lower()))
        tokens = re.findall(r"\w+", query.lower())
        return float(sum(1 for token in tokens if token in haystack))

    def _snippet(self, text: str, *, limit: int = 360) -> str:
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned[:limit]

    def _slugify(self, value: str) -> str:
        slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip().lower()).strip("-._")
        return slug or "wiki-page"

    def _title_from_markdown(self, text: str) -> str | None:
        for line in text.splitlines():
            if line.startswith("# "):
                return line[2:].strip()
        return None

    def _sha256(self, path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    def _yaml_scalar(self, value: str) -> str:
        escaped = str(value).replace('"', '\\"')
        return f'"{escaped}"'

    def _now(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

    def _is_relative_to(self, path: Path, parent: Path) -> bool:
        try:
            path.resolve().relative_to(parent.resolve())
            return True
        except ValueError:
            return False
