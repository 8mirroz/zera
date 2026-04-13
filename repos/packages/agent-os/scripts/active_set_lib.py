from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

SCRIPT_DIR = Path(__file__).resolve().parent
SRC_DIR = SCRIPT_DIR.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent_os.plugin_contracts import validate_plugin_manifest_file


@dataclass(frozen=True)
class SkillSpec:
    name: str
    source_dir: Path


def _sha256_bytes(data: bytes) -> str:
    h = hashlib.sha256()
    h.update(data)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_tree(root: Path) -> str:
    """
    Deterministic tree hash for a directory.

    Includes: relative path + file content hash for all regular files.
    Excludes: __pycache__/ and *.pyc
    """
    root = root.resolve()
    entries: list[tuple[str, str]] = []
    for p in sorted(root.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(root).as_posix()
        if rel.startswith("__pycache__/") or rel.endswith(".pyc"):
            continue
        entries.append((rel, sha256_file(p)))

    payload = json.dumps(entries, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return _sha256_bytes(payload)


def parse_active_skills_md(md_path: Path) -> list[SkillSpec]:
    """
    Parse `configs/skills/ACTIVE_SKILLS.md`.

    Accepted lines:
    - `- `configs/skills/foo``
    - `- configs/skills/foo`
    """
    md_path = md_path.resolve()
    repo_root = md_path.parents[2]
    text = md_path.read_text(encoding="utf-8")
    specs: list[SkillSpec] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line.startswith("-"):
            continue

        m = re.search(r"`([^`]+)`", line)
        value = (m.group(1) if m else line.lstrip("-").strip()).strip()
        if not value or value.startswith("#"):
            continue

        source_dir = (repo_root / value).resolve() if not value.startswith("/") else Path(value)
        name = Path(value).name
        specs.append(SkillSpec(name=name, source_dir=source_dir))

    # De-dupe while preserving order
    seen: set[str] = set()
    out: list[SkillSpec] = []
    for s in specs:
        if s.name in seen:
            continue
        seen.add(s.name)
        out.append(s)
    return out


def ensure_skill_dir_valid(skill_dir: Path) -> None:
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise FileNotFoundError(f"Skill directory not found: {skill_dir}")
    if not (skill_dir / "SKILL.md").exists():
        raise FileNotFoundError(f"Missing SKILL.md in: {skill_dir}")


def safe_rmtree_children(dir_path: Path, keep: Iterable[str] = (".gitkeep",)) -> None:
    if not dir_path.exists():
        return
    keep_set = set(keep)
    for child in dir_path.iterdir():
        if child.name in keep_set:
            continue
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def publish_active_set(
    *,
    repo_root: Path,
    active_md: Path,
    dest_dir: Path,
) -> dict:
    repo_root = repo_root.resolve()
    active_md = active_md.resolve()
    dest_dir = dest_dir.resolve()
    specs = parse_active_skills_md(active_md)
    if not specs:
        raise ValueError(f"No skills found in: {active_md}")

    dest_dir.mkdir(parents=True, exist_ok=True)
    safe_rmtree_children(dest_dir)

    published: list[dict] = []
    for spec in specs:
        ensure_skill_dir_valid(spec.source_dir)
        plugin_metadata = None
        source_plugin_path = spec.source_dir / "plugin.json"
        if source_plugin_path.exists():
            plugin_metadata = validate_plugin_manifest_file(source_plugin_path)
        dest_skill_dir = (dest_dir / spec.name).resolve()
        shutil.copytree(spec.source_dir, dest_skill_dir)
        published_row = {
            "name": spec.name,
            "source": os.path.relpath(spec.source_dir, repo_root),
            "dest": os.path.relpath(dest_skill_dir, repo_root),
            "sha256_tree": sha256_tree(dest_skill_dir),
        }
        if plugin_metadata is not None:
            published_row["plugin"] = {
                "path": os.path.relpath(dest_skill_dir / "plugin.json", repo_root),
                **plugin_metadata.to_dict(),
            }
        published.append(published_row)

    manifest = {
        "version": "agent-os-v2",
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "active_skills_md": os.path.relpath(active_md, repo_root),
        "skills": published,
    }
    (dest_dir / ".active_set_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest
