"""Unified CLI entrypoint for antigravity design system."""

import argparse
import json

from .core import AVAILABLE_STACKS, CSV_CONFIG, search, search_stack
from .design_system import generate_design_system


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Antigravity Design System CLI")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--domain", choices=list(CSV_CONFIG.keys()), help="Search domain")
    parser.add_argument("--stack", choices=AVAILABLE_STACKS, help="Stack-specific search")
    parser.add_argument("--max-results", "-n", type=int, default=3, help="Max results")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--design-system", action="store_true", help="Generate full design system")
    parser.add_argument("--project-name", "-p", type=str, default=None, help="Project name")
    parser.add_argument("--format", "-f", choices=["ascii", "markdown"], default="ascii")
    parser.add_argument("--persist", action="store_true", help="Persist MASTER + page overrides")
    parser.add_argument("--page", type=str, default=None, help="Page override file")
    parser.add_argument("--output-dir", "-o", type=str, default=None, help="Output directory")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.design_system:
        output = generate_design_system(
            args.query,
            project_name=args.project_name,
            output_format=args.format,
            persist=args.persist,
            page=args.page,
            output_dir=args.output_dir,
        )
        print(output)
        return

    if args.stack:
        result = search_stack(args.query, args.stack, args.max_results)
    else:
        result = search(args.query, args.domain, args.max_results)

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
