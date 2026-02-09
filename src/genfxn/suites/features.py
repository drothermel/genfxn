"""Feature extraction for balanced suite generation.

Each function takes a spec dict and returns a
flat dict[str, str] of categorical features.
"""

from collections import Counter
from typing import Any

# ── String predicate / transform scoring (inlined from difficulty.py) ──────


def _string_predicate_score(pred: dict[str, Any]) -> int:
    kind = pred.get("kind", "")
    if kind in ("is_alpha", "is_digit", "is_upper", "is_lower"):
        return 1
    elif kind in ("starts_with", "ends_with", "contains"):
        return 2
    elif kind == "length_cmp":
        op = pred.get("op", "eq")
        return 3 if op in ("lt", "gt") else 2
    elif kind == "not":
        return 4
    elif kind in ("and", "or"):
        operands = pred.get("operands", [])
        return 5 if len(operands) >= 3 else 4
    return 1


def _string_transform_score(trans: dict[str, Any]) -> int:
    kind = trans.get("kind", "identity")
    if kind == "identity":
        return 1
    elif kind in (
        "lowercase",
        "uppercase",
        "capitalize",
        "swapcase",
        "reverse",
    ):
        return 2
    elif kind in ("replace", "strip", "prepend", "append"):
        return 3
    elif kind == "pipeline":
        steps = trans.get("steps", [])
        param_kinds = {"replace", "strip", "prepend", "append"}
        param_steps = sum(1 for s in steps if s.get("kind") in param_kinds)
        if len(steps) == 3 or param_steps >= 2:
            return 5
        elif param_steps >= 1:
            return 4
        else:
            return 3
    return 1


# ── Numeric predicate / transform scoring (inlined) ──────────────────────


def _predicate_score(pred: dict[str, Any]) -> int:
    kind = pred.get("kind", "")
    if kind in ("even", "odd"):
        return 1
    elif kind in ("lt", "le", "gt", "ge"):
        return 2
    elif kind == "mod_eq":
        return 4
    elif kind == "in_set":
        return 3
    elif kind in ("not", "and", "or"):
        return 5
    return 2


def _transform_score(trans: dict[str, Any]) -> int:
    kind = trans.get("kind", "identity")
    if kind == "identity":
        return 1
    elif kind in ("abs", "negate"):
        return 2
    elif kind in ("shift", "scale", "clip"):
        return 3
    elif kind == "pipeline":
        steps = trans.get("steps", [])
        param_kinds = {"shift", "scale", "clip"}
        param_steps = sum(1 for s in steps if s.get("kind") in param_kinds)
        if len(steps) == 3 or param_steps >= 2:
            return 5
        elif param_steps >= 1:
            return 4
        else:
            return 3
    return 1


# ── Helpers ──────────────────────────────────────────────────────────────


def _is_composed_string_pred(pred: dict[str, Any]) -> bool:
    return pred.get("kind", "") in ("not", "and", "or")


def _is_pipeline_string_trans(trans: dict[str, Any]) -> bool:
    return trans.get("kind", "") == "pipeline"


def _n_rules_bucket(n: int) -> str:
    if n <= 5:
        return "4-5"
    elif n <= 7:
        return "6-7"
    else:
        return "8-10"


def _pred_majority_categories(pred: dict[str, Any]) -> list[str]:
    """Collect predicate categories recursively over composed predicates."""
    kind = pred.get("kind", "")
    if kind in ("not",):
        return _pred_majority_categories(pred.get("operand", {}))
    if kind in ("and", "or"):
        operands = pred.get("operands", [])
        categories: list[str] = []
        for operand in operands:
            categories.extend(_pred_majority_categories(operand))
        return categories
    if kind in ("is_alpha", "is_digit", "is_upper", "is_lower"):
        return ["simple"]
    elif kind in ("starts_with", "ends_with", "contains"):
        return ["pattern"]
    elif kind == "length_cmp":
        return ["length"]
    return ["simple"]


def _trans_majority_categories(trans: dict[str, Any]) -> list[str]:
    """Collect transform categories recursively over pipelines."""
    kind = trans.get("kind", "")
    if kind == "pipeline":
        steps = trans.get("steps", [])
        categories: list[str] = []
        for step in steps:
            categories.extend(_trans_majority_categories(step))
        return categories
    if kind == "identity":
        return ["identity"]
    elif kind in (
        "lowercase",
        "uppercase",
        "capitalize",
        "swapcase",
        "reverse",
    ):
        return ["simple"]
    elif kind in ("replace", "strip", "prepend", "append"):
        return ["param"]
    return ["identity"]


