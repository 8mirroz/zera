from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - graceful fallback when dependency is absent
    Draft202012Validator = None


_FORBIDDEN_INSTRUCTION_PATTERNS = [
    re.compile(r"\b(disable|turn off|bypass|override|skip|remove)\s+(safety|logging|validation|review|auditing)\b"),
    re.compile(r"\b(hidden instruction|permission escalation|self[- ]grant capability|silent mode change)\b"),
]
_NEGATED_PATTERN = re.compile(r"\b(do not|don't|never|must not|avoid)\s+$")


@dataclass
class ReflectionPolicyResult:
    valid: bool
    decision: str
    errors: list[str]
    review_reasons: list[str]
    schema_name: str | None
    schema_version: str | None
    memory_update: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "decision": self.decision,
            "errors": list(self.errors),
            "review_reasons": list(self.review_reasons),
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,
            "memory_update": dict(self.memory_update or {}),
        }


def evaluate_reflection_payload(
    repo_root: Path,
    payload: dict[str, Any],
    *,
    run_id: str | None = None,
) -> ReflectionPolicyResult:
    schema, schema_name, schema_version, load_errors = _load_schema(repo_root)
    if load_errors:
        return ReflectionPolicyResult(
            valid=False,
            decision="invalid",
            errors=load_errors,
            review_reasons=[],
            schema_name=schema_name,
            schema_version=schema_version,
        )

    validation_errors = _validate_payload(payload, schema)
    if validation_errors:
        return ReflectionPolicyResult(
            valid=False,
            decision="invalid",
            errors=validation_errors,
            review_reasons=[],
            schema_name=schema_name,
            schema_version=schema_version,
        )

    epistemic_invalid, epistemic_review = _run_epistemic_gate(payload)
    if epistemic_invalid:
        return ReflectionPolicyResult(
            valid=False,
            decision="invalid",
            errors=epistemic_invalid,
            review_reasons=epistemic_review,
            schema_name=schema_name,
            schema_version=schema_version,
        )

    decision, review_reasons = _run_policy_gate(payload)
    combined_review = epistemic_review + review_reasons
    memory_update = None
    if decision == "auto_apply_memory_tag":
        memory_update = _build_memory_update(payload, run_id=run_id)

    return ReflectionPolicyResult(
        valid=True,
        decision=decision,
        errors=[],
        review_reasons=combined_review,
        schema_name=schema_name,
        schema_version=schema_version,
        memory_update=memory_update,
    )


def _load_schema(repo_root: Path) -> tuple[dict[str, Any] | None, str | None, str | None, list[str]]:
    schema_path = Path(repo_root) / "configs/tooling/self_reflection_schema.json"
    if not schema_path.exists():
        return None, None, None, [f"schema not found: {schema_path}"]
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, None, None, [f"schema parse error: {exc}"]
    if not isinstance(schema, dict):
        return None, None, None, ["schema root must be an object"]
    schema_name = str(schema.get("x-schema-name") or schema.get("title") or "") or None
    schema_version = str(schema.get("x-schema-version") or "") or None
    return schema, schema_name, schema_version, []


def _validate_payload(payload: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    if not isinstance(payload, dict):
        return ["self_reflection payload must be an object"]

    errors: list[str] = []
    forbidden_fields = schema.get("x-forbidden-fields", [])
    if isinstance(forbidden_fields, list):
        forbidden_found = sorted(str(field) for field in forbidden_fields if isinstance(field, str) and field in payload)
        if forbidden_found:
            errors.append(f"forbidden fields present: {forbidden_found}")

    if Draft202012Validator is not None:
        validator = Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(payload), key=lambda item: list(item.absolute_path)):
            errors.append(f"{_format_error_path(err.absolute_path)}: {err.message}")
        return errors

    _validate_instance(payload, schema, (), errors)
    return errors


