"""Lightweight audit pass for design system integrity and logic checks."""

from __future__ import annotations

import asyncio
import csv
import json
import re
from dataclasses import asdict
from pathlib import Path

from .adaptive_system import AdaptiveDesignSystem
from .core import CSV_CONFIG, DATA_DIR, search, search_stack
from .design_system import generate_design_system

HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


def _check_csv_headers() -> list[str]:
    issues: list[str] = []
    for domain, cfg in CSV_CONFIG.items():
        path = DATA_DIR / cfg["file"]
        if not path.exists():
            issues.append(f"MISSING_FILE:{path}")
            continue
        with open(path, "r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            headers = reader.fieldnames or []
            for col in cfg["search_cols"]:
                if col not in headers:
                    issues.append(f"MISSING_COLUMN:{path}:{col}")
    return issues


def _check_search_logic() -> list[str]:
    issues: list[str] = []
    cases = [
        ("glassmorphism premium", "style"),
        ("fintech", "color"),
        ("accessibility focus", "ux"),
        ("modern sans", "typography"),
    ]
    for query, domain in cases:
        result = search(query, domain, max_results=2)
        if result.get("count", 0) == 0:
            issues.append(f"EMPTY_RESULT:{domain}:{query}")

    stack_result = search_stack("responsive forms", "html-tailwind", max_results=2)
    if stack_result.get("count", 0) == 0:
        issues.append("EMPTY_STACK_RESULT:html-tailwind")
    return issues


def _check_design_generation() -> list[str]:
    issues: list[str] = []
    rendered = generate_design_system("saas analytics", "Audit Project", output_format="markdown")
    if "### Colors" not in rendered:
        issues.append("MISSING_SECTION:colors")
    if "### Typography" not in rendered:
        issues.append("MISSING_SECTION:typography")

    rendered_json = generate_design_system("luxury ecommerce", "Audit Project", output_format="ascii")
    if "PRE-DELIVERY CHECKLIST" not in rendered_json:
        issues.append("MISSING_CHECKLIST")
    return issues


def _check_color_validity() -> list[str]:
    issues: list[str] = []
    result = search("SaaS", "color", max_results=20)
    for row in result.get("results", []):
        for key in ["Primary (Hex)", "Secondary (Hex)", "CTA (Hex)", "Background (Hex)", "Text (Hex)"]:
            value = row.get(key, "")
            if value and not HEX_RE.match(value):
                issues.append(f"INVALID_HEX:{row.get('Product Type','unknown')}:{key}:{value}")
    return issues


async def _check_adaptive_logic() -> list[str]:
    issues: list[str] = []
    engine = AdaptiveDesignSystem()
    output = await engine.generate(
        product_type="landing_page",
        style="glassmorphism",
        platforms=["web", "mobile", "vision-pro", "blockchain"],
    )

    output_dict = asdict(output)
    if "tokens" not in output_dict:
        issues.append("ADAPTIVE_MISSING_TOKENS")
    if "web" not in output.platforms:
        issues.append("ADAPTIVE_MISSING_WEB_PLATFORM")
    if not output.tailwind_config.strip().startswith("/** @type"):
        issues.append("ADAPTIVE_BAD_TAILWIND_CONFIG")
    return issues


def main() -> None:
    issues: list[str] = []
    issues.extend(_check_csv_headers())
    issues.extend(_check_search_logic())
    issues.extend(_check_design_generation())
    issues.extend(_check_color_validity())
    issues.extend(asyncio.run(_check_adaptive_logic()))

    report = {
        "status": "fail" if issues else "ok",
        "issue_count": len(issues),
        "issues": issues,
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
