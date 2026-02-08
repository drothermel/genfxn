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
from genfxn.langs.rust._helpers import rust_string_literal


def render_string_transform_rust(t: StringTransform, var: str = "s") -> str:
    """Render a string transform as a Rust expression."""
    match t:
        case StringTransformIdentity():
            return f"{var}.to_string()"
        case StringTransformLowercase():
            return f"{var}.to_lowercase()"
        case StringTransformUppercase():
            return f"{var}.to_uppercase()"
        case StringTransformCapitalize():
            return (
                f"{{ let _s = {var}; let mut _chars = _s.chars(); "
                "match _chars.next() "
                "{ None => String::new(), "
                "Some(first) => first.to_uppercase().collect::<String>() + "
                "&_chars.as_str().to_lowercase(), } }"
            )
        case StringTransformSwapcase():
            return (
                f"{var}.chars().flat_map(|c| if c.is_uppercase() "
                "{ c.to_lowercase().collect::<Vec<char>>() } else "
                "{ c.to_uppercase().collect::<Vec<char>>() })"
                ".collect::<String>()"
            )
        case StringTransformReverse():
            return f"{var}.chars().rev().collect::<String>()"
        case StringTransformReplace(old=old, new=new):
            return (
                f"{var}.replace("
                f"{rust_string_literal(old)}, "
                f"{rust_string_literal(new)})"
            )
        case StringTransformStrip(chars=chars):
            if chars is None:
                return f"{var}.trim().to_string()"
            lit_chars = rust_string_literal(chars)
            return (
                f"{var}.trim_matches(|c: char| {lit_chars}.contains(c))"
                ".to_string()"
            )
        case StringTransformPrepend(prefix=prefix):
            return f'format!("{{}}{{}}", {rust_string_literal(prefix)}, {var})'
        case StringTransformAppend(suffix=suffix):
            return f'format!("{{}}{{}}", {var}, {rust_string_literal(suffix)})'
        case StringTransformPipeline(steps=steps):
            expr = var
            for i, step in enumerate(steps):
                if i > 0:
                    expr = f"({expr})"
                expr = render_string_transform_rust(step, expr)
            return expr
        case _:
            raise ValueError(f"Unknown string transform: {t}")
