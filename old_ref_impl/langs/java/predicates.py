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
from genfxn.langs.java._helpers import INT32_MAX, INT32_MIN, java_long_literal


def _java_i64_expr(value: int) -> str:
    if INT32_MIN <= value <= INT32_MAX:
        return str(value)
    return java_long_literal(value)


def _render_in_set(var: str, values: frozenset[int]) -> str:
    items = [f"{var} == {_java_i64_expr(value)}" for value in sorted(values)]
    return f"({' || '.join(items)})"


def render_predicate_java(
    pred: Predicate,
    var: str = "x",
) -> str:
    """Render a numeric predicate as a Java boolean expression."""
    match pred:
        case PredicateEven():
            return f"{var} % 2 == 0"
        case PredicateOdd():
            return f"{var} % 2 != 0"
        case PredicateLt(value=v):
            return f"{var} < {_java_i64_expr(v)}"
        case PredicateLe(value=v):
            return f"{var} <= {_java_i64_expr(v)}"
        case PredicateGt(value=v):
            return f"{var} > {_java_i64_expr(v)}"
        case PredicateGe(value=v):
            return f"{var} >= {_java_i64_expr(v)}"
        case PredicateModEq(divisor=d, remainder=r):
            return (
                f"Math.floorMod({var}, {_java_i64_expr(d)})"
                f" == {_java_i64_expr(r)}"
            )
        case PredicateInSet(values=vals):
            if not vals:
                return "false"
            return _render_in_set(var, vals)
        case PredicateNot(operand=op):
            return f"!({render_predicate_java(op, var)})"
        case PredicateAnd(operands=ops):
            parts = [render_predicate_java(op, var) for op in ops]
            return f"({' && '.join(parts)})"
        case PredicateOr(operands=ops):
            parts = [render_predicate_java(op, var) for op in ops]
            return f"({' || '.join(parts)})"
        case _:
            raise ValueError(f"Unknown predicate: {pred}")
