from __future__ import annotations

import random
from typing import Any, Protocol, runtime_checkable


def get_single_kwarg_value(kwargs: dict[str, Any]) -> object:
    if len(kwargs) != 1:
        raise ValueError("validate_member expects exactly one keyword argument")
    return next(iter(kwargs.values()))


@runtime_checkable
class Space(Protocol):
    """Common interface for all value spaces."""

    def validate_member(self, **kwargs: Any) -> None:
        """Raise ValueError if value is not in the space."""

    def sample(self, n_samples: int, rng: random.Random) -> list[Any]:
        """Sample n_samples IID values from the space."""
