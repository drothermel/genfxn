from __future__ import annotations

import math
import random
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

CategoricalValue = str | int | float | bool | None


class CategoricalSpace(BaseModel):
    """A finite, ordered categorical value space."""

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

    def validate_member(self, value: object) -> None:
        for candidate in self.values:
            if type(candidate) is type(value) and candidate == value:
                return
        raise ValueError(f"value {value!r} is not a member of this space")

    def sample(
        self, n_samples: int, rng: random.Random
    ) -> list[CategoricalValue]:
        if n_samples < 0:
            raise ValueError("n_samples must be >= 0")

        return rng.choices(self.values, k=n_samples)
