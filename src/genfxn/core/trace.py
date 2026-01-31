from typing import Any

from pydantic import BaseModel, Field


class TraceStep(BaseModel):
    """Single step in the generation trace."""

    step: str = Field(description="Step identifier")
    choice: str = Field(description="Human-readable description of choice")
    value: Any = Field(description="The actual sampled value")


class GenerationTrace(BaseModel):
    """Complete trace of a generation run."""

    family: str = Field(description="Function family (piecewise, stateful)")
    steps: list[TraceStep] = Field(
        default_factory=list, description="Ordered list of sampling steps"
    )
