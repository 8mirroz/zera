#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import re
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    import jsonschema
    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False


def repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def utc_now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def policy(root: Path) -> dict[str, Any]:
    path = root / "configs/tooling/repo_aliases_policy.json"
    if not path.exists():
        # V2.0 Robust Defaults
        return {
            "domain_codes": {
                "packages": "pkg",
                "skills": "sk",
                "workflows": "wf",
                "mcp": "mcp",
                "apps": "app"
            },
            "alias_generation": {
                "compact_token_prefix_len": 3,
                "compact_max_tokens": 3,
                "initials_max_tokens": 4
            }
        }
    return load_json(path)


def catalog_root(root: Path) -> Path:
    return root / ".agents/memory/repos-catalog"


def ensure_catalog_structure(root: Path) -> None:
    cat = catalog_root(root)
    (cat / "indexes").mkdir(parents=True, exist_ok=True)
    (cat / "schemas").mkdir(parents=True, exist_ok=True)
    (cat / "templates").mkdir(parents=True, exist_ok=True)
    (cat / "audit/validation_reports").mkdir(parents=True, exist_ok=True)


def split_tokens(name: str) -> list[str]:
    # CamelCase -> camel-case (best-effort), then split non-alnum.
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1-\2", name)
    tokens = [t.lower() for t in re.split(r"[^A-Za-z0-9]+", s) if t]
    return tokens or [name.lower()]


