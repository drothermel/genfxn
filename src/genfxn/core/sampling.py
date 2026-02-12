import random
from typing import TypeVar

T = TypeVar("T")


def pick_from_preferred(
    available: list[T],
    preferred: list[T],
    rng: random.Random,
) -> T:
    if not available:
        raise ValueError("available must contain at least one item")
    preferred_available = [item for item in preferred if item in available]
    if preferred_available:
        return rng.choice(preferred_available)
    return rng.choice(available)
