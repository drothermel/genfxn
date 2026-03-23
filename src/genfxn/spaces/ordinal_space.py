from __future__ import annotations

import random
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, ConfigDict

from genfxn.spaces.space import get_single_kwarg_value


class OrdinalSpace(BaseModel, ABC):
    """Space with values that have a meaningful ordering.

    Subclasses define what values exist and their order. Unlike
    CategoricalSpace, ordinal values have a concept of "between"
    and "neighbors" — position in the sequence matters.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    @abstractmethod
    def ordered_values(self) -> tuple[Any, ...]:
        """Return all values in order from low to high."""

    def validate_member(self, **kwargs: Any) -> None:
        value = get_single_kwarg_value(kwargs)
        if value not in self.ordered_values():
            raise ValueError(f"value {value!r} is not in this ordinal space")

    def sample(self, n_samples: int, rng: random.Random) -> list[Any]:
        if n_samples < 0:
            raise ValueError("n_samples must be >= 0")
        values = self.ordered_values()
        return rng.choices(values, k=n_samples)
