import hashlib
from typing import Any

import srsly

from genfxn.core.models import Query


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
