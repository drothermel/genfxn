import random
from typing import TypeVar

T = TypeVar("T")


def intersect_ranges(
    a: tuple[int, int], b: tuple[int, int]
) -> tuple[int, int] | None:
    """Return intersection of two inclusive ordered ranges.

    Raises ValueError when either input range is malformed (low > high).
    """
    if a[0] > a[1]:
        raise ValueError(
            f"range a is malformed: low ({a[0]}) must be <= high ({a[1]})"
        )
    if b[0] > b[1]:
        raise ValueError(
            f"range b is malformed: low ({b[0]}) must be <= high ({b[1]})"
        )
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


def sample_probability(
    prob_range: tuple[float, float],
    rng: random.Random,
) -> float:
    """Sample uniformly from an inclusive probability range."""
    return rng.uniform(prob_range[0], prob_range[1])