def safe_slug_text(slug: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", slug.lower()).strip("-")


def compress_token(token: str, max_len: int = 3) -> str:
    token = re.sub(r"[^a-z0-9]+", "", token.lower())
    if not token:
        return ""
    if len(token) <= max_len:
        return token
    vowels = set("aeiou")
    out = [token[0]]
    # Prefer consonants for mnemonic compression (`servers` -> `srv`)
    for ch in token[1:]:
        if ch not in vowels:
            out.append(ch)
        if len(out) >= max_len:
            return "".join(out[:max_len])
    for ch in token[1:]:
        if len(out) >= max_len:
            break
        if ch not in out:
            out.append(ch)
    return "".join(out[:max_len])


def discover_repos(root: Path) -> list[Path]:
    base = root / "repos"
    if not base.exists():
        return []
    out: list[Path] = []
    for domain_dir in sorted(base.iterdir()):
        if not domain_dir.is_dir():
            continue
        for repo_dir in sorted(domain_dir.iterdir()):
            if not repo_dir.is_dir():
                continue
            out.append(repo_dir)
    return out


def top_level_signals(repo_dir: Path) -> dict[str, Any]:
    top = {p.name for p in repo_dir.iterdir()}
    file_names = [p.name for p in repo_dir.iterdir() if p.is_file()]
    top_file_count = len(file_names)
    top_dir_count = len([p for p in repo_dir.iterdir() if p.is_dir()])
    has_readme = any(n.lower().startswith("readme") for n in file_names)
    has_git = (repo_dir / ".git").exists()
    has_scripts = (repo_dir / "scripts").exists()
    has_skills = (repo_dir / "skills").exists()
    has_assets = (repo_dir / "assets").exists()
    has_src = (repo_dir / "src").exists()
    has_tests = any(n in top for n in ("tests", "test", "__tests__"))

    tech_markers = []
    stack = []
    for marker, lang in {
        "package.json": "javascript",
        "pyproject.toml": "python",
        "requirements.txt": "python",
        "tsconfig.json": "typescript",
        "Cargo.toml": "rust",
        "go.mod": "go",
        "MAINTAINERS": "core-infra"
    }.items():
        if marker in top:
            tech_markers.append(marker)
            stack.append(lang)

    # Complexity estimation
    if top_file_count + top_dir_count > 50:
        complexity = "C4"
    elif top_file_count + top_dir_count > 20:
        complexity = "C3"
    elif top_file_count + top_dir_count > 5:
        complexity = "C2"
    else:
        complexity = "C1"

    return {
        "has_git": has_git,
        "has_readme": has_readme,
        "has_scripts": has_scripts,
        "has_skills": has_skills,
        "has_assets": has_assets,
        "has_src": has_src,
        "has_tests": has_tests,
        "tech_markers": tech_markers,
        "tech_stack": sorted(list(set(stack))),
        "top_file_count": top_file_count,
        "top_dir_count": top_dir_count,
        "complexity_tier": complexity,
    }


def score_repo(domain: str, slug: str, signals: dict[str, Any]) -> dict[str, int]:
    score = 0
    nav = 40
    reuse = 30

    if domain in {"packages", "skills", "workflows", "mcp"}:
        score += 20
        reuse += 25
    if signals.get("has_readme"):
        score += 15
        nav += 10
    if signals.get("has_scripts"):
        score += 10
        reuse += 10
    if signals.get("has_tests"):
        score += 10
        reuse += 10
    if signals.get("has_skills") or "skills" in slug:
        score += 15
        reuse += 15
    if signals.get("has_git"):
        score += 10
    if domain in {"packages", "workflows"}:
        score += 15
    if domain in {"skills", "mcp"}:
        score += 10
    if (signals.get("top_file_count", 0) + signals.get("top_dir_count", 0)) <= 12:
        score += 10
        nav += 10

    nav += 10 if len(slug) <= 20 else 0
    nav += 5 if "-" in slug else 0
    reuse += 10 if signals.get("has_src") else 0

    return {
        "speed_free_score": max(0, min(100, score)),
        "navigation_priority": max(0, min(100, nav)),
        "reuse_priority": max(0, min(100, reuse)),
    }


def build_compact_short(tokens: list[str], token_prefix_len: int, initials_max_tokens: int) -> tuple[str, str]:
    initials = "".join(t[0] for t in tokens[:initials_max_tokens] if t)

    if len(tokens) == 1:
        compact = compress_token(tokens[0], max_len=max(3, token_prefix_len))
        return compact, initials

    # Prefer acronym for 3+ tokens (e.g., antigravity-awesome-skills -> aas)
    if len(initials) >= 3:
        return initials[:max(3, initials_max_tokens)], initials

    # For 2-token slugs, pad acronym using compressed last token (`agent-os` -> `aos`)
    compact = initials
    last_comp = compress_token(tokens[-1], max_len=max(3, token_prefix_len))
    for ch in last_comp[1:]:
        if len(compact) >= 3:
            break
        if ch not in compact[-1:]:
            compact += ch

    if len(compact) < 3:
        # Add chars from compressed first token if still too short
        first_comp = compress_token(tokens[0], max_len=max(3, token_prefix_len))
        for ch in first_comp[1:]:
            if len(compact) >= 3:
                break
            compact += ch

    return compact[:6], initials


def candidate_aliases(domain_code: str, slug: str, token_prefix_len: int, compact_max_tokens: int, initials_max_tokens: int) -> list[str]:
    tokens = split_tokens(slug)
    compact, initials = build_compact_short(tokens, token_prefix_len=token_prefix_len, initials_max_tokens=initials_max_tokens)
    # Secondary verbose compact (useful if compact collides too much in larger catalogs)
    verbose_compact = "".join(t[:token_prefix_len] for t in tokens[:compact_max_tokens] if t)
    slug_compact = slug if len(slug) <= 18 else slug[:18].rstrip("-")
    out = [
        f"r/{domain_code}/{slug}",
        f"{domain_code}:{compact}" if compact else "",
        f"{domain_code}:{initials}" if initials else "",
        f"{domain_code}:{verbose_compact}" if verbose_compact else "",
        f"{domain_code}-{slug_compact}",
    ]
    # De-duplicate preserving order
    seen: set[str] = set()
    final: list[str] = []
    for a in out:
        if not a or a in seen:
            continue
        seen.add(a)
        final.append(a)
    return final


def build_repo_records(root: Path) -> tuple[list[dict[str, Any]], dict[str, list[str]], list[dict[str, str]]]:
    pol = policy(root)
    alias_cfg = pol.get("alias_generation", {})
    domain_codes = pol.get("domain_codes", {})
    token_prefix_len = int(alias_cfg.get("compact_token_prefix_len", 3))
    compact_max_tokens = int(alias_cfg.get("compact_max_tokens", 3))
    initials_max_tokens = int(alias_cfg.get("initials_max_tokens", 4))

    repos = discover_repos(root)
    alias_claims: dict[str, list[int]] = defaultdict(list)
    records: list[dict[str, Any]] = []

    for idx, repo_dir in enumerate(repos):
        rel = repo_dir.relative_to(root).as_posix()
        _, domain, raw_slug = rel.split("/", 2)
        slug = safe_slug_text(raw_slug)
        domain_code = str(domain_codes.get(domain, domain[:3].lower()))
        signals = top_level_signals(repo_dir)
        scores = score_repo(domain, slug, signals)
        tags: list[str] = [domain, domain_code, "repo-catalog"]
        if signals.get("has_git"):
            tags.append("git")
            tags.append("likely-oss")
        if signals.get("has_scripts"):
            tags.append("scripts")
        if signals.get("has_skills"):
            tags.append("skills")
        if signals.get("has_src"):
            tags.append("src")
        for marker in signals.get("tech_markers", []):
            tags.append(marker)
        if scores["speed_free_score"] >= 60:
            tags.append("fast-free-priority")

        alias_candidates = candidate_aliases(
            domain_code=domain_code,
            slug=slug,
            token_prefix_len=token_prefix_len,
            compact_max_tokens=compact_max_tokens,
            initials_max_tokens=initials_max_tokens,
        )
        for alias in alias_candidates:
            alias_claims[alias].append(idx)

        records.append(
            {
                "repo_id": f"repo::{domain_code}::{slug}",
                "domain": domain,
                "domain_code": domain_code,
                "slug": slug,
                "display_name": raw_slug,
                "path": rel,
                "stable_key": f"repo_catalog:repo:{domain}:{slug}",
                "aliases": {
                    "candidates": alias_candidates
                },
                "signals": signals,
                "scores": scores,
                "tags": sorted(set(tags)),
                "tech_stack": signals.get("tech_stack", []),
                "updated_at": utc_now_iso(),
            }
        )

    warnings: list[dict[str, str]] = []
    alias_map: dict[str, dict[str, Any]] = {}

    # Resolve alias collisions deterministically by path sort and suffix.
    for rec in sorted(records, key=lambda r: (r["domain"], r["slug"])):
        candidates = list(rec["aliases"]["candidates"])
        assigned_all: list[str] = []
        for alias in candidates:
            if alias not in alias_map:
                alias_map[alias] = {
                    "repo_id": rec["repo_id"],
                    "path": rec["path"],
                    "domain": rec["domain"],
                    "slug": rec["slug"],
                    "kind": "primary_candidate",
                }
                assigned_all.append(alias)
                continue
            # collision suffix
            n = 2
            while f"{alias}-{n}" in alias_map:
                n += 1
            ali = f"{alias}-{n}"
            alias_map[ali] = {
                "repo_id": rec["repo_id"],
                "path": rec["path"],
                "domain": rec["domain"],
                "slug": rec["slug"],
                "kind": "collision_resolved",
            }
            assigned_all.append(ali)
            warnings.append(
                {
                    "code": "ALIAS_COLLISION",
                    "message": f"{alias} collision -> assigned {ali}",
                    "repo_id": rec["repo_id"],
                }
            )

        # Select stable aliases by preference order.
        path_alias = next((a for a in assigned_all if a.startswith("r/")), "")
        colon_aliases = [a for a in assigned_all if ":" in a and not a.startswith("r/")]
        compact_alias = ""
        if colon_aliases:
            preferred = [a for a in colon_aliases if 3 <= len(a.split(":", 1)[1]) <= 6]
            pool = preferred if preferred else [a for a in colon_aliases if len(a.split(":", 1)[1]) > 1] or colon_aliases
            # Preserve natural candidate priority first, then shortest among suitable aliases.
            compact_alias = sorted(pool, key=lambda a: (len(a.split(":", 1)[1]), colon_aliases.index(a)))[0]
        initials_alias = sorted(colon_aliases, key=lambda a: (len(a.split(":", 1)[1]), colon_aliases.index(a)))[0] if colon_aliases else ""
        rec["aliases"] = {
            "path_alias": path_alias,
            "compact_alias": compact_alias,
            "initials_alias": initials_alias,
            "all": assigned_all,
        }

    return records, {k: v["path"] for k, v in alias_map.items()}, warnings


def rank_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda r: (
            int(r.get("scores", {}).get("speed_free_score", 0)),
            int(r.get("scores", {}).get("reuse_priority", 0)),
            int(r.get("scores", {}).get("navigation_priority", 0)),
        ),
        reverse=True,
    )