def _majority_vote(categories: list[str], tie_order: list[str]) -> str:
    """Return the most common category, breaking ties by tie_order position."""
    if not categories:
        return tie_order[0]
    counts = Counter(categories)
    max_count = max(counts.values())
    # Among those tied at max_count, pick the one earliest in tie_order
    for cat in tie_order:
        if counts.get(cat, 0) == max_count:
            return cat
    return tie_order[0]


# ── Public feature extractors ────────────────────────────────────────────


def stringrules_features(spec: dict[str, Any]) -> dict[str, str]:
    rules = spec.get("rules", [])
    default_transform = spec.get("default_transform", {})
    n_rules = len(rules)

    # has_comp / has_pipe
    has_comp = any(
        _is_composed_string_pred(r.get("predicate", {})) for r in rules
    )
    has_pipe = any(
        _is_pipeline_string_trans(r.get("transform", {})) for r in rules
    ) or _is_pipeline_string_trans(default_transform)

    # mode
    if has_comp and has_pipe:
        mode = "both"
    elif has_comp:
        mode = "comp-only"
    elif has_pipe:
        mode = "pipe-only"
    else:
        mode = "neither"

    # comp_max_score / pipe_max_score
    comp_scores = [
        _string_predicate_score(r.get("predicate", {}))
        for r in rules
        if _is_composed_string_pred(r.get("predicate", {}))
    ]
    comp_max = max(comp_scores) if comp_scores else 0

    all_transforms = [r.get("transform", {}) for r in rules] + [
        default_transform
    ]
    pipe_scores = [
        _string_transform_score(t)
        for t in all_transforms
        if _is_pipeline_string_trans(t)
    ]
    pipe_max = max(pipe_scores) if pipe_scores else 0

    # comp_rate / pipe_rate
    comp_count = sum(
        1 for r in rules if _is_composed_string_pred(r.get("predicate", {}))
    )
    comp_rate = comp_count / n_rules if n_rules > 0 else 0.0

    pipe_rule_count = sum(
        1 for r in rules if _is_pipeline_string_trans(r.get("transform", {}))
    )
    # pipe_rate counts rules with pipeline transforms (not including default)
    pipe_rate = pipe_rule_count / n_rules if n_rules > 0 else 0.0

    # pred_majority
    pred_cats = [
        category
        for r in rules
        for category in _pred_majority_categories(r.get("predicate", {}))
    ]
    pred_majority = _majority_vote(pred_cats, ["simple", "pattern", "length"])

    # transform_majority (includes default)
    trans_cats = [
        category
        for t in all_transforms
        for category in _trans_majority_categories(t)
    ]
    transform_majority = _majority_vote(
        trans_cats, ["identity", "simple", "param"]
    )

    return {
        "n_rules_bucket": _n_rules_bucket(n_rules),
        "has_comp": str(has_comp).lower(),
        "has_pipe": str(has_pipe).lower(),
        "mode": mode,
        "comp_max_score": str(comp_max),
        "pipe_max_score": str(pipe_max),
        "comp_rate": str(round(comp_rate, 2)),
        "pipe_rate": str(round(pipe_rate, 2)),
        "pred_majority": pred_majority,
        "transform_majority": transform_majority,
    }


