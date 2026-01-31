from typing import Any


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
    return 3


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

    all_exprs = [b["expr"] for b in branches] + [default_expr]
    expr_score = max(_expr_type_score(e) for e in all_exprs)

    all_coeffs = []
    for e in all_exprs:
        all_coeffs.extend(_extract_coeffs(e))
    if all_coeffs:
        avg_coeff = sum(abs(c) for c in all_coeffs) / len(all_coeffs)
        coeff_score = _coeff_to_score(avg_coeff)
    else:
        coeff_score = 1

    raw = 0.4 * branch_score + 0.4 * expr_score + 0.2 * coeff_score
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
    - Template (40%): longest_run=1, conditional_linear_sum=3, resetting_best_prefix_sum=4
    - Predicate (30%): even/odd=1, lt/le/gt/ge=2, mod_eq=4
    - Transforms (30%): identity=1, abs/negate=2, shift/scale=3 (avg of transforms)
    """
    template = spec.get("template", "")
    template_scores = {
        "longest_run": 1,
        "conditional_linear_sum": 3,
        "resetting_best_prefix_sum": 4,
    }
    template_score = template_scores.get(template, 3)

    predicates = _collect_predicates(spec)
    if predicates:
        pred_score = max(_predicate_score(p) for p in predicates)
    else:
        pred_score = 1

    transforms = _collect_transforms(spec)
    if transforms:
        transform_score = sum(_transform_score(t) for t in transforms) / len(transforms)
    else:
        transform_score = 1

    raw = 0.4 * template_score + 0.3 * pred_score + 0.3 * transform_score
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
    return predicates


def _predicate_score(pred: dict[str, Any]) -> int:
    """Score predicate: even/odd=1, lt/le/gt/ge=2, mod_eq=4."""
    kind = pred.get("kind", "")
    if kind in ("even", "odd"):
        return 1
    elif kind in ("lt", "le", "gt", "ge"):
        return 2
    elif kind == "mod_eq":
        return 4
    elif kind == "in_set":
        return 3
    return 2


def _collect_transforms(spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect all transforms from a stateful spec."""
    transforms = []
    if "true_transform" in spec:
        transforms.append(spec["true_transform"])
    if "false_transform" in spec:
        transforms.append(spec["false_transform"])
    return transforms


def _transform_score(trans: dict[str, Any]) -> int:
    """Score transform: identity=1, abs/negate=2, shift/scale=3."""
    kind = trans.get("kind", "identity")
    if kind == "identity":
        return 1
    elif kind in ("abs", "negate"):
        return 2
    elif kind in ("shift", "scale", "clip"):
        return 3
    return 1
