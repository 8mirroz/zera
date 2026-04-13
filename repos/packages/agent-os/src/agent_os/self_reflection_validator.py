from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .reflection_policy import evaluate_reflection_payload


@dataclass
class SelfReflectionValidationResult:
    valid: bool
    errors: list[str]
    schema_name: str | None
    schema_version: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": list(self.errors),
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
        }


def validate_self_reflection(repo_root: Path, payload: dict[str, Any]) -> SelfReflectionValidationResult:
    result = evaluate_reflection_payload(repo_root, payload)
    return SelfReflectionValidationResult(
        valid=result.valid,
        errors=list(result.errors),
        schema_name=result.schema_name,
        schema_version=result.schema_version,
    )
