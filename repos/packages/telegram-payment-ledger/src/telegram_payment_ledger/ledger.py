from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PaymentLedger:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding="utf-8"))
        return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []

    def save(self, rows: list[dict[str, Any]]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def upsert(self, row: dict[str, Any]) -> None:
        rows = self.load()
        row_id = str(row.get("order_id"))
        replaced = False
        for index, item in enumerate(rows):
            if str(item.get("order_id")) == row_id:
                rows[index] = row
                replaced = True
                break
        if not replaced:
            rows.append(row)
        self.save(rows)
