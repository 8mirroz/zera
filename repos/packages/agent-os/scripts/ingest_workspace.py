import os
import json
import argparse
from pathlib import Path

# Configuration
IGNORE_DIRS = {'.git', 'node_modules', '__pycache__', '.agent', 'dist', 'build', 'venv', '.hermes', 'artifacts', 'brain'}
include_extensions = {'.py', '.md', '.yaml', '.yml', '.ts', '.js', '.json', '.txt', '.sh', '.env', '.yaml', '.sql'}

def should_ignore(path: Path) -> bool:
    for part in path.parts:
        if part in IGNORE_DIRS:
            return True
    if path.suffix not in include_extensions:
        return True
    if path.stat().st_size > 500_000: # Skip files > 500KB for now
        return True
    return False

def discover_files(root_dir: Path) -> list[Path]:
    files = []
    for path in root_dir.rglob('*'):
        if path.is_file() and not should_ignore(path):
            files.append(path)
    return files

def main():
    parser = argparse.ArgumentParser(description="Ingest workspace into LightRAG")
    parser.add_argument("--root", default=".", help="Workspace root")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually ingest, just show files")
    args = parser.parse_args()

    root = Path(args.root).absolute()
    files = discover_files(root)

    print(f"Found {len(files)} files to ingest.")

    if args.dry_run:
        for f in files:
            print(f" - {f.relative_to(root)}")
        return

    # Note: In a real standalone script, we'd use an MCP client here.
    # When run by the agent, the agent can use this output to call tools.
    for f in files:
        try:
            content = f.read_text(encoding='utf-8', errors='ignore')
            metadata = {
                "path": str(f.relative_to(root)),
                "filename": f.name,
                "extension": f.suffix,
                "size": f.stat().st_size
            }
            # Output for the agent to process
            print(json.dumps({"action": "ingest", "content": content, "metadata": metadata}))
        except Exception as e:
            print(f"Error reading {f}: {e}")

if __name__ == "__main__":
    main()
