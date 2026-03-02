from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CategoricalValue = str | int | float | bool | None


class CategoricalParamSpace(BaseModel):
    """A categorical parameter space with a finite, ordered set of values."""

    kind: Literal["categorical"] = "categorical"
    values: tuple[CategoricalValue, ...] = Field(min_length=1)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("values")
    @classmethod
    def validate_values(
        cls,
        values: tuple[CategoricalValue, ...],
    ) -> tuple[CategoricalValue, ...]:
        seen: set[tuple[type[object], CategoricalValue]] = set()
        for value in values:
            if isinstance(value, float) and math.isnan(value):
                raise ValueError("values must not contain NaN")

            # Keep equality type-stable so bool/int collisions are not merged.
            key = (type(value), value)
            if key in seen:
                raise ValueError("values must be unique")
            seen.add(key)
        return values