def stateful_features(spec: dict[str, Any]) -> dict[str, str]:
    template = spec.get("template", "")

    # pred_kind: classify the max-scored predicate
    predicates = []
    for key in (
        "predicate",
        "reset_predicate",
        "match_predicate",
        "toggle_predicate",
    ):
        val = spec.get(key)
        if val is not None:
            predicates.append(val)

    if predicates:
        best_pred = max(predicates, key=_predicate_score)
        kind = best_pred.get("kind", "")
        if kind in ("not", "and", "or"):
            pred_kind = "composed"
        elif kind == "mod_eq":
            pred_kind = "mod_eq"
        elif kind in ("lt", "le", "gt", "ge"):
            pred_kind = "comparison"
        elif kind in ("even", "odd"):
            pred_kind = "even_odd"
        else:
            pred_kind = "comparison"
    else:
        pred_kind = "comparison"

    # transform_bucket
    transforms = []
    for key in (
        "true_transform",
        "false_transform",
        "value_transform",
        "on_transform",
        "off_transform",
    ):
        val = spec.get(key)
        if val is not None:
            transforms.append(val)

    if transforms:
        max_tscore = max(_transform_score(t) for t in transforms)
        if max_tscore >= 5:
            transform_bucket = "pipeline5"
        elif max_tscore >= 4:
            transform_bucket = "pipeline4"
        elif max_tscore >= 2:
            transform_bucket = "atomic_nonidentity"
        else:
            transform_bucket = "identity"
    else:
        transform_bucket = "identity"

    features: dict[str, str] = {
        "template": template,
        "pred_kind": pred_kind,
        "transform_bucket": transform_bucket,
    }

    # transform_signature (conditional_linear_sum only)
    if template == "conditional_linear_sum":
        true_t = spec.get("true_transform", {})
        false_t = spec.get("false_transform", {})
        true_kind = true_t.get("kind", "identity")
        false_kind = false_t.get("kind", "identity")
        affine = {"shift", "scale", "clip", "identity"}
        sign = {"abs", "negate"}
        if true_kind in affine and false_kind in affine:
            sig = "both_affine"
        elif true_kind in sign and false_kind in sign:
            sig = "both_sign"
        else:
            sig = "mixed"
        features["transform_signature"] = sig

    return features


def simple_algorithms_features(spec: dict[str, Any]) -> dict[str, str]:
    template = spec.get("template", "")
    has_filter = spec.get("pre_filter") is not None
    has_transform = spec.get("pre_transform") is not None

    # preprocess_bucket
    if has_filter and has_transform:
        preprocess_bucket = "both"
    elif has_filter:
        preprocess_bucket = "filter_only"
    elif has_transform:
        preprocess_bucket = "transform_only"
    else:
        preprocess_bucket = "none"

    # filter_kind
    if has_filter:
        filt = spec["pre_filter"]
        fk = filt.get("kind", "")
        if fk in ("not", "and", "or"):
            filter_kind = "composed"
        elif fk == "mod_eq":
            filter_kind = "mod_eq"
        elif fk in ("lt", "le", "gt", "ge", "even", "odd"):
            filter_kind = "comparison"
        else:
            filter_kind = "comparison"
    else:
        filter_kind = "none"

    # pre_transform_complexity
    if has_transform:
        tscore = _transform_score(spec["pre_transform"])
        if tscore >= 5:
            pre_transform_complexity = "pipeline5"
        elif tscore >= 4:
            pre_transform_complexity = "pipeline4"
        else:
            pre_transform_complexity = "atomic"
    else:
        pre_transform_complexity = "none"

    # edge_count: count non-None new edge fields
    new_edge_fields = ["tie_default", "no_result_default", "short_list_default"]
    if template == "max_window_sum":
        new_edge_fields.append("empty_default")
    edge_count = sum(1 for f in new_edge_fields if spec.get(f) is not None)

    features: dict[str, str] = {
        "template": template,
        "preprocess_bucket": preprocess_bucket,
        "has_filter": str(has_filter).lower(),
        "has_transform": str(has_transform).lower(),
        "filter_kind": filter_kind,
        "pre_transform_complexity": pre_transform_complexity,
        "edge_count": str(edge_count),
    }

    # target_sign (count_pairs_sum only)
    if template == "count_pairs_sum":
        target = spec.get("target", 0)
        if target < 0:
            features["target_sign"] = "neg"
        elif target == 0:
            features["target_sign"] = "zero"
        else:
            features["target_sign"] = "pos"

    # k_bucket (max_window_sum only)
    if template == "max_window_sum":
        k = spec.get("k", 1)
        if 6 <= k <= 7:
            features["k_bucket"] = "6-7"
        elif 8 <= k <= 10:
            features["k_bucket"] = "8-10"
        else:
            features["k_bucket"] = "out_of_range"

    return features


