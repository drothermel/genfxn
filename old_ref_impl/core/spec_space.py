from __future__ import annotations

import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

from genfxn.bitops.models import BitopsAxes
from genfxn.core.family_registry import generate_task_for_family
from genfxn.core.models import Task
from genfxn.fsm.models import FsmAxes
from genfxn.simple_algorithms.models import (
    PREPROCESS_SCALE_RANGE,
    PREPROCESS_SHIFT_RANGE,
    SimpleAlgorithmsAxes,
)
from genfxn.simple_algorithms.models import (
    TemplateType as SimpleAlgorithmTemplateType,
)
from genfxn.stateful.models import (
    SAMPLED_INIT_RANGE,
    StatefulAxes,
)
from genfxn.stateful.models import (
    TemplateType as StatefulTemplateType,
)

SpecSpaceMode = Literal["exact", "lower_bound"]
FeaturePartitioner = Callable[[Mapping[str, str]], str]
TaskPartitioner = Callable[[Task], str]


@dataclass(frozen=True)
class FeatureBucket:
    features: dict[str, str]
    unique_count: int


@dataclass(frozen=True)
class SpecSpaceReport:
    family: str
    mode: SpecSpaceMode
    total_unique: int
    partition_unique: dict[str, int] | None = None
    sampled_draws: int | None = None
    notes: tuple[str, ...] = ()


class SpecCapacityError(ValueError):
    """Raised when requested unique counts are impossible for a spec space."""


def _range_size(bounds: tuple[int, int]) -> int:
    lo, hi = bounds
    return max(0, hi - lo + 1)


def _sum_inclusive(lo: int, hi: int) -> int:
    if hi < lo:
        return 0
    n = hi - lo + 1
    return n * (lo + hi) // 2


def _bucketed_count(
    lo: int,
    hi: int,
    bucket_lo: int,
    bucket_hi: int,
) -> int:
    left = max(lo, bucket_lo)
    right = min(hi, bucket_hi)
    if right < left:
        return 0
    return right - left + 1


def _predicate_count_by_kind(
    *,
    selected_kinds: set[str],
    threshold_range: tuple[int, int],
    divisor_range: tuple[int, int],
    min_composed_operands: int,
) -> dict[str, int]:
    threshold_count = _range_size(threshold_range)
    divisor_lo, divisor_hi = divisor_range
    mod_count = _sum_inclusive(max(1, divisor_lo), divisor_hi)

    atom_counts = {
        "even": 1,
        "odd": 1,
        "lt": threshold_count,
        "le": threshold_count,
        "gt": threshold_count,
        "ge": threshold_count,
        "mod_eq": mod_count,
    }
    atom_total = sum(atom_counts.values())
    composed_count = sum(atom_total**n for n in range(min_composed_operands, 4))
    full_counts = {
        **atom_counts,
        "not": atom_total,
        "and": composed_count,
        "or": composed_count,
    }
    unknown = selected_kinds - set(full_counts)
    if unknown:
        unknown_str = ", ".join(sorted(unknown))
        raise ValueError(
            "unsupported predicate types for exact spec-space analysis: "
            f"{unknown_str}"
        )
    return {kind: full_counts[kind] for kind in selected_kinds}


def _transform_count_by_kind(
    *,
    selected_kinds: set[str],
    shift_range: tuple[int, int],
    scale_range: tuple[int, int],
) -> dict[str, int]:
    shift_count = _range_size(shift_range)
    scale_count = _range_size(scale_range)
    first_count = shift_count + scale_count
    rest_count = shift_count + scale_count + 2  # + abs + negate

    full_counts = {
        "identity": 1,
        "abs": 1,
        "shift": shift_count,
        "negate": 1,
        "scale": scale_count,
        # pipeline lengths are fixed to 2 or 3 in sampler.
        "pipeline": first_count * rest_count + first_count * (rest_count**2),
    }
    unknown = selected_kinds - set(full_counts)
    if unknown:
        unknown_str = ", ".join(sorted(unknown))
        raise ValueError(
            "unsupported transform types for exact spec-space analysis: "
            f"{unknown_str}"
        )
    return {kind: full_counts[kind] for kind in selected_kinds}


def _stateful_transform_class_counts(
    transform_counts: Mapping[str, int],
) -> dict[str, int]:
    low = transform_counts.get("identity", 0) + transform_counts.get(
        "negate", 0
    )
    high = transform_counts.get("scale", 0)
    mixed = sum(
        count
        for kind, count in transform_counts.items()
        if kind not in {"identity", "negate", "scale"}
    )
    return {
        "low": low,
        "mixed": mixed,
        "high": high,
    }


