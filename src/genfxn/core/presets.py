"""Difficulty-targeted axes presets for task generation.

Each family has multiple preset configurations per difficulty level,
enabling variety while targeting specific difficulty scores.
"""

import random
from dataclasses import dataclass
from typing import Any

from genfxn.core.predicates import PredicateType
from genfxn.core.string_predicates import StringPredicateType
from genfxn.core.string_transforms import StringTransformType
from genfxn.core.transforms import TransformType
from genfxn.piecewise.models import ExprType, PiecewiseAxes
from genfxn.simple_algorithms.models import (
    CountingMode,
    SimpleAlgorithmsAxes,
    TieBreakMode,
)
from genfxn.simple_algorithms.models import (
    TemplateType as SimpleAlgoTemplateType,
)
from genfxn.stateful.models import (
    StatefulAxes,
)
from genfxn.stateful.models import (
    TemplateType as StatefulTemplateType,
)
from genfxn.stringrules.models import StringRulesAxes


@dataclass
class DifficultyPreset:
    """A single axes configuration targeting a specific difficulty."""

    name: str
    description: str
    axes_overrides: dict[str, Any]


# =============================================================================
# Piecewise Presets
# Formula: raw = 0.4 × branch_score + 0.4 × expr_score + 0.2 × coeff_score
# =============================================================================

PIECEWISE_PRESETS: dict[int, list[DifficultyPreset]] = {
    1: [
        DifficultyPreset(
            "1A",
            "minimal: 1 branch, affine, small coeffs",
            {
                "n_branches": 1,
                "expr_types": [ExprType.AFFINE],
                "coeff_range": (-1, 1),
            },
        ),
    ],
    2: [
        DifficultyPreset(
            "2A",
            "more branches, simple exprs",
            {
                "n_branches": 2,
                "expr_types": [ExprType.AFFINE],
                "coeff_range": (-2, 2),
            },
        ),
        DifficultyPreset(
            "2B",
            "3 branches, affine, small coeffs",
            {
                "n_branches": 3,
                "expr_types": [ExprType.AFFINE],
                "coeff_range": (-1, 1),
            },
        ),
        DifficultyPreset(
            "2C",
            "1 branch, abs exprs, medium coeffs",
            {
                "n_branches": 1,
                "expr_types": [ExprType.ABS],
                "coeff_range": (-2, 2),
            },
        ),
    ],
    3: [
        DifficultyPreset(
            "3A",
            "3 branches, mod exprs",
            {
                "n_branches": 3,
                "expr_types": [ExprType.MOD],
                "coeff_range": (-1, 1),
            },
        ),
        DifficultyPreset(
            "3B",
            "2 branches, quadratic",
            {
                "n_branches": 2,
                "expr_types": [ExprType.QUADRATIC],
                "coeff_range": (-1, 1),
            },
        ),
        DifficultyPreset(
            "3C",
            "4 branches, abs, medium coeffs",
            {
                "n_branches": 4,
                "expr_types": [ExprType.ABS],
                "coeff_range": (-2, 2),
            },
        ),
        DifficultyPreset(
            "3D",
            "3 branches, abs, large coeffs",
            {
                "n_branches": 3,
                "expr_types": [ExprType.ABS],
                "coeff_range": (-4, 4),
            },
        ),
    ],
    4: [
        DifficultyPreset(
            "4A",
            "5 branches, abs, large coeffs",
            {
                "n_branches": 5,
                "expr_types": [ExprType.ABS],
                "coeff_range": (-4, 4),
            },
        ),
        DifficultyPreset(
            "4B",
            "4 branches, quadratic, medium coeffs",
            {
                "n_branches": 4,
                "expr_types": [ExprType.QUADRATIC],
                "coeff_range": (-2, 2),
            },
        ),
        DifficultyPreset(
            "4C",
            "3 branches, quadratic, large coeffs",
            {
                "n_branches": 3,
                "expr_types": [ExprType.QUADRATIC],
                "coeff_range": (-5, 5),
            },
        ),
    ],
    5: [
        DifficultyPreset(
            "5A",
            "5 branches, quadratic, very large coeffs",
            {
                "n_branches": 5,
                "expr_types": [ExprType.QUADRATIC],
                "coeff_range": (-10, 10),
            },
        ),
        DifficultyPreset(
            "5B",
            "5 branches, mod+quadratic, very large coeffs",
            {
                "n_branches": 5,
                "expr_types": [ExprType.MOD, ExprType.QUADRATIC],
                "coeff_range": (-10, 10),
            },
        ),
    ],
}


