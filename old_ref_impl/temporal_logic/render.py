from genfxn.temporal_logic.models import TemporalLogicSpec


def render_temporal_logic(
    spec: TemporalLogicSpec,
    func_name: str = "f",
) -> str:
    formula_literal = repr(spec.formula)
    output_mode_literal = repr(spec.output_mode.value)
    return f"""def {func_name}(xs: list[int]) -> int:
    formula = {formula_literal}
    output_mode = {output_mode_literal}

    def _eval_predicate(kind: str, constant: int, value: int) -> bool:
        if kind == "eq":
            return value == constant
        if kind == "ne":
            return value != constant
        if kind == "lt":
            return value < constant
        if kind == "le":
            return value <= constant
        if kind == "gt":
            return value > constant
        return value >= constant

    def _eval(node: dict, i: int) -> bool:
        op = node["op"]
        if op == "atom":
            return _eval_predicate(
                node["predicate"],
                int(node["constant"]),
                xs[i],
            )
        if op == "not":
            return not _eval(node["child"], i)
        if op == "and":
            return _eval(node["left"], i) and _eval(node["right"], i)
        if op == "or":
            return _eval(node["left"], i) or _eval(node["right"], i)

        n = len(xs)
        if op == "next":
            if i + 1 >= n:
                return False
            return _eval(node["child"], i + 1)
        if op == "eventually":
            for j in range(i, n):
                if _eval(node["child"], j):
                    return True
            return False
        if op == "always":
            for j in range(i, n):
                if not _eval(node["child"], j):
                    return False
            return True
        if op == "until":
            for j in range(i, n):
                if not _eval(node["right"], j):
                    continue
                valid = True
                for k in range(i, j):
                    if not _eval(node["left"], k):
                        valid = False
                        break
                if valid:
                    return True
            return False
        if op == "since":
            for j in range(i, -1, -1):
                if not _eval(node["right"], j):
                    continue
                valid = True
                for k in range(j + 1, i + 1):
                    if not _eval(node["left"], k):
                        valid = False
                        break
                if valid:
                    return True
            return False
        raise ValueError("Unsupported operator: " + str(op))

    n = len(xs)
    if n == 0:
        if output_mode == "first_sat_index":
            return -1
        return 0

    truth_values = [_eval(formula, i) for i in range(n)]
    if output_mode == "sat_at_start":
        return 1 if truth_values[0] else 0
    if output_mode == "sat_count":
        return sum(1 for value in truth_values if value)
    for idx, value in enumerate(truth_values):
        if value:
            return idx
    return -1
"""
