import json
import os
import shutil
from pathlib import Path

def clean_traces(trace_path: Path):
    if not trace_path.exists():
        print(f"Error: {trace_path} not found.")
        return

    backup_path = trace_path.with_suffix(".jsonl.bak")
    print(f"Creating backup at {backup_path}")
    shutil.copy2(trace_path, backup_path)

    valid_lines = []
    error_count = 0
    total_count = 0

    with open(trace_path, "r", encoding="utf-8") as f:
        for line in f:
            total_count += 1
            line = line.strip()
            if not line:
                continue
            try:
                # Пытаемся распарсить как JSON
                data = json.loads(line)
                # Базовая проверка обязательных полей для логирования
                if "ts" in data and "event_type" in data:
                    valid_lines.append(line)
                else:
                    error_count += 1
            except json.JSONDecodeError:
                error_count += 1

    print(f"Processed {total_count} lines. Found {error_count} corrupted/invalid lines.")
    
    if error_count > 0:
        print(f"Writing {len(valid_lines)} valid lines back to {trace_path}")
        with open(trace_path, "w", encoding="utf-8") as f:
            for line in valid_lines:
                f.write(line + "\n")
        print("Done.")
    else:
        print("No corrupted lines found. No changes made.")

if __name__ == "__main__":
    trace_file = Path("/Users/user/zera/repos/packages/agent-os/logs/agent_traces.jsonl")
    clean_traces(trace_file)