# =============================================================================
# Stateful Presets
# Formula: raw = 0.4 × template + 0.3 × predicate + 0.3 × transform_avg
# =============================================================================

STATEFUL_PRESETS: dict[int, list[DifficultyPreset]] = {
    1: [
        DifficultyPreset(
            "1A",
            "longest_run, even/odd",
            {
                "templates": [StatefulTemplateType.LONGEST_RUN],
                "predicate_types": [PredicateType.EVEN, PredicateType.ODD],
            },
        ),
        DifficultyPreset(
            "1B",
            "longest_run, comparison",
            {
                "templates": [StatefulTemplateType.LONGEST_RUN],
                "predicate_types": [
                    PredicateType.LT,
                    PredicateType.LE,
                    PredicateType.GT,
                    PredicateType.GE,
                ],
            },
        ),
    ],
    2: [
        DifficultyPreset(
            "2A",
            "longest_run, mod_eq",
            {
                "templates": [StatefulTemplateType.LONGEST_RUN],
                "predicate_types": [PredicateType.MOD_EQ],
            },
        ),
        DifficultyPreset(
            "2B",
            "conditional, even/odd, identity",
            {
                "templates": [StatefulTemplateType.CONDITIONAL_LINEAR_SUM],
                "predicate_types": [PredicateType.EVEN, PredicateType.ODD],
                "transform_types": [TransformType.IDENTITY],
            },
        ),
        DifficultyPreset(
            "2C",
            "conditional, comparison, identity",
            {
                "templates": [StatefulTemplateType.CONDITIONAL_LINEAR_SUM],
                "predicate_types": [
                    PredicateType.LT,
                    PredicateType.LE,
                    PredicateType.GT,
                    PredicateType.GE,
                ],
                "transform_types": [TransformType.IDENTITY],
            },
        ),
    ],
    3: [
        DifficultyPreset(
            "3A",
            "conditional, comparison, shift/scale",
            {
                "templates": [StatefulTemplateType.CONDITIONAL_LINEAR_SUM],
                "predicate_types": [
                    PredicateType.LT,
                    PredicateType.LE,
                    PredicateType.GT,
                    PredicateType.GE,
                ],
                "transform_types": [TransformType.SHIFT, TransformType.SCALE],
            },
        ),
        DifficultyPreset(
            "3B",
            "conditional, mod_eq, abs/negate",
            {
                "templates": [StatefulTemplateType.CONDITIONAL_LINEAR_SUM],
                "predicate_types": [PredicateType.MOD_EQ],
                "transform_types": [TransformType.ABS, TransformType.NEGATE],
            },
        ),
        DifficultyPreset(
            "3C",
            "conditional, mod_eq, shift/scale",
            {
                "templates": [StatefulTemplateType.CONDITIONAL_LINEAR_SUM],
                "predicate_types": [PredicateType.MOD_EQ],
                "transform_types": [TransformType.SHIFT, TransformType.SCALE],
            },
        ),
        DifficultyPreset(
            "3D",
            "resetting, mod_eq",
            {
                "templates": [StatefulTemplateType.RESETTING_BEST_PREFIX_SUM],
                "predicate_types": [PredicateType.MOD_EQ],
            },
        ),
    ],
    4: [
        DifficultyPreset(
            "4A",
            "toggle_sum, mod_eq, shift/scale",
            {
                "templates": [StatefulTemplateType.TOGGLE_SUM],
                "predicate_types": [PredicateType.MOD_EQ],
                "transform_types": [TransformType.SHIFT, TransformType.SCALE],
            },
        ),
        DifficultyPreset(
            "4B",
            "resetting, mod_eq, shift value_transform",
            {
                "templates": [StatefulTemplateType.RESETTING_BEST_PREFIX_SUM],
                "predicate_types": [PredicateType.MOD_EQ],
                "transform_types": [TransformType.SHIFT, TransformType.SCALE],
            },
        ),
        DifficultyPreset(
            "4C",
            "toggle_sum, composed NOT, pipeline transform",
            {
                "templates": [StatefulTemplateType.TOGGLE_SUM],
                "predicate_types": [PredicateType.NOT],
                "transform_types": [TransformType.PIPELINE],
            },
        ),
    ],
    5: [
        DifficultyPreset(
            "5A",
            "toggle_sum, composed AND (3+), pipeline transform",
            {
                "templates": [StatefulTemplateType.TOGGLE_SUM],
                "predicate_types": [PredicateType.AND],
                "transform_types": [TransformType.PIPELINE],
                "min_composed_operands": 3,
            },
        ),
        DifficultyPreset(
            "5B",
            "resetting, composed AND (3+), pipeline transform",
            {
                "templates": [StatefulTemplateType.RESETTING_BEST_PREFIX_SUM],
                "predicate_types": [PredicateType.AND],
                "transform_types": [TransformType.PIPELINE],
                "min_composed_operands": 3,
            },
        ),
        DifficultyPreset(
            "5C",
            "toggle_sum, composed OR (3+), pipeline transform",
            {
                "templates": [StatefulTemplateType.TOGGLE_SUM],
                "predicate_types": [PredicateType.OR],
                "transform_types": [TransformType.PIPELINE],
                "min_composed_operands": 3,
            },
        ),
    ],
}


