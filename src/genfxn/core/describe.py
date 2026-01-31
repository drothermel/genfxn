from typing import Any


def describe_task(family: str, spec: dict[str, Any]) -> str:
    """Generate a textual description of the task spec."""
    if family == "piecewise":
        return _describe_piecewise(spec)
    elif family == "stateful":
        return _describe_stateful(spec)
    elif family == "simple_algorithms":
        return _describe_simple_algorithms(spec)
    elif family == "stringrules":
        return _describe_stringrules(spec)
    return ""


def _describe_piecewise(spec: dict[str, Any]) -> str:
    """Generate natural language description for piecewise functions."""
    branches = spec.get("branches", [])
    default_expr = spec.get("default_expr", {})

    parts = []
    for branch in branches:
        cond = branch.get("condition")
        expr = branch.get("expr")
        if isinstance(cond, dict):
            cond_text = _describe_predicate(cond, "x")
        else:
            cond_text = "unknown condition"
        if isinstance(expr, dict):
            expr_text = _describe_expression(expr)
        else:
            expr_text = "unknown expression"
        parts.append(f"When {cond_text}, return {expr_text}.")

    default_text = _describe_expression(default_expr)
    parts.append(f"Otherwise, return {default_text}.")

    return " ".join(parts)


def _describe_stateful(spec: dict[str, Any]) -> str:
    """Generate natural language description for stateful functions."""
    template = spec.get("template", "")

    if template == "longest_run":
        pred = spec.get("match_predicate", {})
        pred_text = _describe_predicate(pred, "element")
        return (
            f"Given a list of integers, find the longest consecutive run of "
            f"elements where {pred_text}. Return the length of that run."
        )

    elif template == "conditional_linear_sum":
        pred = spec.get("predicate", {})
        true_trans = spec.get("true_transform", {})
        false_trans = spec.get("false_transform", {})
        init = spec.get("init_value", 0)

        pred_text = _describe_predicate(pred, "element")
        true_text = _describe_transform(true_trans)
        false_text = _describe_transform(false_trans)

        init_text = _format_number(init)
        return (
            f"Given a list of integers, start with an accumulator of "
            f"{init_text}. "
            f"For each element: when {pred_text}, add {true_text} to the "
            f"accumulator; otherwise, add {false_text}. "
            f"Return the final accumulator value."
        )

    elif template == "resetting_best_prefix_sum":
        pred = spec.get("reset_predicate", {})
        init = spec.get("init_value", 0)

        pred_text = _describe_predicate(pred, "element")
        init_text = _format_number(init)

        return (
            f"Given a list of integers, track a running sum and the best sum "
            f"seen. Start both at {init_text}. For each element: add it to the "
            f"running sum; when {pred_text}, reset the running sum to "
            f"{init_text}; update best sum if running sum is larger. "
            f"Return the best sum."
        )

    return ""


def _describe_predicate(pred: dict[str, Any], var: str) -> str:
    """Convert predicate to natural language."""
    kind = pred.get("kind", "")

    if kind == "even":
        return f"the {var} is even"
    elif kind == "odd":
        return f"the {var} is odd"
    elif kind == "lt":
        value = pred.get("value", 0)
        return f"the {var} is less than {_format_number(value)}"
    elif kind == "le":
        value = pred.get("value", 0)
        return f"the {var} is at most {_format_number(value)}"
    elif kind == "gt":
        value = pred.get("value", 0)
        return f"the {var} is greater than {_format_number(value)}"
    elif kind == "ge":
        value = pred.get("value", 0)
        return f"the {var} is at least {_format_number(value)}"
    elif kind == "mod_eq":
        divisor = pred.get("divisor", 1)
        remainder = pred.get("remainder", 0)
        return f"the {var} mod {divisor} equals {remainder}"
    elif kind == "in_set":
        values = pred.get("values", [])
        if isinstance(values, list | set | frozenset):
            sorted_vals = sorted(values)
        else:
            sorted_vals = list(values)
        vals_text = ", ".join(str(v) for v in sorted_vals)
        return f"the {var} is in {{{vals_text}}}"

    return f"the {var} matches condition"


