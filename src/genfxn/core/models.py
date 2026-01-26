from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QueryTag(str, Enum):
    TYPICAL = "typical"
    BOUNDARY = "boundary"
    COVERAGE = "coverage"
    ADVERSARIAL = "adversarial"


class Query(BaseModel):
    input: Any = Field(description="Function input value")
    output: Any = Field(description="Expected output value")
    tag: QueryTag = Field(description="Query category for analysis")


class Task(BaseModel):
    task_id: str = Field(description="Deterministic hash of spec")
    family: str = Field(description="Function family (piecewise, stateful)")
    spec: dict[str, Any] = Field(description="Full specification as dict")
    code: str = Field(description="Rendered Python function")
    queries: list[Query] = Field(description="Test queries with tags")
