import dataclasses
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
    """Deduplicate queries by input, keeping first occurrence."""

    def _freeze(value: Any) -> Any:
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
            model_type = (
                f"{type(value).__module__}.{type(value).__qualname__}"
            )
            return ("__model__", model_type, _freeze(value.model_dump()))
        try:
            hash(value)
            return ("__hashable__", value)
        except TypeError:
            if hasattr(value, "__dict__"):
                obj_type = (
                    f"{type(value).__module__}.{type(value).__qualname__}"
                )
                return ("__object__", obj_type, _freeze(vars(value)))
            return ("__repr__", repr(value))

    seen: set[Any] = set()
    result: list[Query] = []
    for q in queries:
        key = _freeze(q.input)
        if key not in seen:
            seen.add(key)
            result.append(q)
    return result


class Task(BaseModel):
    task_id: str = Field(description="Deterministic hash of spec")
    family: str = Field(description="Function family (piecewise, stateful)")
    spec: dict[str, Any] = Field(description="Full specification as dict")
    code: str = Field(description="Rendered Python function")
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
