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
from genfxn.langs.java._helpers import java_int_literal


def render_transform_java(t: Transform, var: str = "x") -> str:
    """Render a numeric transform as a Java expression."""
    match t:
        case TransformIdentity():
            return var
        case TransformAbs():
            return f"Math.abs({var})"
        case TransformShift(offset=o):
            if o >= 0:
                return f"{var} + {java_int_literal(o)}"
            return f"{var} - {java_int_literal(-o)}"
        case TransformClip(low=lo, high=hi):
            low = java_int_literal(lo)
            high = java_int_literal(hi)
            return f"Math.max({low}, Math.min({high}, {var}))"
        case TransformNegate():
            return f"-{var}"
        case TransformScale(factor=f):
            return f"{var} * {java_int_literal(f)}"
        case TransformPipeline(steps=steps):
            expr = var
            for i, step in enumerate(steps):
                if i > 0:
                    expr = f"({expr})"
                expr = render_transform_java(step, expr)
            return expr
        case _:
            raise ValueError(f"Unknown transform: {t}")
