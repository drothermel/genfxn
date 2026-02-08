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
from genfxn.langs.java._helpers import java_string_literal


def render_string_predicate_java(pred: StringPredicate, var: str = "s") -> str:
    """Render a string predicate as a Java boolean expression."""
    match pred:
        case StringPredicateStartsWith(prefix=p):
            return f"{var}.startsWith({java_string_literal(p)})"
        case StringPredicateEndsWith(suffix=suf):
            return f"{var}.endsWith({java_string_literal(suf)})"
        case StringPredicateContains(substring=sub):
            return f"{var}.contains({java_string_literal(sub)})"
        case StringPredicateIsAlpha():
            return f"!{var}.isEmpty() && {var}.chars().allMatch(Character::isLetter)"
        case StringPredicateIsDigit():
            return f"!{var}.isEmpty() && {var}.chars().allMatch(Character::isDigit)"
        case StringPredicateIsUpper():
            return f"!{var}.isEmpty() && {var}.chars().anyMatch(Character::isLetter) && {var}.equals({var}.toUpperCase())"
        case StringPredicateIsLower():
            return f"!{var}.isEmpty() && {var}.chars().anyMatch(Character::isLetter) && {var}.equals({var}.toLowerCase())"
        case StringPredicateLengthCmp(op=op, value=v):
            op_map = {"lt": "<", "le": "<=", "gt": ">", "ge": ">=", "eq": "=="}
            return f"{var}.length() {op_map[op]} {v}"
        case StringPredicateNot(operand=op):
            return f"!({render_string_predicate_java(op, var)})"
        case StringPredicateAnd(operands=ops):
            parts = [render_string_predicate_java(op, var) for op in ops]
            return f"({' && '.join(parts)})"
        case StringPredicateOr(operands=ops):
            parts = [render_string_predicate_java(op, var) for op in ops]
            return f"({' || '.join(parts)})"
        case _:
            raise ValueError(f"Unknown string predicate: {pred}")