def _describe_transform(trans: dict[str, Any]) -> str:
    """Convert transform to natural language ('add X to accumulator')."""
    kind = trans.get("kind", "identity")

    if kind == "identity":
        return "the element"
    elif kind == "abs":
        return "the absolute value of the element"
    elif kind == "negate":
        return "the negation of the element"
    elif kind == "shift":
        offset = trans.get("offset", 0)
        if offset >= 0:
            return f"the element plus {offset}"
        else:
            return f"the element minus {abs(offset)}"
    elif kind == "scale":
        factor = trans.get("factor", 1)
        return f"{_format_number(factor)} times the element"
    elif kind == "clip":
        low = trans.get("low", 0)
        high = trans.get("high", 0)
        return f"the element clipped to [{low}, {high}]"

    return "the element"


def _describe_expression(expr: dict[str, Any]) -> str:
    """Convert expression to natural language."""
    kind = expr.get("kind", "affine")

    if kind == "affine":
        a = expr.get("a", 0)
        b = expr.get("b", 0)
        return _describe_linear(a, b, "x")

    elif kind == "quadratic":
        a = expr.get("a", 0)
        b = expr.get("b", 0)
        c = expr.get("c", 0)
        return _describe_quadratic(a, b, c)

    elif kind == "abs":
        a = expr.get("a", 0)
        b = expr.get("b", 0)
        return _describe_abs_expr(a, b)

    elif kind == "mod":
        divisor = expr.get("divisor", 1)
        a = expr.get("a", 0)
        b = expr.get("b", 0)
        return _describe_mod_expr(divisor, a, b)

    return "x"


def _describe_linear(a: int, b: int, var: str) -> str:
    """Describe a*x + b in natural language."""
    parts = []

    if a == 0 and b == 0:
        return "0"
    elif a == 0:
        return _format_number(b)
    elif a == 1:
        parts.append(var)
    elif a == -1:
        parts.append(f"negative {var}")
    elif a < 0:
        parts.append(f"negative {abs(a)} times {var}")
    else:
        parts.append(f"{a} times {var}")

    if b > 0:
        parts.append(f"plus {b}")
    elif b < 0:
        parts.append(f"minus {abs(b)}")

    return " ".join(parts)


def _describe_quadratic(a: int, b: int, c: int) -> str:
    """Describe a*x^2 + b*x + c in natural language."""
    parts = []

    if a == 1:
        parts.append("x squared")
    elif a == -1:
        parts.append("negative x squared")
    elif a < 0:
        parts.append(f"negative {abs(a)} times x squared")
    elif a != 0:
        parts.append(f"{a} times x squared")

    if b == 1:
        if parts:
            parts.append("plus x")
        else:
            parts.append("x")
    elif b == -1:
        if parts:
            parts.append("minus x")
        else:
            parts.append("negative x")
    elif b > 0:
        if parts:
            parts.append(f"plus {b} times x")
        else:
            parts.append(f"{b} times x")
    elif b < 0:
        if parts:
            parts.append(f"minus {abs(b)} times x")
        else:
            parts.append(f"negative {abs(b)} times x")

    if c > 0:
        if parts:
            parts.append(f"plus {c}")
        else:
            parts.append(str(c))
    elif c < 0:
        if parts:
            parts.append(f"minus {abs(c)}")
        else:
            parts.append(f"negative {abs(c)}")

    if not parts:
        return "0"

    return " ".join(parts)


def _describe_abs_expr(a: int, b: int) -> str:
    """Describe a*abs(x) + b in natural language."""
    parts = []

    if a == 0 and b == 0:
        return "0"
    elif a == 0:
        return _format_number(b)
    elif a == 1:
        parts.append("the absolute value of x")
    elif a == -1:
        parts.append("negative the absolute value of x")
    elif a < 0:
        parts.append(f"negative {abs(a)} times the absolute value of x")
    else:
        parts.append(f"{a} times the absolute value of x")

    if b > 0:
        parts.append(f"plus {b}")
    elif b < 0:
        parts.append(f"minus {abs(b)}")

    return " ".join(parts)


def _describe_mod_expr(divisor: int, a: int, b: int) -> str:
    """Describe a*(x mod divisor) + b in natural language."""
    parts = []

    if a == 0 and b == 0:
        return "0"
    elif a == 0:
        return _format_number(b)
    elif a == 1:
        parts.append(f"x mod {divisor}")
    elif a == -1:
        parts.append(f"negative x mod {divisor}")
    elif a < 0:
        parts.append(f"negative {abs(a)} times x mod {divisor}")
    else:
        parts.append(f"{a} times x mod {divisor}")

    if b > 0:
        parts.append(f"plus {b}")
    elif b < 0:
        parts.append(f"minus {abs(b)}")

    return " ".join(parts)


