from __future__ import annotations

from typing import Any


def _strip_yaml_comment(line: str) -> str:
    in_single = False
    in_double = False
    out: list[str] = []
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        if ch == "#" and not in_single and not in_double:
            break
        out.append(ch)
    return "".join(out).rstrip()


def _coerce_scalar(value: str) -> Any:
    if value.isdigit():
        return int(value)
    # Inline list: [a, b, c]
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        if not inner:
            return []
        return [_coerce_scalar(item.strip()) for item in inner.split(",") if item.strip()]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return value


def parse_simple_yaml(yaml_text: str) -> dict[str, Any]:
    """
    Parse a minimal YAML subset used by Antigravity compatibility configs.

    Supported:
    - mappings (`key: value`, `key:`)
    - lists (`- item`)
    - scalar bool/int/string values
    """
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(yaml_text)
        if isinstance(data, dict):
            return data
    except Exception:
        pass

    cleaned_lines: list[tuple[int, str]] = []
    for raw in yaml_text.splitlines():
        raw = _strip_yaml_comment(raw)
        if not raw.strip():
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        cleaned_lines.append((indent, raw.lstrip(" ")))

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(0, root)]

    for idx, (indent, line) in enumerate(cleaned_lines):
        while len(stack) > 1 and indent < stack[-1][0]:
            stack.pop()

        container = stack[-1][1]

        if line.startswith("- "):
            item = line[2:].strip()
            if not isinstance(container, list):
                raise ValueError("YAML structure error: list item in non-list container")
            container.append(_coerce_scalar(item))
            continue

        if ":" not in line:
            raise ValueError(f"YAML syntax error: {line}")

        key, rest = line.split(":", 1)
        key = key.strip()
        rest = rest.strip()

        if not isinstance(container, dict):
            raise ValueError("YAML structure error: key/value in non-dict container")

        if rest == "":
            nested: Any = {}
            if idx + 1 < len(cleaned_lines):
                next_indent, next_line = cleaned_lines[idx + 1]
                if next_indent > indent and next_line.startswith("- "):
                    nested = []
            container[key] = nested
            stack.append((indent + 2, container[key]))
        else:
            container[key] = _coerce_scalar(rest)

    return root