def validate_catalog_entry(root: Path, entry: dict[str, Any]) -> list[str]:
    schema_path = catalog_root(root) / "schemas/repo.schema.json"
    if not schema_path.exists():
        return []
    errors = []
    try:
        schema = load_json(schema_path)
        if HAS_JSONSCHEMA:
            from jsonschema import validate, ValidationError
            try:
                validate(instance=entry, schema=schema)
            except ValidationError as ve:
                errors.append(f"schema violation: {ve.message}")
        else:
            required = schema.get("required", [])
            for field in required:
                if field not in entry:
                    errors.append(f"missing required field: {field}")
    except Exception as e:
        errors.append(f"validation system error: {str(e)}")
    return errors


def write_indexes(root: Path, records: list[dict[str, Any]], alias_index: dict[str, str], warnings: list[dict[str, str]]) -> dict[str, Any]:
    ensure_catalog_structure(root)
    cat = catalog_root(root)

    ranked = rank_records(records)
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_tag: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in ranked:
        mini = {
            "repo_id": r["repo_id"],
            "path": r["path"],
            "slug": r["slug"],
            "compact_alias": r["aliases"]["compact_alias"],
            "path_alias": r["aliases"]["path_alias"],
            "speed_free_score": r["scores"]["speed_free_score"],
            "navigation_priority": r["scores"]["navigation_priority"],
            "reuse_priority": r["scores"]["reuse_priority"],
        }
        by_domain[r["domain"]].append(mini)
        for tag in r.get("tags", []):
            if len(by_tag[tag]) < 50:
                by_tag[tag].append(mini)

    repos_index = {
        "generated_at": utc_now_iso(),
        "repos_count": len(records),
        "records": ranked,
    }
    aliases_index = {
        "generated_at": utc_now_iso(),
        "aliases_count": len(alias_index),
        "aliases": alias_index,
    }
    shortcuts = {
        "generated_at": utc_now_iso(),
        "goal": "max_speed_and_free_solutions",
        "top_fast_free": [
            {
                "path": r["path"],
                "compact_alias": r["aliases"]["compact_alias"],
                "path_alias": r["aliases"]["path_alias"],
                "speed_free_score": r["scores"]["speed_free_score"],
                "tags": r.get("tags", []),
            }
            for r in ranked[:20]
        ],
        "by_domain": dict(by_domain),
        "by_tag": dict(by_tag),
        "recommended_start_points": {
            "skills": [x["compact_alias"] for x in by_domain.get("skills", [])[:5]],
            "workflows": [x["compact_alias"] for x in by_domain.get("workflows", [])[:5]],
            "packages": [x["compact_alias"] for x in by_domain.get("packages", [])[:5]],
            "mcp": [x["compact_alias"] for x in by_domain.get("mcp", [])[:5]],
        },
    }
    validation = {
        "generated_at": utc_now_iso(),
        "warnings_count": len(warnings),
        "warnings": warnings,
    }

    dump_json(cat / "indexes/repos_index.json", repos_index)
    dump_json(cat / "indexes/aliases_index.json", aliases_index)
    dump_json(cat / "indexes/navigation_shortcuts.json", shortcuts)
    dump_json(cat / "indexes/validation_report.json", validation)

    return {
        "status": "ok",
        "repos_count": len(records),
        "aliases_count": len(alias_index),
        "warnings_count": len(warnings),
        "indexes": [
            ".agents/memory/repos-catalog/indexes/repos_index.json",
            ".agents/memory/repos-catalog/indexes/aliases_index.json",
            ".agents/memory/repos-catalog/indexes/navigation_shortcuts.json",
            ".agents/memory/repos-catalog/indexes/validation_report.json"
        ]
    }


