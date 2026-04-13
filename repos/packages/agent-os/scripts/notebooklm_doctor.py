#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


def _run(cmd: list[str], timeout: int = 30) -> dict[str, Any]:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=timeout)
    return {
        "cmd": cmd,
        "code": int(proc.returncode),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def _extract_version(text: str) -> str | None:
    match = re.search(r"(\d+\.\d+\.\d+)", text)
    if not match:
        return None
    return match.group(1)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _auth_source(repo_root: Path) -> dict[str, Any]:
    env_auth = os.getenv("NOTEBOOKLM_AUTH_JSON", "")
    if env_auth.strip():
        try:
            parsed = json.loads(env_auth)
            cookies = parsed.get("cookies") if isinstance(parsed, dict) else None
            return {
                "source": "NOTEBOOKLM_AUTH_JSON",
                "valid": bool(isinstance(parsed, dict) and isinstance(cookies, list) and len(cookies) > 0),
                "cookie_count": len(cookies or []),
            }
        except Exception:
            return {"source": "NOTEBOOKLM_AUTH_JSON", "valid": False, "error": "invalid JSON"}

    home = os.getenv("NOTEBOOKLM_HOME", str(Path.home() / ".notebooklm"))
    storage = Path(home) / "storage_state.json"
    exists = storage.exists()
    return {
        "source": "NOTEBOOKLM_HOME/storage_state.json",
        "valid": bool(exists),
        "path": str(storage),
        "exists": bool(exists),
        "note": "use notebooklm login for local bootstrap" if not exists else None,
    }


def _playwright_check(python_bin: str) -> dict[str, Any]:
    snippet = (
        "from playwright.sync_api import sync_playwright; "
        "p=sync_playwright().start(); "
        "b=p.chromium.launch(headless=True); "
        "b.close(); p.stop(); print('ok')"
    )
    result = _run([python_bin, "-c", snippet], timeout=60)
    return {
        "ok": result["code"] == 0,
        "code": result["code"],
        "stderr": (result["stderr"] or "")[-800:],
    }


def run_notebooklm_doctor(repo_root: Path, *, extended_test: bool = False) -> dict[str, Any]:
    report: dict[str, Any] = {
        "status": "fail",
        "checks": {},
        "hints": [],
    }

    config_path = repo_root / "configs/tooling/notebooklm_integration.json"
    if not config_path.exists():
        report["checks"]["config"] = {"ok": False, "error": f"missing {config_path}"}
        report["hints"].append("Create configs/tooling/notebooklm_integration.json")
        return report

    cfg = _load_json(config_path)
    expected_version = str(cfg.get("version_pin", "0.3.5"))
    python_bin = str(cfg.get("python_bin", "python3.12"))

    report["checks"]["config"] = {"ok": True, "path": str(config_path), "version_pin": expected_version}

    cli_bin = shutil.which("notebooklm")
    binary_ok = cli_bin is not None
    report["checks"]["binary"] = {"ok": binary_ok, "path": cli_bin}
    if not binary_ok:
        report["hints"].append("Run notebooklm bootstrap script: repos/packages/agent-os/scripts/notebooklm_bootstrap.sh")
        return report

    version_run = _run(["notebooklm", "--version"])
    current_version = _extract_version((version_run.get("stdout") or "") + (version_run.get("stderr") or ""))
    version_ok = current_version == expected_version
    report["checks"]["version"] = {
        "ok": version_ok,
        "expected": expected_version,
        "current": current_version,
        "raw": (version_run.get("stdout") or version_run.get("stderr") or "").strip(),
    }
    if not version_ok:
        report["hints"].append(f"Install pinned version notebooklm-py=={expected_version}")

    status_paths = _run(["notebooklm", "status", "--paths"])
    report["checks"]["paths"] = {
        "ok": status_paths["code"] == 0,
        "code": status_paths["code"],
        "stderr": (status_paths.get("stderr") or "")[-400:],
    }

    auth_source = _auth_source(repo_root)
    report["checks"]["auth_source"] = auth_source
    if not auth_source.get("valid"):
        report["hints"].append("Set NOTEBOOKLM_AUTH_JSON (CI) or run notebooklm login (local)")

    auth_check = _run(["notebooklm", "auth", "check", "--json"])
    auth_ok = auth_check["code"] == 0
    auth_json: dict[str, Any] | None = None
    if auth_check.get("stdout", "").strip().startswith("{"):
        try:
            auth_json = json.loads(auth_check["stdout"])
            auth_ok = auth_ok and bool(auth_json.get("ok", True))
        except Exception:
            pass
    report["checks"]["auth_check"] = {
        "ok": auth_ok,
        "code": auth_check["code"],
        "json": auth_json,
        "stderr": (auth_check.get("stderr") or "")[-600:],
    }

    # New in 0.3.5: profile support
    profiles = _run(["notebooklm", "profile", "list", "--json"])
    report["checks"]["profiles"] = {
        "ok": profiles["code"] == 0,
        "stdout": profiles["stdout"],
    }

    # New in 0.3.5: internal doctor
    internal_doctor = _run(["notebooklm", "doctor", "--json"])
    report["checks"]["internal_doctor"] = {
        "ok": internal_doctor["code"] == 0,
        "json": json.loads(internal_doctor["stdout"]) if internal_doctor["code"] == 0 and internal_doctor["stdout"].strip().startswith("{") else None
    }

    if extended_test:
        ext = _run(["notebooklm", "auth", "check", "--test", "--json"], timeout=90)
        ext_ok = ext["code"] == 0
        ext_json: dict[str, Any] | None = None
        if ext.get("stdout", "").strip().startswith("{"):
            try:
                ext_json = json.loads(ext["stdout"])
                ext_ok = ext_ok and bool(ext_json.get("ok", True))
            except Exception:
                pass
        report["checks"]["auth_check_extended"] = {
            "ok": ext_ok,
            "code": ext["code"],
            "json": ext_json,
            "stderr": (ext.get("stderr") or "")[-600:],
        }

    py_exists = shutil.which(python_bin) is not None
    report["checks"]["python_bin"] = {"ok": py_exists, "python_bin": python_bin}
    if py_exists:
        report["checks"]["playwright"] = _playwright_check(python_bin)
    else:
        report["checks"]["playwright"] = {"ok": False, "error": f"missing {python_bin}"}

    report["binary_ok"] = bool(report["checks"]["binary"].get("ok"))
    report["version_ok"] = bool(report["checks"]["version"].get("ok"))
    report["auth_ok"] = bool(report["checks"]["auth_check"].get("ok"))
    report["paths_ok"] = bool(report["checks"]["paths"].get("ok"))

    critical = [
        report["binary_ok"],
        report["version_ok"],
        report["paths_ok"],
    ]
    report["status"] = "pass" if all(critical) and report["auth_ok"] else "fail"
    return report


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def main() -> int:
    parser = argparse.ArgumentParser(description="NotebookLM integration doctor")
    parser.add_argument("--json", action="store_true", help="Output JSON report")
    parser.add_argument("--extended-test", action="store_true", help="Run notebooklm auth check --test")
    args = parser.parse_args()

    report = run_notebooklm_doctor(_repo_root(), extended_test=args.extended_test)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for name, check in report["checks"].items():
            ok = bool(check.get("ok"))
            print(f"[{ 'OK' if ok else 'FAIL' }] {name}")
        for hint in report.get("hints", []):
            print(f"HINT: {hint}")
        print(f"STATUS: {report['status']}")

    return 0 if report.get("status") == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
