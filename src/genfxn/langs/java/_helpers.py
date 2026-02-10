INT32_MIN = -(2**31)
INT32_MAX = 2**31 - 1


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
    if INT32_MIN <= ivalue <= INT32_MAX:
        return str(ivalue)
    return f"((int) {ivalue}L)"


def _regex_char_class_escape(chars: str) -> str:
    """Escape characters for use inside a Java regex character class [...]."""
    result: list[str] = []
    for c in chars:
        if c in ("]", "\\", "^", "-"):
            result.append(f"\\{c}")
        else:
            result.append(c)
    return "".join(result)