# =============================================================================
# Simple Algorithms Presets
# Formula: raw = 0.5*template + 0.3*mode + 0.2*edge
# =============================================================================

SIMPLE_ALGORITHMS_PRESETS: dict[int, list[DifficultyPreset]] = {
    2: [
        DifficultyPreset(
            "2A",
            "most_frequent, smallest tie-break, zero default",
            {
                "templates": [SimpleAlgoTemplateType.MOST_FREQUENT],
                "tie_break_modes": [TieBreakMode.SMALLEST],
                "empty_default_range": (0, 0),
            },
        ),
        DifficultyPreset(
            "2B",
            "most_frequent, first_seen, zero default",
            {
                "templates": [SimpleAlgoTemplateType.MOST_FREQUENT],
                "tie_break_modes": [TieBreakMode.FIRST_SEEN],
                "empty_default_range": (0, 0),
            },
        ),
        DifficultyPreset(
            "2C",
            "max_window_sum, small k",
            {
                "templates": [SimpleAlgoTemplateType.MAX_WINDOW_SUM],
                "window_size_range": (1, 2),
                "empty_default_range": (0, 0),
            },
        ),
        DifficultyPreset(
            "2D",
            "count_pairs_sum, all_indices",
            {
                "templates": [SimpleAlgoTemplateType.COUNT_PAIRS_SUM],
                "counting_modes": [CountingMode.ALL_INDICES],
            },
        ),
    ],
    3: [
        DifficultyPreset(
            "3A",
            "max_window_sum, large k, non-zero default",
            {
                "templates": [SimpleAlgoTemplateType.MAX_WINDOW_SUM],
                "window_size_range": (6, 10),
                "empty_default_range": (-10, -1),
            },
        ),
        DifficultyPreset(
            "3B",
            "count_pairs_sum, unique_values",
            {
                "templates": [SimpleAlgoTemplateType.COUNT_PAIRS_SUM],
                "counting_modes": [CountingMode.UNIQUE_VALUES],
            },
        ),
    ],
    4: [
        DifficultyPreset(
            "4A",
            "most_frequent, filter+transform, tie_default",
            {
                "templates": [SimpleAlgoTemplateType.MOST_FREQUENT],
                "tie_break_modes": [TieBreakMode.FIRST_SEEN],
                "pre_filter_types": [PredicateType.MOD_EQ],
                "pre_transform_types": [TransformType.SHIFT],
                "tie_default_range": (-10, 10),
            },
        ),
        DifficultyPreset(
            "4B",
            "max_window_sum, filter, empty_default",
            {
                "templates": [SimpleAlgoTemplateType.MAX_WINDOW_SUM],
                "window_size_range": (6, 10),
                "pre_filter_types": [PredicateType.MOD_EQ],
                "empty_default_for_empty_range": (-10, 10),
            },
        ),
        DifficultyPreset(
            "4C",
            "count_pairs, filter, no_result_default",
            {
                "templates": [SimpleAlgoTemplateType.COUNT_PAIRS_SUM],
                "counting_modes": [CountingMode.UNIQUE_VALUES],
                "pre_filter_types": [PredicateType.MOD_EQ],
                "no_result_default_range": (-10, 10),
            },
        ),
    ],
    5: [
        DifficultyPreset(
            "5A",
            "count_pairs, composed filter, pipeline, edge defaults",
            {
                "templates": [SimpleAlgoTemplateType.COUNT_PAIRS_SUM],
                "counting_modes": [CountingMode.UNIQUE_VALUES],
                "pre_filter_types": [PredicateType.AND],
                "pre_transform_types": [TransformType.PIPELINE],
                "no_result_default_range": (-10, 10),
                "short_list_default_range": (-5, 5),
            },
        ),
        DifficultyPreset(
            "5B",
            "max_window_sum, composed filter, pipeline, edge defaults",
            {
                "templates": [SimpleAlgoTemplateType.MAX_WINDOW_SUM],
                "window_size_range": (6, 10),
                "empty_default_range": (-10, -1),
                "pre_filter_types": [PredicateType.OR],
                "pre_transform_types": [TransformType.PIPELINE],
                "empty_default_for_empty_range": (-10, 10),
            },
        ),
    ],
}


