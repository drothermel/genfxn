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
    *,
    int32_wrap: bool = False,
) -> str:
    """Render a numeric transform as a Rust expression."""
    if int32_wrap:
        match t:
            case TransformIdentity():
                return f"i32_wrap({var})"
            case TransformAbs():
                return f"i32_abs({var})"
            case TransformShift(offset=o):
                return f"i32_add({var}, {_i64_expr(o)})"
            case TransformClip(low=lo, high=hi):
                low = _i64_expr(lo)
                high = _i64_expr(hi)
                return f"i32_clip({var}, {low}, {high})"
            case TransformNegate():
                return f"i32_neg({var})"
            case TransformScale(factor=f):
                return f"i32_mul({var}, {_i64_expr(f)})"
            case TransformPipeline(steps=steps):
                expr = var
                for i, step in enumerate(steps):
                    if i > 0:
                        expr = f"({expr})"
                    expr = render_transform_rust(
                        step, expr, int32_wrap=True
                    )
                return expr
            case _:
                raise ValueError(f"Unknown transform: {t}")

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
                expr = render_transform_rust(step, expr, int32_wrap=False)
            return expr
        case _:
            raise ValueError(f"Unknown transform: {t}")