def _stateful_pair_transform_class_counts(
    transform_counts: Mapping[str, int],
) -> dict[str, int]:
    class_counts = _stateful_transform_class_counts(transform_counts)
    low = class_counts["low"]
    mixed = class_counts["mixed"]
    high = class_counts["high"]
    total = low + mixed + high
    low_pairs = low**2
    high_pairs = total**2 - (low + mixed) ** 2
    mixed_pairs = total**2 - low_pairs - high_pairs
    return {
        "low": low_pairs,
        "mixed": mixed_pairs,
        "high": high_pairs,
    }


def _stateful_predicate_class_counts(
    predicate_counts: Mapping[str, int],
) -> dict[str, int]:
    result = {
        "parity": 0,
        "comparison": 0,
        "modular": 0,
    }
    for kind, count in predicate_counts.items():
        if kind in {"even", "odd"}:
            result["parity"] += count
        elif kind == "mod_eq":
            result["modular"] += count
        else:
            result["comparison"] += count
    return result


def _stateful_feature_buckets(axes: StatefulAxes) -> list[FeatureBucket]:
    predicate_counts = _predicate_count_by_kind(
        selected_kinds={ptype.value for ptype in set(axes.predicate_types)},
        threshold_range=axes.threshold_range,
        divisor_range=axes.divisor_range,
        min_composed_operands=axes.min_composed_operands,
    )
    transform_counts = _transform_count_by_kind(
        selected_kinds={ttype.value for ttype in set(axes.transform_types)},
        shift_range=axes.shift_range,
        scale_range=axes.scale_range,
    )
    predicate_class_counts = _stateful_predicate_class_counts(predicate_counts)
    single_transform_class_counts = _stateful_transform_class_counts(
        transform_counts
    )
    pair_transform_class_counts = _stateful_pair_transform_class_counts(
        transform_counts
    )
    sampled_init_count = _range_size(SAMPLED_INIT_RANGE)

    buckets: list[FeatureBucket] = []
    selected_templates = {template.value for template in set(axes.templates)}

    def emit(
        *,
        template: str,
        predicate_class: str,
        transform_complexity: str,
        count: int,
    ) -> None:
        if count <= 0:
            return
        buckets.append(
            FeatureBucket(
                features={
                    "template": template,
                    "predicate_class": predicate_class,
                    "transform_complexity": transform_complexity,
                },
                unique_count=count,
            )
        )

    if StatefulTemplateType.CONDITIONAL_LINEAR_SUM.value in selected_templates:
        for predicate_class, predicate_count in predicate_class_counts.items():
            for (
                complexity,
                transform_pair_count,
            ) in pair_transform_class_counts.items():
                emit(
                    template=StatefulTemplateType.CONDITIONAL_LINEAR_SUM.value,
                    predicate_class=predicate_class,
                    transform_complexity=complexity,
                    count=(
                        predicate_count
                        * transform_pair_count
                        * sampled_init_count
                    ),
                )

    if (
        StatefulTemplateType.RESETTING_BEST_PREFIX_SUM.value
        in selected_templates
    ):
        reset_value_transform_class_counts = dict(single_transform_class_counts)
        if "identity" in transform_counts:
            # Identity route serializes as None for resetting template.
            reset_value_transform_class_counts["low"] += 1
            reset_value_transform_class_counts["low"] -= transform_counts[
                "identity"
            ]
        for predicate_class, predicate_count in predicate_class_counts.items():
            for (
                complexity,
                value_transform_count,
            ) in reset_value_transform_class_counts.items():
                emit(
                    template=StatefulTemplateType.RESETTING_BEST_PREFIX_SUM.value,
                    predicate_class=predicate_class,
                    transform_complexity=complexity,
                    count=(
                        predicate_count
                        * value_transform_count
                        * sampled_init_count
                    ),
                )

    if StatefulTemplateType.LONGEST_RUN.value in selected_templates:
        for predicate_class, predicate_count in predicate_class_counts.items():
            emit(
                template=StatefulTemplateType.LONGEST_RUN.value,
                predicate_class=predicate_class,
                transform_complexity="low",
                count=predicate_count,
            )

    if StatefulTemplateType.TOGGLE_SUM.value in selected_templates:
        for predicate_class, predicate_count in predicate_class_counts.items():
            for (
                complexity,
                transform_pair_count,
            ) in pair_transform_class_counts.items():
                emit(
                    template=StatefulTemplateType.TOGGLE_SUM.value,
                    predicate_class=predicate_class,
                    transform_complexity=complexity,
                    count=(
                        predicate_count
                        * transform_pair_count
                        * sampled_init_count
                    ),
                )

    return buckets


