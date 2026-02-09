"""Pool generation, greedy selection, and suite generation pipeline."""

import logging
import random
import zlib
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from genfxn.bitops.models import BitOp, BitopsAxes
from genfxn.bitops.queries import generate_bitops_queries
from genfxn.bitops.render import render_bitops
from genfxn.bitops.sampler import sample_bitops_spec
from genfxn.core.codegen import task_id_from_spec
from genfxn.core.describe import describe_task
from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import Task
from genfxn.core.predicates import PredicateType
from genfxn.core.string_predicates import StringPredicateType
from genfxn.core.string_transforms import StringTransformType
from genfxn.core.trace import GenerationTrace, TraceStep
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
from genfxn.fsm.queries import generate_fsm_queries
from genfxn.fsm.render import render_fsm
from genfxn.fsm.sampler import sample_fsm_spec
from genfxn.intervals.models import (
    BoundaryMode,
    IntervalsAxes,
    OperationType,
)
from genfxn.intervals.queries import generate_intervals_queries
from genfxn.intervals.render import render_intervals
from genfxn.intervals.sampler import sample_intervals_spec
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
from genfxn.sequence_dp.queries import generate_sequence_dp_queries
from genfxn.sequence_dp.render import render_sequence_dp
from genfxn.sequence_dp.sampler import sample_sequence_dp_spec
from genfxn.simple_algorithms.models import (
    CountingMode,
    SimpleAlgorithmsAxes,
)
from genfxn.simple_algorithms.models import TemplateType as SATemplateType
from genfxn.simple_algorithms.queries import generate_simple_algorithms_queries
from genfxn.simple_algorithms.render import render_simple_algorithms
from genfxn.simple_algorithms.sampler import sample_simple_algorithms_spec
from genfxn.stack_bytecode.models import (
    InputMode,
    JumpTargetMode,
    StackBytecodeAxes,
    StackBytecodeSpec,
)
from genfxn.stack_bytecode.queries import generate_stack_bytecode_queries
from genfxn.stack_bytecode.render import render_stack_bytecode
from genfxn.stack_bytecode.templates import stack_template_program
from genfxn.stateful.models import StatefulAxes
from genfxn.stateful.models import TemplateType as StatefulTemplateType
from genfxn.stateful.queries import generate_stateful_queries
from genfxn.stateful.render import render_stateful
from genfxn.stateful.sampler import sample_stateful_spec
from genfxn.stringrules.models import OverlapLevel, StringRulesAxes
from genfxn.stringrules.queries import generate_stringrules_queries
from genfxn.stringrules.render import render_stringrules
from genfxn.stringrules.sampler import sample_stringrules_spec
from genfxn.suites.features import (
    bitops_features,
    fsm_features,
    intervals_features,
    sequence_dp_features,
    simple_algorithms_features,
    stack_bytecode_features,
    stateful_features,
    stringrules_features,
)
from genfxn.suites.quotas import QUOTAS, Bucket, QuotaSpec

logger = logging.getLogger(__name__)

# ── Candidate + PoolStats ────────────────────────────────────────────────


