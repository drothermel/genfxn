from __future__ import annotations

import random
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Space(Protocol):
    """Common interface for all value spaces."""

    def validate_member(self, value: object) -> None:
        """Raise ValueError if value is not in the space."""

    def sample(self, n_samples: int, rng: random.Random) -> list[Any]:
        """Sample n_samples IID values from the space."""