def bitops_features(spec: dict[str, Any]) -> dict[str, str]:
    operations = spec.get("operations", [])
    if not isinstance(operations, list):
        operations = []

    n_ops = len(operations)
    if n_ops <= 2:
        n_ops_bucket = "1-2"
    elif n_ops <= 3:
        n_ops_bucket = "2-3"
    elif n_ops <= 4:
        n_ops_bucket = "3-4"
    elif n_ops <= 5:
        n_ops_bucket = "4-5"
    else:
        n_ops_bucket = "6+"

    width_bits = spec.get("width_bits", 8)
    if not isinstance(width_bits, int):
        width_bits = 8

    if width_bits <= 8:
        width_bucket = "8"
    elif width_bits <= 16:
        width_bucket = "16"
    elif width_bits <= 32:
        width_bucket = "24-32"
    else:
        width_bucket = "33+"

    ops: list[str] = []
    for operation in operations:
        if isinstance(operation, dict):
            op = operation.get("op", "")
            if isinstance(op, str):
                ops.append(op)

    has_shift = any(op in ("shl", "shr_logical") for op in ops)
    has_rotate = any(op in ("rotl", "rotr") for op in ops)
    has_aggregate = any(op in ("popcount", "parity") for op in ops)

    op_score = 1
    for op in ops:
        if op in ("popcount", "parity"):
            op_score = max(op_score, 4)
        elif op in ("rotl", "rotr"):
            op_score = max(op_score, 3)
        elif op in ("shl", "shr_logical"):
            op_score = max(op_score, 2)

    if op_score <= 1:
        op_complexity = "basic"
    elif op_score == 2:
        op_complexity = "shift"
    elif op_score == 3:
        op_complexity = "rotate"
    else:
        op_complexity = "aggregate"

    return {
        "n_ops_bucket": n_ops_bucket,
        "width_bucket": width_bucket,
        "op_complexity": op_complexity,
        "has_shift": str(has_shift).lower(),
        "has_rotate": str(has_rotate).lower(),
        "has_aggregate": str(has_aggregate).lower(),
    }


def stack_bytecode_features(spec: dict[str, Any]) -> dict[str, str]:
    program = spec.get("program", [])
    n_instr = len(program) if isinstance(program, list) else 0
    if n_instr <= 3:
        size_bucket = "1-3"
    elif n_instr <= 5:
        size_bucket = "4-5"
    elif n_instr <= 7:
        size_bucket = "6-7"
    elif n_instr <= 10:
        size_bucket = "8-10"
    else:
        size_bucket = "11+"

    ops = []
    if isinstance(program, list):
        for instr in program:
            if isinstance(instr, dict):
                ops.append(instr.get("op", ""))

    has_cond_jump = any(op in ("jump_if_zero", "jump_if_nonzero") for op in ops)
    has_jump = any(op == "jump" for op in ops)
    has_backward_jump = any(
        isinstance(instr, dict)
        and instr.get("op") in ("jump", "jump_if_zero", "jump_if_nonzero")
        and isinstance(instr.get("target"), int)
        and instr["target"] < idx
        for idx, instr in enumerate(
            program if isinstance(program, list) else []
        )
    )

    if has_cond_jump and has_backward_jump:
        control_flow = "looped_conditional"
    elif has_cond_jump:
        control_flow = "conditional"
    elif has_jump:
        control_flow = "jump_only"
    else:
        control_flow = "linear"

    if any(op in ("jump", "jump_if_zero", "jump_if_nonzero") for op in ops):
        op_complexity = "control"
    elif any(op in ("dup", "swap", "pop", "eq", "gt", "lt") for op in ops):
        op_complexity = "stack_logic"
    elif any(
        op in ("add", "sub", "mul", "div", "mod", "neg", "abs")
        for op in ops
    ):
        op_complexity = "arithmetic"
    else:
        op_complexity = "basic"

    return {
        "size_bucket": size_bucket,
        "control_flow": control_flow,
        "op_complexity": op_complexity,
        "input_mode": str(spec.get("input_mode", "direct")),
        "jump_mode": str(spec.get("jump_target_mode", "error")),
    }


