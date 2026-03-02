from __future__ import annotations

import pytest

from genfxn.bitops.models import BitOp, BitopsAxes
from genfxn.core.predicates import PredicateType
from genfxn.core.spec_space import (
    SpecCapacityError,
    analyze_spec_space,
    enforce_spec_capacity,
)
from genfxn.core.transforms import TransformType
from genfxn.fsm.models import (
    FsmAxes,
    OutputMode,
    UndefinedTransitionPolicy,
)
from genfxn.fsm.models import (
    PredicateType as FsmPredicateType,
)
from genfxn.piecewise.models import PiecewiseAxes
from genfxn.simple_algorithms.models import (
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


def _stateful_cell_key(features: dict[str, str]) -> str:
    return (
        f"{features['template']}|{features['predicate_class']}|"
        f"{features['transform_complexity']}"
    )


def _simple_cell_key(features: dict[str, str]) -> str:
    template = features["template"]
    if template == "most_frequent":
        return (
            f"{template}|{features['tie_break']}|"
            f"{features['preprocess_bucket']}"
        )
    if template == "count_pairs_sum":
        return (
            f"{template}|{features['counting_mode']}|"
            f"{features['preprocess_bucket']}"
        )
    return f"{template}|{features['k_bucket']}|{features['preprocess_bucket']}"


def test_stateful_exact_capacity_flags_impossible_request() -> None:
    axes = StatefulAxes(
        templates=[StatefulTemplateType.LONGEST_RUN],
        predicate_types=[PredicateType.EVEN, PredicateType.ODD],
        transform_types=[TransformType.IDENTITY],
    )
    report = analyze_spec_space(
        family="stateful",
        axes=axes,
        feature_partitioner=_stateful_cell_key,
    )
    assert report.mode == "exact"
    assert report.total_unique == 2
    assert report.partition_unique == {"longest_run|parity|low": 2}

    with pytest.raises(SpecCapacityError):
        enforce_spec_capacity(
            family="stateful",
            axes=axes,
            requested_partition_counts={"longest_run|parity|low": 15},
            feature_partitioner=_stateful_cell_key,
            require_exact=True,
        )


def test_simple_algorithms_exact_capacity() -> None:
    axes = SimpleAlgorithmsAxes(
        templates=[SimpleAlgoTemplateType.MOST_FREQUENT],
        tie_break_modes=[TieBreakMode.SMALLEST],
        empty_default_range=(0, 0),
        pre_filter_types=None,
        pre_transform_types=None,
        tie_default_range=None,
    )
    report = analyze_spec_space(
        family="simple_algorithms",
        axes=axes,
        feature_partitioner=_simple_cell_key,
    )
    assert report.mode == "exact"
    assert report.total_unique == 1
    assert report.partition_unique == {"most_frequent|smallest|none": 1}


def test_fsm_exact_capacity() -> None:
    axes = FsmAxes(
        output_modes=[OutputMode.FINAL_STATE_ID],
        undefined_transition_policies=[UndefinedTransitionPolicy.SINK],
        predicate_types=[FsmPredicateType.EVEN],
        n_states_range=(1, 1),
        transitions_per_state_range=(0, 0),
    )
    report = analyze_spec_space(
        family="fsm",
        axes=axes,
        feature_partitioner=(
            lambda features: (
                f"{features['output_mode']}|"
                f"{features['undefined_transition_policy']}|"
                f"{features['n_states_bucket']}"
            )
        ),
    )
    assert report.mode == "exact"
    assert report.total_unique == 1
    assert report.partition_unique == {"final_state_id|sink|small": 1}


def test_bitops_exact_capacity() -> None:
    axes = BitopsAxes(
        width_choices=[8],
        n_ops_range=(1, 1),
        allowed_ops=[BitOp.NOT],
    )
    report = analyze_spec_space(
        family="bitops",
        axes=axes,
        feature_partitioner=(
            lambda features: (
                f"{features['width_bits_bucket']}|"
                f"{features['n_ops_bucket']}|"
                f"{features['op_mix_bucket']}"
            )
        ),
    )
    assert report.mode == "exact"
    assert report.total_unique == 1
    assert report.partition_unique == {"8|short|logic_only": 1}


def test_fallback_lower_bound_for_unmodeled_family() -> None:
    report = analyze_spec_space(
        family="piecewise",
        axes=PiecewiseAxes(),
        sample_budget=64,
        seed=23,
    )
    assert report.mode == "lower_bound"
    assert report.sampled_draws == 64
    assert report.total_unique > 0
