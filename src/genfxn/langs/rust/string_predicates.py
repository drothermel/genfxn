from genfxn.core.string_predicates import (
    StringPredicate,
    StringPredicateAnd,
    StringPredicateContains,
    StringPredicateEndsWith,
    StringPredicateIsAlpha,
    StringPredicateIsDigit,
    StringPredicateIsLower,
    StringPredicateIsUpper,
    StringPredicateLengthCmp,
    StringPredicateNot,
    StringPredicateOr,
    StringPredicateStartsWith,
)
from genfxn.langs.rust._helpers import rust_string_literal


def render_string_predicate_rust(pred: StringPredicate, var: str = "s") -> str:
    """Render a string predicate as a Rust boolean expression."""
    match pred:
        case StringPredicateStartsWith(prefix=p):
            return f"{var}.starts_with({rust_string_literal(p)})"
        case StringPredicateEndsWith(suffix=suf):
            return f"{var}.ends_with({rust_string_literal(suf)})"
        case StringPredicateContains(substring=sub):
            return f"{var}.contains({rust_string_literal(sub)})"
        case StringPredicateIsAlpha():
            return (
                f"!{var}.is_empty() && {var}.chars().all(|c| c.is_alphabetic())"
            )
        case StringPredicateIsDigit():
            return (
                f"!{var}.is_empty() && "
                f"{var}.chars().all(|c| c.is_numeric())"
            )
        case StringPredicateIsUpper():
            return (
                f"!{var}.is_empty() && "
                f"{var}.chars().any(|c| c.is_alphabetic()) && "
                f"{var}.to_uppercase() == {var}"
            )
        case StringPredicateIsLower():
            return (
                f"!{var}.is_empty() && "
                f"{var}.chars().any(|c| c.is_alphabetic()) && "
                f"{var}.to_lowercase() == {var}"
            )
        case StringPredicateLengthCmp(op=op, value=v):
            op_map = {"lt": "<", "le": "<=", "gt": ">", "ge": ">=", "eq": "=="}
            return f"{var}.len() {op_map[op]} {v}"
        case StringPredicateNot(operand=op):
            return f"!({render_string_predicate_rust(op, var)})"
        case StringPredicateAnd(operands=ops):
            parts = [render_string_predicate_rust(op, var) for op in ops]
            return f"({' && '.join(parts)})"
        case StringPredicateOr(operands=ops):
            parts = [render_string_predicate_rust(op, var) for op in ops]
            return f"({' || '.join(parts)})"
        case _:
            raise ValueError(f"Unknown string predicate: {pred}")
