from typing import Any

PIECEWISE_WEIGHTS = {"branches": 0.4, "expr_type": 0.4, "coeff": 0.2}
STATEFUL_WEIGHTS = {"template": 0.4, "predicate": 0.3, "transform": 0.3}
SIMPLE_ALGORITHMS_WEIGHTS = {"template": 0.5, "mode": 0.3, "edge": 0.2}
STRINGRULES_WEIGHTS = {"rules": 0.4, "predicate": 0.3, "transform": 0.3}


def compute_difficulty(family: str, spec: dict[str, Any]) -> int:
    """Compute difficulty score (1-5) for a task based on its spec."""
    if family == "piecewise":
        return _piecewise_difficulty(spec)
    elif family == "stateful":
        return _stateful_difficulty(spec)
    elif family == "simple_algorithms":
        return _simple_algorithms_difficulty(spec)
    elif family == "stringrules":
        return _stringrules_difficulty(spec)
    raise ValueError(f"Unknown family: {family}")


def _piecewise_difficulty(spec: dict[str, Any]) -> int:
    """Compute difficulty for piecewise functions.

    Scoring:
    - Branch count (40%): 1br=1, 2br=2, 3br=3, 4br=4, 5br=5
    - Expression types (40%): affine=1, abs=2, mod=3, quadratic=4 (max of all)
    - Coefficient complexity (20%): avg(abs(coeffs)): 0-1=1, 2=2, 3=3, 4=4, 5+=5
    """
    branches = spec.get("branches", [])
    default_expr = spec.get("default_expr", {})

    n_branches = len(branches) + 1
    branch_score = min(n_branches, 5)

    branch_exprs = [b.get("expr") for b in branches]
    all_exprs = [e for e in branch_exprs if e is not None]
    if default_expr is not None:
        all_exprs.append(default_expr)
    expr_score = max((_expr_type_score(e) for e in all_exprs), default=0)

    all_coeffs = []
    for e in all_exprs:
        all_coeffs.extend(_extract_coeffs(e))
    if all_coeffs:
        avg_coeff = sum(abs(c) for c in all_coeffs) / len(all_coeffs)
        coeff_score = _coeff_to_score(avg_coeff)
    else:
        coeff_score = 1

    w = PIECEWISE_WEIGHTS
    raw = w["branches"] * branch_score + w["expr_type"] * expr_score + w["coeff"] * coeff_score
    return max(1, min(5, round(raw)))


def _expr_type_score(expr: dict[str, Any]) -> int:
    """Score expression type: affine=1, abs=2, mod=3, quadratic=4."""
    kind = expr.get("kind", "affine")
    scores = {"affine": 1, "abs": 2, "mod": 3, "quadratic": 4}
    return scores.get(kind, 1)


def _extract_coeffs(expr: dict[str, Any]) -> list[int]:
    """Extract all coefficients from an expression."""
    kind = expr.get("kind", "affine")
    if kind == "affine":
        return [expr.get("a", 0), expr.get("b", 0)]
    elif kind == "quadratic":
        return [expr.get("a", 0), expr.get("b", 0), expr.get("c", 0)]
    elif kind == "abs":
        return [expr.get("a", 0), expr.get("b", 0)]
    elif kind == "mod":
        return [expr.get("a", 0), expr.get("b", 0), expr.get("divisor", 1)]
    return []


def _coeff_to_score(avg: float) -> int:
    """Convert average coefficient magnitude to score 1-5."""
    if avg <= 1:
        return 1
    elif avg <= 2:
        return 2
    elif avg <= 3:
        return 3
    elif avg <= 4:
        return 4
    return 5


def _stateful_difficulty(spec: dict[str, Any]) -> int:
    """Compute difficulty for stateful functions.

    Scoring:
    - Template (40%): longest_run=1, conditional_linear_sum=3,
      resetting_best_prefix_sum=4
    - Predicate (30%): even/odd=1, lt/le/gt/ge=2, mod_eq=4
    - Transforms (30%): identity=1, abs/negate=2, shift/scale=3
      (avg of transforms)
    """
    template = spec.get("template", "")
    template_scores = {
        "longest_run": 1,
        "conditional_linear_sum": 3,
        "resetting_best_prefix_sum": 4,
        "toggle_sum": 4,
    }
    template_score = template_scores.get(template, 3)

    predicates = _collect_predicates(spec)
    if predicates:
        pred_score = max(_predicate_score(p) for p in predicates)
    else:
        pred_score = 1

    transforms = _collect_transforms(spec)
    if transforms:
        transform_score = sum(_transform_score(t) for t in transforms) / len(
            transforms
        )
    else:
        transform_score = 1

    w = STATEFUL_WEIGHTS
    raw = w["template"] * template_score + w["predicate"] * pred_score + w["transform"] * transform_score
    return max(1, min(5, round(raw)))


