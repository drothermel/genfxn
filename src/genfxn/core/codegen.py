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
    canonical = srsly.json_dumps(spec, sort_keys=True)
    hash_bytes = hashlib.sha256(canonical.encode()).digest()[:8]
    return f"{family}_{hash_bytes.hex()}"


def render_tests(func_name: str, queries: list[Query]) -> str:
    lines = []
    for i, q in enumerate(queries):
        input_repr = repr(q.input)
        output_repr = repr(q.output)
        msg = f"query {i} ({q.tag.value})"
        lines.append(f"assert {func_name}({input_repr}) == {output_repr}, {msg!r}")
    return "\n".join(lines)
