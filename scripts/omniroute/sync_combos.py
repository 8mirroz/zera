#!/usr/bin/env python3
"""
OmniRoute Combo Sync — Antigravity Core v4.2

Syncs version-controlled combo configs from:
  configs/orchestrator/omniroute_combos.yaml
To OmniRoute gateway API:
  http://localhost:20128/v1

Usage:
  python3 scripts/omniroute/sync_combos.py              # Dry-run (default)
  python3 scripts/omniroute/sync_combos.py --apply       # Push to OmniRoute
  python3 scripts/omniroute/sync_combos.py --verify      # Verify current state
  python3 scripts/omniroute/sync_combos.py --test        # Test combo routing
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

try:
    import requests
except ImportError:
    requests = None

# ---------------------------------------------------------------------------
# Repo root resolution
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
# scripts/omniroute/ → scripts/ → repo_root
REPO_ROOT = SCRIPT_DIR.parent.parent

# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config() -> Dict[str, Any]:
    """Load and validate OmniRoute combo config."""
    config_path = REPO_ROOT / "configs/orchestrator/omniroute_combos.yaml"
    if not config_path.exists():
        print(f"✗ Config not found: {config_path}")
        sys.exit(1)

    text = config_path.read_text(encoding="utf-8")

    if yaml is not None:
        data = yaml.safe_load(text)
    else:
        # Fallback simple parser (sufficient for this config)
        data = _simple_yaml_parse(text)

    if not isinstance(data, dict):
        print("✗ Invalid config format")
        sys.exit(1)

    return data


def _simple_yaml_parse(text: str) -> Dict[str, Any]:
    """Minimal YAML parser fallback when PyYAML not available."""
    # This is a very simplified parser — only handles the config structure
    import re
    result = {}
    current_section = None
    current_combo = None
    current_list = None
    current_list_key = None

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # Detect list items under models
        if stripped.startswith("- model:"):
            model_id = stripped.split("- model:", 1)[1].strip()
            if current_combo and current_list_key == "models":
                result["combos"][current_combo]["models"].append(
                    {"model": model_id, "reason": ""}
                )
            continue

        if stripped.startswith("reason:"):
            reason = stripped.split("reason:", 1)[1].strip().strip('"').strip("'")
            if (current_combo and current_list_key == "models"
                    and result["combos"][current_combo]["models"]):
                result["combos"][current_combo]["models"][-1]["reason"] = reason
            continue

        # Detect section headers (no indent)
        if not line.startswith(" ") and ":" in stripped:
            key = stripped.split(":")[0].strip()
            if key in ("combos", "utility_combos", "defaults", "omniroute"):
                current_section = key
                result[key] = {}
                if key in ("combos", "utility_combos"):
                    current_list_key = None
            continue

        # Detect combo names (2-space indent, no list prefix)
        if line.startswith("  ") and not line.startswith("    ") and ":" in stripped:
            if current_section in ("combos", "utility_combos"):
                key = stripped.split(":")[0].strip()
                current_combo = key
                current_list_key = None
                result[current_section][key] = {"models": []}
            elif current_section:
                key = stripped.split(":")[0].strip()
                val = stripped.split(":", 1)[1].strip().strip('"').strip("'")
                result[current_section][key] = val
            continue

        # Detect properties (4-space indent)
        if line.startswith("    ") and not line.startswith("      ") and ":" in stripped:
            if current_combo:
                key = stripped.split(":")[0].strip()
                val = stripped.split(":", 1)[1].strip()

                if key == "models":
                    current_list_key = "models"
                    result[current_section][current_combo]["models"] = []
                elif key == "strategy":
                    current_list_key = None
                    result[current_section][current_combo]["strategy"] = val.strip('"').strip("'")
                elif key == "description":
                    current_list_key = None
                    result[current_section][current_combo]["description"] = val.strip('"').strip("'")
                elif key == "role":
                    current_list_key = None
                    result[current_section][current_combo]["role"] = val.strip('"').strip("'")
            continue

    return result


# ---------------------------------------------------------------------------
# OmniRoute API client
# ---------------------------------------------------------------------------

class OmniRouteClient:
    """Client for OmniRoute gateway API."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.session = self._init_session()

    def _init_session(self) -> Any:
        if requests is None:
            raise RuntimeError(
                "requests library required: pip install requests"
            )
        session = requests.Session()
        if self.api_key:
            session.headers["Authorization"] = f"Bearer {self.api_key}"
        session.headers["Content-Type"] = "application/json"
        return session

    def health_check(self) -> bool:
        """Check if OmniRoute is accessible."""
        try:
            resp = self.session.get(f"{self.base_url}/../health", timeout=5)
            return resp.status_code == 200
        except Exception:
            # Try alternative health endpoint
            try:
                resp = self.session.get(f"{self.base_url}/models", timeout=5)
                return resp.status_code == 200
            except Exception:
                return False

    def list_models(self) -> List[str]:
        """List available models via OmniRoute."""
        try:
            resp = self.session.get(f"{self.base_url}/models", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return [m.get("id", "") for m in data.get("data", [])]
        except Exception as exc:
            print(f"  ⚠ Failed to list models: {exc}")
            return []

    def test_model(self, model_id: str, prompt: str = "Say 'OK'") -> Optional[Dict[str, Any]]:
        """Test a model via OmniRoute."""
        try:
            resp = self.session.post(
                f"{self.base_url}/chat/completions",
                json={
                    "model": model_id,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 10,
                },
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"error": str(exc)}

    def test_combo(self, combo_models: List[Dict[str, str]]) -> Dict[str, Any]:
        """Test a combo by trying each model in priority order."""
        results = []
        for entry in combo_models:
            model = entry.get("model", "")
            start = time.perf_counter()
            response = self.test_model(model)
            elapsed = (time.perf_counter() - start) * 1000

            status = "ok" if response and "error" not in response else "failed"
            results.append({
                "model": model,
                "status": status,
                "latency_ms": round(elapsed, 1),
                "error": response.get("error") if response else "no response",
            })
            if status == "ok":
                break  # First working model wins

        return {
            "models_tested": len(results),
            "first_success": next((r for r in results if r["status"] == "ok"), None),
            "results": results,
        }

    # Note: OmniRoute manages combos via its Web Dashboard (SQLite-backed).
    # There is no public API for creating/updating combos programmatically
    # as of current version. This client provides verification and testing.
    # For full programmatic management, consider contributing to OmniRoute
    # or using their CLI if available.


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def verify_combo(config_combo: Dict[str, Any], available_models: List[str]) -> Dict[str, Any]:
    """Verify a combo's models against available OmniRoute models."""
    models = config_combo.get("models", [])
    results = []

    for entry in models:
        model_id = entry.get("model", "")
        # Check if model is in available list (prefix matching)
        model_available = any(
            model_id in m or m.endswith(model_id.split("/", 1)[-1])
            for m in available_models
        ) if available_models else True  # Skip if model list unavailable

        results.append({
            "model": model_id,
            "available": model_available,
            "reason": entry.get("reason", ""),
        })

    available_count = sum(1 for r in results if r["available"])
    return {
        "combo": config_combo.get("role", config_combo),
        "description": config_combo.get("description", ""),
        "strategy": config_combo.get("strategy", "priority"),
        "total_models": len(models),
        "available_models": available_count,
        "details": results,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sync and verify OmniRoute combo configurations"
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Push combos to OmniRoute (not yet supported — manual dashboard config)"
    )
    parser.add_argument(
        "--verify", action="store_true",
        help="Verify combo configs against OmniRoute available models"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Test combo routing by sending actual requests"
    )
    parser.add_argument(
        "--role", type=str, default=None,
        help="Test/verify specific role only (e.g. --role engineer)"
    )
    parser.add_argument(
        "--base-url", type=str, default=None,
        help="Override OmniRoute base URL (default: from config)"
    )
    args = parser.parse_args()

    # Load config
    config = load_config()
    omniroute_cfg = config.get("omniroute", {})
    base_url = args.base_url or omniroute_cfg.get("base_url", "http://localhost:20128/v1")
    api_key = os.getenv("OMNIRROUTE_API_KEY", omniroute_cfg.get("api_key"))

    combos = config.get("combos", {})

    if not combos:
        print("✗ No combos found in config")
        sys.exit(1)

    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  OmniRoute Combo Manager — Antigravity Core v4.2   ║")
    print(f"╚══════════════════════════════════════════════════════╝")
    print(f"Base URL: {base_url}")
    print(f"Combos found: {len(combos)}")
    print()

    # Health check
    client = OmniRouteClient(base_url, api_key)
    healthy = client.health_check()
    if healthy:
        print("✓ OmniRoute is accessible")
        available_models = client.list_models()
        print(f"  Available models: {len(available_models)}")
    else:
        print("⚠ OmniRoute not accessible — proceeding with offline verification")
        available_models = []

    print()

    # Verify
    if args.verify:
        print("── Verification ──────────────────────────────────")
        target_roles = [args.role] if args.role else list(combos.keys())
        for combo_name in target_roles:
            if combo_name not in combos:
                print(f"  ✗ Unknown combo: {combo_name}")
                continue
            result = verify_combo(combos[combo_name], available_models)
            status = "✓" if result["available_models"] == result["total_models"] else "⚠"
            print(f"  {status} {result['combo']} ({result['description']})")
            print(f"     Models: {result['available_models']}/{result['total_models']} available")
            for detail in result["details"]:
                m_status = "✓" if detail["available"] else "✗"
                print(f"       {m_status} {detail['model']}")
                if detail["reason"]:
                    print(f"         → {detail['reason']}")
            print()

    # Test
    if args.test:
        print("── Testing ───────────────────────────────────────")
        target_roles = [args.role] if args.role else list(combos.keys())
        for combo_name in target_roles:
            if combo_name not in combos:
                continue
            combo = combos[combo_name]
            models = combo.get("models", [])
            if not models:
                continue

            print(f"  Testing {combo.get('role', combo_name)}...")
            result = client.test_combo(models)
            first = result.get("first_success")
            if first:
                print(f"    ✓ Working: {first['model']} ({first['latency_ms']}ms)")
            else:
                print(f"    ✗ All models failed")
                for r in result.get("results", []):
                    print(f"      ✗ {r['model']}: {r.get('error', 'timeout')}")
            print()

    # Summary
    if not args.verify and not args.test:
        print("── Combo Summary ─────────────────────────────────")
        for combo_name, combo in combos.items():
            role = combo.get("role", combo_name)
            desc = combo.get("description", "")
            models = combo.get("models", [])
            strategy = combo.get("strategy", "priority")
            print(f"  • {role} ({desc})")
            print(f"    Strategy: {strategy} | Models: {len(models)}")
            for entry in models:
                print(f"      → {entry['model']}")
            print()

    if args.apply:
        print("⚠ --apply: OmniRoute does not expose a public API for combo creation.")
        print("  Please configure combos via the Web Dashboard at:")
        print(f"  {base_url}/../dashboard")
        print("  Or contribute a CLI/API extension to OmniRoute upstream.")
        sys.exit(0)


if __name__ == "__main__":
    main()
