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
    seen: set[Any] = set()
    result: list[Query] = []
    for q in queries:
        key = tuple(q.input) if isinstance(q.input, list) else q.input
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
    description: str = Field(description="Natural language description of the task")