def _format_number(n: int) -> str:
    """Format a number for natural language."""
    if n < 0:
        return f"negative {abs(n)}"
    return str(n)


def _describe_simple_algorithms(spec: dict[str, Any]) -> str:
    """Generate natural language description for simple_algorithms functions."""
    template = spec.get("template", "")

    if template == "most_frequent":
        tie_break = spec.get("tie_break", "smallest")
        empty_default = spec.get("empty_default", 0)
        tie_text = (
            "the smallest value" if tie_break == "smallest" else "the first value seen"
        )
        default_text = _format_number(empty_default)
        return (
            f"Given a list of integers, find the most frequently occurring "
            f"value. When there's a tie, return {tie_text}. "
            f"Return {default_text} for an empty list."
        )

    elif template == "count_pairs_sum":
        target = spec.get("target", 0)
        counting_mode = spec.get("counting_mode", "all_indices")
        target_text = _format_number(target)
        if counting_mode == "all_indices":
            mode_text = "all index pairs (i, j) where i < j"
        else:
            mode_text = "unique value pairs only"
        return (
            f"Given a list of integers, count the number of pairs that sum to "
            f"{target_text}. Count {mode_text}."
        )

    elif template == "max_window_sum":
        k = spec.get("k", 1)
        invalid_default = spec.get("invalid_k_default", 0)
        default_text = _format_number(invalid_default)
        return (
            f"Given a list of integers, find the maximum sum of any {k} "
            f"consecutive elements. If the list has fewer than {k} elements, "
            f"return {default_text}."
        )

    return ""


def _describe_stringrules(spec: dict[str, Any]) -> str:
    """Generate natural language description for stringrules functions."""
    rules = spec.get("rules", [])
    default_transform = spec.get("default_transform", {})

    parts = ["Given a string, transform it according to these rules:"]

    for rule in rules:
        pred = rule.get("predicate", {})
        trans = rule.get("transform", {})
        pred_text = _describe_string_predicate(pred)
        trans_text = _describe_string_transform(trans)
        parts.append(f"If {pred_text}, {trans_text}.")

    default_text = _describe_string_transform(default_transform)
    parts.append(f"Otherwise, {default_text}.")

    return " ".join(parts)


def _describe_string_predicate(pred: dict[str, Any]) -> str:
    """Convert string predicate to natural language."""
    kind = pred.get("kind", "")

    if kind == "starts_with":
        prefix = pred.get("prefix", "")
        return f"the string starts with '{prefix}'"
    elif kind == "ends_with":
        suffix = pred.get("suffix", "")
        return f"the string ends with '{suffix}'"
    elif kind == "contains":
        substring = pred.get("substring", "")
        return f"the string contains '{substring}'"
    elif kind == "is_alpha":
        return "the string contains only letters"
    elif kind == "is_digit":
        return "the string contains only digits"
    elif kind == "is_upper":
        return "the string is all uppercase"
    elif kind == "is_lower":
        return "the string is all lowercase"
    elif kind == "length_cmp":
        op = pred.get("op", "eq")
        value = pred.get("value", 0)
        op_map = {
            "lt": "fewer than",
            "le": "at most",
            "gt": "more than",
            "ge": "at least",
            "eq": "exactly",
        }
        return f"the string has {op_map.get(op, 'exactly')} {value} characters"

    return "the string matches condition"


def _describe_string_transform(trans: dict[str, Any]) -> str:
    """Convert string transform to natural language."""
    kind = trans.get("kind", "identity")

    if kind == "identity":
        return "return it unchanged"
    elif kind == "lowercase":
        return "convert to lowercase"
    elif kind == "uppercase":
        return "convert to uppercase"
    elif kind == "capitalize":
        return "capitalize the first letter"
    elif kind == "swapcase":
        return "swap the case of each letter"
    elif kind == "reverse":
        return "reverse the string"
    elif kind == "replace":
        old = trans.get("old", "")
        new = trans.get("new", "")
        return f"replace '{old}' with '{new}'"
    elif kind == "strip":
        chars = trans.get("chars")
        if chars:
            return f"strip '{chars}'"
        return "strip whitespace"
    elif kind == "prepend":
        prefix = trans.get("prefix", "")
        return f"prepend '{prefix}'"
    elif kind == "append":
        suffix = trans.get("suffix", "")
        return f"append '{suffix}'"

    return "return it unchanged"
