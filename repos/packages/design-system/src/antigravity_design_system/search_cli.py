#!/usr/bin/env python3
"""CLI for searching and generating Antigravity design systems."""

import argparse
import io
import json
import sys

from .core import AVAILABLE_STACKS, CSV_CONFIG, MAX_RESULTS, search, search_stack
from .design_system import generate_design_system

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def format_output(result: dict) -> str:
    if "error" in result:
        return f"Error: {result['error']}"

    out = []
    if result.get("stack"):
        out.append("## Stack Guidelines")
        out.append(f"**Stack:** {result['stack']} | **Query:** {result['query']}")
    else:
        out.append("## Search Results")
        out.append(f"**Domain:** {result['domain']} | **Query:** {result['query']}")

    out.append(f"**Source:** {result['file']} | **Found:** {result['count']} results")
    out.append("")

    for idx, row in enumerate(result["results"], start=1):
        out.append(f"### Result {idx}")
        for key, value in row.items():
            value_str = str(value)
            if len(value_str) > 300:
                value_str = value_str[:300] + "..."
            out.append(f"- **{key}:** {value_str}")
        out.append("")

    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="UI Pro Max Search")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--domain", "-d", choices=list(CSV_CONFIG.keys()), help="Search domain")
    parser.add_argument("--stack", "-s", choices=AVAILABLE_STACKS, help="Stack-specific search")
    parser.add_argument("--max-results", "-n", type=int, default=MAX_RESULTS, help="Max results")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--design-system", "-ds", action="store_true", help="Generate design system")
    parser.add_argument("--project-name", "-p", type=str, default=None, help="Project name")
    parser.add_argument("--format", "-f", choices=["ascii", "markdown"], default="ascii", help="Output format")
    parser.add_argument("--persist", action="store_true", help="Persist MASTER + page override")
    parser.add_argument("--page", type=str, default=None, help="Page name for override")
    parser.add_argument("--output-dir", "-o", type=str, default=None, help="Output directory")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.design_system:
        result = generate_design_system(
            args.query,
            args.project_name,
            args.format,
            persist=args.persist,
            page=args.page,
            output_dir=args.output_dir,
        )
        print(result)
        return

    if args.stack:
        result = search_stack(args.query, args.stack, args.max_results)
    else:
        result = search(args.query, args.domain, args.max_results)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return

    print(format_output(result))


if __name__ == "__main__":
    main()
