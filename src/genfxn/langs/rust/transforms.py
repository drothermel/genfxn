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
from genfxn.langs.rust._helpers import rust_i64_literal


def _i64_expr(value: int) -> str:
    literal = rust_i64_literal(value)
    if literal.endswith("i64"):
        return literal[:-3]
    return literal


def render_transform_rust(
    t: Transform,
    var: str = "x",
) -> str:
    """Render a numeric transform as a Rust expression."""
    match t:
        case TransformIdentity():
            return var
        case TransformAbs():
            return f"{var}.abs()"
        case TransformShift(offset=o):
            ro = _i64_expr(o)
            if o >= 0:
                return f"{var} + {ro}"
            return f"{var} - {_i64_expr(-o)}"
        case TransformClip(low=lo, high=hi):
            low = _i64_expr(lo)
            high = _i64_expr(hi)
            return f"{var}.max({low}).min({high})"
        case TransformNegate():
            return f"-{var}"
        case TransformScale(factor=f):
            return f"{var} * {_i64_expr(f)}"
        case TransformPipeline(steps=steps):
            expr = var
            for i, step in enumerate(steps):
                if i > 0:
                    expr = f"({expr})"
                expr = render_transform_rust(step, expr)
            return expr
        case _:
            raise ValueError(f"Unknown transform: {t}")
