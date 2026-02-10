import hashlib
import math
from typing import Any

import srsly

from genfxn.core.models import Query


def _lookup_spec_path(spec: dict[str, Any], path: str) -> tuple[bool, Any]:
    """Resolve a dot-path in a spec and preserve explicit None leaf values."""
    keys = path.split(".")
    value: Any = spec
    for key in keys:
        if isinstance(value, dict):
            if key not in value:
                return False, None
            value = value[key]
        elif isinstance(value, list) and key.isdigit():
            idx = int(key)
            if idx >= len(value):
                return False, None
            value = value[idx]
        else:
            return False, None
    return True, value


def get_spec_value(spec: dict[str, Any], path: str) -> Any:
    """Access nested spec value by dot-path (e.g., 'predicate.kind').

    Returns None if path doesn't exist.
    """
    found, value = _lookup_spec_path(spec, path)
    if not found:
        return None
    return value


def has_spec_value(spec: dict[str, Any], path: str) -> bool:
    """Return True when a dot-path exists, even if its value is None."""
    found, _ = _lookup_spec_path(spec, path)
    return found


def task_id_from_spec(family: str, spec: dict[str, Any]) -> str:
    canonical = srsly.json_dumps(_canonicalize_for_hash(spec), sort_keys=True)
    hash_bytes = hashlib.sha256(canonical.encode()).digest()[:8]
    return f"{family}_{hash_bytes.hex()}"


def _canonicalize_for_hash(value: Any) -> Any:
    """Convert values into a deterministic JSON-serializable form."""
    if isinstance(value, dict):
        return {
            str(k): _canonicalize_for_hash(v)
            for k, v in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, list | tuple):
        return [_canonicalize_for_hash(v) for v in value]
    if isinstance(value, set | frozenset):
        items = [_canonicalize_for_hash(v) for v in value]
        return sorted(items, key=lambda item: srsly.json_dumps(item))
    return value


def render_tests(func_name: str, queries: list[Query]) -> str:
    def _render_python_literal(value: Any) -> str:
        if isinstance(value, float):
            if math.isnan(value):
                return 'float("nan")'
            if math.isinf(value):
                if value > 0:
                    return 'float("inf")'
                return 'float("-inf")'
            return repr(value)
        if isinstance(value, list):
            return (
                "["
                + ", ".join(_render_python_literal(item) for item in value)
                + "]"
            )
        if isinstance(value, tuple):
            inner = ", ".join(_render_python_literal(item) for item in value)
            if len(value) == 1:
                inner += ","
            return f"({inner})"
        if isinstance(value, dict):
            parts = [
                f"{_render_python_literal(key)}: "
                f"{_render_python_literal(item)}"
                for key, item in value.items()
            ]
            return "{" + ", ".join(parts) + "}"
        if isinstance(value, set):
            if not value:
                return "set()"
            return (
                "{"
                + ", ".join(_render_python_literal(item) for item in value)
                + "}"
            )
        if isinstance(value, frozenset):
            if not value:
                return "frozenset()"
            rendered_items = ", ".join(
                _render_python_literal(item) for item in value
            )
            return f"frozenset({{{rendered_items}}})"
        return repr(value)

    lines = []
    for i, q in enumerate(queries):
        input_repr = _render_python_literal(q.input)
        output_repr = _render_python_literal(q.output)
        msg = f"query {i} ({q.tag.value})"
        lines.append(
            f"assert {func_name}({input_repr}) == {output_repr}, {msg!r}"
        )
    return "\n".join(lines)
