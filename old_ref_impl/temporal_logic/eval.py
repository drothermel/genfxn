from typing import Any

from genfxn.temporal_logic.models import (
    PredicateKind,
    TemporalLogicSpec,
    TemporalOperator,
    TemporalOutputMode,
)


def _eval_predicate(kind: PredicateKind, constant: int, value: int) -> bool:
    if kind == PredicateKind.EQ:
        return value == constant
    if kind == PredicateKind.NE:
        return value != constant
    if kind == PredicateKind.LT:
        return value < constant
    if kind == PredicateKind.LE:
        return value <= constant
    if kind == PredicateKind.GT:
        return value > constant
    if kind == PredicateKind.GE:
        return value >= constant
    raise ValueError(f"Unsupported predicate kind: {kind}")


def _eval_formula(node: dict[str, Any], xs: list[int], index: int) -> bool:
    op = TemporalOperator(node["op"])

    if op == TemporalOperator.ATOM:
        kind = PredicateKind(node["predicate"])
        constant = int(node["constant"])
        return _eval_predicate(kind, constant, xs[index])

    if op == TemporalOperator.NOT:
        child = node["child"]
        if not isinstance(child, dict):
            raise ValueError("not node child must be a dict")
        return not _eval_formula(child, xs, index)

    if op == TemporalOperator.AND:
        left = node["left"]
        right = node["right"]
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise ValueError("and node children must be dicts")
        return _eval_formula(left, xs, index) and _eval_formula(
            right, xs, index
        )

    if op == TemporalOperator.OR:
        left = node["left"]
        right = node["right"]
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise ValueError("or node children must be dicts")
        return _eval_formula(left, xs, index) or _eval_formula(right, xs, index)

    n = len(xs)
    if op == TemporalOperator.NEXT:
        child = node["child"]
        if not isinstance(child, dict):
            raise ValueError("next node child must be a dict")
        if index + 1 >= n:
            return False
        return _eval_formula(child, xs, index + 1)

    if op == TemporalOperator.EVENTUALLY:
        child = node["child"]
        if not isinstance(child, dict):
            raise ValueError("eventually node child must be a dict")
        for j in range(index, n):
            if _eval_formula(child, xs, j):
                return True
        return False

    if op == TemporalOperator.ALWAYS:
        child = node["child"]
        if not isinstance(child, dict):
            raise ValueError("always node child must be a dict")
        for j in range(index, n):
            if not _eval_formula(child, xs, j):
                return False
        return True

    if op == TemporalOperator.UNTIL:
        left = node["left"]
        right = node["right"]
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise ValueError("until node children must be dicts")
        for j in range(index, n):
            if not _eval_formula(right, xs, j):
                continue
            if all(_eval_formula(left, xs, k) for k in range(index, j)):
                return True
        return False

    if op == TemporalOperator.SINCE:
        left = node["left"]
        right = node["right"]
        if not isinstance(left, dict) or not isinstance(right, dict):
            raise ValueError("since node children must be dicts")
        for j in range(index, -1, -1):
            if not _eval_formula(right, xs, j):
                continue
            if all(_eval_formula(left, xs, k) for k in range(j + 1, index + 1)):
                return True
        return False

    raise ValueError(f"Unsupported operator: {op.value}")


def eval_temporal_logic(spec: TemporalLogicSpec, xs: list[int]) -> int:
    n = len(xs)
    if n == 0:
        if spec.output_mode == TemporalOutputMode.FIRST_SAT_INDEX:
            return -1
        return 0

    truth_values = [_eval_formula(spec.formula, xs, i) for i in range(n)]

    if spec.output_mode == TemporalOutputMode.SAT_AT_START:
        return 1 if truth_values[0] else 0
    if spec.output_mode == TemporalOutputMode.SAT_COUNT:
        return sum(1 for value in truth_values if value)
    for i, value in enumerate(truth_values):
        if value:
            return i
    return -1
