#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sanitize_local_mcp_config(data: dict[str, Any]) -> dict[str, Any]:
    servers = {}
    for name, cfg in (data.get("mcpServers") or {}).items():
        if not isinstance(cfg, dict):
            continue
        item = dict(cfg)
        if "env" in item and isinstance(item["env"], dict):
            redacted_env = {}
            for k, v in item["env"].items():
                key_upper = str(k).upper()
                if any(token in key_upper for token in ("KEY", "TOKEN", "SECRET", "PASSWORD")):
                    redacted_env[k] = "***REDACTED***"
                else:
                    redacted_env[k] = v
            item["env"] = redacted_env
        if "args" in item and isinstance(item["args"], list):
            redacted_args: list[str] = []
            for arg in item["args"]:
                s = str(arg)
                if "API_KEY" in s or "TOKEN" in s or "X-API-KEY:" in s or "X-Goog-Api-Key:" in s:
                    redacted_args.append("***REDACTED_ARG***")
                else:
                    redacted_args.append(s)
            item["args"] = redacted_args
        servers[name] = item
    return {"mcpServers": servers}


def build_report(root: Path, include_local: bool = True) -> dict[str, Any]:
    profiles = load_json(root / "configs/tooling/mcp_profiles.json")
    design_sources = load_json(root / "configs/tooling/mcp_design_sources.json")

    findings: list[dict[str, str]] = []
    profiles_defined = set((profiles.get("profiles") or {}).keys())
    default_profile = profiles.get("default_profile")

    if default_profile not in profiles_defined:
        findings.append(
            {
                "severity": "error",
                "code": "DEFAULT_PROFILE_MISSING",
                "message": f"default_profile={default_profile} is not defined",
            }
        )

    for row in profiles.get("routing", []):
        if row.get("profile") not in profiles_defined:
            findings.append(
                {
                    "severity": "error",
                    "code": "ROUTING_REFERENCES_UNKNOWN_PROFILE",
                    "message": f"Unknown profile in routing: {row.get('profile')}",
                }
            )

    design_declared = set((design_sources.get("mcpServers") or {}).keys())
    ui_design_servers = set(((profiles.get("profiles") or {}).get("ui-design") or {}).get("servers") or [])
    design_specific_servers = {s for s in ui_design_servers if s in {"stitch", "magic", "magicui"}}
    missing_design_sources = sorted(design_specific_servers - design_declared)
    if missing_design_sources:
        findings.append(
            {
                "severity": "warn",
                "code": "DESIGN_SOURCE_REGISTRY_INCOMPLETE",
                "message": f"ui-design profile declares servers missing in mcp_design_sources.json: {missing_design_sources}",
            }
        )

    local_summary: dict[str, Any] = {"local_config_checked": False}
    local_redacted_preview: dict[str, Any] | None = None
    local_path = Path.home() / ".gemini/antigravity/mcp_config.json"
    if include_local and local_path.exists():
        local = load_json(local_path)
        local_servers = set((local.get("mcpServers") or {}).keys())
        local_summary = {
            "local_config_checked": True,
            "path": str(local_path),
            "server_count": len(local_servers),
        }
        local_redacted_preview = sanitize_local_mcp_config(local)
        # Compare only common policy servers, not every optional server.
        required_policy_servers = set()
        for prof in (profiles.get("profiles") or {}).values():
            required_policy_servers.update(set(prof.get("servers") or []))
        missing_locally = sorted(s for s in required_policy_servers if s not in local_servers)
        if missing_locally:
            findings.append(
                {
                    "severity": "warn",
                    "code": "LOCAL_GEMINI_MCP_MISSING_POLICY_SERVERS",
                    "message": f"Local Gemini MCP config lacks policy-declared servers: {missing_locally}",
                }
            )
        # Filesystem allowlist parity check.
        fs_cfg = (local.get("mcpServers") or {}).get("filesystem")
        if isinstance(fs_cfg, dict):
            args = [str(x) for x in (fs_cfg.get("args") or [])]
            actual_paths = {
                os.path.expanduser(os.path.expandvars(a))
                for a in args
                if os.path.expanduser(os.path.expandvars(a)).startswith("/")
            }
            policy_allowlist = {
                os.path.expanduser(os.path.expandvars(p))
                for p in (profiles.get("allowlist") or [])
                if os.path.expanduser(os.path.expandvars(p)).startswith("/")
            }
            missing_allowlist_paths = sorted(policy_allowlist - actual_paths)
            if missing_allowlist_paths:
                findings.append(
                    {
                        "severity": "warn",
                        "code": "FILESYSTEM_ALLOWLIST_DRIFT",
                        "message": f"Local filesystem MCP missing policy allowlist paths: {missing_allowlist_paths}",
                    }
                )

    severity = "ok"
    if any(f["severity"] == "error" for f in findings):
        severity = "error"
    elif findings:
        severity = "warn"

    report = {
        "severity": severity,
        "summary": {
            "profile_count": len(profiles_defined),
            "default_profile": default_profile,
            "design_sources_declared": sorted(design_declared),
            "ui_design_servers": sorted(ui_design_servers),
            **local_summary,
        },
        "findings": findings,
        "diff_spec_proposals": [
            "Align mcp_design_sources.json with ui-design profile server declarations (or narrow ui-design profile)",
            "Document per-client MCP parity expectations and optional server classes",
            "Normalize local filesystem MCP allowlist to match policy allowlist",
        ],
    }
    if local_redacted_preview is not None:
        report["local_config_redacted_preview"] = local_redacted_preview
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only validator for MCP profile consistency")
    parser.add_argument("--json", action="store_true", help="Output JSON only")
    parser.add_argument("--no-local", action="store_true", help="Skip local ~/.gemini/antigravity/mcp_config.json checks")
    args = parser.parse_args()

    report = build_report(repo_root(), include_local=not args.no_local)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["severity"] != "error" else 1

    print(f"severity={report['severity']}")
    for k, v in report["summary"].items():
        if k == "path":
            print(f"{k}: {v}")
            continue
        print(f"{k}: {v}")
    if report["findings"]:
        print("findings:")
        for f in report["findings"]:
            print(f"- [{f['severity']}] {f['code']}: {f['message']}")
    else:
        print("findings: -")
    print("diff-spec:")
    for item in report["diff_spec_proposals"]:
        print(f"- {item}")
    return 0 if report["severity"] != "error" else 1


if __name__ == "__main__":
    raise SystemExit(main())
