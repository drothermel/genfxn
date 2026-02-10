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


def render_predicate_rust(pred: Predicate, var: str = "x") -> str:
    """Render a numeric predicate as a Rust boolean expression."""
    match pred:
        case PredicateEven():
            return f"{var} % 2 == 0"
        case PredicateOdd():
            return f"{var} % 2 != 0"
        case PredicateLt(value=v):
            return f"{var} < {v}"
        case PredicateLe(value=v):
            return f"{var} <= {v}"
        case PredicateGt(value=v):
            return f"{var} > {v}"
        case PredicateGe(value=v):
            return f"{var} >= {v}"
        case PredicateModEq(divisor=d, remainder=r):
            return f"{var}.rem_euclid({d}) == {r}"
        case PredicateInSet(values=vals):
            if not vals:
                return "false"
            items = ", ".join(str(v) for v in sorted(vals))
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