class Candidate(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    spec: Any
    spec_dict: dict[str, Any]
    task_id: str
    features: dict[str, str]
    trace_steps: list[TraceStep] = Field(default_factory=list)
    axes: Any = None


class PoolStats(BaseModel):
    total_sampled: int = 0
    duplicates: int = 0
    wrong_difficulty: int = 0
    errors: int = 0
    candidates: int = 0


# ── Stable seeding ───────────────────────────────────────────────────────


def _stable_seed(seed: int, family: str, difficulty: int, index: int) -> int:
    return (
        zlib.crc32(f"{seed}:{family}:{difficulty}:{index}".encode())
        & 0xFFFFFFFF
    )


# ── Pool axes generators ────────────────────────────────────────────────

# Predicate type groups
_SIMPLE_PREDS = [
    StringPredicateType.IS_ALPHA,
    StringPredicateType.IS_DIGIT,
    StringPredicateType.IS_UPPER,
    StringPredicateType.IS_LOWER,
]
_PATTERN_PREDS = [
    StringPredicateType.STARTS_WITH,
    StringPredicateType.ENDS_WITH,
    StringPredicateType.CONTAINS,
]
_LENGTH_PREDS = [StringPredicateType.LENGTH_CMP]
_COMPOSED_STRING_PREDS = [
    StringPredicateType.NOT,
    StringPredicateType.AND,
    StringPredicateType.OR,
]

# Transform type groups
_IDENTITY_TRANS = [StringTransformType.IDENTITY]
_SIMPLE_TRANS = [
    StringTransformType.LOWERCASE,
    StringTransformType.UPPERCASE,
    StringTransformType.CAPITALIZE,
    StringTransformType.SWAPCASE,
    StringTransformType.REVERSE,
]
_PARAM_TRANS = [
    StringTransformType.REPLACE,
    StringTransformType.STRIP,
    StringTransformType.PREPEND,
    StringTransformType.APPEND,
]
_ALL_ATOMIC_STRING_TRANS = _IDENTITY_TRANS + _SIMPLE_TRANS + _PARAM_TRANS

# Numeric pred groups
_COMPARISON_PREDS = [
    PredicateType.LT,
    PredicateType.LE,
    PredicateType.GT,
    PredicateType.GE,
]
_COMPOSED_PREDS = [PredicateType.NOT, PredicateType.AND, PredicateType.OR]

# Numeric transform groups
_ATOMIC_NONIDENTITY_TRANS = [
    TransformType.ABS,
    TransformType.SHIFT,
    TransformType.NEGATE,
    TransformType.SCALE,
]
_AFFINE_TRANS = [
    TransformType.SHIFT,
    TransformType.SCALE,
    TransformType.IDENTITY,
]
_SIGN_TRANS = [TransformType.ABS, TransformType.NEGATE]


def _pool_axes_stringrules_d3(rng: random.Random) -> StringRulesAxes:
    """D3 stringrules: no comp, no pipe. Random pred/trans categories."""
    n_rules = rng.randint(4, 10)
    # Pick one pred category
    pred_cat = rng.choice(["simple", "pattern", "length"])
    if pred_cat == "simple":
        pred_types = _SIMPLE_PREDS
    elif pred_cat == "pattern":
        pred_types = _PATTERN_PREDS
    else:
        pred_types = _LENGTH_PREDS

    # Pick one trans category (exclude pipeline)
    trans_cat = rng.choice(["identity", "simple", "param"])
    if trans_cat == "identity":
        trans_types = _IDENTITY_TRANS
    elif trans_cat == "simple":
        trans_types = _SIMPLE_TRANS
    else:
        trans_types = _PARAM_TRANS

    return StringRulesAxes(
        n_rules=n_rules,
        predicate_types=pred_types,
        transform_types=trans_types,
        overlap_level=OverlapLevel.LOW,
    )


def _pool_axes_stringrules_d4(rng: random.Random) -> StringRulesAxes:
    """D4 stringrules: comp XOR pipe."""
    n_rules = rng.randint(4, 10)
    mode = rng.choice(["comp-only", "pipe-only"])

    if mode == "comp-only":
        # Composed preds + atomic transforms (no pipeline)
        atom_preds = rng.choice([_SIMPLE_PREDS, _PATTERN_PREDS, _LENGTH_PREDS])
        # Mix NOT (score 4) and AND/OR (score 4-5) for variety
        comp_choice = rng.choice(["not_only", "and_or", "all_composed"])
        if comp_choice == "not_only":
            pred_types = [StringPredicateType.NOT] + atom_preds
        elif comp_choice == "and_or":
            pred_types = [
                StringPredicateType.AND,
                StringPredicateType.OR,
            ] + atom_preds
        else:
            pred_types = _COMPOSED_STRING_PREDS + atom_preds
        trans_types = rng.choice(
            [_SIMPLE_TRANS, _PARAM_TRANS, _IDENTITY_TRANS + _SIMPLE_TRANS]
        )
    else:
        # Atomic preds + pipeline transform
        pred_types = rng.choice(
            [
                _SIMPLE_PREDS,
                _PATTERN_PREDS,
                _LENGTH_PREDS,
                _SIMPLE_PREDS + _PATTERN_PREDS,
            ]
        )
        # Score 4: 2 steps, 1 param. Score 5: 3 steps or 2+ param.
        # Include param + non-param atom types alongside PIPELINE.
        # Weight toward PIPELINE so most rules get pipelines.
        trans_types = [StringTransformType.PIPELINE] * 4 + rng.choice(
            [
                _SIMPLE_TRANS
                + [StringTransformType.REPLACE],  # mix → some score 4
                _PARAM_TRANS,  # all param → score 5
            ]
        )

    return StringRulesAxes(
        n_rules=n_rules,
        predicate_types=pred_types,
        transform_types=trans_types,
        overlap_level=OverlapLevel.HIGH,
    )


def _pool_axes_stringrules_d5(rng: random.Random) -> StringRulesAxes:
    """D5 stringrules: both comp AND pipe."""
    n_rules = rng.randint(4, 10)
    atom_preds = rng.choice([_SIMPLE_PREDS, _PATTERN_PREDS, _LENGTH_PREDS])
    # Mix NOT (score 4) and AND/OR (score 4-5)
    comp_choice = rng.choice(["not_only", "and_or", "all_composed"])
    if comp_choice == "not_only":
        comp_preds = [StringPredicateType.NOT]
    elif comp_choice == "and_or":
        comp_preds = [StringPredicateType.AND, StringPredicateType.OR]
    else:
        comp_preds = _COMPOSED_STRING_PREDS
    pred_types = comp_preds + atom_preds
    # For D5: need high trans_avg (≥4). Heavily weight toward PIPELINE.
    # Including param atom types alongside PIPELINE gives pipeline steps
    # the param types needed for score 4-5.
    # Repeat PIPELINE to bias per-rule selection toward pipelines.
    pipe_atom_choice = rng.choice(["mix", "param_only", "param_only"])
    if pipe_atom_choice == "mix":
        # Some non-param atoms → pipeline score 4 (2 steps, 1 param)
        atom_types = _SIMPLE_TRANS + [StringTransformType.REPLACE]
    else:
        # All param atoms → pipeline score 5
        atom_types = list(_PARAM_TRANS)
    # Weight heavily toward PIPELINE (~80%)
    trans_types = [StringTransformType.PIPELINE] * 4 + atom_types

    return StringRulesAxes(
        n_rules=n_rules,
        predicate_types=pred_types,
        transform_types=trans_types,
        overlap_level=OverlapLevel.HIGH,
    )


def _pool_axes_stateful_d3(rng: random.Random) -> StatefulAxes:
    """D3 stateful: no pipeline, no composed, no toggle_sum."""
    template = rng.choice(
        [
            StatefulTemplateType.CONDITIONAL_LINEAR_SUM,
            StatefulTemplateType.CONDITIONAL_LINEAR_SUM,  # weighted 2:1
            StatefulTemplateType.RESETTING_BEST_PREFIX_SUM,
        ]
    )
    pred_types = rng.choice(
        [
            _COMPARISON_PREDS,
            [PredicateType.MOD_EQ],
            _COMPARISON_PREDS + [PredicateType.MOD_EQ],
        ]
    )
    # Atomic transforms only, no pipeline
    trans_cat = rng.choice(["affine", "sign", "mixed"])
    if trans_cat == "affine":
        trans_types = _AFFINE_TRANS
    elif trans_cat == "sign":
        trans_types = _SIGN_TRANS
    else:
        trans_types = _AFFINE_TRANS + _SIGN_TRANS

    return StatefulAxes(
        templates=[template],
        predicate_types=pred_types,
        transform_types=trans_types,
    )


def _pool_axes_stateful_d4(rng: random.Random) -> StatefulAxes:
    """D4 stateful: mixed templates/preds/transforms.

    Comparison preds need pipeline transforms to reach D4:
      toggle/resetting + comparison + pipeline5 → D4
      conditional + mod_eq + atomic → D3
    """
    template = rng.choice(
        [
            StatefulTemplateType.CONDITIONAL_LINEAR_SUM,
            StatefulTemplateType.CONDITIONAL_LINEAR_SUM,
            StatefulTemplateType.RESETTING_BEST_PREFIX_SUM,
            StatefulTemplateType.TOGGLE_SUM,
        ]
    )
    pred_choice = rng.choice(
        ["mod_eq", "composed", "comparison", "mod_eq_composed"]
    )
    if pred_choice == "mod_eq":
        pred_types = [PredicateType.MOD_EQ]
    elif pred_choice == "composed":
        pred_types = _COMPOSED_PREDS
    elif pred_choice == "comparison":
        # Comparison preds need high-scoring transforms to reach D4
        pred_types = _COMPARISON_PREDS
    else:
        pred_types = [PredicateType.MOD_EQ] + _COMPOSED_PREDS

    # Mix of atomic and pipeline transforms
    trans_choice = rng.choice(["atomic", "pipeline", "mixed"])
    if trans_choice == "atomic":
        trans_types = _ATOMIC_NONIDENTITY_TRANS
    elif trans_choice == "pipeline":
        trans_types = [TransformType.PIPELINE]
    else:
        trans_types = _ATOMIC_NONIDENTITY_TRANS + [TransformType.PIPELINE]

    return StatefulAxes(
        templates=[template],
        predicate_types=pred_types,
        transform_types=trans_types,
    )


def _pool_axes_stateful_d5(rng: random.Random) -> StatefulAxes:
    """D5 stateful: toggle_sum/resetting, pipeline5, composed preds.

    mod_eq + template(4) + pipeline5 → raw 4.3 → D4.
    Only composed(5) reaches D5: raw 4.6 → D5.
    """
    template = rng.choice(
        [
            StatefulTemplateType.TOGGLE_SUM,
            StatefulTemplateType.RESETTING_BEST_PREFIX_SUM,
        ]
    )

    return StatefulAxes(
        templates=[template],
        predicate_types=_COMPOSED_PREDS,
        transform_types=[TransformType.PIPELINE],
        min_composed_operands=3,
    )


def _pool_axes_simple_algorithms_d3(rng: random.Random) -> SimpleAlgorithmsAxes:
    """D3 simple_algorithms: no preprocess."""
    template = rng.choice(
        [
            SATemplateType.COUNT_PAIRS_SUM,
            SATemplateType.MAX_WINDOW_SUM,
        ]
    )

    axes_kwargs: dict[str, Any] = {
        "templates": [template],
    }

    if template == SATemplateType.COUNT_PAIRS_SUM:
        # Vary target sign
        sign = rng.choice(["neg", "zero", "pos"])
        if sign == "neg":
            axes_kwargs["target_range"] = (-50, -1)
        elif sign == "zero":
            axes_kwargs["target_range"] = (0, 0)
            # Without extra edge defaults, zero/all_indices remains D2 and
            # the D3 pool collapses to one unique zero candidate.
            axes_kwargs["counting_modes"] = [
                CountingMode.ALL_INDICES,
                CountingMode.UNIQUE_VALUES,
            ]
            axes_kwargs["no_result_default_range"] = (-10, 10)
            axes_kwargs["short_list_default_range"] = (-5, 5)
        else:
            axes_kwargs["target_range"] = (1, 50)
    else:
        # max_window_sum: k in 6-10 for D3 (k<6 gives D2)
        # Vary invalid_k_default for dedup diversity
        axes_kwargs["window_size_range"] = (6, 10)
        axes_kwargs["empty_default_range"] = (-10, 10)

    return SimpleAlgorithmsAxes(**axes_kwargs)


def _pool_axes_simple_algorithms_d4(rng: random.Random) -> SimpleAlgorithmsAxes:
    """D4 simple_algorithms: preprocess present.

    most_frequent needs 'both' preprocess to reach D4.
    count_pairs_sum/max_window_sum can reach D4 with
    any preprocess mode.
    """
    template = rng.choice(
        [
            SATemplateType.MOST_FREQUENT,
            SATemplateType.MOST_FREQUENT,  # extra weight
            SATemplateType.COUNT_PAIRS_SUM,
            SATemplateType.COUNT_PAIRS_SUM,
            SATemplateType.MAX_WINDOW_SUM,
        ]
    )

    # most_frequent needs 'both' preprocess for D4
    if template == SATemplateType.MOST_FREQUENT:
        pp_mode = "both"
    else:
        pp_mode = rng.choice(["filter_only", "transform_only", "both"])

    axes_kwargs: dict[str, Any] = {"templates": [template]}

    if pp_mode in ("filter_only", "both"):
        filter_kind = rng.choice(["comparison", "mod_eq", "composed"])
        if filter_kind == "comparison":
            axes_kwargs["pre_filter_types"] = _COMPARISON_PREDS
        elif filter_kind == "mod_eq":
            axes_kwargs["pre_filter_types"] = [PredicateType.MOD_EQ]
        else:
            axes_kwargs["pre_filter_types"] = _COMPOSED_PREDS

    if pp_mode in ("transform_only", "both"):
        tc = rng.choice(["atomic", "pipeline4"])
        if tc == "atomic":
            axes_kwargs["pre_transform_types"] = _ATOMIC_NONIDENTITY_TRANS
        else:
            axes_kwargs["pre_transform_types"] = [TransformType.PIPELINE]

    # Edge defaults:
    # - most_frequent contributes tie_default only
    # - max_window_sum contributes empty_default only
    # - count_pairs_sum can contribute 1 or 2 edge fields
    edge_count = 1
    if template == SATemplateType.MOST_FREQUENT:
        axes_kwargs["tie_default_range"] = (-10, 10)
    elif template == SATemplateType.COUNT_PAIRS_SUM:
        edge_count = rng.choice([1, 1, 1, 2])  # weighted toward 1
        axes_kwargs["no_result_default_range"] = (-10, 10)
        if edge_count >= 2:
            axes_kwargs["short_list_default_range"] = (-5, 5)
    else:
        axes_kwargs["empty_default_for_empty_range"] = (-10, 10)

    return SimpleAlgorithmsAxes(**axes_kwargs)


def _pool_axes_simple_algorithms_d5(rng: random.Random) -> SimpleAlgorithmsAxes:
    """D5 simple_algorithms: both preprocess, pipeline5, 2 edges.

    most_frequent can't reach D5 (max raw=4.1, base template=2), so only
    count_pairs_sum (base=3) and max_window_sum (base=3) are used.
    """
    template = rng.choice(
        [
            SATemplateType.COUNT_PAIRS_SUM,
            SATemplateType.COUNT_PAIRS_SUM,
            SATemplateType.MAX_WINDOW_SUM,
        ]
    )

    filter_kind = rng.choice(["mod_eq", "composed"])
    if filter_kind == "mod_eq":
        pre_filter_types = [PredicateType.MOD_EQ]
    else:
        pre_filter_types = _COMPOSED_PREDS

    axes_kwargs: dict[str, Any] = {
        "templates": [template],
        "pre_filter_types": pre_filter_types,
        "pre_transform_types": [TransformType.PIPELINE],
    }

    # 2 edge defaults
    if template == SATemplateType.MOST_FREQUENT:
        axes_kwargs["tie_default_range"] = (-10, 10)
        axes_kwargs["empty_default_range"] = (-5, 5)
    elif template == SATemplateType.COUNT_PAIRS_SUM:
        axes_kwargs["no_result_default_range"] = (-10, 10)
        axes_kwargs["short_list_default_range"] = (-5, 5)
    else:
        # max_window_sum: empty_default is the edge field, and
        # invalid_k_default != 0 adds to base_edge_score for D5 scoring
        axes_kwargs["empty_default_for_empty_range"] = (-10, 10)
        axes_kwargs["empty_default_range"] = (-10, -1)  # invalid_k_default ≠ 0
        axes_kwargs["window_size_range"] = (6, 10)

    return SimpleAlgorithmsAxes(**axes_kwargs)


def _pool_axes_stack_bytecode_d1(_: random.Random) -> StackBytecodeAxes:
    return StackBytecodeAxes(
        target_difficulty=1,
        max_step_count_range=(20, 32),
        jump_target_modes=[JumpTargetMode.ERROR],
        input_modes=[InputMode.DIRECT],
    )


def _pool_axes_stack_bytecode_d2(_: random.Random) -> StackBytecodeAxes:
    return StackBytecodeAxes(
        target_difficulty=2,
        max_step_count_range=(32, 64),
        jump_target_modes=[JumpTargetMode.ERROR],
        input_modes=[InputMode.DIRECT],
    )


def _pool_axes_stack_bytecode_d3(_: random.Random) -> StackBytecodeAxes:
    return StackBytecodeAxes(
        target_difficulty=3,
        max_step_count_range=(64, 96),
        jump_target_modes=[JumpTargetMode.CLAMP],
        input_modes=[InputMode.CYCLIC],
    )


def _pool_axes_stack_bytecode_d4(_: random.Random) -> StackBytecodeAxes:
    return StackBytecodeAxes(
        target_difficulty=4,
        max_step_count_range=(96, 128),
        jump_target_modes=[JumpTargetMode.CLAMP],
        input_modes=[InputMode.DIRECT],
    )


def _pool_axes_stack_bytecode_d5(_: random.Random) -> StackBytecodeAxes:
    return StackBytecodeAxes(
        target_difficulty=5,
        max_step_count_range=(128, 160),
        jump_target_modes=[JumpTargetMode.WRAP],
        input_modes=[InputMode.CYCLIC],
    )


def _pool_axes_fsm_d1(_: random.Random) -> FsmAxes:
    return FsmAxes(
        target_difficulty=1,
        machine_types=[MachineType.MOORE],
        output_modes=[OutputMode.FINAL_STATE_ID],
        undefined_transition_policies=[UndefinedTransitionPolicy.STAY],
        predicate_types=[FsmPredicateType.EVEN, FsmPredicateType.ODD],
        n_states_range=(2, 2),
        transitions_per_state_range=(0, 1),
    )


def _pool_axes_fsm_d2(_: random.Random) -> FsmAxes:
    return FsmAxes(
        target_difficulty=2,
        machine_types=[MachineType.MOORE],
        output_modes=[OutputMode.FINAL_STATE_ID, OutputMode.ACCEPT_BOOL],
        undefined_transition_policies=[
            UndefinedTransitionPolicy.STAY,
            UndefinedTransitionPolicy.SINK,
        ],
        predicate_types=[
            FsmPredicateType.EVEN,
            FsmPredicateType.ODD,
            FsmPredicateType.LT,
            FsmPredicateType.GT,
        ],
        n_states_range=(2, 3),
        transitions_per_state_range=(1, 2),
    )


def _pool_axes_fsm_d3(_: random.Random) -> FsmAxes:
    return FsmAxes(
        target_difficulty=3,
        machine_types=[MachineType.MEALY],
        output_modes=[OutputMode.ACCEPT_BOOL, OutputMode.TRANSITION_COUNT],
        undefined_transition_policies=[UndefinedTransitionPolicy.SINK],
        predicate_types=[
            FsmPredicateType.LT,
            FsmPredicateType.LE,
            FsmPredicateType.GT,
            FsmPredicateType.GE,
            FsmPredicateType.MOD_EQ,
        ],
        n_states_range=(4, 5),
        transitions_per_state_range=(2, 3),
    )


def _pool_axes_fsm_d4(_: random.Random) -> FsmAxes:
    return FsmAxes(
        target_difficulty=4,
        machine_types=[MachineType.MEALY],
        output_modes=[OutputMode.TRANSITION_COUNT],
        undefined_transition_policies=[UndefinedTransitionPolicy.ERROR],
        predicate_types=[
            FsmPredicateType.MOD_EQ,
            FsmPredicateType.LT,
            FsmPredicateType.LE,
            FsmPredicateType.GT,
            FsmPredicateType.GE,
        ],
        n_states_range=(5, 5),
        transitions_per_state_range=(2, 3),
    )


def _pool_axes_fsm_d5(_: random.Random) -> FsmAxes:
    return FsmAxes(
        target_difficulty=5,
        machine_types=[MachineType.MEALY],
        output_modes=[OutputMode.TRANSITION_COUNT],
        undefined_transition_policies=[UndefinedTransitionPolicy.ERROR],
        predicate_types=[
            FsmPredicateType.MOD_EQ,
            FsmPredicateType.LT,
            FsmPredicateType.LE,
            FsmPredicateType.GT,
            FsmPredicateType.GE,
        ],
        n_states_range=(6, 6),
        transitions_per_state_range=(4, 5),
    )


def _pool_axes_bitops_d1(_: random.Random) -> BitopsAxes:
    return BitopsAxes(
        target_difficulty=1,
        width_choices=[8],
        n_ops_range=(1, 2),
        allowed_ops=[
            BitOp.AND_MASK,
            BitOp.OR_MASK,
            BitOp.XOR_MASK,
            BitOp.NOT,
        ],
    )


def _pool_axes_bitops_d2(_: random.Random) -> BitopsAxes:
    return BitopsAxes(
        target_difficulty=2,
        width_choices=[8, 16],
        n_ops_range=(2, 3),
        allowed_ops=[
            BitOp.AND_MASK,
            BitOp.OR_MASK,
            BitOp.XOR_MASK,
            BitOp.NOT,
            BitOp.SHL,
            BitOp.SHR_LOGICAL,
        ],
    )


def _pool_axes_bitops_d3(_: random.Random) -> BitopsAxes:
    return BitopsAxes(
        target_difficulty=3,
        width_choices=[16],
        n_ops_range=(3, 4),
        allowed_ops=[
            BitOp.SHL,
            BitOp.SHR_LOGICAL,
            BitOp.ROTL,
            BitOp.ROTR,
            BitOp.NOT,
        ],
    )


def _pool_axes_bitops_d4(_: random.Random) -> BitopsAxes:
    return BitopsAxes(
        target_difficulty=4,
        width_choices=[32],
        n_ops_range=(4, 5),
        allowed_ops=[
            BitOp.ROTL,
            BitOp.ROTR,
            BitOp.POPCOUNT,
            BitOp.PARITY,
            BitOp.XOR_MASK,
        ],
    )


def _pool_axes_bitops_d5(_: random.Random) -> BitopsAxes:
    return BitopsAxes(
        target_difficulty=5,
        width_choices=[32],
        n_ops_range=(6, 7),
        allowed_ops=[
            BitOp.POPCOUNT,
            BitOp.PARITY,
            BitOp.ROTL,
            BitOp.ROTR,
            BitOp.SHR_LOGICAL,
        ],
    )


def _pool_axes_sequence_dp_d1(_: random.Random) -> SequenceDpAxes:
    return SequenceDpAxes(
        templates=[SequenceDpTemplateType.GLOBAL],
        output_modes=[SequenceDpOutputMode.SCORE],
        predicate_types=[SequenceDpPredicateType.EQ],
        tie_break_orders=[TieBreakOrder.DIAG_UP_LEFT],
        match_score_range=(4, 9),
        mismatch_score_range=(-6, 0),
        gap_score_range=(-6, 0),
    )


def _pool_axes_sequence_dp_d2(_: random.Random) -> SequenceDpAxes:
    return SequenceDpAxes(
        target_difficulty=2,
        templates=[SequenceDpTemplateType.GLOBAL],
        output_modes=[SequenceDpOutputMode.ALIGNMENT_LEN],
        predicate_types=[SequenceDpPredicateType.ABS_DIFF_LE],
        abs_diff_range=(0, 2),
        tie_break_orders=[
            TieBreakOrder.DIAG_UP_LEFT,
            TieBreakOrder.DIAG_LEFT_UP,
        ],
        match_score_range=(4, 6),
        mismatch_score_range=(-1, 0),
        gap_score_range=(-2, -1),
    )


def _pool_axes_sequence_dp_d3(_: random.Random) -> SequenceDpAxes:
    return SequenceDpAxes(
        target_difficulty=3,
        templates=[SequenceDpTemplateType.GLOBAL],
        output_modes=[SequenceDpOutputMode.ALIGNMENT_LEN],
        predicate_types=[
            SequenceDpPredicateType.ABS_DIFF_LE,
            SequenceDpPredicateType.MOD_EQ,
        ],
        abs_diff_range=(1, 3),
        divisor_range=(2, 6),
        tie_break_orders=[
            TieBreakOrder.UP_DIAG_LEFT,
            TieBreakOrder.LEFT_DIAG_UP,
        ],
        match_score_range=(2, 4),
        mismatch_score_range=(-1, 1),
        gap_score_range=(-2, 0),
    )


def _pool_axes_sequence_dp_d4(_: random.Random) -> SequenceDpAxes:
    return SequenceDpAxes(
        target_difficulty=4,
        templates=[SequenceDpTemplateType.LOCAL],
        output_modes=[
            SequenceDpOutputMode.ALIGNMENT_LEN,
            SequenceDpOutputMode.GAP_COUNT,
        ],
        predicate_types=[SequenceDpPredicateType.MOD_EQ],
        divisor_range=(3, 8),
        tie_break_orders=[
            TieBreakOrder.UP_LEFT_DIAG,
            TieBreakOrder.LEFT_UP_DIAG,
        ],
        match_score_range=(2, 4),
        mismatch_score_range=(1, 2),
        gap_score_range=(-1, 1),
    )


def _pool_axes_sequence_dp_d5(_: random.Random) -> SequenceDpAxes:
    return SequenceDpAxes(
        target_difficulty=5,
        templates=[SequenceDpTemplateType.LOCAL],
        output_modes=[SequenceDpOutputMode.GAP_COUNT],
        predicate_types=[SequenceDpPredicateType.MOD_EQ],
        divisor_range=(5, 10),
        tie_break_orders=[
            TieBreakOrder.LEFT_UP_DIAG,
            TieBreakOrder.UP_LEFT_DIAG,
        ],
        match_score_range=(1, 2),
        mismatch_score_range=(1, 2),
        gap_score_range=(1, 2),
    )


def _pool_axes_intervals_d1(_: random.Random) -> IntervalsAxes:
    return IntervalsAxes(
        operation_types=[
            OperationType.TOTAL_COVERAGE,
            OperationType.MERGED_COUNT,
        ],
        boundary_modes=[BoundaryMode.CLOSED_CLOSED],
        merge_touching_choices=[False, True],
    )


def _pool_axes_intervals_d2(_: random.Random) -> IntervalsAxes:
    return IntervalsAxes(
        operation_types=[
            OperationType.TOTAL_COVERAGE,
            OperationType.MERGED_COUNT,
            OperationType.MAX_OVERLAP_COUNT,
        ],
        boundary_modes=[
            BoundaryMode.CLOSED_CLOSED,
            BoundaryMode.CLOSED_OPEN,
            BoundaryMode.OPEN_CLOSED,
            BoundaryMode.OPEN_OPEN,
        ],
        merge_touching_choices=[False, True],
    )


def _pool_axes_intervals_d3(_: random.Random) -> IntervalsAxes:
    return IntervalsAxes(
        operation_types=[
            OperationType.TOTAL_COVERAGE,
            OperationType.MERGED_COUNT,
            OperationType.MAX_OVERLAP_COUNT,
            OperationType.GAP_COUNT,
        ],
        boundary_modes=[
            BoundaryMode.CLOSED_CLOSED,
            BoundaryMode.CLOSED_OPEN,
            BoundaryMode.OPEN_CLOSED,
            BoundaryMode.OPEN_OPEN,
        ],
        merge_touching_choices=[False, True],
    )


def _pool_axes_intervals_d4(_: random.Random) -> IntervalsAxes:
    return IntervalsAxes(
        operation_types=[
            OperationType.MAX_OVERLAP_COUNT,
            OperationType.GAP_COUNT,
        ],
        boundary_modes=[
            BoundaryMode.CLOSED_OPEN,
            BoundaryMode.OPEN_CLOSED,
            BoundaryMode.OPEN_OPEN,
        ],
        merge_touching_choices=[False, True],
    )


def _pool_axes_intervals_d5(_: random.Random) -> IntervalsAxes:
    return IntervalsAxes(
        operation_types=[OperationType.GAP_COUNT],
        boundary_modes=[
            BoundaryMode.CLOSED_OPEN,
            BoundaryMode.OPEN_CLOSED,
            BoundaryMode.OPEN_OPEN,
        ],
        merge_touching_choices=[True],
    )


# ── Pool axes dispatch ───────────────────────────────────────────────────

_POOL_AXES_FNS: dict[str, dict[int, Any]] = {
    "stringrules": {
        3: _pool_axes_stringrules_d3,
        4: _pool_axes_stringrules_d4,
        5: _pool_axes_stringrules_d5,
    },
    "stateful": {
        3: _pool_axes_stateful_d3,
        4: _pool_axes_stateful_d4,
        5: _pool_axes_stateful_d5,
    },
    "simple_algorithms": {
        3: _pool_axes_simple_algorithms_d3,
        4: _pool_axes_simple_algorithms_d4,
        5: _pool_axes_simple_algorithms_d5,
    },
    "stack_bytecode": {
        1: _pool_axes_stack_bytecode_d1,
        2: _pool_axes_stack_bytecode_d2,
        3: _pool_axes_stack_bytecode_d3,
        4: _pool_axes_stack_bytecode_d4,
        5: _pool_axes_stack_bytecode_d5,
    },
    "fsm": {
        1: _pool_axes_fsm_d1,
        2: _pool_axes_fsm_d2,
        3: _pool_axes_fsm_d3,
        4: _pool_axes_fsm_d4,
        5: _pool_axes_fsm_d5,
    },
    "bitops": {
        1: _pool_axes_bitops_d1,
        2: _pool_axes_bitops_d2,
        3: _pool_axes_bitops_d3,
        4: _pool_axes_bitops_d4,
        5: _pool_axes_bitops_d5,
    },
    "sequence_dp": {
        1: _pool_axes_sequence_dp_d1,
        2: _pool_axes_sequence_dp_d2,
        3: _pool_axes_sequence_dp_d3,
        4: _pool_axes_sequence_dp_d4,
        5: _pool_axes_sequence_dp_d5,
    },
    "intervals": {
        1: _pool_axes_intervals_d1,
        2: _pool_axes_intervals_d2,
        3: _pool_axes_intervals_d3,
        4: _pool_axes_intervals_d4,
        5: _pool_axes_intervals_d5,
    },
}

# ── Sampling dispatch ────────────────────────────────────────────────────

_FEATURE_FNS = {
    "stringrules": stringrules_features,
    "stateful": stateful_features,
    "simple_algorithms": simple_algorithms_features,
    "stack_bytecode": stack_bytecode_features,
    "fsm": fsm_features,
    "bitops": bitops_features,
    "sequence_dp": sequence_dp_features,
    "intervals": intervals_features,
}


def _format_valid_options(options: Sequence[str | int]) -> str:
    return ", ".join(str(option) for option in options)


def _validate_family_key(
    *,
    family: str,
    family_keys: set[str],
    context: str,
) -> None:
    if family not in family_keys:
        valid_options = _format_valid_options(sorted(family_keys))
        raise ValueError(
            f"Invalid family '{family}' for {context}. "
            f"Valid options: {valid_options}"
        )


def _validate_difficulty_key(
    *,
    family: str,
    difficulty: int,
    family_to_difficulties: dict[str, dict[int, Any]],
    context: str,
) -> None:
    valid_difficulties = sorted(family_to_difficulties[family].keys())
    if difficulty not in family_to_difficulties[family]:
        valid_options = _format_valid_options(valid_difficulties)
        raise ValueError(
            f"Invalid difficulty '{difficulty}' for family '{family}' "
            f"in {context}. Valid options: {valid_options}"
        )


def _sample_spec(
    family: str,
    axes: Any,
    rng: random.Random,
    trace: list[TraceStep] | None = None,
) -> Any:
    if family == "stringrules":
        return sample_stringrules_spec(axes, rng, trace=trace)
    elif family == "stateful":
        return sample_stateful_spec(axes, rng, trace=trace)
    elif family == "simple_algorithms":
        return sample_simple_algorithms_spec(axes, rng, trace=trace)
    elif family == "stack_bytecode":
        return _sample_stack_bytecode_spec(axes, rng, trace=trace)
    elif family == "fsm":
        return sample_fsm_spec(axes, rng, trace=trace)
    elif family == "bitops":
        return sample_bitops_spec(axes, rng, trace=trace)
    elif family == "sequence_dp":
        return sample_sequence_dp_spec(axes, rng, trace=trace)
    elif family == "intervals":
        return sample_intervals_spec(axes, rng, trace=trace)
    raise ValueError(f"Unknown family: {family}")


def _sample_stack_bytecode_spec(
    axes: StackBytecodeAxes,
    rng: random.Random,
    trace: list[TraceStep] | None = None,
) -> StackBytecodeSpec:
    target = axes.target_difficulty or rng.randint(1, 5)
    program = stack_template_program(target, rng)
    jump_mode = rng.choice(axes.jump_target_modes)
    input_mode = rng.choice(axes.input_modes)
    max_steps = rng.randint(*axes.max_step_count_range)
    if trace is not None:
        trace.extend(
            [
                TraceStep(
                    step="target_difficulty",
                    choice="target difficulty for template",
                    value=target,
                ),
                TraceStep(
                    step="jump_target_mode",
                    choice="jump target handling mode",
                    value=jump_mode.value,
                ),
                TraceStep(
                    step="input_mode",
                    choice="input indexing mode",
                    value=input_mode.value,
                ),
                TraceStep(
                    step="max_step_count",
                    choice="maximum VM step count",
                    value=max_steps,
                ),
            ]
        )
    return StackBytecodeSpec(
        program=program,
        max_step_count=max_steps,
        jump_target_mode=jump_mode,
        input_mode=input_mode,
    )


# ── Pool generation ──────────────────────────────────────────────────────


def generate_pool(
    family: str,
    difficulty: int,
    seed: int,
    pool_size: int,
) -> tuple[list[Candidate], PoolStats]:
    """Generate a candidate pool of specs at the target difficulty."""
    _validate_family_key(
        family=family,
        family_keys=set(_POOL_AXES_FNS.keys()),
        context="generate_pool",
    )
    _validate_difficulty_key(
        family=family,
        difficulty=difficulty,
        family_to_difficulties=_POOL_AXES_FNS,
        context="generate_pool",
    )
    _validate_family_key(
        family=family,
        family_keys=set(_FEATURE_FNS.keys()),
        context="generate_pool",
    )

    axes_fn = _POOL_AXES_FNS[family][difficulty]
    feature_fn = _FEATURE_FNS[family]
    candidates: list[Candidate] = []
    seen_ids: set[str] = set()
    stats = PoolStats()
    # Surface systemic sampling failures instead of silently degrading pools.
    max_failures = max(10, pool_size // 5)

    for i in range(pool_size):
        stats.total_sampled += 1
        sub_seed = _stable_seed(seed, family, difficulty, i)
        rng = random.Random(sub_seed)

        axes = axes_fn(rng)
        trace_steps: list[TraceStep] = []
        try:
            spec = _sample_spec(family, axes, rng, trace=trace_steps)
        except Exception as exc:
            stats.errors += 1
            if stats.errors >= max_failures:
                raise RuntimeError(
                    f"Sampling failed {stats.errors} times while generating "
                    f"{family} D{difficulty} pool (size={pool_size}). "
                    f"Last error: {type(exc).__name__}: {exc}"
                ) from exc
            continue

        spec_dict = spec.model_dump()
        task_id = task_id_from_spec(family, spec_dict)

        if task_id in seen_ids:
            stats.duplicates += 1
            continue
        seen_ids.add(task_id)

        actual_difficulty = compute_difficulty(family, spec_dict)
        if actual_difficulty != difficulty:
            stats.wrong_difficulty += 1
            continue

        features = feature_fn(spec_dict)
        stats.candidates += 1
        candidates.append(
            Candidate(
                spec=spec,
                spec_dict=spec_dict,
                task_id=task_id,
                features=features,
                trace_steps=trace_steps,
                axes=axes,
            )
        )

    logger.debug(
        (
            "%s D%d pool: %d sampled, %d candidates, %d dupes, "
            "%d wrong-diff, %d errors"
        ),
        family,
        difficulty,
        stats.total_sampled,
        stats.candidates,
        stats.duplicates,
        stats.wrong_difficulty,
        stats.errors,
    )
    return candidates, stats


# ── Greedy selection ─────────────────────────────────────────────────────


def _bucket_applies(bucket: Bucket, features: dict[str, str]) -> bool:
    """Check if a candidate's features match a bucket (including conditions)."""
    if features.get(bucket.axis) != bucket.value:
        return False
    if bucket.condition is not None:
        for key, val in bucket.condition.items():
            if features.get(key) != val:
                return False
    return True


def _condition_applies(bucket: Bucket, features: dict[str, str]) -> bool:
    """Check if the bucket's condition matches (True if no condition)."""
    if bucket.condition is None:
        return True
    return all(features.get(k) == v for k, v in bucket.condition.items())


def _quota_targets_met(selected: list[Candidate], quota: QuotaSpec) -> bool:
    """Return True when all bucket targets are met by selected candidates."""
    filled: dict[int, int] = {i: 0 for i in range(len(quota.buckets))}
    for candidate in selected:
        for bi, bucket in enumerate(quota.buckets):
            if _bucket_applies(bucket, candidate.features):
                filled[bi] += 1
    return all(
        filled[bi] >= bucket.target for bi, bucket in enumerate(quota.buckets)
    )


def greedy_select(
    candidates: list[Candidate],
    quota: QuotaSpec,
    rng: random.Random,
) -> list[Candidate]:
    """Greedy selection to fill quota buckets."""
    # Filter by hard constraints
    filtered = []
    for cand in candidates:
        match = True
        for key, val in quota.hard_constraints.items():
            if cand.features.get(key) != val:
                match = False
                break
        if match:
            filtered.append(cand)

    # Shuffle for tie-breaking
    rng.shuffle(filtered)

    # Precompute candidate <-> bucket applicability once.
    candidate_to_buckets: list[list[int]] = [[] for _ in filtered]
    bucket_to_candidates: list[list[int]] = [
        [] for _ in range(len(quota.buckets))
    ]
    for ci, cand in enumerate(filtered):
        for bi, bucket in enumerate(quota.buckets):
            if _bucket_applies(bucket, cand.features):
                candidate_to_buckets[ci].append(bi)
                bucket_to_candidates[bi].append(ci)

    selected: list[Candidate] = []
    deficits: list[int] = [bucket.target for bucket in quota.buckets]
    deficit_weights: list[float] = [
        0.0 if bucket.target <= 0 else deficit / bucket.target
        for deficit, bucket in zip(deficits, quota.buckets, strict=True)
    ]
    candidate_scores: list[float] = [
        sum(deficit_weights[bi] for bi in candidate_to_buckets[ci])
        for ci in range(len(filtered))
    ]
    used_ids: set[str] = set()

    for _ in range(quota.total):
        deficits_remaining = any(deficit > 0 for deficit in deficits)
        best_idx: int | None = None
        best_score = -1.0

        for ci in range(len(filtered)):
            if filtered[ci].task_id in used_ids:
                continue

            score = candidate_scores[ci]

            if score > best_score:
                best_score = score
                best_idx = ci

        if best_idx is None:
            break
        if deficits_remaining and best_score <= 0.0:
            # Do not consume quota slots with zero-contribution picks while
            # any bucket target is still underfilled.
            break

        best_cand = filtered[best_idx]
        selected.append(best_cand)
        used_ids.add(best_cand.task_id)

        # Update deficit-derived weights incrementally for affected buckets.
        changed_candidates: set[int] = set()
        for bi in candidate_to_buckets[best_idx]:
            if deficits[bi] <= 0:
                continue

            deficits[bi] -= 1
            bucket_target = quota.buckets[bi].target
            new_weight = (
                deficits[bi] / bucket_target
                if deficits[bi] > 0 and bucket_target > 0
                else 0.0
            )
            if new_weight == deficit_weights[bi]:
                continue
            deficit_weights[bi] = new_weight
            changed_candidates.update(bucket_to_candidates[bi])

        # Recompute impacted candidate scores using current deficit weights.
        for ci in changed_candidates:
            candidate_scores[ci] = sum(
                deficit_weights[bi] for bi in candidate_to_buckets[ci]
            )

    return selected


# ── Full task generation from spec ───────────────────────────────────────


def _generate_task_from_candidate(
    family: str,
    candidate: Candidate,
    rng: random.Random,
) -> Task:
    """Generate a full Task from a Candidate."""
    spec = candidate.spec
    spec_dict = candidate.spec_dict
    axes = candidate.axes

    if family == "stringrules":
        if axes is None:
            axes = StringRulesAxes()
        py_code = render_stringrules(spec)
        queries = generate_stringrules_queries(spec, axes, rng)
    elif family == "stateful":
        if axes is None:
            axes = StatefulAxes()
        py_code = render_stateful(spec)
        queries = generate_stateful_queries(spec, axes, rng)
    elif family == "simple_algorithms":
        if axes is None:
            axes = SimpleAlgorithmsAxes()
        py_code = render_simple_algorithms(spec)
        queries = generate_simple_algorithms_queries(spec, axes, rng)
    elif family == "stack_bytecode":
        if axes is None:
            axes = StackBytecodeAxes()
        py_code = render_stack_bytecode(spec)
        queries = generate_stack_bytecode_queries(spec, axes, rng)
    elif family == "fsm":
        if axes is None:
            axes = FsmAxes()
        py_code = render_fsm(spec)
        queries = generate_fsm_queries(spec, axes, rng)
    elif family == "bitops":
        if axes is None:
            axes = BitopsAxes()
        py_code = render_bitops(spec)
        queries = generate_bitops_queries(spec, axes, rng)
    elif family == "sequence_dp":
        if axes is None:
            axes = SequenceDpAxes()
        py_code = render_sequence_dp(spec)
        queries = generate_sequence_dp_queries(spec, axes, rng)
    elif family == "intervals":
        if axes is None:
            axes = IntervalsAxes()
        py_code = render_intervals(spec)
        queries = generate_intervals_queries(spec, axes, rng)
    else:
        raise ValueError(f"Unknown family: {family}")

    difficulty = compute_difficulty(family, spec_dict)
    description = describe_task(family, spec_dict)
    trace = GenerationTrace(family=family, steps=candidate.trace_steps)

    return Task(
        task_id=candidate.task_id,
        family=family,
        spec=spec_dict,
        code=py_code,
        queries=queries,
        trace=trace,
        axes=axes.model_dump(),
        difficulty=difficulty,
        description=description,
    )


# ── Main pipeline ────────────────────────────────────────────────────────


def generate_suite(
    family: str,
    difficulty: int,
    seed: int = 42,
    pool_size: int = 3000,
    max_retries: int = 2,
) -> list[Task]:
    """Generate a balanced 50-task suite for (family, difficulty)."""
    if max_retries < 0:
        raise ValueError(f"max_retries must be >= 0, got {max_retries}")

    _validate_family_key(
        family=family,
        family_keys=set(QUOTAS.keys()),
        context="generate_suite",
    )
    _validate_difficulty_key(
        family=family,
        difficulty=difficulty,
        family_to_difficulties=QUOTAS,
        context="generate_suite",
    )

    quota = QUOTAS[family][difficulty]
    selected: list[Candidate] = []
    current_pool_size = pool_size

    for attempt in range(max_retries + 1):
        current_pool_size = pool_size * (2**attempt)
        candidates, stats = generate_pool(
            family, difficulty, seed, current_pool_size
        )

        select_rng = random.Random(
            _stable_seed(seed, family, difficulty, 999999)
        )
        selected = greedy_select(candidates, quota, select_rng)

        if len(selected) >= quota.total and _quota_targets_met(selected, quota):
            break
        logger.debug(
            (
                "%s D%d attempt %d: selected=%d/%d "
                "targets_met=%s (pool=%d, candidates=%d)"
            ),
            family,
            difficulty,
            attempt,
            len(selected),
            quota.total,
            _quota_targets_met(selected, quota),
            current_pool_size,
            stats.candidates,
        )

    if len(selected) < quota.total or not _quota_targets_met(selected, quota):
        raise RuntimeError(
            f"Could not fill suite for {family} D{difficulty}: "
            f"selected {len(selected)}/{quota.total}, "
            f"targets_met={_quota_targets_met(selected, quota)} after "
            f"{max_retries + 1} attempt(s), final pool_size={current_pool_size}"
        )

    # Generate full tasks for selected candidates
    tasks: list[Task] = []
    for candidate in selected[: quota.total]:
        task_rng = random.Random(
            _stable_seed(
                seed,
                family,
                difficulty,
                zlib.crc32(candidate.task_id.encode()) & 0xFFFFFFFF,
            )
        )
        task = _generate_task_from_candidate(family, candidate, task_rng)
        tasks.append(task)

    return tasks


def quota_report(
    tasks: list[Task],
    family: str,
    difficulty: int,
) -> list[tuple[str, str, int, int, str]]:
    """Generate a quota satisfaction report.

    Returns list of (axis, value, target, achieved, status) tuples.
    """
    _validate_family_key(
        family=family,
        family_keys=set(QUOTAS.keys()),
        context="quota_report",
    )
    _validate_difficulty_key(
        family=family,
        difficulty=difficulty,
        family_to_difficulties=QUOTAS,
        context="quota_report",
    )
    _validate_family_key(
        family=family,
        family_keys=set(_FEATURE_FNS.keys()),
        context="quota_report",
    )

    quota = QUOTAS[family][difficulty]
    feature_fn = _FEATURE_FNS[family]

    all_features = [feature_fn(t.spec) for t in tasks]

    rows: list[tuple[str, str, int, int, str]] = []
    for bucket in quota.buckets:
        count = 0
        for features in all_features:
            if _bucket_applies(bucket, features):
                count += 1
        status = "OK" if count >= bucket.target else "UNDER"
        cond_str = ""
        if bucket.condition:
            cond_str = f" (when {bucket.condition})"
        rows.append(
            (
                f"{bucket.axis}{cond_str}",
                bucket.value,
                bucket.target,
                count,
                status,
            )
        )

    return rows
