"""Tests for balanced suite generation."""

import importlib.util
import random
from collections.abc import Callable
from typing import cast

import pytest

from genfxn.simple_algorithms.models import (
    CountingMode,
)
from genfxn.simple_algorithms.models import (
    TemplateType as SATemplateType,
)
from genfxn.suites.features import (
    bitops_features,
    fsm_features,
    graph_queries_features,
    intervals_features,
    sequence_dp_features,
    simple_algorithms_features,
    stateful_features,
    stringrules_features,
    temporal_logic_features,
)
from genfxn.suites.generate import (
    Candidate,
    PoolStats,
    _pool_axes_simple_algorithms_d3,
    _pool_axes_simple_algorithms_d4,
    generate_pool,
    generate_suite,
    greedy_select,
    quota_report,
)
from genfxn.suites.quotas import QUOTAS, Bucket, QuotaSpec

StackBytecodeRenderFn = Callable[[list[int]], tuple[int, int]]
FsmRenderFn = Callable[[list[int]], int]
BitopsRenderFn = Callable[[int], int]
SequenceDpRenderFn = Callable[[list[int], list[int]], int]
IntervalsRenderFn = Callable[[list[tuple[int, int]]], int]
GraphQueriesRenderFn = Callable[[int, int], int]
TemporalLogicRenderFn = Callable[[list[int]], int]


def _require_family_suite_module(family: str, module: str) -> None:
    if family not in QUOTAS:
        pytest.fail(f"{family} is missing from suite quotas")
    if importlib.util.find_spec(module) is None:
        pytest.fail(f"{module} is not importable")


def _stack_suite_available() -> bool:
    _require_family_suite_module("stack_bytecode", "genfxn.stack_bytecode.task")
    return True


def _fsm_suite_available() -> bool:
    _require_family_suite_module("fsm", "genfxn.fsm.task")
    return True


def _bitops_suite_available() -> bool:
    _require_family_suite_module("bitops", "genfxn.bitops.task")
    return True


def _sequence_dp_suite_available() -> bool:
    _require_family_suite_module("sequence_dp", "genfxn.sequence_dp.task")
    return True


def _intervals_suite_available() -> bool:
    _require_family_suite_module("intervals", "genfxn.intervals.task")
    return True


def _graph_queries_suite_available() -> bool:
    _require_family_suite_module("graph_queries", "genfxn.graph_queries.task")
    return True


def _temporal_logic_suite_available() -> bool:
    _require_family_suite_module("temporal_logic", "genfxn.temporal_logic.task")
    return True


# ── Feature extraction tests ─────────────────────────────────────────────


class TestStringrulesFeatures:
    def test_simple_no_comp_no_pipe(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "lowercase"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "a"},
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "identity"},
                },
                {
                    "predicate": {"kind": "is_lower"},
                    "transform": {"kind": "capitalize"},
                },
            ],
            "default_transform": {"kind": "reverse"},
        }
        f = stringrules_features(spec)
        assert f["n_rules_bucket"] == "4-5"
        assert f["has_comp"] == "false"
        assert f["has_pipe"] == "false"
        assert f["mode"] == "neither"
        assert f["comp_max_score"] == "0"
        assert f["pipe_max_score"] == "0"
        assert f["pred_majority"] == "simple"  # 3 simple vs 1 pattern
        assert (
            f["transform_majority"] == "simple"
        )  # lowercase, uppercase, capitalize, reverse = 4 simple vs 1 identity

    def test_comp_only_mode(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {
                        "kind": "not",
                        "operand": {"kind": "is_alpha"},
                    },
                    "transform": {"kind": "lowercase"},
                },
                {
                    "predicate": {
                        "kind": "and",
                        "operands": [
                            {"kind": "is_digit"},
                            {"kind": "is_lower"},
                        ],
                    },
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "capitalize"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "x"},
                    "transform": {"kind": "reverse"},
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "lowercase"},
        }
        f = stringrules_features(spec)
        assert f["has_comp"] == "true"
        assert f["has_pipe"] == "false"
        assert f["mode"] == "comp-only"
        assert int(f["comp_max_score"]) >= 4

    def test_pipe_only_mode(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {
                        "kind": "pipeline",
                        "steps": [{"kind": "lowercase"}, {"kind": "reverse"}],
                    },
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "is_lower"},
                    "transform": {"kind": "capitalize"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "a"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "reverse"},
        }
        f = stringrules_features(spec)
        assert f["has_comp"] == "false"
        assert f["has_pipe"] == "true"
        assert f["mode"] == "pipe-only"
        assert int(f["pipe_max_score"]) >= 3

    def test_both_mode(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {
                        "kind": "not",
                        "operand": {"kind": "is_alpha"},
                    },
                    "transform": {
                        "kind": "pipeline",
                        "steps": [
                            {"kind": "lowercase"},
                            {"kind": "replace", "old": "a", "new": "b"},
                        ],
                    },
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "is_lower"},
                    "transform": {"kind": "capitalize"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "x"},
                    "transform": {"kind": "identity"},
                },
                {
                    "predicate": {"kind": "ends_with", "suffix": "y"},
                    "transform": {"kind": "reverse"},
                },
                {
                    "predicate": {"kind": "contains", "substring": "z"},
                    "transform": {"kind": "swapcase"},
                },
            ],
            "default_transform": {"kind": "lowercase"},
        }
        f = stringrules_features(spec)
        assert f["has_comp"] == "true"
        assert f["has_pipe"] == "true"
        assert f["mode"] == "both"
        assert f["n_rules_bucket"] == "6-7"

    def test_n_rules_buckets(self) -> None:
        def make_spec(n: int) -> dict:
            rules = [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "identity"},
                }
            ] * n
            return {"rules": rules, "default_transform": {"kind": "identity"}}

        assert stringrules_features(make_spec(4))["n_rules_bucket"] == "4-5"
        assert stringrules_features(make_spec(5))["n_rules_bucket"] == "4-5"
        assert stringrules_features(make_spec(6))["n_rules_bucket"] == "6-7"
        assert stringrules_features(make_spec(7))["n_rules_bucket"] == "6-7"
        assert stringrules_features(make_spec(8))["n_rules_bucket"] == "8-10"
        assert stringrules_features(make_spec(10))["n_rules_bucket"] == "8-10"

    def test_pred_majority_recurses_all_composed_operands(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {
                        "kind": "and",
                        "operands": [
                            {"kind": "is_alpha"},
                            {"kind": "length_cmp", "op": "gt", "n": 5},
                            {"kind": "length_cmp", "op": "eq", "n": 2},
                        ],
                    },
                    "transform": {"kind": "identity"},
                },
                {
                    "predicate": {"kind": "starts_with", "prefix": "a"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        f = stringrules_features(spec)
        assert f["pred_majority"] == "length"

    def test_transform_majority_recurses_all_pipeline_steps(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {
                        "kind": "pipeline",
                        "steps": [
                            {"kind": "identity"},
                            {"kind": "replace", "old": "a", "new": "b"},
                            {"kind": "append", "suffix": "x"},
                            {"kind": "prepend", "prefix": "y"},
                        ],
                    },
                }
            ],
            "default_transform": {"kind": "lowercase"},
        }
        f = stringrules_features(spec)
        assert f["transform_majority"] == "param"


class TestStatefulFeatures:
    def test_conditional_comparison(self) -> None:
        spec = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "gt", "value": 5},
            "true_transform": {"kind": "shift", "offset": 3},
            "false_transform": {"kind": "scale", "factor": 2},
            "init_value": 0,
        }
        f = stateful_features(spec)
        assert f["template"] == "conditional_linear_sum"
        assert f["pred_kind"] == "comparison"
        assert f["transform_bucket"] == "atomic_nonidentity"
        assert f["transform_signature"] == "both_affine"

    def test_conditional_mixed_signature(self) -> None:
        spec = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "mod_eq", "divisor": 3, "remainder": 0},
            "true_transform": {"kind": "abs"},
            "false_transform": {"kind": "shift", "offset": 1},
            "init_value": 0,
        }
        f = stateful_features(spec)
        assert f["pred_kind"] == "mod_eq"
        assert f["transform_signature"] == "mixed"

    def test_conditional_sign_signature(self) -> None:
        spec = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "lt", "value": 0},
            "true_transform": {"kind": "abs"},
            "false_transform": {"kind": "negate"},
            "init_value": 0,
        }
        f = stateful_features(spec)
        assert f["transform_signature"] == "both_sign"

    def test_resetting_pipeline5(self) -> None:
        spec = {
            "template": "resetting_best_prefix_sum",
            "reset_predicate": {
                "kind": "and",
                "operands": [{"kind": "gt", "value": 0}, {"kind": "even"}],
            },
            "init_value": 0,
            "value_transform": {
                "kind": "pipeline",
                "steps": [
                    {"kind": "shift", "offset": 1},
                    {"kind": "scale", "factor": 2},
                    {"kind": "abs"},
                ],
            },
        }
        f = stateful_features(spec)
        assert f["template"] == "resetting_best_prefix_sum"
        assert f["pred_kind"] == "composed"
        assert f["transform_bucket"] == "pipeline5"
        assert "transform_signature" not in f  # only for conditional

    def test_toggle_sum(self) -> None:
        spec = {
            "template": "toggle_sum",
            "toggle_predicate": {
                "kind": "mod_eq",
                "divisor": 2,
                "remainder": 0,
            },
            "on_transform": {
                "kind": "pipeline",
                "steps": [{"kind": "shift", "offset": 5}, {"kind": "abs"}],
            },
            "off_transform": {
                "kind": "pipeline",
                "steps": [{"kind": "scale", "factor": -1}, {"kind": "negate"}],
            },
            "init_value": 0,
        }
        f = stateful_features(spec)
        assert f["template"] == "toggle_sum"
        assert f["pred_kind"] == "mod_eq"
        # pipeline with 1 param step → score 4
        assert f["transform_bucket"] == "pipeline4"


