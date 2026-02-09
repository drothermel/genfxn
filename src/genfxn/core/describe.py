from enum import Enum
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
    elif family == "fsm":
        return _describe_fsm(spec)
    elif family == "stack_bytecode":
        return _describe_stack_bytecode(spec)
    elif family == "bitops":
        return _describe_bitops(spec)
    elif family == "sequence_dp":
        return _describe_sequence_dp(spec)
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
        value_transform = spec.get("value_transform")

        pred_text = _describe_predicate(pred, "element")
        init_text = _format_number(init)
        value_text = (
            _describe_transform(value_transform)
            if isinstance(value_transform, dict)
            else "the element"
        )

        return (
            f"Given a list of integers, track a running sum and the best sum "
            f"seen. Start both at {init_text}. For each element: when "
            f"{pred_text}, reset the running sum to {init_text}; otherwise, "
            f"add {value_text} to the running sum and update best sum if "
            f"running sum is larger. "
            f"Return the best sum."
        )

    elif template == "toggle_sum":
        pred = spec.get("toggle_predicate", {})
        on_trans = spec.get("on_transform", {})
        off_trans = spec.get("off_transform", {})
        init = spec.get("init_value", 0)

        pred_text = _describe_predicate(pred, "element")
        on_text = _describe_transform(on_trans)
        off_text = _describe_transform(off_trans)
        init_text = _format_number(init)

        return (
            f"Given a list of integers, start with an accumulator of "
            f"{init_text} and a toggle initially off. For each element: "
            f"when {pred_text}, flip the toggle; when the toggle is on, "
            f"add {on_text} to the accumulator; when the toggle is off, "
            f"add {off_text}. Return the final accumulator value."
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
    elif kind == "and":
        operands = pred.get("operands", [])
        parts = [_describe_predicate(op, var) for op in operands]
        return " and ".join(parts)
    elif kind == "or":
        operands = pred.get("operands", [])
        parts = [_describe_predicate(op, var) for op in operands]
        return " or ".join(parts)
    elif kind == "not":
        operand = pred.get("operand", {})
        return f"it is not the case that {_describe_predicate(operand, var)}"

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
    elif kind == "pipeline":
        steps = trans.get("steps", [])
        if not steps:
            return "the element"
        result = "the element"
        for step in steps:
            step_kind = step.get("kind", "identity")
            if step_kind == "abs":
                result = f"the absolute value of {result}"
            elif step_kind == "negate":
                result = f"the negation of {result}"
            elif step_kind == "scale":
                factor = step.get("factor", 1)
                result = f"{_format_number(factor)} times {result}"
            elif step_kind == "shift":
                offset = step.get("offset", 0)
                if offset >= 0:
                    result = f"{result} plus {offset}"
                else:
                    result = f"{result} minus {abs(offset)}"
            elif step_kind == "clip":
                low = step.get("low", 0)
                high = step.get("high", 0)
                result = f"{result} clipped to [{low}, {high}]"
        return result

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


def _describe_preprocess_steps(spec: dict[str, Any]) -> str:
    """Describe optional pre-filter and pre-transform steps."""
    pre_filter = spec.get("pre_filter")
    pre_transform = spec.get("pre_transform")
    steps: list[str] = []

    if isinstance(pre_filter, dict):
        pred_text = _describe_predicate(pre_filter, "element")
        steps.append(f"keep only elements where {pred_text}")

    if isinstance(pre_transform, dict):
        trans_text = _describe_transform(pre_transform)
        target = "remaining element" if steps else "element"
        steps.append(f"replace each {target} with {trans_text}")

    if not steps:
        return ""
    if len(steps) == 1:
        return f"First, {steps[0]}."
    return f"First, {steps[0]}; then {steps[1]}."


def _join_description_parts(*parts: str) -> str:
    """Join non-empty description fragments with spaces."""
    return " ".join(part for part in parts if part)


def _enum_text(value: Any) -> str:
    """Return stable text for enum-like or string values."""
    if isinstance(value, Enum):
        return str(value.value)
    return str(value)


def _describe_simple_algorithms(spec: dict[str, Any]) -> str:
    """Generate natural language description for simple_algorithms functions."""
    template = spec.get("template", "")
    preprocess = _describe_preprocess_steps(spec)

    if template == "most_frequent":
        tie_break = spec.get("tie_break", "smallest")
        empty_default = spec.get("empty_default", 0)
        tie_default = spec.get("tie_default")
        default_text = _format_number(empty_default)
        if tie_default is not None:
            tie_text = _format_number(tie_default)
            tie_clause = (
                f"If multiple values tie for highest frequency, return "
                f"{tie_text}."
            )
        else:
            tie_break_text = (
                "the smallest value"
                if tie_break == "smallest"
                else "the first value seen"
            )
            tie_clause = f"When there's a tie, return {tie_break_text}."

        intro = (
            "Given a list of integers, find the most frequently occurring "
            "value."
        )
        empty_clause = (
            f"If the list is empty after preprocessing, return {default_text}."
        )
        return _join_description_parts(
            intro,
            preprocess,
            tie_clause,
            empty_clause,
        )

    elif template == "count_pairs_sum":
        target = spec.get("target", 0)
        counting_mode = spec.get("counting_mode", "all_indices")
        short_list_default = spec.get("short_list_default")
        no_result_default = spec.get("no_result_default")
        target_text = _format_number(target)
        if counting_mode == "all_indices":
            mode_text = "all index pairs (i, j) where i < j"
        else:
            mode_text = "unique value pairs only"

        default_clause = ""
        if short_list_default is not None:
            short_text = _format_number(short_list_default)
            default_clause = (
                f"If fewer than 2 elements remain after preprocessing, "
                f"return {short_text}."
            )
        if no_result_default is not None:
            no_result_text = _format_number(no_result_default)
            if short_list_default is not None:
                default_clause += (
                    f" Otherwise, if no pairs match, return {no_result_text}."
                )
            else:
                default_clause = f"If no pairs match, return {no_result_text}."

        intro = (
            f"Given a list of integers, count the number of pairs that sum to "
            f"{target_text}."
        )
        mode_clause = f"Count {mode_text}."
        return _join_description_parts(
            intro,
            preprocess,
            mode_clause,
            default_clause,
        )

    elif template == "max_window_sum":
        k = spec.get("k", 1)
        invalid_default = spec.get("invalid_k_default", 0)
        empty_default = spec.get("empty_default")
        default_text = _format_number(invalid_default)
        intro = (
            f"Given a list of integers, find the maximum sum of any {k} "
            f"consecutive elements."
        )
        if empty_default is not None:
            empty_text = _format_number(empty_default)
            empty_clause = (
                f"If no elements remain after preprocessing, return "
                f"{empty_text}."
            )
            short_clause = (
                f"Otherwise, if fewer than {k} elements remain after "
                f"preprocessing, return {default_text}."
            )
        else:
            empty_clause = ""
            short_clause = (
                f"If fewer than {k} elements remain after preprocessing, "
                f"return {default_text}."
            )
        return _join_description_parts(
            intro,
            preprocess,
            empty_clause,
            short_clause,
        )

    return ""


def _describe_stringrules(spec: dict[str, Any]) -> str:
    """Generate natural language description for stringrules functions."""
    rules = spec.get("rules", [])
    default_transform = spec.get("default_transform", {})
    default_text = _describe_string_transform(default_transform)

    if not rules:
        return (
            f"Given a string, transform it using the default rule: "
            f"{default_text}."
        )

    parts = ["Given a string, transform it according to these rules:"]
    for rule in rules:
        pred = rule.get("predicate", {})
        trans = rule.get("transform", {})
        pred_text = _describe_string_predicate(pred)
        trans_text = _describe_string_transform(trans)
        parts.append(f"If {pred_text}, {trans_text}.")
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
    elif kind == "not":
        operand = pred.get("operand")
        if isinstance(operand, dict):
            operand_text = _describe_string_predicate(operand)
            return f"it is not the case that ({operand_text})"
    elif kind == "and":
        operands = pred.get("operands")
        if isinstance(operands, list):
            parts = [
                f"({_describe_string_predicate(op)})"
                for op in operands
                if isinstance(op, dict)
            ]
            if parts:
                return " and ".join(parts)
    elif kind == "or":
        operands = pred.get("operands")
        if isinstance(operands, list):
            parts = [
                f"({_describe_string_predicate(op)})"
                for op in operands
                if isinstance(op, dict)
            ]
            if parts:
                return " or ".join(parts)

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
    elif kind == "pipeline":
        steps = trans.get("steps")
        if isinstance(steps, list):
            step_texts = [
                _describe_string_transform(step)
                for step in steps
                if isinstance(step, dict)
            ]
            if step_texts:
                return f"apply in order: {', then '.join(step_texts)}"

    return "return it unchanged"


def _describe_stack_bytecode(spec: dict[str, Any]) -> str:
    program = spec.get("program", [])
    n_instr = len(program) if isinstance(program, list) else 0
    input_mode = _enum_text(spec.get("input_mode", "direct"))
    jump_mode = _enum_text(spec.get("jump_target_mode", "error"))
    max_steps = spec.get("max_step_count", 64)
    has_conditional = any(
        isinstance(instr, dict)
        and instr.get("op") in ("jump_if_zero", "jump_if_nonzero")
        for instr in program
    )
    has_loop = any(
        isinstance(instr, dict)
        and instr.get("op") in ("jump", "jump_if_zero", "jump_if_nonzero")
        and isinstance(instr.get("target"), int)
        and instr["target"] < idx
        for idx, instr in enumerate(program)
    )
    flow_text = "linear control flow"
    if has_conditional and has_loop:
        flow_text = "conditional jumps with potential loops"
    elif has_conditional:
        flow_text = "conditional jumps"
    elif any(
        isinstance(instr, dict) and instr.get("op") == "jump"
        for instr in program
    ):
        flow_text = "unconditional jumps"

    if input_mode == "direct":
        input_text = (
            "For load_input i, push xs[i]; if i is out of range, return "
            "status 5."
        )
    else:
        input_text = (
            "For load_input i, push xs[i % len(xs)] in cyclic mode; when xs "
            "is empty, return status 5."
        )

    if jump_mode == "error":
        jump_text = (
            "For jumps, out-of-range targets are invalid and return status 3."
        )
    elif jump_mode == "clamp":
        jump_text = (
            "For jumps, out-of-range targets are clamped into [0, n-1], "
            "where n is the program length."
        )
    else:
        jump_text = (
            "For jumps, targets are wrapped modulo n, where n is the "
            "program length."
        )

    return _join_description_parts(
        (
            "Implement f(xs: list[int]) -> tuple[int, int] for a stack-based "
            "bytecode machine."
        ),
        (
            f"The program has {n_instr} instructions with {flow_text}, "
            f"input_mode '{input_mode}', jump_target_mode '{jump_mode}', "
            f"and max_step_count {max_steps}."
        ),
        "Start at instruction 0 with an empty stack.",
        input_text,
        jump_text,
        (
            "Return (status, value) with status codes "
            "0=ok, 1=step_limit, 2=stack_underflow, 3=bad_jump_target, "
            "4=div_or_mod_by_zero, 5=invalid_input_index, "
            "6=empty_stack_on_halt."
        ),
        (
            "On status 0, value is the top of stack at halt; on nonzero "
            "status, value is 0."
        ),
    )


def _describe_bitops(spec: dict[str, Any]) -> str:
    width_bits = spec.get("width_bits", 8)
    operations = spec.get("operations", [])
    if not isinstance(operations, list):
        operations = []

    if not operations:
        return (
            f"Implement f(x: int) -> int using fixed-width ({width_bits}-bit) "
            "bit arithmetic; return x masked to the configured width."
        )

    rendered_ops: list[str] = []
    for op in operations:
        if not isinstance(op, dict):
            continue
        name = str(op.get("op", "unknown"))
        arg = op.get("arg")
        rendered_ops.append(name if arg is None else f"{name}({arg})")

    if not rendered_ops:
        n_operations = len(operations)
        return (
            f"Implement f(x: int) -> int using fixed-width ({width_bits}-bit) "
            f"bit arithmetic with {n_operations} listed operation(s). "
            f"After each operation, mask the intermediate result to "
            f"{width_bits} bits."
        )

    return (
        f"Implement f(x: int) -> int. Treat x as a {width_bits}-bit pattern, "
        f"apply operations in order: {', then '.join(rendered_ops)}, and "
        f"after each operation mask the intermediate result to {width_bits} "
        "bits. Return the resulting integer."
    )


def _describe_sequence_dp(spec: dict[str, Any]) -> str:
    def _read_int(value: Any, default: int) -> int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return default

    template = _enum_text(spec.get("template", "global"))
    output_mode = _enum_text(spec.get("output_mode", "score"))
    tie_break = _enum_text(spec.get("step_tie_break", "diag_up_left"))
    match_score = _format_number(_read_int(spec.get("match_score"), 1))
    mismatch_score = _format_number(_read_int(spec.get("mismatch_score"), -1))
    gap_score = _format_number(_read_int(spec.get("gap_score"), -1))

    predicate = spec.get("match_predicate", {})
    predicate_text = "elements are equal"
    if isinstance(predicate, dict):
        kind = _enum_text(predicate.get("kind", "eq"))
        if kind == "abs_diff_le":
            max_diff = _format_number(_read_int(predicate.get("max_diff"), 0))
            predicate_text = (
                "absolute difference between paired elements is at most "
                f"{max_diff}"
            )
        elif kind == "mod_eq":
            divisor = _format_number(_read_int(predicate.get("divisor"), 2))
            remainder = _format_number(
                _read_int(predicate.get("remainder"), 0)
            )
            predicate_text = (
                "paired elements satisfy modular match "
                f"(a-b) % {divisor} == {remainder}"
            )

    return _join_description_parts(
        (
            "Implement f(a: list[int], b: list[int]) -> int using "
            f"{template} sequence dynamic-programming semantics."
        ),
        f"Use match predicate: {predicate_text}.",
        (
            f"Use match_score={match_score}, "
            f"mismatch_score={mismatch_score}, gap_score={gap_score}."
        ),
        (
            f"Break ties with '{tie_break}' move ordering and return "
            f"'{output_mode}'."
        ),
    )


def _describe_fsm(spec: dict[str, Any]) -> str:
    machine_type = _enum_text(spec.get("machine_type", "moore"))
    output_mode = _enum_text(spec.get("output_mode", "final_state_id"))
    policy = _enum_text(spec.get("undefined_transition_policy", "stay"))
    start_state_id = spec.get("start_state_id", 0)
    states = spec.get("states", [])

    n_states = len(states) if isinstance(states, list) else 0
    n_transitions = 0
    accept_states: list[int] = []
    if isinstance(states, list):
        for state in states:
            if not isinstance(state, dict):
                continue
            transitions = state.get("transitions", [])
            if isinstance(transitions, list):
                n_transitions += len(transitions)
            if state.get("is_accept"):
                state_id = state.get("id")
                if isinstance(state_id, int):
                    accept_states.append(state_id)

    if output_mode == "accept_bool":
        if accept_states:
            accept_text = ", ".join(str(state_id) for state_id in accept_states)
            output_text = (
                "return 1 when the final state is accepting "
                f"(accepting states: {accept_text}), otherwise 0"
            )
        else:
            output_text = (
                "return 1 when the final state is accepting, otherwise 0"
            )
    elif output_mode == "transition_count":
        output_text = "return the number of transitions taken"
    else:
        output_text = "return the final state id"

    if policy == "stay":
        policy_text = (
            "If no transition matches, stay in the current state and do not "
            "increment transition_count."
        )
    elif policy == "sink":
        policy_text = (
            "If no transition matches, move to sink state "
            "(max_state_id + 1) and increment transition_count."
        )
    else:
        policy_text = (
            "If no transition matches, raise an undefined-transition error."
        )

    return _join_description_parts(
        (
            "Implement f(xs: list[int]) -> int for a deterministic "
            f"{machine_type} finite-state machine."
        ),
        (
            f"The machine has {n_states} states, {n_transitions} transitions, "
            f"and starts in state {start_state_id}."
        ),
        (
            "For each x in xs, scan the current state's transitions in listed "
            "order and take the first predicate that matches."
        ),
        policy_text,
        (
            f"Use output_mode '{output_mode}': {output_text}."
        ),
    )
