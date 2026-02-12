import random


def sample_sequence(
    *,
    length_range: tuple[int, int],
    value_range: tuple[int, int],
    rng: random.Random,
) -> list[int]:
    n = rng.randint(length_range[0], length_range[1])
    return [rng.randint(value_range[0], value_range[1]) for _ in range(n)]