class TestSimpleAlgorithmsFeatures:
    def test_no_preprocess(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": -5,
            "counting_mode": "all_indices",
        }
        f = simple_algorithms_features(spec)
        assert f["template"] == "count_pairs_sum"
        assert f["preprocess_bucket"] == "none"
        assert f["has_filter"] == "false"
        assert f["has_transform"] == "false"
        assert f["filter_kind"] == "none"
        assert f["pre_transform_complexity"] == "none"
        assert f["edge_count"] == "0"
        assert f["target_sign"] == "neg"

    def test_with_preprocess_both(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": 0,
            "pre_filter": {"kind": "mod_eq", "divisor": 3, "remainder": 0},
            "pre_transform": {
                "kind": "pipeline",
                "steps": [
                    {"kind": "shift", "offset": 1},
                    {"kind": "scale", "factor": 2},
                ],
            },
            "tie_default": 99,
        }
        f = simple_algorithms_features(spec)
        assert f["preprocess_bucket"] == "both"
        assert f["has_filter"] == "true"
        assert f["has_transform"] == "true"
        assert f["filter_kind"] == "mod_eq"
        assert (
            f["pre_transform_complexity"] == "pipeline5"
        )  # 2 param steps → score 5
        assert f["edge_count"] == "1"  # tie_default

    def test_max_window_sum_edges(self) -> None:
        spec = {
            "template": "max_window_sum",
            "k": 8,
            "invalid_k_default": 0,
            "pre_filter": {"kind": "gt", "value": 0},
            "pre_transform": {"kind": "abs"},
            "empty_default": -1,
        }
        f = simple_algorithms_features(spec)
        assert f["template"] == "max_window_sum"
        assert f["k_bucket"] == "8-10"
        assert f["preprocess_bucket"] == "both"
        assert f["filter_kind"] == "comparison"
        assert f["pre_transform_complexity"] == "atomic"
        assert f["edge_count"] == "1"  # empty_default

    def test_max_window_sum_k_bucket_out_of_range(self) -> None:
        spec = {
            "template": "max_window_sum",
            "k": 5,
            "pre_filter": None,
            "pre_transform": None,
        }
        f = simple_algorithms_features(spec)
        assert f["k_bucket"] == "out_of_range"

    def test_target_sign_zero(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 0,
            "counting_mode": "unique_values",
        }
        f = simple_algorithms_features(spec)
        assert f["target_sign"] == "zero"

    def test_target_sign_pos(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 10,
            "counting_mode": "all_indices",
        }
        f = simple_algorithms_features(spec)
        assert f["target_sign"] == "pos"

    def test_filter_only(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 5,
            "counting_mode": "all_indices",
            "pre_filter": {
                "kind": "and",
                "operands": [
                    {"kind": "gt", "value": 0},
                    {"kind": "lt", "value": 100},
                ],
            },
            "no_result_default": -1,
        }
        f = simple_algorithms_features(spec)
        assert f["preprocess_bucket"] == "filter_only"
        assert f["filter_kind"] == "composed"
        assert f["edge_count"] == "1"


class TestFsmFeatures:
    def test_basic_fsm_features(self) -> None:
        spec = {
            "machine_type": "moore",
            "output_mode": "final_state_id",
            "undefined_transition_policy": "stay",
            "states": [
                {
                    "id": 0,
                    "is_accept": False,
                    "transitions": [
                        {
                            "predicate": {"kind": "even"},
                            "target_state_id": 1,
                        }
                    ],
                },
                {
                    "id": 1,
                    "is_accept": True,
                    "transitions": [
                        {
                            "predicate": {"kind": "odd"},
                            "target_state_id": 0,
                        }
                    ],
                },
            ],
        }
        f = fsm_features(spec)
        assert f["n_states_bucket"] == "2"
        assert f["transition_density_bucket"] == "low"
        assert f["predicate_complexity"] == "basic"
        assert f["machine_type"] == "moore"
        assert f["output_mode"] == "final_state_id"
        assert f["undefined_policy"] == "stay"

    def test_modular_predicates_and_dense_transitions(self) -> None:
        spec = {
            "machine_type": "mealy",
            "output_mode": "transition_count",
            "undefined_transition_policy": "error",
            "states": [
                {
                    "id": 0,
                    "is_accept": False,
                    "transitions": [
                        {
                            "predicate": {
                                "kind": "mod_eq",
                                "divisor": 3,
                                "remainder": 1,
                            },
                            "target_state_id": 1,
                        },
                        {
                            "predicate": {"kind": "gt", "value": 0},
                            "target_state_id": 2,
                        },
                        {
                            "predicate": {"kind": "lt", "value": 0},
                            "target_state_id": 3,
                        },
                    ],
                },
                {"id": 1, "is_accept": True, "transitions": []},
                {"id": 2, "is_accept": False, "transitions": []},
                {"id": 3, "is_accept": False, "transitions": []},
            ],
        }
        f = fsm_features(spec)
        assert f["n_states_bucket"] == "3-4"
        assert f["transition_density_bucket"] == "low"
        assert f["predicate_complexity"] == "modular"
        assert f["machine_type"] == "mealy"
        assert f["output_mode"] == "transition_count"
        assert f["undefined_policy"] == "error"


class TestBitopsFeatures:
    def test_basic_bitops_features(self) -> None:
        spec = {
            "width_bits": 8,
            "operations": [
                {"op": "xor_mask", "arg": 3},
                {"op": "not", "arg": None},
            ],
        }
        f = bitops_features(spec)
        assert f["n_ops_bucket"] == "1-2"
        assert f["width_bucket"] == "8"
        assert f["op_complexity"] == "basic"
        assert f["has_shift"] == "false"
        assert f["has_rotate"] == "false"
        assert f["has_aggregate"] == "false"

    def test_aggregate_bitops_features(self) -> None:
        spec = {
            "width_bits": 32,
            "operations": [
                {"op": "rotl", "arg": 3},
                {"op": "popcount", "arg": None},
                {"op": "parity", "arg": None},
                {"op": "shr_logical", "arg": 1},
            ],
        }
        f = bitops_features(spec)
        assert f["n_ops_bucket"] == "3-4"
        assert f["width_bucket"] == "24-32"
        assert f["op_complexity"] == "aggregate"
        assert f["has_shift"] == "true"
        assert f["has_rotate"] == "true"
        assert f["has_aggregate"] == "true"


class TestSequenceDpFeatures:
    def test_eq_score_profile_and_tie_bucket(self) -> None:
        spec = {
            "template": "global",
            "output_mode": "score",
            "match_predicate": {"kind": "eq"},
            "match_score": 7,
            "mismatch_score": -3,
            "gap_score": -4,
            "step_tie_break": "diag_up_left",
        }
        f = sequence_dp_features(spec)
        assert f["template"] == "global"
        assert f["output_mode"] == "score"
        assert f["predicate_kind"] == "eq"
        assert f["score_profile"] == "wide"
        assert f["tie_break_bucket"] == "diag_first"
        assert f["abs_diff_bucket"] == "na"
        assert f["divisor_bucket"] == "na"

    def test_abs_diff_bucket(self) -> None:
        spec = {
            "template": "global",
            "output_mode": "alignment_len",
            "match_predicate": {"kind": "abs_diff_le", "max_diff": 3},
            "match_score": 5,
            "mismatch_score": 0,
            "gap_score": -1,
            "step_tie_break": "diag_left_up",
        }
        f = sequence_dp_features(spec)
        assert f["predicate_kind"] == "abs_diff_le"
        assert f["abs_diff_bucket"] == "2-3"
        assert f["tie_break_order"] == "diag_left_up"

    def test_mod_divisor_bucket_and_tie_heavy(self) -> None:
        spec = {
            "template": "local",
            "output_mode": "gap_count",
            "match_predicate": {
                "kind": "mod_eq",
                "divisor": 9,
                "remainder": 2,
            },
            "match_score": 1,
            "mismatch_score": 2,
            "gap_score": 2,
            "step_tie_break": "left_up_diag",
        }
        f = sequence_dp_features(spec)
        assert f["predicate_kind"] == "mod_eq"
        assert f["divisor_bucket"] == "8+"
        assert f["tie_break_bucket"] == "left_first"
        assert f["score_profile"] == "tie_heavy"


class TestIntervalsFeatures:
    def test_total_coverage_closed(self) -> None:
        spec = {
            "operation": "total_coverage",
            "boundary_mode": "closed_closed",
            "merge_touching": True,
            "endpoint_clip_abs": 18,
            "endpoint_quantize_step": 1,
        }
        f = intervals_features(spec)
        assert f["operation"] == "total_coverage"
        assert f["boundary_mode"] == "closed_closed"
        assert f["boundary_bucket"] == "closed"
        assert f["merge_touching"] == "true"
        assert f["clip_bucket"] == "very_wide"
        assert f["quantize_bucket"] == "none"

    def test_gap_count_open_boundary(self) -> None:
        spec = {
            "operation": "gap_count",
            "boundary_mode": "open_open",
            "merge_touching": False,
            "endpoint_clip_abs": 5,
            "endpoint_quantize_step": 2,
        }
        f = intervals_features(spec)
        assert f["operation"] == "gap_count"
        assert f["boundary_bucket"] == "open"
        assert f["merge_touching"] == "false"
        assert f["clip_bucket"] == "tight"
        assert f["quantize_bucket"] == "step2"

    def test_mixed_boundary_bucket(self) -> None:
        spec = {
            "operation": "merged_count",
            "boundary_mode": "closed_open",
            "merge_touching": False,
            "endpoint_clip_abs": 10,
            "endpoint_quantize_step": 4,
        }
        f = intervals_features(spec)
        assert f["boundary_bucket"] == "mixed"
        assert f["clip_bucket"] == "medium"
        assert f["quantize_bucket"] == "step3-4"

    def test_bool_like_inputs_use_consistent_coercion(self) -> None:
        spec = {
            "operation": "merged_count",
            "boundary_mode": "closed_open",
            "merge_touching": "false",
            "endpoint_clip_abs": True,
            "endpoint_quantize_step": True,
        }
        f = intervals_features(spec)
        assert f["merge_touching"] == "false"
        assert f["clip_bucket"] == "very_wide"
        assert f["quantize_bucket"] == "none"


