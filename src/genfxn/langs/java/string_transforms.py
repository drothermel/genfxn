from genfxn.core.string_transforms import (
    StringTransform,
    StringTransformAppend,
    StringTransformCapitalize,
    StringTransformIdentity,
    StringTransformLowercase,
    StringTransformPipeline,
    StringTransformPrepend,
    StringTransformReplace,
    StringTransformReverse,
    StringTransformStrip,
    StringTransformSwapcase,
    StringTransformUppercase,
)
from genfxn.langs.java._helpers import (
    _regex_char_class_escape,
    java_string_literal,
)


def render_string_transform_java(t: StringTransform, var: str = "s") -> str:
    """Render a string transform as a Java expression."""
    match t:
        case StringTransformIdentity():
            return var
        case StringTransformLowercase():
            return f"{var}.toLowerCase()"
        case StringTransformUppercase():
            return f"{var}.toUpperCase()"
        case StringTransformCapitalize():
            return (
                f"{var}.isEmpty() ? {var} : "
                f"{var}.substring(0, 1).toUpperCase() + "
                f"{var}.substring(1).toLowerCase()"
            )
        case StringTransformSwapcase():
            return (
                f"{var}.codePoints()"
                ".map(c -> Character.isUpperCase(c) ? "
                "Character.toLowerCase(c) : Character.toUpperCase(c))"
                ".collect(StringBuilder::new, "
                "StringBuilder::appendCodePoint, StringBuilder::append)"
                ".toString()"
            )
        case StringTransformReverse():
            return f"new StringBuilder({var}).reverse().toString()"
        case StringTransformReplace(old=old, new=new):
            return (
                f"{var}.replace("
                f"{java_string_literal(old)}, "
                f"{java_string_literal(new)})"
            )
        case StringTransformStrip(chars=chars):
            if chars is None:
                return f"{var}.strip()"
            escaped = _regex_char_class_escape(chars)
            pattern = f"^[{escaped}]+|[{escaped}]+$"
            return f'{var}.replaceAll({java_string_literal(pattern)}, "")'
        case StringTransformPrepend(prefix=prefix):
            return f"{java_string_literal(prefix)} + {var}"
        case StringTransformAppend(suffix=suffix):
            return f"{var} + {java_string_literal(suffix)}"
        case StringTransformPipeline(steps=steps):
            expr = var
            for i, step in enumerate(steps):
                if i > 0:
                    expr = f"({expr})"
                expr = render_string_transform_java(step, expr)
            return expr
        case _:
            raise ValueError(f"Unknown string transform: {t}")