def refresh(root: Path) -> dict[str, Any]:
    records, alias_index, warnings = build_repo_records(root)
    
    # Validation step
    validation_errors = []
    for r in records:
        errs = validate_catalog_entry(root, r)
        if errs:
            validation_errors.append({"repo_id": r["repo_id"], "errors": errs})

    result = write_indexes(root, records, alias_index, warnings)
    result["validation_errors_count"] = len(validation_errors)
    result["top_fast_free_aliases"] = [
        r["aliases"]["compact_alias"] for r in rank_records(records)[:10]
    ]
    
    val_report = {
        "generated_at": utc_now_iso(),
        "ok_count": len(records) - len(validation_errors),
        "error_count": len(validation_errors),
        "errors": validation_errors
    }
    dump_json(catalog_root(root) / "audit/validation_reports/last_run.json", val_report)
    
    return result


def load_current_indexes(root: Path) -> tuple[list[dict[str, Any]], dict[str, str]]:
    cat = catalog_root(root)
    repos_index = load_json(cat / "indexes/repos_index.json")
    aliases_index = load_json(cat / "indexes/aliases_index.json")
    return list(repos_index.get("records", [])), dict(aliases_index.get("aliases", {}))


def query(root: Path, *, text: str | None, domain: str | None, tag: str | None, min_score: int | None, limit: int) -> dict[str, Any]:
    records, _ = load_current_indexes(root)
    needle = (text or "").lower().strip()
    out = []
    for r in rank_records(records):
        if domain and r.get("domain") != domain:
            continue
        if tag and tag not in r.get("tags", []):
            continue
        if min_score is not None and int(r.get("scores", {}).get("speed_free_score", 0)) < min_score:
            continue
        hay = " ".join([
            r.get("path", ""),
            r.get("slug", ""),
            r.get("display_name", ""),
            " ".join(r.get("tags", [])),
            " ".join(r.get("aliases", {}).get("all", [])),
        ]).lower()
        if needle and needle not in hay:
            continue
        out.append(
            {
                "repo_id": r["repo_id"],
                "path": r["path"],
                "compact_alias": r["aliases"]["compact_alias"],
                "path_alias": r["aliases"]["path_alias"],
                "speed_free_score": r["scores"]["speed_free_score"],
                "tags": r["tags"],
            }
        )
        if len(out) >= limit:
            break
    return {"status": "ok", "results_count": len(out), "results": out}


