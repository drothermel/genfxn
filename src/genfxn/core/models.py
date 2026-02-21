import dataclasses
import math
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

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


def _freeze_query_value(value: Any) -> Any:
    def _freeze_scalar(scalar: Any) -> tuple[str, str, Any]:
        scalar_type = type(scalar)
        type_name = f"{scalar_type.__module__}.{scalar_type.__qualname__}"
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
            (_freeze_query_value(key), _freeze_query_value(val))
            for key, val in value.items()
        ]
        return (
            "__dict__",
            tuple(sorted(frozen_items, key=lambda pair: _sort_key(pair[0]))),
        )
    if isinstance(value, list):
        return (
            "__list__",
            tuple(_freeze_query_value(item) for item in value),
        )
    if isinstance(value, tuple):
        return (
            "__tuple__",
            tuple(_freeze_query_value(item) for item in value),
        )
    if isinstance(value, set):
        frozen_items = [_freeze_query_value(item) for item in value]
        return (
            "__set__",
            tuple(sorted(frozen_items, key=_sort_key)),
        )
    if isinstance(value, frozenset):
        frozen_items = [_freeze_query_value(item) for item in value]
        return (
            "__frozenset__",
            tuple(sorted(frozen_items, key=_sort_key)),
        )
    if dataclasses.is_dataclass(value):
        return ("__dataclass__", _freeze_query_value(dataclasses.asdict(value)))
    if hasattr(value, "model_dump") and callable(value.model_dump):
        model_type = f"{type(value).__module__}.{type(value).__qualname__}"
        return (
            "__model__",
            model_type,
            _freeze_query_value(value.model_dump()),
        )
    value_type = f"{type(value).__module__}.{type(value).__qualname__}"
    try:
        hash(value)
        return ("__hashable__", value_type, value)
    except TypeError:
        if hasattr(value, "__dict__"):
            try:
                return (
                    "__object__",
                    value_type,
                    _freeze_query_value(vars(value)),
                )
            except TypeError:
                pass
        return ("__repr__", value_type, _safe_repr(value))


def _query_outputs_equal(left: Any, right: Any) -> bool:
    if (
        isinstance(left, float)
        and isinstance(right, float)
        and math.isnan(left)
        and math.isnan(right)
    ):
        return True

    if type(left) is not type(right):
        return False

    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return False
        return all(
            _query_outputs_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=False)
        )

    if isinstance(left, tuple) and isinstance(right, tuple):
        if len(left) != len(right):
            return False
        return all(
            _query_outputs_equal(left_item, right_item)
            for left_item, right_item in zip(left, right, strict=False)
        )

    if isinstance(left, dict | set | frozenset):
        return _freeze_query_value(left) == _freeze_query_value(right)

    return left == right


def dedupe_queries(queries: list[Query]) -> list[Query]:
    """Deduplicate queries by input, preserving highest-value tag evidence."""

    tag_priority = {
        QueryTag.TYPICAL: 0,
        QueryTag.BOUNDARY: 1,
        QueryTag.ADVERSARIAL: 2,
        QueryTag.COVERAGE: 3,
    }

    seen_idx: dict[Any, int] = {}
    result: list[Query] = []
    for q in queries:
        key = _freeze_query_value(q.input)
        idx = seen_idx.get(key)
        if idx is None:
            seen_idx[key] = len(result)
            result.append(q)
            continue

        existing = result[idx]
        if not _query_outputs_equal(existing.output, q.output):
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


def dedupe_queries_per_tag_input(queries: list[Query]) -> list[Query]:
    """Deduplicate queries by `(tag, input)` while preserving stable order.

    This contract intentionally allows the same input to appear across
    different tags, which keeps tag coverage feasible on compact domains.
    """

    seen_idx: dict[tuple[QueryTag, Any], int] = {}
    result: list[Query] = []
    for query in queries:
        key = (query.tag, _freeze_query_value(query.input))
        idx = seen_idx.get(key)
        if idx is None:
            seen_idx[key] = len(result)
            result.append(query)
            continue

        existing = result[idx]
        if not _query_outputs_equal(existing.output, query.output):
            raise ValueError(
                "Duplicate query tag+input has conflicting outputs: "
                f"{existing.tag.value}:{existing.input!r} -> "
                f"{existing.output!r} vs {query.output!r}"
            )

    return result


class Task(BaseModel):
    model_config = ConfigDict(extra="forbid")

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
    description: str = Field(
        description="Natural language description of the task"
    )
