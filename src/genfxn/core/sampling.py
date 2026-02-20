import random
from typing import TypeVar

T = TypeVar("T")


def intersect_ranges(
    a: tuple[int, int], b: tuple[int, int]
) -> tuple[int, int] | None:
    """Return the intersection of two inclusive ranges, or None if disjoint."""
    lo = max(a[0], b[0])
    hi = min(a[1], b[1])
    if lo > hi:
        return None
    return (lo, hi)


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