def resolve_alias(root: Path, alias: str) -> dict[str, Any]:
    records, aliases = load_current_indexes(root)
    path = aliases.get(alias)
    if not path:
        return {"status": "error", "error": f"Alias not found: {alias}"}
    rec = next((r for r in records if r.get("path") == path), None)
    if rec is None:
        return {"status": "error", "error": f"Alias exists but repo record missing: {alias}"}
    return {
        "status": "ok",
        "alias": alias,
        "repo_id": rec["repo_id"],
        "path": rec["path"],
        "compact_alias": rec["aliases"]["compact_alias"],
        "path_alias": rec["aliases"]["path_alias"],
        "tags": rec["tags"],
        "scores": rec["scores"],
    }


def sync_memory(root: Path) -> dict[str, Any]:
    records, aliases = load_current_indexes(root)
    memory_file = root / ".agents/memory/memory.jsonl"
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    if not memory_file.exists():
        memory_file.write_text("", encoding="utf-8")

    existing_keys: set[str] = set()
    for line in memory_file.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            key = row.get("key")
            if isinstance(key, str):
                existing_keys.add(key)
        except: continue

    written = 0
    with memory_file.open("a", encoding="utf-8") as f:
        for r in records:
            key = r["stable_key"]
            if key in existing_keys:
                continue
            row = {
                "id": str(uuid4()),
                "key": key,
                "payload": {
                    "source": "repo_memory_catalog",
                    "id": r["repo_id"],
                    "path": r["path"],
                    "domain": r["domain"],
                    "slug": r["slug"],
                    "aliases": r["aliases"],
                    "score": r["scores"]["speed_free_score"],
                    "tags": r["tags"],
                    "tech_stack": r.get("tech_stack", []),
                    "updated_at": r["updated_at"],
                }
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1

    return {
        "status": "ok",
        "synced_repos": written,
        "memory_file": str(memory_file.relative_to(root))
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Repository memory catalog + alias index for Antigravity agents")
    p.add_argument("--json", action="store_true", help="JSON output")
    sub = p.add_subparsers(dest="cmd", required=True)

    rf = sub.add_parser("refresh", help="Scan repos, rebuild indexes, optionally sync runtime memory")
    rf.add_argument("--sync-memory", action="store_true", help="Sync catalog entries/aliases into .agents/memory/memory.jsonl")

    q = sub.add_parser("query", help="Query catalog")
    q.add_argument("--text", help="Text search")
    q.add_argument("--domain", help="Filter by domain (e.g. packages, skills, mcp)")
    q.add_argument("--tag", help="Filter by tag")
    q.add_argument("--min-score", type=int, help="Minimum speed_free_score")
    q.add_argument("--limit", type=int, default=10)

    rs = sub.add_parser("resolve", help="Resolve alias to repo path")
    rs.add_argument("--alias", required=True)

    sub.add_parser("sync-memory", help="Sync current indexes to .agents/memory/memory.jsonl")

    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = repo_root()
    try:
        if args.cmd == "refresh":
            result = refresh(root)
            if args.sync_memory:
                result["sync_memory"] = sync_memory(root)
        elif args.cmd == "query":
            result = query(
                root,
                text=args.text,
                domain=args.domain,
                tag=args.tag,
                min_score=args.min_score,
                limit=max(1, int(args.limit)),
            )
        elif args.cmd == "resolve":
            result = resolve_alias(root, alias=args.alias)
            if result.get("status") == "error":
                if args.json:
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                else:
                    print(f"error: {result['error']}")
                return 1
        elif args.cmd == "sync-memory":
            result = sync_memory(root)
        else:
            raise ValueError(f"Unknown command: {args.cmd}")

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            for k, v in result.items():
                print(f"{k}: {v}")
        return 0
    except Exception as e:
        err = {"status": "error", "error": str(e)}
        if args.json:
            print(json.dumps(err, ensure_ascii=False, indent=2))
        else:
            print(f"error: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
