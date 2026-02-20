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
from genfxn.langs.rust._helpers import rust_i64_literal


def _i64_expr(value: int) -> str:
    literal = rust_i64_literal(value)
    if literal.endswith("i64"):
        return literal[:-3]
    return literal


def render_predicate_rust(
    pred: Predicate,
    var: str = "x",
) -> str:
    """Render a numeric predicate as a Rust boolean expression."""
    match pred:
        case PredicateEven():
            return f"{var} % 2 == 0"
        case PredicateOdd():
            return f"{var} % 2 != 0"
        case PredicateLt(value=v):
            rv = _i64_expr(v)
            return f"{var} < {rv}"
        case PredicateLe(value=v):
            rv = _i64_expr(v)
            return f"{var} <= {rv}"
        case PredicateGt(value=v):
            rv = _i64_expr(v)
            return f"{var} > {rv}"
        case PredicateGe(value=v):
            rv = _i64_expr(v)
            return f"{var} >= {rv}"
        case PredicateModEq(divisor=d, remainder=r):
            rd = _i64_expr(d)
            rr = _i64_expr(r)
            return f"{var}.rem_euclid({rd}) == {rr}"
        case PredicateInSet(values=vals):
            if not vals:
                return "false"
            items = ", ".join(_i64_expr(v) for v in sorted(vals))
            return f"[{items}].contains(&{var})"
        case PredicateNot(operand=op):
            return f"!({render_predicate_rust(op, var)})"
        case PredicateAnd(operands=ops):
            parts = [render_predicate_rust(op, var) for op in ops]
            return f"({' && '.join(parts)})"
        case PredicateOr(operands=ops):
            parts = [render_predicate_rust(op, var) for op in ops]
            return f"({' || '.join(parts)})"
        case _:
            raise ValueError(f"Unknown predicate: {pred}")
