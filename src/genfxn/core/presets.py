"""Difficulty-targeted axes presets for task generation.

Each family has multiple preset configurations per difficulty level,
enabling variety while targeting specific difficulty scores.
"""

import random
from dataclasses import dataclass
from typing import Any

from genfxn.bitops.models import BitOp, BitopsAxes
from genfxn.core.predicates import PredicateType
from genfxn.core.string_predicates import StringPredicateType
from genfxn.core.string_transforms import StringTransformType
from genfxn.core.transforms import TransformType
from genfxn.fsm.models import (
    FsmAxes,
    MachineType,
    OutputMode,
    UndefinedTransitionPolicy,
)
from genfxn.fsm.models import (
    PredicateType as FsmPredicateType,
)
from genfxn.piecewise.models import ExprType, PiecewiseAxes
from genfxn.sequence_dp.models import (
    OutputMode as SequenceDpOutputMode,
)
from genfxn.sequence_dp.models import (
    PredicateType as SequenceDpPredicateType,
)
from genfxn.sequence_dp.models import (
    SequenceDpAxes,
    TieBreakOrder,
)
from genfxn.sequence_dp.models import (
    TemplateType as SequenceDpTemplateType,
)
from genfxn.simple_algorithms.models import (
    CountingMode,
    SimpleAlgorithmsAxes,
    TieBreakMode,
)
from genfxn.simple_algorithms.models import (
    TemplateType as SimpleAlgoTemplateType,
)
from genfxn.stack_bytecode.models import (
    InputMode,
    JumpTargetMode,
    StackBytecodeAxes,
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
            "5 branches, quadratic, large coeffs",
            {
                "n_branches": 5,
                "expr_types": [ExprType.QUADRATIC],
                "coeff_range": (-4, 4),
            },
        ),
        DifficultyPreset(
            "4B",
            "4 branches, quadratic, medium coeffs",
            {
                "n_branches": 4,
                "expr_types": [ExprType.QUADRATIC],
                "coeff_range": (-3, 3),
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
# Stack Bytecode Presets
# Difficulty maps directly from target_difficulty in stack axes.
# =============================================================================

STACK_BYTECODE_PRESETS: dict[int, list[DifficultyPreset]] = {
    1: [
        DifficultyPreset(
            "1A",
            "linear, tiny programs with direct input and strict jumps",
            {
                "target_difficulty": 1,
                "max_step_count_range": (20, 32),
                "jump_target_modes": [JumpTargetMode.ERROR],
                "input_modes": [InputMode.DIRECT],
            },
        )
    ],
    2: [
        DifficultyPreset(
            "2A",
            "small arithmetic programs, still strict control",
            {
                "target_difficulty": 2,
                "max_step_count_range": (32, 64),
                "jump_target_modes": [JumpTargetMode.ERROR],
                "input_modes": [InputMode.DIRECT],
            },
        )
    ],
    3: [
        DifficultyPreset(
            "3A",
            "medium programs, mixed jump handling",
            {
                "target_difficulty": 3,
                "max_step_count_range": (64, 96),
                "jump_target_modes": [
                    JumpTargetMode.ERROR,
                    JumpTargetMode.CLAMP,
                ],
                "input_modes": [InputMode.DIRECT, InputMode.CYCLIC],
            },
        )
    ],
    4: [
        DifficultyPreset(
            "4A",
            "larger programs with conditional control flow",
            {
                "target_difficulty": 4,
                "max_step_count_range": (96, 128),
                "jump_target_modes": [
                    JumpTargetMode.CLAMP,
                    JumpTargetMode.WRAP,
                ],
                "input_modes": [InputMode.DIRECT, InputMode.CYCLIC],
            },
        )
    ],
    5: [
        DifficultyPreset(
            "5A",
            "loop-heavy programs with permissive runtime modes",
            {
                "target_difficulty": 5,
                "max_step_count_range": (128, 160),
                "jump_target_modes": [JumpTargetMode.WRAP],
                "input_modes": [InputMode.CYCLIC],
            },
        )
    ],
}

# =============================================================================
# FSM Presets
# Difficulty maps directly from target_difficulty in FSM axes.
# =============================================================================

FSM_PRESETS: dict[int, list[DifficultyPreset]] = {
    1: [
        DifficultyPreset(
            "1A",
            "small moore machines with simple predicates and stay policy",
            {
                "target_difficulty": 1,
                "machine_types": [MachineType.MOORE],
                "output_modes": [OutputMode.FINAL_STATE_ID],
                "undefined_transition_policies": [
                    UndefinedTransitionPolicy.STAY
                ],
                "predicate_types": [
                    FsmPredicateType.EVEN,
                    FsmPredicateType.ODD,
                ],
                "n_states_range": (2, 2),
                "transitions_per_state_range": (0, 1),
            },
        )
    ],
    2: [
        DifficultyPreset(
            "2A",
            "slightly larger moore machines with comparison predicates",
            {
                "target_difficulty": 2,
                "machine_types": [MachineType.MOORE],
                "output_modes": [
                    OutputMode.FINAL_STATE_ID,
                    OutputMode.ACCEPT_BOOL,
                ],
                "undefined_transition_policies": [
                    UndefinedTransitionPolicy.STAY,
                    UndefinedTransitionPolicy.SINK,
                ],
                "predicate_types": [
                    FsmPredicateType.EVEN,
                    FsmPredicateType.ODD,
                    FsmPredicateType.LT,
                    FsmPredicateType.GT,
                ],
                "n_states_range": (2, 3),
                "transitions_per_state_range": (1, 2),
            },
        )
    ],
    3: [
        DifficultyPreset(
            "3A",
            "mixed machine/output styles with moderate branching",
            {
                "target_difficulty": 3,
                "machine_types": [MachineType.MOORE, MachineType.MEALY],
                "output_modes": [
                    OutputMode.FINAL_STATE_ID,
                    OutputMode.ACCEPT_BOOL,
                ],
                "undefined_transition_policies": [
                    UndefinedTransitionPolicy.STAY,
                    UndefinedTransitionPolicy.SINK,
                ],
                "predicate_types": [
                    FsmPredicateType.LT,
                    FsmPredicateType.LE,
                    FsmPredicateType.GT,
                    FsmPredicateType.GE,
                    FsmPredicateType.EVEN,
                    FsmPredicateType.ODD,
                ],
                "n_states_range": (3, 4),
                "transitions_per_state_range": (1, 3),
            },
        )
    ],
    4: [
        DifficultyPreset(
            "4A",
            "mealy-heavy machines with sink/error handling",
            {
                "target_difficulty": 4,
                "machine_types": [MachineType.MEALY, MachineType.MOORE],
                "output_modes": [
                    OutputMode.TRANSITION_COUNT,
                    OutputMode.ACCEPT_BOOL,
                ],
                "undefined_transition_policies": [
                    UndefinedTransitionPolicy.SINK,
                    UndefinedTransitionPolicy.ERROR,
                ],
                "predicate_types": [
                    FsmPredicateType.MOD_EQ,
                    FsmPredicateType.LT,
                    FsmPredicateType.LE,
                    FsmPredicateType.GT,
                    FsmPredicateType.GE,
                ],
                "n_states_range": (4, 5),
                "transitions_per_state_range": (2, 3),
            },
        )
    ],
    5: [
        DifficultyPreset(
            "5A",
            "larger mealy machines with error policy and mod predicates",
            {
                "target_difficulty": 5,
                "machine_types": [MachineType.MEALY],
                "output_modes": [OutputMode.TRANSITION_COUNT],
                "undefined_transition_policies": [
                    UndefinedTransitionPolicy.ERROR
                ],
                "predicate_types": [
                    FsmPredicateType.MOD_EQ,
                    FsmPredicateType.LE,
                    FsmPredicateType.GE,
                    FsmPredicateType.LT,
                    FsmPredicateType.GT,
                ],
                "n_states_range": (5, 6),
                "transitions_per_state_range": (3, 4),
            },
        )
    ],
}

# =============================================================================
# Bitops Presets
# Difficulty maps directly from target_difficulty in bitops axes.
# =============================================================================

BITOPS_PRESETS: dict[int, list[DifficultyPreset]] = {
    1: [
        DifficultyPreset(
            "1A",
            "tiny bit pipelines at lowest target difficulty",
            {
                "target_difficulty": 1,
                "width_choices": [8],
                "n_ops_range": (1, 2),
                "allowed_ops": [
                    BitOp.AND_MASK,
                    BitOp.OR_MASK,
                    BitOp.XOR_MASK,
                    BitOp.NOT,
                ],
            },
        )
    ],
    2: [
        DifficultyPreset(
            "2A",
            "small bit pipelines at target difficulty 2",
            {
                "target_difficulty": 2,
                "width_choices": [16],
                "n_ops_range": (3, 3),
                "allowed_ops": [
                    BitOp.AND_MASK,
                    BitOp.OR_MASK,
                    BitOp.XOR_MASK,
                    BitOp.NOT,
                    BitOp.SHL,
                    BitOp.SHR_LOGICAL,
                ],
            },
        )
    ],
    3: [
        DifficultyPreset(
            "3A",
            "moderate bit pipelines at target difficulty 3",
            {
                "target_difficulty": 3,
                "width_choices": [24],
                "n_ops_range": (4, 4),
                "allowed_ops": [
                    BitOp.SHL,
                    BitOp.SHR_LOGICAL,
                    BitOp.ROTL,
                    BitOp.ROTR,
                    BitOp.NOT,
                ],
            },
        )
    ],
    4: [
        DifficultyPreset(
            "4A",
            "complex bit pipelines at target difficulty 4",
            {
                "target_difficulty": 4,
                "width_choices": [32],
                "n_ops_range": (5, 5),
                "allowed_ops": [
                    BitOp.ROTL,
                    BitOp.ROTR,
                    BitOp.POPCOUNT,
                    BitOp.PARITY,
                    BitOp.XOR_MASK,
                ],
            },
        )
    ],
    5: [
        DifficultyPreset(
            "5A",
            "advanced bit pipelines at highest target difficulty",
            {
                "target_difficulty": 5,
                "width_choices": [16],
                "n_ops_range": (6, 7),
                "allowed_ops": [
                    BitOp.POPCOUNT,
                    BitOp.PARITY,
                    BitOp.ROTL,
                    BitOp.ROTR,
                    BitOp.SHR_LOGICAL,
                ],
            },
        )
    ],
}

# =============================================================================
# Sequence DP Presets
# Difficulty maps directly from target_difficulty in sequence_dp axes.
# =============================================================================

SEQUENCE_DP_PRESETS: dict[int, list[DifficultyPreset]] = {
    1: [
        DifficultyPreset(
            "1A",
            "global score with equality and large positive margin",
            {
                "target_difficulty": 1,
                "templates": [SequenceDpTemplateType.GLOBAL],
                "output_modes": [SequenceDpOutputMode.SCORE],
                "predicate_types": [SequenceDpPredicateType.EQ],
                "tie_break_orders": [TieBreakOrder.DIAG_UP_LEFT],
                "len_a_range": (2, 4),
                "len_b_range": (2, 4),
                "value_range": (-10, 10),
                "match_score_range": (7, 7),
                "mismatch_score_range": (-5, -5),
                "gap_score_range": (-5, -5),
            },
        )
    ],
    2: [
        DifficultyPreset(
            "2A",
            "global alignment length with strict abs-diff predicate",
            {
                "target_difficulty": 2,
                "templates": [SequenceDpTemplateType.GLOBAL],
                "output_modes": [SequenceDpOutputMode.ALIGNMENT_LEN],
                "predicate_types": [SequenceDpPredicateType.ABS_DIFF_LE],
                "tie_break_orders": [TieBreakOrder.DIAG_LEFT_UP],
                "len_a_range": (3, 6),
                "len_b_range": (3, 6),
                "value_range": (-15, 15),
                "abs_diff_range": (0, 0),
                "match_score_range": (5, 5),
                "mismatch_score_range": (0, 0),
                "gap_score_range": (-1, -1),
            },
        )
    ],
    3: [
        DifficultyPreset(
            "3A",
            "global alignment length with medium abs-diff and tie complexity",
            {
                "target_difficulty": 3,
                "templates": [SequenceDpTemplateType.GLOBAL],
                "output_modes": [SequenceDpOutputMode.ALIGNMENT_LEN],
                "predicate_types": [SequenceDpPredicateType.ABS_DIFF_LE],
                "tie_break_orders": [TieBreakOrder.UP_DIAG_LEFT],
                "len_a_range": (4, 8),
                "len_b_range": (4, 8),
                "value_range": (-20, 20),
                "abs_diff_range": (2, 2),
                "match_score_range": (3, 3),
                "mismatch_score_range": (1, 1),
                "gap_score_range": (-1, -1),
            },
        )
    ],
    4: [
        DifficultyPreset(
            "4A",
            "local alignment with modular matching and advanced tie-break",
            {
                "target_difficulty": 4,
                "templates": [SequenceDpTemplateType.LOCAL],
                "output_modes": [SequenceDpOutputMode.ALIGNMENT_LEN],
                "predicate_types": [SequenceDpPredicateType.MOD_EQ],
                "tie_break_orders": [TieBreakOrder.UP_LEFT_DIAG],
                "len_a_range": (6, 10),
                "len_b_range": (6, 10),
                "value_range": (-25, 25),
                "divisor_range": (3, 5),
                "match_score_range": (3, 3),
                "mismatch_score_range": (2, 2),
                "gap_score_range": (-1, -1),
            },
        )
    ],
    5: [
        DifficultyPreset(
            "5A",
            "local gap-count objective with mod predicate and dense ties",
            {
                "target_difficulty": 5,
                "templates": [SequenceDpTemplateType.LOCAL],
                "output_modes": [SequenceDpOutputMode.GAP_COUNT],
                "predicate_types": [SequenceDpPredicateType.MOD_EQ],
                "tie_break_orders": [TieBreakOrder.LEFT_UP_DIAG],
                "len_a_range": (8, 12),
                "len_b_range": (8, 12),
                "value_range": (-30, 30),
                "divisor_range": (6, 10),
                "match_score_range": (1, 1),
                "mismatch_score_range": (1, 1),
                "gap_score_range": (1, 1),
            },
        )
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
    "stack_bytecode": STACK_BYTECODE_PRESETS,
    "fsm": FSM_PRESETS,
    "bitops": BITOPS_PRESETS,
    "sequence_dp": SEQUENCE_DP_PRESETS,
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
) -> (
    PiecewiseAxes
    | StatefulAxes
    | SimpleAlgorithmsAxes
    | StringRulesAxes
    | StackBytecodeAxes
    | FsmAxes
    | BitopsAxes
    | SequenceDpAxes
):
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
) -> (
    PiecewiseAxes
    | StatefulAxes
    | SimpleAlgorithmsAxes
    | StringRulesAxes
    | StackBytecodeAxes
    | FsmAxes
    | BitopsAxes
    | SequenceDpAxes
):
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
        case "stack_bytecode":
            return StackBytecodeAxes(**overrides)
        case "fsm":
            return FsmAxes(**overrides)
        case "bitops":
            return BitopsAxes(**overrides)
        case "sequence_dp":
            return SequenceDpAxes(**overrides)
        case _:
            raise ValueError(f"Unknown family: {family}")
