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
                return f"i32_add({var}, {o})"
            case TransformClip(low=lo, high=hi):
                return f"i32_clip({var}, {lo}, {hi})"
            case TransformNegate():
                return f"i32_neg({var})"
            case TransformScale(factor=f):
                return f"i32_mul({var}, {f})"
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
            if o >= 0:
                return f"{var} + {o}"
            return f"{var} - {-o}"
        case TransformClip(low=lo, high=hi):
            return f"{var}.max({lo}).min({hi})"
        case TransformNegate():
            return f"-{var}"
        case TransformScale(factor=f):
            return f"{var} * {f}"
        case TransformPipeline(steps=steps):
            expr = var
            for i, step in enumerate(steps):
                if i > 0:
                    expr = f"({expr})"
                expr = render_transform_rust(step, expr, int32_wrap=False)
            return expr
        case _:
            raise ValueError(f"Unknown transform: {t}")
