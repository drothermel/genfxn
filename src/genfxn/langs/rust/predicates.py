from genfxn.core.predicates import (
    Predicate,
    PredicateAnd,
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateInSet,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateNot,
    PredicateOdd,
    PredicateOr,
)


def render_predicate_rust(
    pred: Predicate,
    var: str = "x",
    *,
    int32_wrap: bool = False,
) -> str:
    """Render a numeric predicate as a Rust boolean expression."""
    match pred:
        case PredicateEven():
            if int32_wrap:
                return f"i32_wrap({var}) % 2 == 0"
            return f"{var} % 2 == 0"
        case PredicateOdd():
            if int32_wrap:
                return f"i32_wrap({var}) % 2 != 0"
            return f"{var} % 2 != 0"
        case PredicateLt(value=v):
            if int32_wrap:
                return f"i32_wrap({var}) < i32_wrap({v})"
            return f"{var} < {v}"
        case PredicateLe(value=v):
            if int32_wrap:
                return f"i32_wrap({var}) <= i32_wrap({v})"
            return f"{var} <= {v}"
        case PredicateGt(value=v):
            if int32_wrap:
                return f"i32_wrap({var}) > i32_wrap({v})"
            return f"{var} > {v}"
        case PredicateGe(value=v):
            if int32_wrap:
                return f"i32_wrap({var}) >= i32_wrap({v})"
            return f"{var} >= {v}"
        case PredicateModEq(divisor=d, remainder=r):
            if int32_wrap:
                return f"i32_wrap({var}).rem_euclid({d}) == i32_wrap({r})"
            return f"{var}.rem_euclid({d}) == {r}"
        case PredicateInSet(values=vals):
            if not vals:
                return "false"
            if int32_wrap:
                items = ", ".join(
                    f"i32_wrap({v})" for v in sorted(vals)
                )
                return f"[{items}].contains(&i32_wrap({var}))"
            items = ", ".join(str(v) for v in sorted(vals))
            return f"[{items}].contains(&{var})"
        case PredicateNot(operand=op):
            return (
                f"!({render_predicate_rust(op, var, int32_wrap=int32_wrap)})"
            )
        case PredicateAnd(operands=ops):
            parts = [
                render_predicate_rust(op, var, int32_wrap=int32_wrap)
                for op in ops
            ]
            return f"({' && '.join(parts)})"
        case PredicateOr(operands=ops):
            parts = [
                render_predicate_rust(op, var, int32_wrap=int32_wrap)
                for op in ops
            ]
            return f"({' || '.join(parts)})"
        case _:
            raise ValueError(f"Unknown predicate: {pred}")
