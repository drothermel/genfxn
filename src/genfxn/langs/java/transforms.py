from genfxn.core.transforms import (
    Transform,
    TransformAbs,
    TransformClip,
    TransformIdentity,
    TransformNegate,
    TransformPipeline,
    TransformScale,
    TransformShift,
)
from genfxn.langs.java._helpers import INT32_MAX, INT32_MIN, java_long_literal


def _java_literal(value: int) -> str:
    if INT32_MIN <= value <= INT32_MAX:
        return str(value)
    return java_long_literal(value)


def render_transform_java(t: Transform, var: str = "x") -> str:
    """Render a numeric transform as a Java expression."""
    match t:
        case TransformIdentity():
            return var
        case TransformAbs():
            return f"Math.abs({var})"
        case TransformShift(offset=o):
            if o >= 0:
                return f"{var} + {_java_literal(o)}"
            return f"{var} - {_java_literal(-o)}"
        case TransformClip(low=lo, high=hi):
            low = _java_literal(lo)
            high = _java_literal(hi)
            return f"Math.max({low}, Math.min({high}, {var}))"
        case TransformNegate():
            return f"-{var}"
        case TransformScale(factor=f):
            return f"{var} * {_java_literal(f)}"
        case TransformPipeline(steps=steps):
            expr = var
            for i, step in enumerate(steps):
                if i > 0:
                    expr = f"({expr})"
                expr = render_transform_java(step, expr)
            return expr
        case _:
            raise ValueError(f"Unknown transform: {t}")