def _simple_algorithms_feature_buckets(
    axes: SimpleAlgorithmsAxes,
) -> list[FeatureBucket]:
    if axes.pre_filter_types is None:
        pre_filter_none_count = 1
        pre_filter_non_none_count = 0
    else:
        pre_filter_counts = _predicate_count_by_kind(
            selected_kinds={
                ptype.value for ptype in set(axes.pre_filter_types)
            },
            threshold_range=(-50, 50),
            divisor_range=(2, 10),
            min_composed_operands=2,
        )
        pre_filter_none_count = 0
        pre_filter_non_none_count = sum(pre_filter_counts.values())

    if axes.pre_transform_types is None:
        pre_transform_none_count = 1
        pre_transform_non_none_count = 0
    else:
        pre_transform_counts = _transform_count_by_kind(
            selected_kinds={
                ttype.value for ttype in set(axes.pre_transform_types)
            },
            shift_range=PREPROCESS_SHIFT_RANGE,
            scale_range=PREPROCESS_SCALE_RANGE,
        )
        pre_transform_none_count = 0
        pre_transform_non_none_count = sum(pre_transform_counts.values())

    preprocess_bucket_counts = {
        "none": pre_filter_none_count * pre_transform_none_count,
        "single": (
            pre_filter_none_count * pre_transform_non_none_count
            + pre_filter_non_none_count * pre_transform_none_count
        ),
        "both": pre_filter_non_none_count * pre_transform_non_none_count,
    }

    buckets: list[FeatureBucket] = []
    selected_templates = {template.value for template in set(axes.templates)}

    if SimpleAlgorithmTemplateType.MOST_FREQUENT.value in selected_templates:
        static_count = _range_size(axes.empty_default_range) * (
            1
            if axes.tie_default_range is None
            else _range_size(axes.tie_default_range)
        )
        for tie_break_mode in {
            mode.value for mode in set(axes.tie_break_modes)
        }:
            for (
                preprocess_bucket,
                preprocess_count,
            ) in preprocess_bucket_counts.items():
                if preprocess_count <= 0:
                    continue
                buckets.append(
                    FeatureBucket(
                        features={
                            "template": (
                                SimpleAlgorithmTemplateType.MOST_FREQUENT.value
                            ),
                            "tie_break": tie_break_mode,
                            "preprocess_bucket": preprocess_bucket,
                        },
                        unique_count=static_count * preprocess_count,
                    )
                )

    if SimpleAlgorithmTemplateType.COUNT_PAIRS_SUM.value in selected_templates:
        static_count = (
            _range_size(axes.target_range)
            * (
                1
                if axes.no_result_default_range is None
                else _range_size(axes.no_result_default_range)
            )
            * (
                1
                if axes.short_list_default_range is None
                else _range_size(axes.short_list_default_range)
            )
        )
        for counting_mode in {mode.value for mode in set(axes.counting_modes)}:
            for (
                preprocess_bucket,
                preprocess_count,
            ) in preprocess_bucket_counts.items():
                if preprocess_count <= 0:
                    continue
                buckets.append(
                    FeatureBucket(
                        features={
                            "template": (
                                SimpleAlgorithmTemplateType.COUNT_PAIRS_SUM.value
                            ),
                            "counting_mode": counting_mode,
                            "preprocess_bucket": preprocess_bucket,
                        },
                        unique_count=static_count * preprocess_count,
                    )
                )

    if SimpleAlgorithmTemplateType.MAX_WINDOW_SUM.value in selected_templates:
        lo, hi = axes.window_size_range
        k_bucket_counts = {
            "small": _bucketed_count(lo, hi, 1, 3),
            "medium": _bucketed_count(lo, hi, 4, 6),
            "large": 0 if hi < 7 else hi - max(lo, 7) + 1,
        }
        static_count = _range_size(axes.empty_default_range) * (
            1
            if axes.empty_default_for_empty_range is None
            else _range_size(axes.empty_default_for_empty_range)
        )
        for k_bucket, k_count in k_bucket_counts.items():
            if k_count <= 0:
                continue
            for (
                preprocess_bucket,
                preprocess_count,
            ) in preprocess_bucket_counts.items():
                if preprocess_count <= 0:
                    continue
                buckets.append(
                    FeatureBucket(
                        features={
                            "template": (
                                SimpleAlgorithmTemplateType.MAX_WINDOW_SUM.value
                            ),
                            "k_bucket": k_bucket,
                            "preprocess_bucket": preprocess_bucket,
                        },
                        unique_count=k_count * static_count * preprocess_count,
                    )
                )

    return buckets