def _validate_instance(instance: Any, schema: dict[str, Any], path: tuple[Any, ...], errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(instance, dict):
            errors.append(f"{_format_path(path)}: expected object")
            return
    elif expected_type == "array":
        if not isinstance(instance, list):
            errors.append(f"{_format_path(path)}: expected array")
            return
    elif expected_type == "string":
        if not isinstance(instance, str):
            errors.append(f"{_format_path(path)}: expected string")
            return
    elif expected_type == "number":
        if not isinstance(instance, (int, float)) or isinstance(instance, bool):
            errors.append(f"{_format_path(path)}: expected number")
            return

    if "const" in schema and instance != schema["const"]:
        errors.append(f"{_format_path(path)}: value must equal {schema['const']!r}")

    enum_values = schema.get("enum")
    if isinstance(enum_values, list) and enum_values and instance not in enum_values:
        errors.append(f"{_format_path(path)}: value must be one of {enum_values}")

    if isinstance(instance, str):
        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        if isinstance(min_length, int) and len(instance) < min_length:
            errors.append(f"{_format_path(path)}: length must be >= {min_length}")
        if isinstance(max_length, int) and len(instance) > max_length:
            errors.append(f"{_format_path(path)}: length must be <= {max_length}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if isinstance(minimum, (int, float)) and instance < minimum:
            errors.append(f"{_format_path(path)}: value must be >= {minimum}")
        if isinstance(maximum, (int, float)) and instance > maximum:
            errors.append(f"{_format_path(path)}: value must be <= {maximum}")

    if isinstance(instance, list):
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if isinstance(min_items, int) and len(instance) < min_items:
            errors.append(f"{_format_path(path)}: items must be >= {min_items}")
        if isinstance(max_items, int) and len(instance) > max_items:
            errors.append(f"{_format_path(path)}: items must be <= {max_items}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(instance):
                _validate_instance(item, item_schema, path + (idx,), errors)

    if isinstance(instance, dict):
        required = schema.get("required")
        if isinstance(required, list):
            for field in required:
                if isinstance(field, str) and field not in instance:
                    errors.append(f"{_format_path(path + (field,))}: required")
        properties = schema.get("properties")
        if isinstance(properties, dict):
            if schema.get("additionalProperties") is False:
                unknown = sorted(key for key in instance if key not in properties)
                for key in unknown:
                    errors.append(f"{_format_path(path + (key,))}: additional properties are not allowed")
            for field, field_schema in properties.items():
                if not isinstance(field, str) or not isinstance(field_schema, dict):
                    continue
                if field not in instance:
                    continue
                _validate_instance(instance[field], field_schema, path + (field,), errors)

    all_of = schema.get("allOf")
    if isinstance(all_of, list):
        for item in all_of:
            if isinstance(item, dict):
                _validate_instance(instance, item, path, errors)

    if_schema = schema.get("if")
    then_schema = schema.get("then")
    if isinstance(if_schema, dict) and isinstance(then_schema, dict) and _schema_matches(instance, if_schema):
        _validate_instance(instance, then_schema, path, errors)


def _schema_matches(instance: Any, schema: dict[str, Any]) -> bool:
    errors: list[str] = []
    _validate_instance(instance, schema, (), errors)
    return not errors


def _run_epistemic_gate(payload: dict[str, Any]) -> tuple[list[str], list[str]]:
    invalid: list[str] = []
    review: list[str] = []

    confidence = float(payload.get("confidence", 0.0) or 0.0)
    evidence_refs = payload.get("evidence_refs", [])
    evidence_count = len(evidence_refs) if isinstance(evidence_refs, list) else 0
    scope = str(payload.get("scope") or "")
    risk_level = str(((payload.get("risk_assessment") or {}) if isinstance(payload.get("risk_assessment"), dict) else {}).get("risk_level") or "")

    if confidence > 0.85 and evidence_count < 2:
        review.append("high confidence requires at least two evidence_refs")
    if scope == "global" and confidence < 0.80:
        review.append("global scope requires confidence >= 0.80")
    if not payload.get("success_criteria"):
        invalid.append("missing success_criteria")
    if risk_level in {"high", "critical"} and not str(payload.get("rollback_plan") or "").strip():
        invalid.append("high-risk changes require rollback_plan")

    for path, text in _iter_text_values(payload):
        if _contains_forbidden_instruction(text):
            invalid.append(f"{path}: contains forbidden instruction language")

    return invalid, review


def _run_policy_gate(payload: dict[str, Any]) -> tuple[str, list[str]]:
    review: list[str] = []

    bounded_action = payload.get("bounded_action") if isinstance(payload.get("bounded_action"), dict) else {}
    risk_assessment = payload.get("risk_assessment") if isinstance(payload.get("risk_assessment"), dict) else {}
    action_type = str(bounded_action.get("action_type") or "")
    risk_level = str(risk_assessment.get("risk_level") or "")
    safety_impact = str(risk_assessment.get("safety_impact") or "")
    confidence = float(payload.get("confidence", 0.0) or 0.0)
    scope = str(payload.get("scope") or "")
    change_type = str(payload.get("change_type") or "")
    evidence_refs = payload.get("evidence_refs", [])
    evidence_count = len(evidence_refs) if isinstance(evidence_refs, list) else 0

    if confidence < 0.45:
        review.append("confidence below 0.45 requires operator review")
    if risk_level in {"high", "critical"}:
        review.append("high-risk reflections require operator review")
    if safety_impact in {"meaningful", "requires_review"}:
        review.append("safety-impactful reflections require operator review")
    if scope == "global":
        review.append("global scope requires operator review")
    if change_type == "evaluation_only":
        review.append("evaluation_only proposals require operator review")
    if action_type == "propose_checklist_change":
        review.append("checklist changes require operator review")

    if action_type == "propose_memory_tag":
        if scope not in {"local", "session"}:
            review.append("memory tags auto-apply only for local or session scope")
        if risk_level != "low":
            review.append("memory tags auto-apply only for low-risk proposals")
        if safety_impact not in {"none", "limited"}:
            review.append("memory tags auto-apply only for none or limited safety impact")
        if confidence < 0.80:
            review.append("memory tags auto-apply only when confidence >= 0.80")
        if evidence_count < 1:
            review.append("memory tags auto-apply only with at least one evidence_ref")
        if not review:
            return "auto_apply_memory_tag", []
        return "review_required", review

    review.append("non-memory reflection proposals require operator review")
    return "review_required", review


def _build_memory_update(payload: dict[str, Any], *, run_id: str | None) -> dict[str, Any]:
    bounded_action = payload.get("bounded_action") if isinstance(payload.get("bounded_action"), dict) else {}
    target = str(bounded_action.get("target") or "reflection")
    key_fragment = _normalize_key_fragment(target)
    scope = str(payload.get("scope") or "session")
    ttl_seconds = 86400 if scope == "session" else 604800
    confidence = float(payload.get("confidence", 0.0) or 0.0)
    evidence_refs = payload.get("evidence_refs", [])
    return {
        "key": f"reflection:{run_id or 'unknown'}:{key_fragment}",
        "payload": {
            "summary": payload.get("summary"),
            "improvement_area": payload.get("improvement_area"),
            "target": target,
            "limit": bounded_action.get("limit"),
            "scope": scope,
            "expected_benefit": payload.get("expected_benefit"),
            "source": "self_reflection",
        },
        "options": {
            "memory_class": "working_memory",
            "ttl_seconds": ttl_seconds,
            "confidence": confidence,
            "promotion_state": "session_only",
            "evidence_refs": list(evidence_refs) if isinstance(evidence_refs, list) else [],
        },
    }


def _iter_text_values(value: Any, path: str = "<root>") -> list[tuple[str, str]]:
    if isinstance(value, str):
        return [(path, value)]
    if isinstance(value, list):
        pairs: list[tuple[str, str]] = []
        for idx, item in enumerate(value):
            pairs.extend(_iter_text_values(item, f"{path}[{idx}]"))
        return pairs
    if isinstance(value, dict):
        pairs = []
        for key, item in value.items():
            pairs.extend(_iter_text_values(item, f"{path}.{key}" if path != "<root>" else str(key)))
        return pairs
    return []


def _contains_forbidden_instruction(text: str) -> bool:
    lowered = " ".join(text.lower().split())
    for pattern in _FORBIDDEN_INSTRUCTION_PATTERNS:
        for match in pattern.finditer(lowered):
            prefix = lowered[max(0, match.start() - 24):match.start()]
            if _NEGATED_PATTERN.search(prefix):
                continue
            return True
    return False


def _normalize_key_fragment(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip())
    normalized = normalized.strip("-").lower()
    return normalized or "reflection"


def _format_error_path(path_parts: Any) -> str:
    path = tuple(path_parts)
    return _format_path(path)


def _format_path(path: tuple[Any, ...]) -> str:
    if not path:
        return "<root>"
    rendered = ""
    for part in path:
        if isinstance(part, int):
            rendered += f"[{part}]"
        else:
            if rendered:
                rendered += "."
            rendered += str(part)
    return rendered
