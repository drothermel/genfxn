import hashlib
from typing import Any

import srsly

from genfxn.core.models import Query


def get_spec_value(spec: dict[str, Any], path: str) -> Any:
    """Access nested spec value by dot-path (e.g., 'predicate.kind').

    Returns None if path doesn't exist.
    """
    keys = path.split(".")
    value: Any = spec
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        elif isinstance(value, list) and key.isdigit():
            idx = int(key)
            value = value[idx] if idx < len(value) else None
        else:
            return None
        if value is None:
            return None
    return value


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
    lines = []
    for i, q in enumerate(queries):
        input_repr = repr(q.input)
        output_repr = repr(q.output)
        msg = f"query {i} ({q.tag.value})"
        lines.append(
            f"assert {func_name}({input_repr}) == {output_repr}, {msg!r}"
        )
    return "\n".join(lines)