class TestGraphQueriesFeatures:
    def test_directed_unweighted_with_duplicates(self) -> None:
        spec = {
            "query_type": "min_hops",
            "directed": True,
            "weighted": False,
            "n_nodes": 6,
            "edges": [
                {"u": 0, "v": 1, "w": 1},
                {"u": 1, "v": 2, "w": 1},
                {"u": 1, "v": 2, "w": 3},
                {"u": 2, "v": 3, "w": 1},
            ],
        }
        f = graph_queries_features(spec)
        assert f["query_type"] == "min_hops"
        assert f["mode"] == "directed_unweighted"
        assert f["nodes_bucket"] == "6-7"
        assert f["density_bucket"] == "sparse"
        assert f["has_duplicates"] == "true"
        assert f["has_isolated"] == "true"

    def test_undirected_weighted_denseish(self) -> None:
        spec = {
            "query_type": "shortest_path_cost",
            "directed": False,
            "weighted": True,
            "n_nodes": 5,
            "edges": [
                {"u": 0, "v": 1, "w": 2},
                {"u": 0, "v": 2, "w": 4},
                {"u": 1, "v": 2, "w": 1},
                {"u": 1, "v": 3, "w": 3},
                {"u": 2, "v": 4, "w": 5},
            ],
        }
        f = graph_queries_features(spec)
        assert f["query_type"] == "shortest_path_cost"
        assert f["mode"] == "undirected_weighted"
        assert f["nodes_bucket"] == "4-5"
        assert f["density_bucket"] in {"light", "medium"}
        assert f["has_duplicates"] == "false"

    def test_single_node_bucket(self) -> None:
        spec = {
            "query_type": "reachable",
            "directed": False,
            "weighted": False,
            "n_nodes": 1,
            "edges": [],
        }
        f = graph_queries_features(spec)
        assert f["nodes_bucket"] == "1"

    def test_bool_like_mode_inputs_are_coerced(self) -> None:
        spec = {
            "query_type": "reachable",
            "directed": "false",
            "weighted": "true",
            "n_nodes": 4,
            "edges": [],
        }
        f = graph_queries_features(spec)
        assert f["directed"] == "false"
        assert f["weighted"] == "true"
        assert f["mode"] == "undirected_weighted"


class TestTemporalLogicFeatures:
    def test_atom_sat_at_start(self) -> None:
        spec = {
            "output_mode": "sat_at_start",
            "formula": {"op": "atom", "predicate": "eq", "constant": 1},
        }
        f = temporal_logic_features(spec)
        assert f["output_mode"] == "sat_at_start"
        assert f["depth_bucket"] == "1"
        assert f["temporal_bucket"] == "none"
        assert f["binary_bucket"] == "0"
        assert f["has_since"] == "false"

    def test_temporal_and_binary_buckets(self) -> None:
        spec = {
            "output_mode": "sat_count",
            "formula": {
                "op": "until",
                "left": {
                    "op": "eventually",
                    "child": {"op": "atom", "predicate": "lt", "constant": 0},
                },
                "right": {
                    "op": "and",
                    "left": {"op": "atom", "predicate": "ge", "constant": 2},
                    "right": {"op": "atom", "predicate": "ne", "constant": 4},
                },
            },
        }
        f = temporal_logic_features(spec)
        assert f["output_mode"] == "sat_count"
        assert f["depth_bucket"] == "3"
        assert f["temporal_bucket"] in {"single", "multi"}
        assert f["binary_bucket"] == "1-2"
        assert f["has_since"] == "false"

    def test_since_detected_as_hard_temporal(self) -> None:
        spec = {
            "output_mode": "first_sat_index",
            "formula": {
                "op": "since",
                "left": {"op": "atom", "predicate": "gt", "constant": 3},
                "right": {"op": "atom", "predicate": "le", "constant": 1},
            },
        }
        f = temporal_logic_features(spec)
        assert f["output_mode"] == "first_sat_index"
        assert f["temporal_bucket"] == "hard"
        assert f["has_since"] == "true"


class _FixedChoiceRng:
    def __init__(self, choices: list[object]) -> None:
        self._choices = choices
        self._idx = 0

    def choice(self, options: list[object]) -> object:
        if self._idx >= len(self._choices):
            raise AssertionError(f"Unexpected choice call: {options!r}")

        picked = self._choices[self._idx]
        self._idx += 1
        assert picked in options, f"{picked!r} not in {options!r}"
        return picked


class TestSimpleAlgorithmsD3PoolAxes:
    def test_zero_target_enables_both_edge_defaults(self) -> None:
        rng = _FixedChoiceRng([SATemplateType.COUNT_PAIRS_SUM, "zero"])

        axes = _pool_axes_simple_algorithms_d3(cast(random.Random, rng))

        assert axes.templates == [SATemplateType.COUNT_PAIRS_SUM]
        assert axes.target_range == (0, 0)
        assert axes.counting_modes == [
            CountingMode.ALL_INDICES,
            CountingMode.UNIQUE_VALUES,
        ]
        assert axes.no_result_default_range == (-10, 10)
        assert axes.short_list_default_range == (-5, 5)


class TestSimpleAlgorithmsD4PoolAxes:
    def test_most_frequent_uses_only_tie_default_edge(self) -> None:
        rng = _FixedChoiceRng(
            [
                SATemplateType.MOST_FREQUENT,
                "comparison",
                "atomic",
            ]
        )

        axes = _pool_axes_simple_algorithms_d4(cast(random.Random, rng))

        assert axes.templates == [SATemplateType.MOST_FREQUENT]
        assert axes.tie_default_range == (-10, 10)
        assert axes.empty_default_range == (0, 0)
        assert axes.no_result_default_range is None
        assert axes.short_list_default_range is None

    def test_max_window_sum_uses_only_empty_default_edge(self) -> None:
        rng = _FixedChoiceRng(
            [
                SATemplateType.MAX_WINDOW_SUM,
                "filter_only",
                "comparison",
            ]
        )

        axes = _pool_axes_simple_algorithms_d4(cast(random.Random, rng))

        assert axes.templates == [SATemplateType.MAX_WINDOW_SUM]
        assert axes.empty_default_for_empty_range == (-10, 10)
        assert axes.window_size_range == (1, 10)
        assert axes.no_result_default_range is None
        assert axes.short_list_default_range is None

    def test_count_pairs_sum_can_enable_second_edge(self) -> None:
        rng = _FixedChoiceRng(
            [
                SATemplateType.COUNT_PAIRS_SUM,
                "filter_only",
                "comparison",
                2,
            ]
        )

        axes = _pool_axes_simple_algorithms_d4(cast(random.Random, rng))

        assert axes.templates == [SATemplateType.COUNT_PAIRS_SUM]
        assert axes.no_result_default_range == (-10, 10)
        assert axes.short_list_default_range == (-5, 5)


# ── Hard constraint filtering tests ──────────────────────────────────────


