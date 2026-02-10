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
from genfxn.langs.java._helpers import INT32_MAX, INT32_MIN, java_int_literal


def _render_comparison_unwrapped(var: str, op: str, value: int) -> str:
    """Render comparison preserving Python predicate intent for int inputs."""
    if value > INT32_MAX:
        return "true" if op in ("<", "<=") else "false"
    if value < INT32_MIN:
        return "false" if op in ("<", "<=") else "true"
    return f"{var} {op} {value}"


def _render_in_set_unwrapped(var: str, values: frozenset[int]) -> str:
    """Render membership without narrowing out-of-int32 constants."""
    in_range_values = sorted(
        value for value in values if INT32_MIN <= value <= INT32_MAX
    )
    if not in_range_values:
        return "false"
    items = [f"{var} == {value}" for value in in_range_values]
    return f"({' || '.join(items)})"


def render_predicate_java(
    pred: Predicate,
    var: str = "x",
    *,
    int32_wrap: bool = False,
) -> str:
    """Render a numeric predicate as a Java boolean expression."""
    match pred:
        case PredicateEven():
            return f"{var} % 2 == 0"
        case PredicateOdd():
            return f"{var} % 2 != 0"
        case PredicateLt(value=v):
            if not int32_wrap:
                return _render_comparison_unwrapped(var, "<", v)
            return f"{var} < {java_int_literal(v)}"
        case PredicateLe(value=v):
            if not int32_wrap:
                return _render_comparison_unwrapped(var, "<=", v)
            return f"{var} <= {java_int_literal(v)}"
        case PredicateGt(value=v):
            if not int32_wrap:
                return _render_comparison_unwrapped(var, ">", v)
            return f"{var} > {java_int_literal(v)}"
        case PredicateGe(value=v):
            if not int32_wrap:
                return _render_comparison_unwrapped(var, ">=", v)
            return f"{var} >= {java_int_literal(v)}"
        case PredicateModEq(divisor=d, remainder=r):
            divisor = java_int_literal(d) if int32_wrap else str(d)
            remainder = java_int_literal(r) if int32_wrap else str(r)
            return f"Math.floorMod({var}, {divisor}) == {remainder}"
        case PredicateInSet(values=vals):
            if not vals:
                return "false"
            if int32_wrap:
                items = [
                    f"{var} == {java_int_literal(v)}" for v in sorted(vals)
                ]
                return f"({' || '.join(items)})"
            return _render_in_set_unwrapped(var, vals)
        case PredicateNot(operand=op):
            return (
                f"!({render_predicate_java(op, var, int32_wrap=int32_wrap)})"
            )
        case PredicateAnd(operands=ops):
            parts = [
                render_predicate_java(op, var, int32_wrap=int32_wrap)
                for op in ops
            ]
            return f"({' && '.join(parts)})"
        case PredicateOr(operands=ops):
            parts = [
                render_predicate_java(op, var, int32_wrap=int32_wrap)
                for op in ops
            ]
            return f"({' || '.join(parts)})"
        case _:
            raise ValueError(f"Unknown predicate: {pred}")
