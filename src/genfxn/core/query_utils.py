from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def find_satisfying(
    generate: Callable[[], T],
    predicate: Callable[[T], bool],
    max_attempts: int = 100,
) -> T | None:
    """Try up to max_attempts to generate a value satisfying predicate.

    Returns the first satisfying value, or None if none found.
    """
    for _ in range(max_attempts):
        try:
            value = generate()
            if predicate(value):
                return value
        except Exception:
            continue
    return None
