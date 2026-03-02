INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


def rust_string_literal(s: str) -> str:
    """Escape a string for use as a Rust string literal."""
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def rust_i64_literal(value: int) -> str:
    """Render an i64-typed Rust literal for signed-64-bit values."""
    ivalue = int(value)
    if not (INT64_MIN <= ivalue <= INT64_MAX):
        raise ValueError(
            f"Value {ivalue} is out of signed 64-bit range for Rust i64"
        )
    if ivalue == INT64_MIN:
        return "i64::MIN"
    return f"{ivalue}i64"


def _i64_expr(value: int) -> str:
    literal = rust_i64_literal(value)
    if literal.endswith("i64"):
        return literal[:-3]
    return literal
