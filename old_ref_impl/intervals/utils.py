def _clamp(value: int, lo: int, hi: int) -> int:
    return min(max(value, lo), hi)
