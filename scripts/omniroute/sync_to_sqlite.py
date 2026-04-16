#!/usr/bin/env python3
import sqlite3
import yaml
import json
import uuid
import datetime
from pathlib import Path
import os

# Paths
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_PATH = REPO_ROOT / "configs/orchestrator/omniroute_combos.yaml"
DB_PATH = Path("~/.omniroute/storage.sqlite").expanduser()

def get_now_iso():
    return datetime.datetime.now().isoformat() + "Z"

def sync():
    if not CONFIG_PATH.exists():
        print(f"✗ Config not found: {CONFIG_PATH}")
        return

    print(f"Loading config from {CONFIG_PATH}...")
    with open(CONFIG_PATH, "r") as f:
        data = yaml.safe_load(f)

    if not DB_PATH.exists():
        print(f"✗ DB not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    combos = data.get("combos", {})
    utility_combos = data.get("utility_combos", {})
    all_combos = {**combos, **utility_combos}

    print(f"Found {len(all_combos)} combos in YAML. Syncing to SQLite...")

    for name, combo_cfg in all_combos.items():
        role = combo_cfg.get("role", name)
        strategy = combo_cfg.get("strategy", "priority")
        models = combo_cfg.get("models", [])

        # 1. Prepare 'data' JSON blob for 'combos' table
        combo_data = {
            "name": name,
            "models": [
                {
                    "id": m["model"],
                    "kind": "model",
                    "model": m["model"],
                    "providerId": m["model"].split("/")[0] if "/" in m["model"] else "unknown",
                    "weight": 0,
                    "label": m.get("reason", "")
                } for m in models
            ],
            "strategy": strategy,
            "config": {
                "maxRetries": 3,
                "retryDelayMs": 1000,
                "timeoutMs": 60000,
                "healthCheckEnabled": True,
                "healthCheckTimeoutMs": 3000,
                "trackMetrics": True
            }
        }

        # 2. Check if combo exists
        cursor.execute("SELECT id FROM combos WHERE name = ?", (name,))
        row = cursor.fetchone()
        
        now = get_now_iso()
        if row:
            combo_id = row[0]
            print(f"  → Updating combo: {name} ({combo_id})")
            cursor.execute("""
                UPDATE combos 
                SET data = ?, updated_at = ?
                WHERE id = ?
            """, (json.dumps(combo_data), now, combo_id))
        else:
            combo_id = str(uuid.uuid4())
            print(f"  + Creating combo: {name} ({combo_id})")
            cursor.execute("""
                INSERT INTO combos (id, name, data, sort_order, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (combo_id, name, json.dumps(combo_data), 0, now, now))

        # 3. Handle model mappings (Optional but good for fallback)
        # For each model in the combo, let's ensure it maps to the combo if requested exactly
        for i, m in enumerate(models):
            model_id = m["model"]
            mapping_id = str(uuid.uuid4())
            # Check if mapping already exists for this pattern and combo
            cursor.execute("SELECT id FROM model_combo_mappings WHERE pattern = ? AND combo_id = ?", (model_id, combo_id))
            if not cursor.fetchone():
                cursor.execute("""
                    INSERT INTO model_combo_mappings (id, pattern, combo_id, priority, enabled, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (mapping_id, model_id, combo_id, 100 - i, 1, now, now))

    conn.commit()
    conn.close()
    print("✓ Sync complete.")

if __name__ == "__main__":
    sync()
