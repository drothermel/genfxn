INT64_MIN = -(1 << 63)
INT64_MAX = (1 << 63) - 1

type IntRange = tuple[int, int]


def fits_signed_i64(bounds: IntRange) -> bool:
    lo, hi = bounds
    return lo >= INT64_MIN and hi <= INT64_MAX


def add_ranges(left: IntRange, right: IntRange) -> IntRange:
    return (left[0] + right[0], left[1] + right[1])


def mul_ranges(left: IntRange, right: IntRange) -> IntRange:
    l_lo, l_hi = left
    r_lo, r_hi = right
    products = (
        l_lo * r_lo,
        l_lo * r_hi,
        l_hi * r_lo,
        l_hi * r_hi,
    )
    return (min(products), max(products))


def square_range(values: IntRange) -> IntRange:
    lo, hi = values
    if lo <= 0 <= hi:
        min_sq = 0
    else:
        min_sq = min(lo * lo, hi * hi)
    max_sq = max(lo * lo, hi * hi)
    return (min_sq, max_sq)


def abs_range(values: IntRange) -> IntRange:
    lo, hi = values
    lo_abs = abs(lo)
    hi_abs = abs(hi)
    if lo <= 0 <= hi:
        min_abs = 0
    else:
        min_abs = min(lo_abs, hi_abs)
    return (min_abs, max(lo_abs, hi_abs))


def neg_range(values: IntRange) -> IntRange:
    lo, hi = values
    return (-hi, -lo)


def max_abs(values: IntRange) -> int:
    lo, hi = values
    return max(abs(lo), abs(hi))
