INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1
INT64_MIN = -(2**63)
INT64_MAX = 2**63 - 1


def java_string_literal(s: str) -> str:
    """Escape a string for use as a Java string literal."""
    escaped = (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
    return f'"{escaped}"'


def java_int_literal(value: int) -> str:
    """Render an int-typed Java literal expression for any Python int."""
    ivalue = int(value)
    if not (INT64_MIN <= ivalue <= INT64_MAX):
        raise ValueError(
            f"Value {ivalue} is out of signed 64-bit range for Java long"
        )
    if INT32_MIN <= ivalue <= INT32_MAX:
        return str(ivalue)
    return f"((int) {ivalue}L)"


def java_long_literal(value: int) -> str:
    """Render a long-typed Java literal for signed-64-bit values."""
    ivalue = int(value)
    if not (INT64_MIN <= ivalue <= INT64_MAX):
        raise ValueError(
            f"Value {ivalue} is out of signed 64-bit range for Java long"
        )
    if ivalue == INT64_MIN:
        return "Long.MIN_VALUE"
    return f"{ivalue}L"


def _java_literal(value: int) -> str:
    if INT32_MIN <= value <= INT32_MAX:
        return str(value)
    return java_long_literal(value)


def _regex_char_class_escape(chars: str) -> str:
    """Escape characters for use inside a Java regex character class [...]."""
    result: list[str] = []
    for c in chars:
        if c in ("]", "\\", "^", "-"):
            result.append(f"\\{c}")
        else:
            result.append(c)
    return "".join(result)
