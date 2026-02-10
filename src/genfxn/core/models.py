import dataclasses
import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from genfxn.core.trace import GenerationTrace


class QueryTag(str, Enum):
    TYPICAL = "typical"
    BOUNDARY = "boundary"
    COVERAGE = "coverage"
    ADVERSARIAL = "adversarial"


class Query(BaseModel):
    input: Any = Field(description="Function input value")
    output: Any = Field(description="Expected output value")
    tag: QueryTag = Field(description="Query category for analysis")


def dedupe_queries(queries: list[Query]) -> list[Query]:
    """Deduplicate queries by input, preserving highest-value tag evidence."""

    def _freeze(value: Any) -> Any:
        def _freeze_scalar(scalar: Any) -> tuple[str, str, Any]:
            scalar_type = type(scalar)
            type_name = (
                f"{scalar_type.__module__}.{scalar_type.__qualname__}"
            )
            if isinstance(scalar, float) and math.isnan(scalar):
                return ("__scalar__", type_name, "__nan__")
            return ("__scalar__", type_name, scalar)

        # Fast paths for common primitive/query container types.
        if type(value) in {int, str, bool, float, type(None)}:
            return _freeze_scalar(value)
        if isinstance(value, list) and all(
            type(item) in {int, str, bool, float, type(None)} for item in value
        ):
            return (
                "__flat_list__",
                tuple(_freeze_scalar(item) for item in value),
            )
        if isinstance(value, tuple) and all(
            type(item) in {int, str, bool, float, type(None)} for item in value
        ):
            return (
                "__flat_tuple__",
                tuple(_freeze_scalar(item) for item in value),
            )

        def _safe_repr(v: Any) -> str:
            try:
                rep = repr(v)
            except Exception as exc:  # pragma: no cover - defensive fallback
                return f"<repr_error:{type(exc).__name__}>"
            if not isinstance(rep, str):
                return f"<non_str_repr:{type(rep).__name__}>"
            return rep

        def _sort_key(v: Any) -> tuple[str, str, str]:
            typ = type(v)
            return (
                typ.__module__,
                typ.__qualname__,
                _safe_repr(v),
            )

        if isinstance(value, dict):
            frozen_items = [
                (_freeze(key), _freeze(val)) for key, val in value.items()
            ]
            return (
                "__dict__",
                tuple(
                    sorted(frozen_items, key=lambda pair: _sort_key(pair[0]))
                ),
            )
        if isinstance(value, list):
            return ("__list__", tuple(_freeze(item) for item in value))
        if isinstance(value, tuple):
            return ("__tuple__", tuple(_freeze(item) for item in value))
        if isinstance(value, set):
            frozen_items = [_freeze(item) for item in value]
            return (
                "__set__",
                tuple(sorted(frozen_items, key=_sort_key)),
            )
        if dataclasses.is_dataclass(value):
            return ("__dataclass__", _freeze(dataclasses.asdict(value)))
        if hasattr(value, "model_dump") and callable(value.model_dump):
            model_type = f"{type(value).__module__}.{type(value).__qualname__}"
            return ("__model__", model_type, _freeze(value.model_dump()))
        value_type = f"{type(value).__module__}.{type(value).__qualname__}"
        try:
            hash(value)
            return ("__hashable__", value_type, value)
        except TypeError:
            if hasattr(value, "__dict__"):
                try:
                    return ("__object__", value_type, _freeze(vars(value)))
                except TypeError:
                    pass
            return ("__repr__", value_type, _safe_repr(value))

    def _outputs_equal(left: Any, right: Any) -> bool:
        if (
            isinstance(left, float)
            and isinstance(right, float)
            and math.isnan(left)
            and math.isnan(right)
        ):
            return True
        return left == right

    tag_priority = {
        QueryTag.TYPICAL: 0,
        QueryTag.BOUNDARY: 1,
        QueryTag.ADVERSARIAL: 2,
        QueryTag.COVERAGE: 3,
    }

    seen_idx: dict[Any, int] = {}
    result: list[Query] = []
    for q in queries:
        key = _freeze(q.input)
        idx = seen_idx.get(key)
        if idx is None:
            seen_idx[key] = len(result)
            result.append(q)
            continue

        existing = result[idx]
        if not _outputs_equal(existing.output, q.output):
            raise ValueError(
                "Duplicate query input has conflicting outputs: "
                f"{existing.input!r} -> {existing.output!r} vs {q.output!r}"
            )

        if tag_priority[q.tag] > tag_priority[existing.tag]:
            result[idx] = Query(
                input=existing.input,
                output=existing.output,
                tag=q.tag,
            )
    return result


class Task(BaseModel):
    task_id: str = Field(description="Deterministic hash of spec")
    family: str = Field(description="Function family (piecewise, stateful)")
    spec: dict[str, Any] = Field(description="Full specification as dict")
    code: str | dict[str, str] = Field(
        description="Rendered function code (single language or map)"
    )
    queries: list[Query] = Field(description="Test queries with tags")
    trace: GenerationTrace | None = Field(
        default=None, description="Optional generation trace for debugging"
    )
    axes: dict[str, Any] | None = Field(
        default=None, description="Axes/ranges used for sampling"
    )
    difficulty: int | None = Field(
        default=None,
        ge=1,
        le=5,
        description="Difficulty score (1-5)",
    )
    description: str = Field(
        description="Natural language description of the task"
    )
