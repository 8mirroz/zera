#!/usr/bin/env python3
"""
Hermes/Zera Terminal Style Previewer
═════════════════════════════════════
Renders a complete demo of all three terminal styles side-by-side.

Usage:
    python scripts/hermes_terminal_preview.py          # Preview all 3 styles
    python scripts/hermes_terminal_preview.py void_prism  # Preview single style
    python scripts/hermes_terminal_preview.py --json   # Output config as JSON
"""

from __future__ import annotations

import sys
import os
import json
import importlib.util


def load_hermes_terminal():
    """Load hermes_terminal module directly, bypassing agent_os __init__.py."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, "repos/packages/agent-os/src/agent_os/hermes_terminal.py")
    spec = importlib.util.spec_from_file_location("hermes_terminal", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hermes_terminal"] = mod
    spec.loader.exec_module(mod)
    return mod


# ── Sample Report Data ──────────────────────────────────────────────

SAMPLE_REPORT_SECTIONS = [
    {
        "title": "System Health",
        "content": "All subsystems operational. Memory usage nominal across all monitored axes. "
                    "No anomalies detected in the last 47 evolution cycles.",
        "items": [
            "Agent OS: v4.2.0 — all services healthy",
            "Active workflows: 12 executing, 3 queued",
            "Model routing: OpenRouter primary, 3 fallbacks ready",
            "BM25 index: 14,892 entries, 12ms avg retrieval",
        ],
        "status": "ok",
    },
    {
        "title": "Task Execution Metrics",
        "content": "Processed 234 tasks in the last hour. Average completion time: 4.2s. "
                    "Zero failures, zero rollbacks.",
        "items": [
            "C1 trivial: 89 completed (avg 1.1s)",
            "C2 simple: 96 completed (avg 2.8s)",
            "C3 medium: 42 completed (avg 5.4s)",
            "C4 complex: 3 completed (avg 18.2s)",
        ],
        "status": "ok",
    },
    {
        "title": "Memory & Knowledge",
        "content": "LightRAG graph: 3,201 nodes, 8,947 edges. "
                    "Semantic embeddings current. No stale partitions.",
        "status": "ok",
    },
    {
        "title": "Warnings",
        "content": "Minor latency spike detected on Gemini fallback (p99: 2.1s vs SLA 1.5s). "
                    "Auto-fallback to OpenRouter completed without user impact.",
        "status": "warn",
    },
]

SAMPLE_RESPONSE_BODY = (
    "The system is operating within expected parameters across all monitored dimensions. "
    "No degradation detected in agent routing, memory retrieval, or workflow execution. "
    "The next full diagnostic is scheduled for 06:00 UTC. "
    "All role contracts remain satisfied. No council review required at this time."
)

SAMPLE_METADATA = {
    "command_id": "zera:status",
    "client": "hermes",
    "tier": "C2",
    "timestamp": "2026-04-15T14:32:00Z",
    "algorithm": "karpathy",
}


# ── Module-level cache ──────────────────────────────────────────────
_mod = None

def _get_mod():
    global _mod
    if _mod is None:
        _mod = load_hermes_terminal()
    return _mod


def preview_style(style) -> None:
    """Render a complete preview of one style."""
    mod = _get_mod()
    Terminal = mod.Terminal
    _get_terminal_width = mod._get_terminal_width
    t = Terminal(style=style)

    # Style header
    width = _get_terminal_width()
    sep = "═" * width
    print(f"\n{sep}")
    print(f"  ║  STYLE: {style.value.upper()}")
    print(f"  ║  {get_style_description(style)}")
    print(f"{sep}\n")

    # Report
    print(t.report("⚕ Hermes/Zera — System Report", SAMPLE_REPORT_SECTIONS))
    print()

    # Response
    print(t.response(
        "Analysis complete — all systems nominal",
        body=SAMPLE_RESPONSE_BODY,
        metadata=SAMPLE_METADATA,
    ))


def get_style_description(style) -> str:
    descriptions = {
        "void_prism": "Cyber-minimal with geometric depth",
        "neural_glass": "Luxury monochrome with layered transparency",
        "phantom_pulse": "Retro-futurist CRT with kinetic energy",
    }
    return descriptions.get(style.value if hasattr(style, 'value') else style, "")


def main() -> None:
    mod = _get_mod()
    Terminal = mod.Terminal
    Style = mod.Style
    _get_terminal_width = mod._get_terminal_width

    if "--json" in sys.argv:
        config = {
            "styles": {
                s.value: get_style_description(s) for s in Style
            },
            "default": Style.VOID_PRISM.value,
            "env_var": "HERMES_STYLE",
        }
        print(json.dumps(config, indent=2))
        return

    args = [a for a in sys.argv[1:] if not a.startswith("-")]

    if args:
        # Preview single style
        name = args[0]
        style_map = {
            "void_prism": Style.VOID_PRISM,
            "neural_glass": Style.NEURAL_GLASS,
            "phantom_pulse": Style.PHANTOM_PULSE,
        }
        style = style_map.get(name)
        if style is None:
            print(f"Unknown style: {name}")
            print(f"Available: {', '.join(style_map.keys())}")
            sys.exit(1)
        preview_style(style)
    else:
        # Preview all styles
        for style in Style:
            preview_style(style)

        # Summary
        width = _get_terminal_width()
        print("═" * width)
        print(f"  SUMMARY")
        print(f"  {'─' * 40}")
        print(f"  Set your preferred style via:")
        print(f"    export HERMES_STYLE=<style>")
        print(f"  Or in code:")
        print(f"    t = Terminal(style=Style.VOID_PRISM)")
        print(f"  Or via config: configs/tooling/hermes_terminal.yaml")
        print(f"  {'─' * 40}")
        for s in Style:
            print(f"    {s.value:20s} — {get_style_description(s)}")
        print("═" * width)
        print()


if __name__ == "__main__":
    main()
