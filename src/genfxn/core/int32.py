"""Helpers for Java-style signed 32-bit integer arithmetic."""

INT32_BITS = 32
INT32_MASK = (1 << INT32_BITS) - 1
INT32_MIN = -(1 << (INT32_BITS - 1))


def wrap_i32(value: int) -> int:
    """Wrap an integer into signed 32-bit range."""
    return ((value + (1 << (INT32_BITS - 1))) & INT32_MASK) + INT32_MIN


def i32_add(lhs: int, rhs: int) -> int:
    return wrap_i32(wrap_i32(lhs) + wrap_i32(rhs))


def i32_sub(lhs: int, rhs: int) -> int:
    return wrap_i32(wrap_i32(lhs) - wrap_i32(rhs))


def i32_mul(lhs: int, rhs: int) -> int:
    return wrap_i32(wrap_i32(lhs) * wrap_i32(rhs))


def i32_neg(value: int) -> int:
    return wrap_i32(-wrap_i32(value))


def i32_abs(value: int) -> int:
    value_i32 = wrap_i32(value)
    if value_i32 == INT32_MIN:
        return INT32_MIN
    return abs(value_i32)