def _collect_predicates(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all predicates from a stateful spec."""
    predicates = []
    if "predicate" in spec:
        predicates.append(spec["predicate"])
    if "reset_predicate" in spec:
        predicates.append(spec["reset_predicate"])
    if "match_predicate" in spec:
        predicates.append(spec["match_predicate"])
    if "toggle_predicate" in spec:
        predicates.append(spec["toggle_predicate"])
    return predicates


def _predicate_score(pred: dict[str, Any]) -> int:
    """Score predicate complexity."""
    kind = pred.get("kind", "")
    if kind in ("even", "odd"):
        return 1
    elif kind in ("lt", "le", "gt", "ge"):
        return 2
    elif kind == "mod_eq":
        return 4
    elif kind == "in_set":
        return 3
    elif kind == "not":
        return 4
    elif kind in ("and", "or"):
        operands = pred.get("operands", [])
        return 5 if len(operands) >= 3 else 4
    return 2


def _collect_transforms(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all transforms from a stateful spec."""
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
    return transforms


def _transform_score(trans: dict[str, Any]) -> int:
    """Score transform complexity."""
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


def _simple_algorithms_difficulty(spec: dict[str, Any]) -> int:
    """Compute difficulty for simple_algorithms functions.

    Legacy scoring (no preprocess/edge fields):
    - Template (50%): most_frequent=2, count_pairs_sum=3, max_window_sum=3
    - Mode complexity (30%):
      - tie_break: smallest=1, first_seen=2
      - counting_mode: all_indices=2, unique_values=3
      - k: 1-2=1, 3-5=2, 6+=3
    - Edge cases (20%): non-zero defaults = +1

    Extended scoring (with preprocess/edge fields):
    - Template (50%): base + preprocess bonuses
    - Mode (30%): max of base mode and preprocess scores
    - Edge (20%): 1 + count of enabled edge fields
    """
    template = spec.get("template", "")
    base_template_scores = {
        "most_frequent": 2,
        "count_pairs_sum": 3,
        "max_window_sum": 3,
    }
    base_template_score = base_template_scores.get(template, 2)

    base_mode_score = 1
    if template == "most_frequent":
        tie_break = spec.get("tie_break", "smallest")
        base_mode_score = 1 if tie_break == "smallest" else 2
    elif template == "count_pairs_sum":
        counting_mode = spec.get("counting_mode", "all_indices")
        base_mode_score = 2 if counting_mode == "all_indices" else 3
    elif template == "max_window_sum":
        k = spec.get("k", 1)
        if k <= 2:
            base_mode_score = 1
        elif k <= 5:
            base_mode_score = 2
        else:
            base_mode_score = 3

    base_edge_score = 1
    if template == "most_frequent":
        if spec.get("empty_default", 0) != 0:
            base_edge_score = 2
    elif template == "max_window_sum":
        if spec.get("invalid_k_default", 0) != 0:
            base_edge_score = 2

    # Check for extended fields
    has_pre_filter = spec.get("pre_filter") is not None
    has_pre_transform = spec.get("pre_transform") is not None
    new_edge_fields = ["tie_default", "no_result_default", "short_list_default"]
    if template == "max_window_sum":
        new_edge_fields.append("empty_default")
    has_new_edge = any(spec.get(f) is not None for f in new_edge_fields)

    if not has_pre_filter and not has_pre_transform and not has_new_edge:
        # Legacy scoring — exact same formula
        w = SIMPLE_ALGORITHMS_WEIGHTS
        raw = (
            w["template"] * base_template_score
            + w["mode"] * base_mode_score
            + w["edge"] * base_edge_score
        )
        return max(1, min(5, round(raw)))

    # Extended scoring
    preprocess_bonus = 0
    preprocess_scores: list[int] = []
    if has_pre_filter:
        pre_filter = spec["pre_filter"]
        score = _predicate_score(pre_filter)
        preprocess_scores.append(score)
        preprocess_bonus += 1
    if has_pre_transform:
        pre_transform = spec["pre_transform"]
        score = _transform_score(pre_transform)
        preprocess_scores.append(score)
        preprocess_bonus += 1

    template_score = min(5, base_template_score + preprocess_bonus)

    preprocess_mode = max(preprocess_scores) if preprocess_scores else 0
    mode_score = max(base_mode_score, preprocess_mode)

    edge_count = sum(1 for f in new_edge_fields if spec.get(f) is not None)
    if base_edge_score > 1:
        edge_count += 1
    edge_score = 1 + edge_count

    w = SIMPLE_ALGORITHMS_WEIGHTS
    raw = w["template"] * template_score + w["mode"] * mode_score + w["edge"] * edge_score
    return max(1, min(5, round(raw)))


def _stringrules_difficulty(spec: dict[str, Any]) -> int:
    """Compute difficulty for stringrules functions.

    Scoring:
    - Rule count (40%): 1=1, 2=2, 3=3, 4+=4-5
    - Predicate complexity (30%): avg of predicates
    - Transform complexity (30%): avg of transforms
    """
    rules = spec.get("rules", [])
    default_transform = spec.get("default_transform", {})

    n_rules = len(rules)
    if n_rules <= 1:
        rule_score = 1
    elif n_rules == 2:
        rule_score = 2
    elif n_rules == 3:
        rule_score = 3
    elif n_rules == 4:
        rule_score = 4
    else:
        rule_score = 5

    pred_scores = [
        _string_predicate_score(r.get("predicate", {})) for r in rules
    ]
    pred_score = sum(pred_scores) / len(pred_scores) if pred_scores else 1

    all_transforms = [r.get("transform", {}) for r in rules] + [
        default_transform
    ]
    trans_scores = [_string_transform_score(t) for t in all_transforms]
    trans_score = sum(trans_scores) / len(trans_scores) if trans_scores else 1

    w = STRINGRULES_WEIGHTS
    raw = w["rules"] * rule_score + w["predicate"] * pred_score + w["transform"] * trans_score
    return max(1, min(5, round(raw)))


def _string_predicate_score(pred: dict[str, Any]) -> int:
    """Score string predicate complexity."""
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
    """Score string transform complexity."""
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
