from __future__ import annotations

import math
import random
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

ConstantValue = str | int | float | bool | None


class ConstantSpace(BaseModel):
    """A singleton value space."""

    kind: Literal["constant"] = "constant"
    value: ConstantValue

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: ConstantValue) -> ConstantValue:
        if isinstance(value, float) and math.isnan(value):
            raise ValueError("value must not be NaN")
        return value

    def validate_member(self, candidate: object) -> None:
        if type(candidate) is type(self.value) and candidate == self.value:
            return
        raise ValueError(
            f"value {candidate!r} is not equal to constant {self.value!r}"
        )

    def sample(self, n_samples: int, rng: random.Random) -> list[ConstantValue]:
        del rng
        if n_samples < 0:
            raise ValueError("n_samples must be >= 0")
        return [self.value for _ in range(n_samples)]