def _fsm_n_states_bucket(n_states: int) -> str:
    if n_states <= 3:
        return "small"
    if n_states == 4:
        return "medium"
    return "large"


def _fsm_feature_buckets(axes: FsmAxes) -> list[FeatureBucket]:
    predicate_counts = _predicate_count_by_kind(
        selected_kinds={ptype.value for ptype in set(axes.predicate_types)},
        threshold_range=axes.threshold_range,
        divisor_range=axes.divisor_range,
        min_composed_operands=2,
    )
    per_transition_predicate_count = sum(predicate_counts.values())

    lo_states, hi_states = axes.n_states_range
    lo_transitions, hi_transitions = axes.transitions_per_state_range
    output_modes = {mode.value for mode in set(axes.output_modes)}
    undefined_policies = {
        policy.value for policy in set(axes.undefined_transition_policies)
    }

    buckets: list[FeatureBucket] = []
    for n_states in range(lo_states, hi_states + 1):
        per_transition_count = per_transition_predicate_count * n_states
        per_state_count = sum(
            per_transition_count**k
            for k in range(lo_transitions, hi_transitions + 1)
        )
        # all accept-flag assignments except all-false survive post-processing.
        accept_assignment_count = (1 << n_states) - 1
        state_structure_count = (
            per_state_count**n_states
        ) * accept_assignment_count
        start_state_count = n_states
        per_mode_policy_count = state_structure_count * start_state_count
        for output_mode in output_modes:
            for undefined_policy in undefined_policies:
                buckets.append(
                    FeatureBucket(
                        features={
                            "output_mode": output_mode,
                            "undefined_transition_policy": undefined_policy,
                            "n_states": str(n_states),
                            "n_states_bucket": _fsm_n_states_bucket(n_states),
                        },
                        unique_count=per_mode_policy_count,
                    )
                )
    return buckets


def _bitops_width_bucket(width_bits: int) -> str:
    if width_bits <= 8:
        return "8"
    if width_bits <= 16:
        return "16"
    return "32"


def _bitops_n_ops_bucket(n_ops: int) -> str:
    if n_ops <= 3:
        return "short"
    if n_ops == 4:
        return "medium"
    return "long"


def _bitops_feature_buckets(axes: BitopsAxes) -> list[FeatureBucket]:
    widths = sorted(set(axes.width_choices))
    allowed_ops = {op.value for op in set(axes.allowed_ops)}
    n_ops_lo, n_ops_hi = axes.n_ops_range

    mask_op_names = {"and_mask", "or_mask", "xor_mask"}
    shift_op_names = {"shl", "shr_logical", "rotl", "rotr"}
    advanced_op_names = {"popcount", "parity"}
    logic_op_names = {"and_mask", "or_mask", "xor_mask", "not"}

    mask_range_size = _range_size(axes.mask_range)
    shift_arg_count = _range_size(axes.shift_range)

    buckets: list[FeatureBucket] = []
    for width_bits in widths:
        mask_value_count = min(mask_range_size, 1 << width_bits)

        instruction_count_by_op: dict[str, int] = {}
        for op_name in allowed_ops:
            if op_name in mask_op_names:
                instruction_count_by_op[op_name] = mask_value_count
            elif op_name in shift_op_names:
                instruction_count_by_op[op_name] = shift_arg_count
            else:
                instruction_count_by_op[op_name] = 1

        total_instruction_count = sum(instruction_count_by_op.values())
        advanced_instruction_count = sum(
            count
            for op_name, count in instruction_count_by_op.items()
            if op_name in advanced_op_names
        )
        logic_instruction_count = sum(
            count
            for op_name, count in instruction_count_by_op.items()
            if op_name in logic_op_names
        )
        non_advanced_instruction_count = (
            total_instruction_count - advanced_instruction_count
        )

        for n_ops in range(n_ops_lo, n_ops_hi + 1):
            total_sequences = total_instruction_count**n_ops
            advanced_sequences = (
                total_sequences - non_advanced_instruction_count**n_ops
                if advanced_instruction_count > 0
                else 0
            )
            logic_only_sequences = (
                logic_instruction_count**n_ops
                if logic_instruction_count > 0
                else 0
            )
            shift_mix_sequences = (
                total_sequences - advanced_sequences - logic_only_sequences
            )

            shared_features = {
                "width_bits": str(width_bits),
                "width_bits_bucket": _bitops_width_bucket(width_bits),
                "n_ops": str(n_ops),
                "n_ops_bucket": _bitops_n_ops_bucket(n_ops),
            }
            if logic_only_sequences > 0:
                buckets.append(
                    FeatureBucket(
                        features={
                            **shared_features,
                            "op_mix_bucket": "logic_only",
                        },
                        unique_count=logic_only_sequences,
                    )
                )
            if shift_mix_sequences > 0:
                buckets.append(
                    FeatureBucket(
                        features={
                            **shared_features,
                            "op_mix_bucket": "shift_mix",
                        },
                        unique_count=shift_mix_sequences,
                    )
                )
            if advanced_sequences > 0:
                buckets.append(
                    FeatureBucket(
                        features={
                            **shared_features,
                            "op_mix_bucket": "advanced",
                        },
                        unique_count=advanced_sequences,
                    )
                )
    return buckets


