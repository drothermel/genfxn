from __future__ import annotations

import random
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from genfxn.spaces.space import get_single_kwarg_value
from genfxn.types import DEFAULT_MAX_STR_LEN, DEFAULT_MIN_STR_LEN


class UniformIntSpace(BaseModel):
    """Uniform integer space over an inclusive range."""

    kind: Literal["uniform_int"] = "uniform_int"
    low: int = Field(default=DEFAULT_MIN_STR_LEN)
    high: int = Field(default=DEFAULT_MAX_STR_LEN)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_bounds(self) -> UniformIntSpace:
        if self.high < self.low:
            raise ValueError(f"high ({self.high}) must be >= low ({self.low})")
        return self

    def validate_member(self, **kwargs: Any) -> None:
        value = get_single_kwarg_value(kwargs)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("value must be an int")
        if not (self.low <= value <= self.high):
            raise ValueError(
                f"value {value} must be in [{self.low}, {self.high}]"
            )

    def sample(self, n_samples: int, rng: random.Random) -> list[int]:
        if n_samples < 0:
            raise ValueError("n_samples must be >= 0")
        return [rng.randint(self.low, self.high) for _ in range(n_samples)]