# =============================================================================
# Stringrules Presets
# Formula: raw = 0.4 × rule_count + 0.3 × pred_avg + 0.3 × trans_avg
# Max achievable: ~3.8 (difficulty 4)
# =============================================================================

STRINGRULES_PRESETS: dict[int, list[DifficultyPreset]] = {
    1: [
        DifficultyPreset(
            "1A",
            "1 rule, simple pred, identity",
            {
                "n_rules": 1,
                "predicate_types": [
                    StringPredicateType.IS_ALPHA,
                    StringPredicateType.IS_DIGIT,
                    StringPredicateType.IS_UPPER,
                    StringPredicateType.IS_LOWER,
                ],
                "transform_types": [StringTransformType.IDENTITY],
            },
        ),
        DifficultyPreset(
            "1B",
            "1 rule, simple pred, case transform",
            {
                "n_rules": 1,
                "predicate_types": [
                    StringPredicateType.IS_ALPHA,
                    StringPredicateType.IS_DIGIT,
                    StringPredicateType.IS_UPPER,
                    StringPredicateType.IS_LOWER,
                ],
                "transform_types": [
                    StringTransformType.LOWERCASE,
                    StringTransformType.UPPERCASE,
                ],
            },
        ),
        DifficultyPreset(
            "1C",
            "2 rules, simple pred, identity",
            {
                "n_rules": 2,
                "predicate_types": [
                    StringPredicateType.IS_ALPHA,
                    StringPredicateType.IS_DIGIT,
                    StringPredicateType.IS_UPPER,
                    StringPredicateType.IS_LOWER,
                ],
                "transform_types": [StringTransformType.IDENTITY],
            },
        ),
    ],
    2: [
        DifficultyPreset(
            "2A",
            "2 rules, simple pred, case transform",
            {
                "n_rules": 2,
                "predicate_types": [
                    StringPredicateType.IS_ALPHA,
                    StringPredicateType.IS_DIGIT,
                    StringPredicateType.IS_UPPER,
                    StringPredicateType.IS_LOWER,
                ],
                "transform_types": [
                    StringTransformType.LOWERCASE,
                    StringTransformType.UPPERCASE,
                ],
            },
        ),
        DifficultyPreset(
            "2B",
            "1 rule, pattern pred, parameterized transform",
            {
                "n_rules": 1,
                "predicate_types": [
                    StringPredicateType.STARTS_WITH,
                    StringPredicateType.ENDS_WITH,
                ],
                "transform_types": [StringTransformType.REPLACE],
            },
        ),
        DifficultyPreset(
            "2C",
            "3 rules, simple pred, identity",
            {
                "n_rules": 3,
                "predicate_types": [
                    StringPredicateType.IS_ALPHA,
                    StringPredicateType.IS_DIGIT,
                    StringPredicateType.IS_UPPER,
                    StringPredicateType.IS_LOWER,
                ],
                "transform_types": [StringTransformType.IDENTITY],
            },
        ),
    ],
    3: [
        DifficultyPreset(
            "3A",
            "4 rules, pattern pred, parameterized transform",
            {
                "n_rules": 4,
                "predicate_types": [
                    StringPredicateType.STARTS_WITH,
                    StringPredicateType.ENDS_WITH,
                ],
                "transform_types": [StringTransformType.REPLACE],
            },
        ),
        DifficultyPreset(
            "3B",
            "5 rules, simple pred, case transform",
            {
                "n_rules": 5,
                "predicate_types": [
                    StringPredicateType.IS_ALPHA,
                    StringPredicateType.IS_DIGIT,
                    StringPredicateType.IS_UPPER,
                    StringPredicateType.IS_LOWER,
                ],
                "transform_types": [
                    StringTransformType.LOWERCASE,
                    StringTransformType.UPPERCASE,
                ],
            },
        ),
        DifficultyPreset(
            "3C",
            "4 rules, simple pred, parameterized transform",
            {
                "n_rules": 4,
                "predicate_types": [
                    StringPredicateType.IS_ALPHA,
                    StringPredicateType.IS_DIGIT,
                    StringPredicateType.IS_UPPER,
                    StringPredicateType.IS_LOWER,
                ],
                "transform_types": [StringTransformType.REPLACE],
            },
        ),
    ],
    4: [
        DifficultyPreset(
            "4A",
            "7 rules, pattern pred, parameterized transform",
            {
                "n_rules": 7,
                "predicate_types": [
                    StringPredicateType.STARTS_WITH,
                    StringPredicateType.ENDS_WITH,
                ],
                "transform_types": [StringTransformType.REPLACE],
            },
        ),
        DifficultyPreset(
            "4B",
            "6 rules, length_cmp, parameterized transform",
            {
                "n_rules": 6,
                "predicate_types": [StringPredicateType.LENGTH_CMP],
                "transform_types": [StringTransformType.REPLACE],
            },
        ),
        DifficultyPreset(
            "4C",
            "7 rules, simple pred, parameterized transform",
            {
                "n_rules": 7,
                "predicate_types": [
                    StringPredicateType.IS_ALPHA,
                    StringPredicateType.IS_DIGIT,
                    StringPredicateType.IS_UPPER,
                    StringPredicateType.IS_LOWER,
                ],
                "transform_types": [StringTransformType.REPLACE],
            },
        ),
    ],
    5: [
        DifficultyPreset(
            "5A",
            "8 rules, composed AND, pipeline transforms",
            {
                "n_rules": 8,
                "predicate_types": [StringPredicateType.AND],
                "transform_types": [StringTransformType.PIPELINE],
            },
        ),
        DifficultyPreset(
            "5B",
            "10 rules, composed OR, pipeline transforms",
            {
                "n_rules": 10,
                "predicate_types": [StringPredicateType.OR],
                "transform_types": [StringTransformType.PIPELINE],
            },
        ),
        DifficultyPreset(
            "5C",
            "6 rules, composed AND+OR, pipeline transforms",
            {
                "n_rules": 6,
                "predicate_types": [
                    StringPredicateType.AND,
                    StringPredicateType.OR,
                ],
                "transform_types": [StringTransformType.PIPELINE],
            },
        ),
    ],
}