class TestHardConstraints:
    def test_stringrules_d3_filters(self) -> None:
        quota = QUOTAS["stringrules"][3]
        # Should pass: no comp, no pipe
        features_ok = {
            "has_comp": "false",
            "has_pipe": "false",
            "n_rules_bucket": "4-5",
        }
        # Should fail: has comp
        features_bad = {
            "has_comp": "true",
            "has_pipe": "false",
            "n_rules_bucket": "4-5",
        }

        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val
        assert any(
            features_bad.get(k) != v for k, v in quota.hard_constraints.items()
        )

    def test_simple_algorithms_d5_filters(self) -> None:
        quota = QUOTAS["simple_algorithms"][5]
        features_ok = {"preprocess_bucket": "both"}
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_stateful_d5_filters(self) -> None:
        quota = QUOTAS["stateful"][5]
        features_ok = {"transform_bucket": "pipeline5", "pred_kind": "composed"}
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_fsm_d4_filters_when_available(self) -> None:
        if not _fsm_suite_available():
            pytest.skip("fsm suite generation is not available")
        quota = QUOTAS["fsm"][4]
        features_ok = {
            "machine_type": "mealy",
            "output_mode": "transition_count",
            "undefined_policy": "error",
            "transition_density_bucket": "high",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_fsm_d5_filters_when_available(self) -> None:
        if not _fsm_suite_available():
            pytest.skip("fsm suite generation is not available")
        quota = QUOTAS["fsm"][5]
        features_ok = {
            "machine_type": "mealy",
            "output_mode": "transition_count",
            "undefined_policy": "error",
            "transition_density_bucket": "very_high",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_bitops_d4_filters_when_available(self) -> None:
        if not _bitops_suite_available():
            pytest.skip("bitops suite generation is not available")
        quota = QUOTAS["bitops"][4]
        features_ok = {
            "op_complexity": "aggregate",
            "n_ops_bucket": "4-5",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_bitops_d5_filters_when_available(self) -> None:
        if not _bitops_suite_available():
            pytest.skip("bitops suite generation is not available")
        quota = QUOTAS["bitops"][5]
        features_ok = {
            "op_complexity": "aggregate",
            "n_ops_bucket": "6+",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_sequence_dp_d4_filters_when_available(self) -> None:
        if not _sequence_dp_suite_available():
            pytest.skip("sequence_dp suite generation is not available")
        quota = QUOTAS["sequence_dp"][4]
        features_ok = {
            "template": "local",
            "predicate_kind": "mod_eq",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_sequence_dp_d5_filters_when_available(self) -> None:
        if not _sequence_dp_suite_available():
            pytest.skip("sequence_dp suite generation is not available")
        quota = QUOTAS["sequence_dp"][5]
        features_ok = {
            "template": "local",
            "output_mode": "gap_count",
            "predicate_kind": "mod_eq",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_graph_queries_d4_filters_when_available(self) -> None:
        if not _graph_queries_suite_available():
            pytest.skip("graph_queries suite generation is not available")
        quota = QUOTAS["graph_queries"][4]
        features_ok = {
            "mode": "directed_weighted",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_graph_queries_d5_filters_when_available(self) -> None:
        if not _graph_queries_suite_available():
            pytest.skip("graph_queries suite generation is not available")
        quota = QUOTAS["graph_queries"][5]
        features_ok = {
            "query_type": "shortest_path_cost",
            "mode": "directed_weighted",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_temporal_logic_d4_filters_when_available(self) -> None:
        if not _temporal_logic_suite_available():
            pytest.skip("temporal_logic suite generation is not available")
        quota = QUOTAS["temporal_logic"][4]
        features_ok = {
            "output_mode": "first_sat_index",
            "depth_bucket": "4",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val

    def test_temporal_logic_d2_uses_depth_bucket_quota_axis(self) -> None:
        quota = QUOTAS["temporal_logic"][2]
        assert quota.hard_constraints["depth_bucket"] == "2"
        assert quota.buckets == [Bucket("depth_bucket", "2", 50)]

    def test_temporal_logic_d5_filters_when_available(self) -> None:
        if not _temporal_logic_suite_available():
            pytest.skip("temporal_logic suite generation is not available")
        quota = QUOTAS["temporal_logic"][5]
        features_ok = {
            "output_mode": "first_sat_index",
            "depth_bucket": "5+",
        }
        for key, val in quota.hard_constraints.items():
            assert features_ok.get(key) == val


# ── Greedy selection tests ───────────────────────────────────────────────


class TestGreedySelect:
    def _make_candidate(
        self, task_id: str, features: dict[str, str]
    ) -> Candidate:
        return Candidate(
            spec=None,
            spec_dict={},
            task_id=task_id,
            features=features,
        )

    def _reference_greedy_select(
        self,
        candidates: list[Candidate],
        quota: QuotaSpec,
        rng: random.Random,
    ) -> list[Candidate]:
        """Reference implementation matching pre-refactor behavior."""
        filtered = []
        for cand in candidates:
            match = True
            for key, val in quota.hard_constraints.items():
                if cand.features.get(key) != val:
                    match = False
                    break
            if match:
                filtered.append(cand)

        rng.shuffle(filtered)

        selected: list[Candidate] = []
        filled: dict[int, int] = {i: 0 for i in range(len(quota.buckets))}
        used_ids: set[str] = set()

        for _ in range(quota.total):
            deficits_remaining = any(
                filled[bi] < bucket.target
                for bi, bucket in enumerate(quota.buckets)
            )
            best_cand = None
            best_score = -1.0

            for cand in filtered:
                if cand.task_id in used_ids:
                    continue

                score = 0.0
                for bi, bucket in enumerate(quota.buckets):
                    deficit = max(0, bucket.target - filled[bi])
                    if (
                        deficit > 0
                        and cand.features.get(bucket.axis) == bucket.value
                    ):
                        if bucket.condition is not None:
                            cond_match = True
                            for key, val in bucket.condition.items():
                                if cand.features.get(key) != val:
                                    cond_match = False
                                    break
                            if not cond_match:
                                continue
                        score += deficit / bucket.target

                if score > best_score:
                    best_score = score
                    best_cand = cand

            if best_cand is None:
                break
            if deficits_remaining and best_score <= 0.0:
                break

            selected.append(best_cand)
            used_ids.add(best_cand.task_id)
            for bi, bucket in enumerate(quota.buckets):
                if best_cand.features.get(bucket.axis) == bucket.value:
                    if bucket.condition is not None and any(
                        best_cand.features.get(k) != v
                        for k, v in bucket.condition.items()
                    ):
                        continue
                    filled[bi] += 1

        return selected

    def test_simple_selection(self) -> None:
        """Small synthetic pool, verify greedy fills buckets."""
        quota = QuotaSpec(
            hard_constraints={},
            buckets=[
                Bucket("color", "red", 3),
                Bucket("color", "blue", 2),
            ],
            total=5,
        )

        candidates = []
        for i in range(10):
            color = "red" if i % 3 == 0 else "blue"
            candidates.append(self._make_candidate(f"id_{i}", {"color": color}))

        rng = random.Random(42)
        selected = greedy_select(candidates, quota, rng)
        assert len(selected) == 5

        red_count = sum(1 for c in selected if c.features["color"] == "red")
        blue_count = sum(1 for c in selected if c.features["color"] == "blue")
        assert red_count >= 3
        assert blue_count >= 2

    def test_hard_constraints_filter(self) -> None:
        """Hard constraints filter out non-matching candidates."""
        quota = QuotaSpec(
            hard_constraints={"shape": "circle"},
            buckets=[Bucket("color", "red", 2)],
            total=3,
        )

        candidates = [
            self._make_candidate("id_0", {"shape": "circle", "color": "red"}),
            self._make_candidate("id_1", {"shape": "square", "color": "red"}),
            self._make_candidate("id_2", {"shape": "circle", "color": "blue"}),
            self._make_candidate("id_3", {"shape": "circle", "color": "red"}),
        ]

        rng = random.Random(42)
        selected = greedy_select(candidates, quota, rng)
        # Only circles should be selected
        assert all(c.features["shape"] == "circle" for c in selected)
        assert len(selected) == 3

    def test_conditional_buckets(self) -> None:
        """Conditional buckets only count candidates matching conditions."""
        quota = QuotaSpec(
            hard_constraints={},
            buckets=[
                Bucket("shape", "circle", 2),
                Bucket("shape", "square", 2),
                Bucket("color", "red", 1, condition={"shape": "circle"}),
                Bucket("color", "blue", 1, condition={"shape": "circle"}),
            ],
            total=4,
        )

        candidates = [
            self._make_candidate("id_0", {"shape": "circle", "color": "red"}),
            self._make_candidate("id_1", {"shape": "circle", "color": "blue"}),
            self._make_candidate("id_2", {"shape": "circle", "color": "red"}),
            self._make_candidate("id_3", {"shape": "square", "color": "red"}),
            self._make_candidate("id_4", {"shape": "square", "color": "blue"}),
        ]

        rng = random.Random(42)
        selected = greedy_select(candidates, quota, rng)
        assert len(selected) == 4

        circles = [c for c in selected if c.features["shape"] == "circle"]
        squares = [c for c in selected if c.features["shape"] == "square"]
        assert len(circles) >= 2
        assert len(squares) >= 2

    def test_stops_before_zero_score_pick_when_deficits_remain(self) -> None:
        quota = QuotaSpec(
            hard_constraints={},
            buckets=[Bucket("color", "red", 2), Bucket("color", "blue", 1)],
            total=3,
        )
        candidates = [
            self._make_candidate("id_0", {"color": "red"}),
            self._make_candidate("id_1", {"color": "red"}),
            self._make_candidate("id_2", {"color": "green"}),
            self._make_candidate("id_3", {"color": "green"}),
        ]

        selected = greedy_select(candidates, quota, random.Random(42))
        assert len(selected) == 2
        assert all(c.features["color"] == "red" for c in selected)

    def test_matches_reference_behavior_across_seeds(self) -> None:
        quota = QuotaSpec(
            hard_constraints={"material": "metal"},
            buckets=[
                Bucket("shape", "circle", 4),
                Bucket("shape", "square", 3),
                Bucket("color", "red", 2, condition={"shape": "circle"}),
                Bucket("size", "large", 2, condition={"shape": "square"}),
                Bucket("color", "blue", 3),
            ],
            total=10,
        )
        candidates = [
            self._make_candidate(
                f"id_{i}",
                {
                    "shape": ["circle", "square", "triangle"][i % 3],
                    "color": ["red", "blue", "green"][(i // 2) % 3],
                    "size": "large" if i % 4 in (0, 1) else "small",
                    "material": "metal" if i % 5 != 0 else "wood",
                },
            )
            for i in range(40)
        ]

        for seed in range(12):
            actual = greedy_select(candidates, quota, random.Random(seed))
            expected = self._reference_greedy_select(
                candidates, quota, random.Random(seed)
            )
            assert [c.task_id for c in actual] == [c.task_id for c in expected]


# ── Pool generation smoke test ───────────────────────────────────────────


class TestPoolGeneration:
    @pytest.mark.parametrize(
        "family,difficulty",
        [
            ("stringrules", 3),
            ("stringrules", 4),
            ("stringrules", 5),
            ("stateful", 3),
            ("stateful", 4),
            ("stateful", 5),
            ("simple_algorithms", 3),
            ("simple_algorithms", 4),
            ("simple_algorithms", 5),
        ],
    )
    def test_pool_generates_candidates(
        self, family: str, difficulty: int
    ) -> None:
        """Pool produces candidates at correct difficulty."""
        from genfxn.core.difficulty import compute_difficulty

        candidates, stats = generate_pool(
            family, difficulty, seed=42, pool_size=200
        )
        assert len(candidates) > 0, f"No candidates for {family} D{difficulty}"
        assert stats.candidates == len(candidates)
        assert stats.total_sampled == 200
        # All should have the right difficulty
        for cand in candidates:
            assert compute_difficulty(family, cand.spec_dict) == difficulty

    def test_stack_bytecode_pool_generates_candidates_when_available(
        self,
    ) -> None:
        if not _stack_suite_available():
            pytest.skip("stack_bytecode suite generation is not available")

        from genfxn.core.difficulty import compute_difficulty

        for difficulty in sorted(QUOTAS["stack_bytecode"].keys()):
            candidates, stats = generate_pool(
                "stack_bytecode",
                difficulty,
                seed=42,
                pool_size=120,
            )
            assert len(candidates) > 0
            assert stats.candidates == len(candidates)
            for cand in candidates:
                assert (
                    compute_difficulty("stack_bytecode", cand.spec_dict)
                    == difficulty
                )

    def test_stack_bytecode_pool_features_cover_quota_axes_when_available(
        self,
    ) -> None:
        if not _stack_suite_available():
            pytest.skip("stack_bytecode suite generation is not available")

        for difficulty in sorted(QUOTAS["stack_bytecode"].keys()):
            candidates, _ = generate_pool(
                "stack_bytecode",
                difficulty,
                seed=43,
                pool_size=150,
            )
            assert candidates
            quota = QUOTAS["stack_bytecode"][difficulty]
            for bucket in quota.buckets:
                assert any(
                    cand.features.get(bucket.axis) == bucket.value
                    for cand in candidates
                ), (
                    "Missing bucket coverage for stack_bytecode "
                    f"D{difficulty}: "
                    f"{bucket.axis}={bucket.value}"
                )

    def test_fsm_pool_generates_candidates_when_available(
        self,
    ) -> None:
        if not _fsm_suite_available():
            pytest.skip("fsm suite generation is not available")

        from genfxn.core.difficulty import compute_difficulty

        for difficulty in sorted(QUOTAS["fsm"].keys()):
            candidates, stats = generate_pool(
                "fsm",
                difficulty,
                seed=42,
                pool_size=140,
            )
            assert len(candidates) > 0
            assert stats.candidates == len(candidates)
            for cand in candidates:
                assert compute_difficulty("fsm", cand.spec_dict) == difficulty

    def test_fsm_pool_features_cover_quota_axes_when_available(
        self,
    ) -> None:
        if not _fsm_suite_available():
            pytest.skip("fsm suite generation is not available")

        for difficulty in sorted(QUOTAS["fsm"].keys()):
            candidates, _ = generate_pool(
                "fsm",
                difficulty,
                seed=43,
                pool_size=180,
            )
            assert candidates
            quota = QUOTAS["fsm"][difficulty]
            for bucket in quota.buckets:
                assert any(
                    cand.features.get(bucket.axis) == bucket.value
                    for cand in candidates
                ), (
                    "Missing bucket coverage for fsm "
                    f"D{difficulty}: "
                    f"{bucket.axis}={bucket.value}"
                )

    def test_bitops_pool_generates_candidates_when_available(
        self,
    ) -> None:
        if not _bitops_suite_available():
            pytest.skip("bitops suite generation is not available")

        from genfxn.core.difficulty import compute_difficulty

        for difficulty in sorted(QUOTAS["bitops"].keys()):
            candidates, stats = generate_pool(
                "bitops",
                difficulty,
                seed=42,
                pool_size=140,
            )
            assert len(candidates) > 0
            assert stats.candidates == len(candidates)
            for cand in candidates:
                assert (
                    compute_difficulty("bitops", cand.spec_dict) == difficulty
                )

    def test_bitops_pool_features_cover_quota_axes_when_available(
        self,
    ) -> None:
        if not _bitops_suite_available():
            pytest.skip("bitops suite generation is not available")

        for difficulty in sorted(QUOTAS["bitops"].keys()):
            candidates, _ = generate_pool(
                "bitops",
                difficulty,
                seed=43,
                pool_size=180,
            )
            assert candidates
            quota = QUOTAS["bitops"][difficulty]
            for bucket in quota.buckets:
                assert any(
                    cand.features.get(bucket.axis) == bucket.value
                    for cand in candidates
                ), (
                    "Missing bucket coverage for bitops "
                    f"D{difficulty}: "
                    f"{bucket.axis}={bucket.value}"
                )

    def test_sequence_dp_pool_generates_candidates_when_available(
        self,
    ) -> None:
        if not _sequence_dp_suite_available():
            pytest.skip("sequence_dp suite generation is not available")

        from genfxn.core.difficulty import compute_difficulty

        for difficulty in sorted(QUOTAS["sequence_dp"].keys()):
            candidates, stats = generate_pool(
                "sequence_dp",
                difficulty,
                seed=42,
                pool_size=220,
            )
            assert len(candidates) > 0
            assert stats.candidates == len(candidates)
            for cand in candidates:
                assert (
                    compute_difficulty("sequence_dp", cand.spec_dict)
                    == difficulty
                )

    def test_sequence_dp_pool_features_cover_quota_axes_when_available(
        self,
    ) -> None:
        if not _sequence_dp_suite_available():
            pytest.skip("sequence_dp suite generation is not available")

        for difficulty in sorted(QUOTAS["sequence_dp"].keys()):
            candidates, _ = generate_pool(
                "sequence_dp",
                difficulty,
                seed=43,
                pool_size=260,
            )
            assert candidates
            quota = QUOTAS["sequence_dp"][difficulty]
            for bucket in quota.buckets:
                assert any(
                    cand.features.get(bucket.axis) == bucket.value
                    for cand in candidates
                ), (
                    "Missing bucket coverage for sequence_dp "
                    f"D{difficulty}: "
                    f"{bucket.axis}={bucket.value}"
                )

    def test_intervals_pool_generates_candidates_when_available(
        self,
    ) -> None:
        if not _intervals_suite_available():
            pytest.skip("intervals suite generation is not available")

        from genfxn.core.difficulty import compute_difficulty

        for difficulty in sorted(QUOTAS["intervals"].keys()):
            candidates, stats = generate_pool(
                "intervals",
                difficulty,
                seed=42,
                pool_size=120,
            )
            assert len(candidates) > 0
            assert stats.candidates == len(candidates)
            for cand in candidates:
                assert (
                    compute_difficulty("intervals", cand.spec_dict)
                    == difficulty
                )

    def test_intervals_pool_features_cover_quota_axes_when_available(
        self,
    ) -> None:
        if not _intervals_suite_available():
            pytest.skip("intervals suite generation is not available")

        for difficulty in sorted(QUOTAS["intervals"].keys()):
            candidates, _ = generate_pool(
                "intervals",
                difficulty,
                seed=43,
                pool_size=120,
            )
            assert candidates
            quota = QUOTAS["intervals"][difficulty]
            for bucket in quota.buckets:
                assert any(
                    cand.features.get(bucket.axis) == bucket.value
                    for cand in candidates
                ), (
                    "Missing bucket coverage for intervals "
                    f"D{difficulty}: "
                    f"{bucket.axis}={bucket.value}"
                )

    def test_graph_queries_pool_generates_candidates_when_available(
        self,
    ) -> None:
        if not _graph_queries_suite_available():
            pytest.skip("graph_queries suite generation is not available")

        from genfxn.core.difficulty import compute_difficulty

        for difficulty in sorted(QUOTAS["graph_queries"].keys()):
            candidates, stats = generate_pool(
                "graph_queries",
                difficulty,
                seed=42,
                pool_size=220,
            )
            assert len(candidates) > 0
            assert stats.candidates == len(candidates)
            for cand in candidates:
                assert (
                    compute_difficulty("graph_queries", cand.spec_dict)
                    == difficulty
                )

    def test_graph_queries_pool_features_cover_quota_axes_when_available(
        self,
    ) -> None:
        if not _graph_queries_suite_available():
            pytest.skip("graph_queries suite generation is not available")

        for difficulty in sorted(QUOTAS["graph_queries"].keys()):
            candidates, _ = generate_pool(
                "graph_queries",
                difficulty,
                seed=43,
                pool_size=260,
            )
            assert candidates
            quota = QUOTAS["graph_queries"][difficulty]
            for bucket in quota.buckets:
                assert any(
                    cand.features.get(bucket.axis) == bucket.value
                    for cand in candidates
                ), (
                    "Missing bucket coverage for graph_queries "
                    f"D{difficulty}: "
                    f"{bucket.axis}={bucket.value}"
                )

    def test_temporal_logic_pool_generates_candidates_when_available(
        self,
    ) -> None:
        if not _temporal_logic_suite_available():
            pytest.skip("temporal_logic suite generation is not available")

        from genfxn.core.difficulty import compute_difficulty

        for difficulty in sorted(QUOTAS["temporal_logic"].keys()):
            candidates, stats = generate_pool(
                "temporal_logic",
                difficulty,
                seed=42,
                pool_size=260,
            )
            assert len(candidates) > 0
            assert stats.candidates == len(candidates)
            for cand in candidates:
                assert (
                    compute_difficulty("temporal_logic", cand.spec_dict)
                    == difficulty
                )

    def test_temporal_logic_pool_features_cover_quota_axes_when_available(
        self,
    ) -> None:
        if not _temporal_logic_suite_available():
            pytest.skip("temporal_logic suite generation is not available")

        for difficulty in sorted(QUOTAS["temporal_logic"].keys()):
            candidates, _ = generate_pool(
                "temporal_logic",
                difficulty,
                seed=43,
                pool_size=320,
            )
            assert candidates
            quota = QUOTAS["temporal_logic"][difficulty]
            for bucket in quota.buckets:
                assert any(
                    cand.features.get(bucket.axis) == bucket.value
                    for cand in candidates
                ), (
                    "Missing bucket coverage for temporal_logic "
                    f"D{difficulty}: "
                    f"{bucket.axis}={bucket.value}"
                )

    def test_pool_raises_after_too_many_sampling_failures(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        def always_fail(
            _family: str,
            _axes: object,
            _rng: random.Random,
            trace: object = None,
        ) -> object:
            raise ValueError("forced sampler failure")

        monkeypatch.setattr(suite_generate, "_sample_spec", always_fail)

        with pytest.raises(RuntimeError, match="Sampling failed"):
            generate_pool("stateful", 3, seed=42, pool_size=50)

    def test_pool_raises_on_small_pool_when_all_samples_fail(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        def always_fail(
            _family: str,
            _axes: object,
            _rng: random.Random,
            trace: object = None,
        ) -> object:
            raise ValueError("forced sampler failure")

        monkeypatch.setattr(suite_generate, "_sample_spec", always_fail)

        with pytest.raises(RuntimeError, match="Sampling failed"):
            generate_pool("stateful", 3, seed=42, pool_size=1)


# ── Determinism test ─────────────────────────────────────────────────────


class TestDeterminism:
    def test_generate_suite_deterministic(self) -> None:
        """Same seed produces identical task_ids and queries across calls."""
        from genfxn.suites.generate import generate_suite

        a = generate_suite("stringrules", 3, seed=7, pool_size=3000)
        b = generate_suite("stringrules", 3, seed=7, pool_size=3000)

        assert len(a) == len(b) > 0
        for ta, tb in zip(a, b):
            assert ta.task_id == tb.task_id
            assert ta.queries == tb.queries

    def test_generate_suite_raises_when_quota_unfilled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        monkeypatch.setattr(
            suite_generate, "generate_pool", lambda *_: ([], PoolStats())
        )

        with pytest.raises(RuntimeError, match="Could not fill suite"):
            suite_generate.generate_suite(
                "stringrules", 3, seed=7, pool_size=20, max_retries=1
            )

    def test_generate_suite_tries_pool_variants_when_first_pool_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        quota = QUOTAS["stringrules"][3]
        calls = 0
        fake_selected = [
            Candidate(spec=None, spec_dict={}, task_id=f"id_{i}", features={})
            for i in range(quota.total)
        ]

        def fake_generate_pool(*_args, **_kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                return [], PoolStats()
            return (
                fake_selected,
                PoolStats(candidates=len(fake_selected)),
            )

        monkeypatch.setattr(suite_generate, "generate_pool", fake_generate_pool)
        monkeypatch.setattr(
            suite_generate,
            "_bucket_supply_shortfall",
            lambda candidates, _quota: len(candidates) == 0,
        )
        monkeypatch.setattr(
            suite_generate,
            "_select_best_with_restarts",
            lambda candidates, *_args, **_kwargs: candidates[: quota.total],
        )
        monkeypatch.setattr(
            suite_generate,
            "_selection_satisfies_quota",
            lambda selected, _quota: len(selected) >= quota.total,
        )
        monkeypatch.setattr(
            suite_generate,
            "_generate_task_from_candidate",
            lambda *_args, **_kwargs: object(),
        )

        tasks = suite_generate.generate_suite(
            "stringrules", 3, seed=7, pool_size=20, max_retries=0
        )

        assert len(tasks) == quota.total
        assert calls == 2

    def test_generate_suite_raises_when_targets_not_met(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        quota = QUOTAS["stringrules"][3]
        fake_selected = [
            Candidate(spec=None, spec_dict={}, task_id=f"id_{i}", features={})
            for i in range(quota.total)
        ]
        monkeypatch.setattr(
            suite_generate,
            "generate_pool",
            lambda *_: (
                fake_selected,
                PoolStats(candidates=len(fake_selected)),
            ),
        )
        monkeypatch.setattr(
            suite_generate,
            "greedy_select",
            lambda *_: list(fake_selected),
        )

        with pytest.raises(RuntimeError, match="targets_met=False"):
            suite_generate.generate_suite(
                "stringrules", 3, seed=7, pool_size=20, max_retries=0
            )

    def test_generate_suite_retries_with_distinct_selection_rng(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        draws: list[float] = []
        monkeypatch.setattr(
            suite_generate,
            "generate_pool",
            lambda *_: ([], PoolStats()),
        )

        def _capture_rng_draw(
            _candidates: list[Candidate],
            _quota: QuotaSpec,
            rng: random.Random,
        ) -> list[Candidate]:
            draws.append(rng.random())
            return []

        monkeypatch.setattr(suite_generate, "greedy_select", _capture_rng_draw)

        with pytest.raises(RuntimeError, match="Could not fill suite"):
            suite_generate.generate_suite(
                "stringrules",
                3,
                seed=7,
                pool_size=20,
                max_retries=2,
            )

        # 3 attempts (max_retries=2) × 3 restarts per attempt.
        assert len(draws) == 9
        assert len(set(draws)) == 9

    def test_generate_suite_retries_with_distinct_pool_seed(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import genfxn.suites.generate as suite_generate

        pool_seeds: list[int] = []

        def _capture_pool_seed(
            _family: str,
            _difficulty: int,
            pool_seed: int,
            _pool_size: int,
        ) -> tuple[list[Candidate], PoolStats]:
            pool_seeds.append(pool_seed)
            return [], PoolStats()

        monkeypatch.setattr(suite_generate, "generate_pool", _capture_pool_seed)
        monkeypatch.setattr(
            suite_generate,
            "_bucket_supply_shortfall",
            lambda *_args, **_kwargs: False,
        )
        monkeypatch.setattr(
            suite_generate,
            "greedy_select",
            lambda *_: [],
        )

        with pytest.raises(RuntimeError, match="Could not fill suite"):
            suite_generate.generate_suite(
                "stringrules",
                3,
                seed=7,
                pool_size=20,
                max_retries=2,
            )

        assert len(pool_seeds) == 3
        assert len(set(pool_seeds)) == 3

    def test_stack_bytecode_generate_suite_deterministic_when_available(
        self,
    ) -> None:
        if not _stack_suite_available():
            pytest.skip("stack_bytecode suite generation is not available")
        difficulty = sorted(QUOTAS["stack_bytecode"].keys())[0]
        a = generate_suite("stack_bytecode", difficulty, seed=19, pool_size=250)
        b = generate_suite("stack_bytecode", difficulty, seed=19, pool_size=250)
        assert [t.task_id for t in a] == [t.task_id for t in b]

    def test_stack_bytecode_suite_renderer_and_queries_when_available(
        self,
    ) -> None:
        if not _stack_suite_available():
            pytest.skip("stack_bytecode suite generation is not available")
        from genfxn.stack_bytecode.eval import eval_stack_bytecode
        from genfxn.stack_bytecode.models import StackBytecodeSpec

        difficulty = sorted(QUOTAS["stack_bytecode"].keys())[0]
        tasks = generate_suite(
            "stack_bytecode",
            difficulty,
            seed=42,
            pool_size=250,
        )
        assert tasks
        task = tasks[0]
        spec = StackBytecodeSpec.model_validate(task.spec)

        code = cast(str, task.code)
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        f_obj = namespace["f"]
        assert callable(f_obj)
        f = cast(StackBytecodeRenderFn, f_obj)
        out = f([1, 2, 3])
        assert isinstance(out, tuple)
        assert len(out) == 2

        for q in task.queries:
            assert isinstance(q.output, tuple)
            assert len(q.output) == 2
            assert q.output == eval_stack_bytecode(spec, list(q.input))

    def test_fsm_generate_suite_deterministic_when_available(
        self,
    ) -> None:
        if not _fsm_suite_available():
            pytest.skip("fsm suite generation is not available")
        difficulty = sorted(QUOTAS["fsm"].keys())[0]
        a = generate_suite("fsm", difficulty, seed=19, pool_size=260)
        b = generate_suite("fsm", difficulty, seed=19, pool_size=260)
        assert [t.task_id for t in a] == [t.task_id for t in b]

    def test_fsm_suite_renderer_and_queries_when_available(
        self,
    ) -> None:
        if not _fsm_suite_available():
            pytest.skip("fsm suite generation is not available")
        from genfxn.fsm.eval import eval_fsm
        from genfxn.fsm.models import FsmSpec

        difficulty = sorted(QUOTAS["fsm"].keys())[0]
        tasks = generate_suite(
            "fsm",
            difficulty,
            seed=42,
            pool_size=260,
        )
        assert tasks
        task = tasks[0]
        spec = FsmSpec.model_validate(task.spec)

        code = cast(str, task.code)
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        f_obj = namespace["f"]
        assert callable(f_obj)
        f = cast(FsmRenderFn, f_obj)
        out = f([1, 2, 3])
        assert isinstance(out, int)

        for q in task.queries:
            assert isinstance(q.output, int)
            assert q.output == eval_fsm(spec, list(q.input))

    def test_bitops_generate_suite_deterministic_when_available(
        self,
    ) -> None:
        if not _bitops_suite_available():
            pytest.skip("bitops suite generation is not available")
        difficulty = sorted(QUOTAS["bitops"].keys())[0]
        a = generate_suite("bitops", difficulty, seed=19, pool_size=260)
        b = generate_suite("bitops", difficulty, seed=19, pool_size=260)
        assert [t.task_id for t in a] == [t.task_id for t in b]

    def test_bitops_suite_renderer_and_queries_when_available(
        self,
    ) -> None:
        if not _bitops_suite_available():
            pytest.skip("bitops suite generation is not available")
        from genfxn.bitops.eval import eval_bitops
        from genfxn.bitops.models import BitopsSpec

        difficulty = sorted(QUOTAS["bitops"].keys())[0]
        tasks = generate_suite(
            "bitops",
            difficulty,
            seed=42,
            pool_size=260,
        )
        assert tasks
        task = tasks[0]
        spec = BitopsSpec.model_validate(task.spec)

        code = cast(str, task.code)
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        f_obj = namespace["f"]
        assert callable(f_obj)
        f = cast(BitopsRenderFn, f_obj)
        out = f(123)
        assert isinstance(out, int)

        for q in task.queries:
            assert isinstance(q.output, int)
            assert q.output == eval_bitops(spec, cast(int, q.input))

    def test_sequence_dp_generate_suite_deterministic_when_available(
        self,
    ) -> None:
        if not _sequence_dp_suite_available():
            pytest.skip("sequence_dp suite generation is not available")
        difficulty = sorted(QUOTAS["sequence_dp"].keys())[0]
        a = generate_suite("sequence_dp", difficulty, seed=19, pool_size=320)
        b = generate_suite("sequence_dp", difficulty, seed=19, pool_size=320)
        assert [t.task_id for t in a] == [t.task_id for t in b]

    def test_sequence_dp_suite_renderer_and_queries_when_available(
        self,
    ) -> None:
        if not _sequence_dp_suite_available():
            pytest.skip("sequence_dp suite generation is not available")
        from genfxn.sequence_dp.eval import eval_sequence_dp
        from genfxn.sequence_dp.models import SequenceDpSpec

        difficulty = sorted(QUOTAS["sequence_dp"].keys())[0]
        tasks = generate_suite(
            "sequence_dp",
            difficulty,
            seed=42,
            pool_size=320,
        )
        assert tasks
        task = tasks[0]
        spec = SequenceDpSpec.model_validate(task.spec)

        code = cast(str, task.code)
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        f_obj = namespace["f"]
        assert callable(f_obj)
        f = cast(SequenceDpRenderFn, f_obj)
        out = f([1, 2], [1, 2])
        assert isinstance(out, int)

        for q in task.queries:
            q_input = cast(dict[str, list[int]], q.input)
            assert isinstance(q.output, int)
            assert q.output == eval_sequence_dp(
                spec, q_input["a"], q_input["b"]
            )

    def test_intervals_generate_suite_deterministic_when_available(
        self,
    ) -> None:
        if not _intervals_suite_available():
            pytest.skip("intervals suite generation is not available")
        difficulty = sorted(QUOTAS["intervals"].keys())[0]
        a = generate_suite("intervals", difficulty, seed=19, pool_size=300)
        b = generate_suite("intervals", difficulty, seed=19, pool_size=300)
        assert [t.task_id for t in a] == [t.task_id for t in b]

    def test_intervals_suite_renderer_and_queries_when_available(
        self,
    ) -> None:
        if not _intervals_suite_available():
            pytest.skip("intervals suite generation is not available")
        from genfxn.intervals.eval import eval_intervals
        from genfxn.intervals.models import IntervalsSpec

        difficulty = sorted(QUOTAS["intervals"].keys())[0]
        tasks = generate_suite(
            "intervals",
            difficulty,
            seed=42,
            pool_size=300,
        )
        assert tasks
        task = tasks[0]
        spec = IntervalsSpec.model_validate(task.spec)

        code = cast(str, task.code)
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        f_obj = namespace["f"]
        assert callable(f_obj)
        f = cast(IntervalsRenderFn, f_obj)

        for q in task.queries:
            assert isinstance(q.output, int)
            intervals_input = cast(list[tuple[int, int]], list(q.input))
            expected = eval_intervals(spec, intervals_input)
            result = f(intervals_input)
            assert q.output == expected
            assert result == expected

    def test_graph_queries_generate_suite_deterministic_when_available(
        self,
    ) -> None:
        if not _graph_queries_suite_available():
            pytest.skip("graph_queries suite generation is not available")
        difficulty = sorted(QUOTAS["graph_queries"].keys())[0]
        a = generate_suite("graph_queries", difficulty, seed=19, pool_size=320)
        b = generate_suite("graph_queries", difficulty, seed=19, pool_size=320)
        assert [t.task_id for t in a] == [t.task_id for t in b]

    def test_graph_queries_suite_renderer_and_queries_when_available(
        self,
    ) -> None:
        if not _graph_queries_suite_available():
            pytest.skip("graph_queries suite generation is not available")
        from genfxn.graph_queries.eval import eval_graph_queries
        from genfxn.graph_queries.models import GraphQueriesSpec

        difficulty = sorted(QUOTAS["graph_queries"].keys())[0]
        tasks = generate_suite(
            "graph_queries",
            difficulty,
            seed=42,
            pool_size=320,
        )
        assert tasks
        task = tasks[0]
        spec = GraphQueriesSpec.model_validate(task.spec)

        code = cast(str, task.code)
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        f_obj = namespace["f"]
        assert callable(f_obj)
        f = cast(GraphQueriesRenderFn, f_obj)

        for q in task.queries:
            q_input = cast(dict[str, int], q.input)
            src = q_input["src"]
            dst = q_input["dst"]
            expected = eval_graph_queries(spec, src, dst)
            result = f(src, dst)
            assert isinstance(q.output, int)
            assert q.output == expected
            assert result == expected

    def test_temporal_logic_generate_suite_deterministic_when_available(
        self,
    ) -> None:
        if not _temporal_logic_suite_available():
            pytest.skip("temporal_logic suite generation is not available")
        difficulty = sorted(QUOTAS["temporal_logic"].keys())[0]
        a = generate_suite("temporal_logic", difficulty, seed=19, pool_size=320)
        b = generate_suite("temporal_logic", difficulty, seed=19, pool_size=320)
        assert [t.task_id for t in a] == [t.task_id for t in b]

    def test_temporal_logic_suite_renderer_and_queries_when_available(
        self,
    ) -> None:
        if not _temporal_logic_suite_available():
            pytest.skip("temporal_logic suite generation is not available")
        from genfxn.temporal_logic.eval import eval_temporal_logic
        from genfxn.temporal_logic.models import TemporalLogicSpec

        difficulty = sorted(QUOTAS["temporal_logic"].keys())[0]
        tasks = generate_suite(
            "temporal_logic",
            difficulty,
            seed=42,
            pool_size=320,
        )
        assert tasks
        task = tasks[0]
        spec = TemporalLogicSpec.model_validate(task.spec)

        code = cast(str, task.code)
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        f_obj = namespace["f"]
        assert callable(f_obj)
        f = cast(TemporalLogicRenderFn, f_obj)

        for q in task.queries:
            xs = cast(list[int], list(q.input))
            expected = eval_temporal_logic(spec, xs)
            result = f(xs)
            assert isinstance(q.output, int)
            assert q.output == expected
            assert result == expected


class TestSuiteGenerationValidation:
    def test_generate_suite_rejects_non_positive_pool_size(self) -> None:
        with pytest.raises(ValueError, match="pool_size must be >= 1"):
            generate_suite("stringrules", 3, seed=7, pool_size=0)

    def test_generate_pool_rejects_non_positive_pool_size(self) -> None:
        with pytest.raises(ValueError, match="pool_size must be >= 1"):
            generate_pool("stringrules", 3, seed=7, pool_size=0)

    def test_generate_suite_rejects_negative_max_retries(self) -> None:
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            generate_suite("stringrules", 3, seed=7, max_retries=-1)

    @pytest.mark.parametrize(
        "call",
        [
            lambda: generate_pool("bad_family", 3, seed=42, pool_size=10),
            lambda: generate_suite("bad_family", 3, seed=42),
            lambda: quota_report([], "bad_family", 3),
        ],
    )
    def test_invalid_family_raises_value_error(
        self, call: Callable[[], object]
    ) -> None:
        with pytest.raises(
            ValueError,
            match=r"Invalid family 'bad_family'.*Valid options:",
        ):
            call()

    @pytest.mark.parametrize(
        "call",
        [
            lambda: generate_pool("stringrules", 999, seed=42, pool_size=10),
            lambda: generate_suite("stringrules", 999, seed=42),
            lambda: quota_report([], "stringrules", 999),
        ],
    )
    def test_invalid_difficulty_raises_value_error(
        self, call: Callable[[], object]
    ) -> None:
        with pytest.raises(
            ValueError,
            match=(
                r"Invalid difficulty '999' for family 'stringrules'.*"
                r"Valid options: 3, 4, 5"
            ),
        ):
            call()


# ── Integration test (marked slow) ──────────────────────────────────────


@pytest.mark.full
class TestIntegration:
    @pytest.mark.slow
    @pytest.mark.parametrize(
        "family,difficulty",
        [
            ("stringrules", 3),
            ("stateful", 3),
            ("simple_algorithms", 3),
        ],
    )
    def test_full_suite_generation(self, family: str, difficulty: int) -> None:
        """Full suite generation with quota checking."""
        from genfxn.suites.generate import generate_suite, quota_report

        tasks = generate_suite(family, difficulty, seed=42, pool_size=2000)
        assert len(tasks) == 50

        report = quota_report(tasks, family, difficulty)
        for axis, value, target, achieved, status in report:
            # Allow some slack (within 80% of target)
            min_acceptable = max(1, int(target * 0.8))
            assert achieved >= min_acceptable, (
                f"{family} D{difficulty}: {axis}={value} got {achieved}, "
                f"need >= {min_acceptable} (target={target})"
            )

    @pytest.mark.slow
    def test_stack_bytecode_suite_generation_when_available(self) -> None:
        if not _stack_suite_available():
            pytest.skip("stack_bytecode suite generation is not available")
        from genfxn.suites.generate import generate_suite, quota_report

        difficulty = sorted(QUOTAS["stack_bytecode"].keys())[0]
        tasks = generate_suite(
            "stack_bytecode",
            difficulty,
            seed=42,
            pool_size=2000,
        )
        quota = QUOTAS["stack_bytecode"][difficulty]
        assert len(tasks) == quota.total

        report = quota_report(tasks, "stack_bytecode", difficulty)
        for _, _, target, achieved, _ in report:
            min_acceptable = max(1, int(target * 0.8))
            assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_stack_bytecode_all_difficulties_quota_report_when_available(
        self,
    ) -> None:
        if not _stack_suite_available():
            pytest.skip("stack_bytecode suite generation is not available")

        for difficulty in sorted(QUOTAS["stack_bytecode"].keys()):
            tasks = generate_suite(
                "stack_bytecode",
                difficulty,
                seed=101 + difficulty,
                pool_size=1600,
            )
            quota = QUOTAS["stack_bytecode"][difficulty]
            assert len(tasks) == quota.total
            report = quota_report(tasks, "stack_bytecode", difficulty)
            for _, _, target, achieved, _ in report:
                min_acceptable = max(1, int(target * 0.75))
                assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_fsm_suite_generation_when_available(self) -> None:
        if not _fsm_suite_available():
            pytest.skip("fsm suite generation is not available")
        from genfxn.suites.generate import generate_suite, quota_report

        difficulty = sorted(QUOTAS["fsm"].keys())[0]
        tasks = generate_suite(
            "fsm",
            difficulty,
            seed=52,
            pool_size=2000,
        )
        quota = QUOTAS["fsm"][difficulty]
        assert len(tasks) == quota.total

        report = quota_report(tasks, "fsm", difficulty)
        for _, _, target, achieved, _ in report:
            min_acceptable = max(1, int(target * 0.8))
            assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_fsm_all_difficulties_quota_report_when_available(
        self,
    ) -> None:
        if not _fsm_suite_available():
            pytest.skip("fsm suite generation is not available")

        for difficulty in sorted(QUOTAS["fsm"].keys()):
            tasks = generate_suite(
                "fsm",
                difficulty,
                seed=201 + difficulty,
                pool_size=1800,
            )
            quota = QUOTAS["fsm"][difficulty]
            assert len(tasks) == quota.total
            report = quota_report(tasks, "fsm", difficulty)
            for _, _, target, achieved, _ in report:
                min_acceptable = max(1, int(target * 0.75))
                assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_bitops_suite_generation_when_available(self) -> None:
        if not _bitops_suite_available():
            pytest.skip("bitops suite generation is not available")
        from genfxn.suites.generate import generate_suite, quota_report

        difficulty = sorted(QUOTAS["bitops"].keys())[0]
        tasks = generate_suite(
            "bitops",
            difficulty,
            seed=62,
            pool_size=2000,
        )
        quota = QUOTAS["bitops"][difficulty]
        assert len(tasks) == quota.total

        report = quota_report(tasks, "bitops", difficulty)
        for _, _, target, achieved, _ in report:
            min_acceptable = max(1, int(target * 0.8))
            assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_bitops_all_difficulties_quota_report_when_available(
        self,
    ) -> None:
        if not _bitops_suite_available():
            pytest.skip("bitops suite generation is not available")

        for difficulty in sorted(QUOTAS["bitops"].keys()):
            tasks = generate_suite(
                "bitops",
                difficulty,
                seed=301 + difficulty,
                pool_size=1800,
            )
            quota = QUOTAS["bitops"][difficulty]
            assert len(tasks) == quota.total
            report = quota_report(tasks, "bitops", difficulty)
            for _, _, target, achieved, _ in report:
                min_acceptable = max(1, int(target * 0.75))
                assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_sequence_dp_suite_generation_when_available(self) -> None:
        if not _sequence_dp_suite_available():
            pytest.skip("sequence_dp suite generation is not available")
        from genfxn.suites.generate import generate_suite, quota_report

        difficulty = sorted(QUOTAS["sequence_dp"].keys())[0]
        tasks = generate_suite(
            "sequence_dp",
            difficulty,
            seed=72,
            pool_size=2200,
        )
        quota = QUOTAS["sequence_dp"][difficulty]
        assert len(tasks) == quota.total

        report = quota_report(tasks, "sequence_dp", difficulty)
        for _, _, target, achieved, _ in report:
            min_acceptable = max(1, int(target * 0.8))
            assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_sequence_dp_all_difficulties_quota_report_when_available(
        self,
    ) -> None:
        if not _sequence_dp_suite_available():
            pytest.skip("sequence_dp suite generation is not available")

        for difficulty in sorted(QUOTAS["sequence_dp"].keys()):
            tasks = generate_suite(
                "sequence_dp",
                difficulty,
                seed=401 + difficulty,
                pool_size=2000,
            )
            quota = QUOTAS["sequence_dp"][difficulty]
            assert len(tasks) == quota.total
            report = quota_report(tasks, "sequence_dp", difficulty)
            for _, _, target, achieved, _ in report:
                min_acceptable = max(1, int(target * 0.75))
                assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_intervals_suite_generation_when_available(self) -> None:
        if not _intervals_suite_available():
            pytest.skip("intervals suite generation is not available")
        from genfxn.suites.generate import generate_suite, quota_report

        difficulty = sorted(QUOTAS["intervals"].keys())[0]
        tasks = generate_suite(
            "intervals",
            difficulty,
            seed=82,
            pool_size=1200,
        )
        quota = QUOTAS["intervals"][difficulty]
        assert len(tasks) == quota.total

        report = quota_report(tasks, "intervals", difficulty)
        for _, _, target, achieved, _ in report:
            min_acceptable = max(1, int(target * 0.75))
            assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_intervals_all_difficulties_quota_report_when_available(
        self,
    ) -> None:
        if not _intervals_suite_available():
            pytest.skip("intervals suite generation is not available")

        for difficulty in sorted(QUOTAS["intervals"].keys()):
            tasks = generate_suite(
                "intervals",
                difficulty,
                seed=501 + difficulty,
                pool_size=1200,
            )
            quota = QUOTAS["intervals"][difficulty]
            assert len(tasks) == quota.total
            report = quota_report(tasks, "intervals", difficulty)
            for _, _, target, achieved, _ in report:
                min_acceptable = max(1, int(target * 0.75))
                assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_intervals_d2_local_optimum_recovery_when_available(
        self,
    ) -> None:
        if not _intervals_suite_available():
            pytest.skip("intervals suite generation is not available")
        if 2 not in QUOTAS["intervals"]:
            pytest.skip("intervals D2 suite generation is not available")
        import genfxn.suites.generate as suite_generate

        difficulty = 2
        seed = 231
        pool_size = 200
        quota = QUOTAS["intervals"][difficulty]

        # Baseline greedy restart-0 can miss quota targets on this pool.
        pool_seed = suite_generate._stable_seed(
            seed, "intervals", difficulty, 800000
        )
        candidates, _ = suite_generate.generate_pool(
            "intervals",
            difficulty,
            pool_seed,
            pool_size,
        )
        restart0_rng = random.Random(
            suite_generate._stable_seed(
                seed,
                "intervals",
                difficulty,
                900000,
            )
        )
        restart0_selected = suite_generate.greedy_select(
            candidates,
            quota,
            restart0_rng,
        )
        restart0_selected = suite_generate._repair_selection_with_swaps(
            restart0_selected,
            candidates,
            quota,
        )
        assert len(restart0_selected) == quota.total
        assert not suite_generate._quota_targets_met(
            restart0_selected,
            quota,
        )

        tasks_a = generate_suite(
            "intervals",
            difficulty,
            seed=seed,
            pool_size=pool_size,
            max_retries=0,
        )
        tasks_b = generate_suite(
            "intervals",
            difficulty,
            seed=seed,
            pool_size=pool_size,
            max_retries=0,
        )
        assert len(tasks_a) == quota.total
        assert [task.task_id for task in tasks_a] == [
            task.task_id for task in tasks_b
        ]

        report = quota_report(tasks_a, "intervals", difficulty)
        for _, _, target, achieved, _ in report:
            assert achieved >= target

    @pytest.mark.slow
    def test_graph_queries_suite_generation_when_available(self) -> None:
        if not _graph_queries_suite_available():
            pytest.skip("graph_queries suite generation is not available")
        from genfxn.suites.generate import generate_suite, quota_report

        difficulty = sorted(QUOTAS["graph_queries"].keys())[0]
        tasks = generate_suite(
            "graph_queries",
            difficulty,
            seed=92,
            pool_size=1400,
        )
        quota = QUOTAS["graph_queries"][difficulty]
        assert len(tasks) == quota.total

        report = quota_report(tasks, "graph_queries", difficulty)
        for _, _, target, achieved, _ in report:
            min_acceptable = max(1, int(target * 0.75))
            assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_graph_queries_all_difficulties_quota_report_when_available(
        self,
    ) -> None:
        if not _graph_queries_suite_available():
            pytest.skip("graph_queries suite generation is not available")

        for difficulty in sorted(QUOTAS["graph_queries"].keys()):
            tasks = generate_suite(
                "graph_queries",
                difficulty,
                seed=601 + difficulty,
                pool_size=1400,
            )
            quota = QUOTAS["graph_queries"][difficulty]
            assert len(tasks) == quota.total
            report = quota_report(tasks, "graph_queries", difficulty)
            for _, _, target, achieved, _ in report:
                min_acceptable = max(1, int(target * 0.75))
                assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_temporal_logic_suite_generation_when_available(self) -> None:
        if not _temporal_logic_suite_available():
            pytest.skip("temporal_logic suite generation is not available")
        from genfxn.suites.generate import generate_suite, quota_report

        difficulty = sorted(QUOTAS["temporal_logic"].keys())[0]
        tasks = generate_suite(
            "temporal_logic",
            difficulty,
            seed=102,
            pool_size=1400,
        )
        quota = QUOTAS["temporal_logic"][difficulty]
        assert len(tasks) == quota.total

        report = quota_report(tasks, "temporal_logic", difficulty)
        for _, _, target, achieved, _ in report:
            min_acceptable = max(1, int(target * 0.75))
            assert achieved >= min_acceptable

    @pytest.mark.slow
    def test_temporal_logic_all_difficulties_quota_report_when_available(
        self,
    ) -> None:
        if not _temporal_logic_suite_available():
            pytest.skip("temporal_logic suite generation is not available")

        for difficulty in sorted(QUOTAS["temporal_logic"].keys()):
            tasks = generate_suite(
                "temporal_logic",
                difficulty,
                seed=701 + difficulty,
                pool_size=1400,
            )
            quota = QUOTAS["temporal_logic"][difficulty]
            assert len(tasks) == quota.total
            report = quota_report(tasks, "temporal_logic", difficulty)
            for _, _, target, achieved, _ in report:
                min_acceptable = max(1, int(target * 0.75))
                assert achieved >= min_acceptable
