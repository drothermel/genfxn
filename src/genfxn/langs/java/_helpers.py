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


def _regex_char_class_escape(chars: str) -> str:
    """Escape characters for use inside a Java regex character class [...]."""
    result: list[str] = []
    for c in chars:
        if c in ("]", "\\", "^", "-"):
            result.append(f"\\{c}")
        else:
            result.append(c)
    return "".join(result)