# =============================================================================
# Lookup Functions
# =============================================================================

_FAMILY_PRESETS: dict[str, dict[int, list[DifficultyPreset]]] = {
    "piecewise": PIECEWISE_PRESETS,
    "stateful": STATEFUL_PRESETS,
    "simple_algorithms": SIMPLE_ALGORITHMS_PRESETS,
    "stringrules": STRINGRULES_PRESETS,
}


def get_valid_difficulties(family: str) -> list[int]:
    """Return valid difficulty levels for a family."""
    presets = _FAMILY_PRESETS.get(family)
    if presets is None:
        raise ValueError(f"Unknown family: {family}")
    return sorted(presets.keys())


def get_difficulty_presets(
    family: str, difficulty: int
) -> list[DifficultyPreset]:
    """Get all presets for a family/difficulty combination."""
    presets = _FAMILY_PRESETS.get(family)
    if presets is None:
        raise ValueError(f"Unknown family: {family}")

    valid = get_valid_difficulties(family)
    if difficulty not in presets:
        raise ValueError(
            f"Invalid difficulty {difficulty} for {family}. Valid: {valid}"
        )

    return presets[difficulty]


def get_difficulty_axes(
    family: str,
    difficulty: int,
    variant: str | None = None,
    rng: random.Random | None = None,
) -> PiecewiseAxes | StatefulAxes | SimpleAlgorithmsAxes | StringRulesAxes:
    """Return axes for target difficulty.

    Args:
        family: Task family name
        difficulty: Target difficulty level (1-5, depends on family)
        variant: Specific preset variant (e.g., "3A", "3B"). Random if None.
        rng: Random generator for selecting variant when not specified.

    Returns:
        Axes object configured for target difficulty.

    Raises:
        ValueError: If family, difficulty, or variant is invalid.
    """
    presets = get_difficulty_presets(family, difficulty)

    if variant is not None:
        matching = [p for p in presets if p.name == variant]
        if not matching:
            valid_variants = [p.name for p in presets]
            raise ValueError(
                f"Invalid variant '{variant}' for {family} difficulty "
                f"{difficulty}. Valid: {valid_variants}"
            )
        preset = matching[0]
    else:
        if rng is None:
            rng = random.Random()
        preset = rng.choice(presets)

    return _build_axes(family, preset.axes_overrides)


def _build_axes(
    family: str, overrides: dict[str, Any]
) -> PiecewiseAxes | StatefulAxes | SimpleAlgorithmsAxes | StringRulesAxes:
    """Build axes object from overrides."""
    match family:
        case "piecewise":
            return PiecewiseAxes(**overrides)
        case "stateful":
            return StatefulAxes(**overrides)
        case "simple_algorithms":
            return SimpleAlgorithmsAxes(**overrides)
        case "stringrules":
            return StringRulesAxes(**overrides)
        case _:
            raise ValueError(f"Unknown family: {family}")