def fsm_features(spec: dict[str, Any]) -> dict[str, str]:
    def _enum_or_str(value: Any, default: str) -> str:
        if value is None:
            return default
        if hasattr(value, "value"):
            enum_value = value.value
            if isinstance(enum_value, str):
                return enum_value
        if isinstance(value, str):
            return value
        return str(value)

    states = spec.get("states", [])
    n_states = len(states) if isinstance(states, list) else 0

    if n_states <= 2:
        n_states_bucket = "2"
    elif n_states <= 3:
        n_states_bucket = "2-3"
    elif n_states <= 4:
        n_states_bucket = "3-4"
    elif n_states <= 5:
        n_states_bucket = "4-5"
    elif n_states <= 6:
        n_states_bucket = "5-6"
    else:
        n_states_bucket = "7+"

    total_transitions = 0
    predicate_scores: list[int] = []
    if isinstance(states, list):
        for state in states:
            if not isinstance(state, dict):
                continue
            transitions = state.get("transitions", [])
            if not isinstance(transitions, list):
                continue
            total_transitions += len(transitions)
            for transition in transitions:
                if not isinstance(transition, dict):
                    continue
                predicate = transition.get("predicate", {})
                if isinstance(predicate, dict):
                    predicate_scores.append(_predicate_score(predicate))

    avg_transitions = total_transitions / n_states if n_states > 0 else 0.0
    if avg_transitions <= 1:
        transition_density_bucket = "low"
    elif avg_transitions <= 2:
        transition_density_bucket = "medium"
    elif avg_transitions <= 3:
        transition_density_bucket = "high"
    else:
        transition_density_bucket = "very_high"

    max_pred_score = max(predicate_scores, default=1)
    if max_pred_score <= 1:
        predicate_complexity = "basic"
    elif max_pred_score <= 2:
        predicate_complexity = "comparison"
    else:
        predicate_complexity = "modular"

    return {
        "n_states_bucket": n_states_bucket,
        "transition_density_bucket": transition_density_bucket,
        "predicate_complexity": predicate_complexity,
        "machine_type": _enum_or_str(spec.get("machine_type"), "moore"),
        "output_mode": _enum_or_str(spec.get("output_mode"), "final_state_id"),
        "undefined_policy": _enum_or_str(
            spec.get("undefined_transition_policy"),
            "stay",
        ),
    }


def sequence_dp_features(spec: dict[str, Any]) -> dict[str, str]:
    def _enum_or_str(value: Any, default: str) -> str:
        if value is None:
            return default
        if hasattr(value, "value"):
            enum_value = value.value
            if isinstance(enum_value, str):
                return enum_value
        if isinstance(value, str):
            return value
        return str(value)

    def _safe_int(value: Any, default: int) -> int:
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return default

    template = _enum_or_str(spec.get("template"), "global")
    output_mode = _enum_or_str(spec.get("output_mode"), "score")
    tie_break_order = _enum_or_str(
        spec.get("step_tie_break"), "diag_up_left"
    )

    if tie_break_order.startswith("diag_"):
        tie_break_bucket = "diag_first"
    elif tie_break_order.startswith("up_"):
        tie_break_bucket = "up_first"
    elif tie_break_order.startswith("left_"):
        tie_break_bucket = "left_first"
    else:
        tie_break_bucket = "diag_first"

    predicate = spec.get("match_predicate", {})
    if isinstance(predicate, dict):
        predicate_kind = _enum_or_str(predicate.get("kind"), "eq")
    else:
        predicate_kind = "eq"

    match_score = _safe_int(spec.get("match_score"), 1)
    mismatch_score = _safe_int(spec.get("mismatch_score"), -1)
    gap_score = _safe_int(spec.get("gap_score"), -1)
    margin = match_score - max(mismatch_score, gap_score)
    if margin >= 4:
        score_profile = "wide"
    elif margin >= 2:
        score_profile = "medium"
    elif margin >= 1:
        score_profile = "narrow"
    else:
        score_profile = "tie_heavy"

    abs_diff_bucket = "na"
    divisor_bucket = "na"
    if isinstance(predicate, dict):
        if predicate_kind == "abs_diff_le":
            max_diff = _safe_int(predicate.get("max_diff"), 0)
            if max_diff <= 1:
                abs_diff_bucket = "0-1"
            elif max_diff <= 3:
                abs_diff_bucket = "2-3"
            else:
                abs_diff_bucket = "4+"
        elif predicate_kind == "mod_eq":
            divisor = _safe_int(predicate.get("divisor"), 2)
            if divisor <= 3:
                divisor_bucket = "2-3"
            elif divisor <= 5:
                divisor_bucket = "4-5"
            elif divisor <= 7:
                divisor_bucket = "6-7"
            else:
                divisor_bucket = "8+"

    return {
        "template": template,
        "output_mode": output_mode,
        "predicate_kind": predicate_kind,
        "tie_break_order": tie_break_order,
        "tie_break_bucket": tie_break_bucket,
        "score_profile": score_profile,
        "abs_diff_bucket": abs_diff_bucket,
        "divisor_bucket": divisor_bucket,
    }