_EXACT_ANALYZERS: dict[str, Callable[[Any], list[FeatureBucket]]] = {
    "stateful": _stateful_feature_buckets,
    "simple_algorithms": _simple_algorithms_feature_buckets,
    "fsm": _fsm_feature_buckets,
    "bitops": _bitops_feature_buckets,
}


def analyze_spec_space(
    *,
    family: str,
    axes: Any,
    feature_partitioner: FeaturePartitioner | None = None,
    task_partitioner: TaskPartitioner | None = None,
    sample_budget: int = 10_000,
    seed: int = 0,
) -> SpecSpaceReport:
    analyzer = _EXACT_ANALYZERS.get(family)
    if analyzer is not None:
        buckets = analyzer(axes)
        total_unique = sum(bucket.unique_count for bucket in buckets)
        partition_unique: dict[str, int] | None = None
        if feature_partitioner is not None:
            partition_unique = {}
            for bucket in buckets:
                key = feature_partitioner(bucket.features)
                partition_unique[key] = (
                    partition_unique.get(key, 0) + bucket.unique_count
                )
        return SpecSpaceReport(
            family=family,
            mode="exact",
            total_unique=total_unique,
            partition_unique=partition_unique,
        )

    rng = random.Random(seed)
    seen_task_ids: set[str] = set()
    partition_unique: dict[str, int] | None = (
        {} if task_partitioner is not None else None
    )
    for _ in range(max(0, sample_budget)):
        task = generate_task_for_family(family, rng=rng, axes=axes)
        if not task.queries or task.task_id in seen_task_ids:
            continue
        seen_task_ids.add(task.task_id)
        if partition_unique is not None and task_partitioner is not None:
            key = task_partitioner(task)
            partition_unique[key] = partition_unique.get(key, 0) + 1

    notes = (
        "lower_bound_only",
        "family lacks exact spec-space analyzer",
    )
    return SpecSpaceReport(
        family=family,
        mode="lower_bound",
        total_unique=len(seen_task_ids),
        partition_unique=partition_unique,
        sampled_draws=sample_budget,
        notes=notes,
    )


def enforce_spec_capacity(
    *,
    family: str,
    axes: Any,
    requested_total: int | None = None,
    requested_partition_counts: dict[str, int] | None = None,
    feature_partitioner: FeaturePartitioner | None = None,
    task_partitioner: TaskPartitioner | None = None,
    require_exact: bool = False,
    sample_budget: int = 10_000,
    seed: int = 0,
) -> SpecSpaceReport:
    report = analyze_spec_space(
        family=family,
        axes=axes,
        feature_partitioner=feature_partitioner,
        task_partitioner=task_partitioner,
        sample_budget=sample_budget,
        seed=seed,
    )
    if require_exact and report.mode != "exact":
        raise SpecCapacityError(
            "exact spec-space analysis is required but unavailable for "
            f"family={family!r}"
        )

    if report.mode != "exact":
        return report

    if requested_total is not None and requested_total > report.total_unique:
        raise SpecCapacityError(
            "requested unique count exceeds exact spec-space capacity: "
            f"family={family!r} requested={requested_total} "
            f"capacity={report.total_unique}"
        )

    if requested_partition_counts is None:
        return report

    if report.partition_unique is None:
        raise SpecCapacityError(
            "requested partition counts require a partitioner for "
            f"family={family!r}"
        )

    deficits: list[tuple[str, int, int]] = []
    for key, requested in requested_partition_counts.items():
        available = report.partition_unique.get(key, 0)
        if requested > available:
            deficits.append((key, requested, available))

    if deficits:
        details = "; ".join(
            f"{key}: requested={requested}, available={available}"
            for key, requested, available in sorted(deficits)
        )
        raise SpecCapacityError(
            "requested partition counts exceed exact spec-space capacity: "
            f"family={family!r}; {details}"
        )

    return report


def default_exact_families() -> tuple[str, ...]:
    return tuple(sorted(_EXACT_ANALYZERS))
