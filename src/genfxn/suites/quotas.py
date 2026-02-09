"""Quota table definitions for balanced suite generation."""

from dataclasses import dataclass


@dataclass
class Bucket:
    axis: str
    value: str
    target: int
    condition: dict[str, str] | None = None


@dataclass
class QuotaSpec:
    hard_constraints: dict[str, str]
    buckets: list[Bucket]
    total: int = 50


# ── Stringrules quotas ───────────────────────────────────────────────────

_STRINGRULES_D3 = QuotaSpec(
    hard_constraints={"has_comp": "false", "has_pipe": "false"},
    buckets=[
        # n_rules_bucket
        Bucket("n_rules_bucket", "4-5", 20),
        Bucket("n_rules_bucket", "6-7", 20),
        Bucket("n_rules_bucket", "8-10", 10),
        # pred_majority
        Bucket("pred_majority", "simple", 20),
        Bucket("pred_majority", "pattern", 20),
        Bucket("pred_majority", "length", 10),
        # transform_majority
        Bucket("transform_majority", "identity", 10),
        Bucket("transform_majority", "simple", 20),
        Bucket("transform_majority", "param", 20),
    ],
)

_STRINGRULES_D4 = QuotaSpec(
    hard_constraints={},  # XOR enforced via mode buckets summing to 50
    buckets=[
        # mode (comp XOR pipe)
        Bucket("mode", "comp-only", 25),
        Bucket("mode", "pipe-only", 25),
        # n_rules_bucket
        Bucket("n_rules_bucket", "4-5", 10),
        Bucket("n_rules_bucket", "6-7", 20),
        Bucket("n_rules_bucket", "8-10", 20),
        # comp_max_score within comp-only
        Bucket("comp_max_score", "4", 15, condition={"mode": "comp-only"}),
        Bucket("comp_max_score", "5", 10, condition={"mode": "comp-only"}),
        # pipe_max_score within pipe-only
        # With multiple pipelines per spec, max almost always reaches 5
        Bucket("pipe_max_score", "4", 4, condition={"mode": "pipe-only"}),
        Bucket("pipe_max_score", "5", 21, condition={"mode": "pipe-only"}),
    ],
)

_STRINGRULES_D5 = QuotaSpec(
    hard_constraints={"has_comp": "true", "has_pipe": "true"},
    buckets=[
        # n_rules_bucket
        Bucket("n_rules_bucket", "4-5", 10),
        Bucket("n_rules_bucket", "6-7", 20),
        Bucket("n_rules_bucket", "8-10", 20),
        # comp_max_score — NOT predicates give score 4; AND/OR give 4-5
        Bucket("comp_max_score", "4", 3),
        Bucket("comp_max_score", "5", 47),
        # pipe_max_score — with multiple pipelines, max almost always hits 5
        Bucket("pipe_max_score", "5", 50),
    ],
)

# ── Stateful quotas ──────────────────────────────────────────────────────

_STATEFUL_D3 = QuotaSpec(
    hard_constraints={},  # enforced via pool gen
    buckets=[
        # template
        Bucket("template", "conditional_linear_sum", 35),
        Bucket("template", "resetting_best_prefix_sum", 15),
        # pred_kind
        Bucket("pred_kind", "comparison", 25),
        Bucket("pred_kind", "mod_eq", 25),
        # conditional transform_signature
        Bucket(
            "transform_signature",
            "both_affine",
            15,
            condition={"template": "conditional_linear_sum"},
        ),
        Bucket(
            "transform_signature",
            "both_sign",
            10,
            condition={"template": "conditional_linear_sum"},
        ),
        Bucket(
            "transform_signature",
            "mixed",
            10,
            condition={"template": "conditional_linear_sum"},
        ),
    ],
)

_STATEFUL_D4 = QuotaSpec(
    hard_constraints={},
    buckets=[
        # template
        Bucket("template", "conditional_linear_sum", 25),
        Bucket("template", "resetting_best_prefix_sum", 15),
        Bucket("template", "toggle_sum", 10),
        # pred_kind — comparison needs pipeline5 for D4
        Bucket("pred_kind", "mod_eq", 25),
        Bucket("pred_kind", "composed", 16),
        Bucket("pred_kind", "comparison", 9),
        # transform_bucket
        Bucket("transform_bucket", "atomic_nonidentity", 23),
        Bucket("transform_bucket", "pipeline4", 18),
        Bucket("transform_bucket", "pipeline5", 9),
    ],
)

_STATEFUL_D5 = QuotaSpec(
    hard_constraints={"transform_bucket": "pipeline5", "pred_kind": "composed"},
    buckets=[
        # template
        Bucket("template", "toggle_sum", 25),
        Bucket("template", "resetting_best_prefix_sum", 25),
        # pred_kind — mod_eq can't reach D5 (max raw=4.3), so all composed
        Bucket("pred_kind", "composed", 50),
    ],
)

# ── Simple algorithms quotas ─────────────────────────────────────────────

_SIMPLE_ALGORITHMS_D3 = QuotaSpec(
    hard_constraints={"preprocess_bucket": "none"},
    buckets=[
        # template
        Bucket("template", "count_pairs_sum", 25),
        Bucket("template", "max_window_sum", 25),
        # within count_pairs_sum: target_sign
        # zero target has only 2 unique specs (2 counting modes), so cap at 2
        Bucket(
            "target_sign", "neg", 11, condition={"template": "count_pairs_sum"}
        ),
        Bucket(
            "target_sign", "zero", 2, condition={"template": "count_pairs_sum"}
        ),
        Bucket(
            "target_sign", "pos", 11, condition={"template": "count_pairs_sum"}
        ),
        # within max_window_sum: k_bucket
        Bucket("k_bucket", "6-7", 12, condition={"template": "max_window_sum"}),
        Bucket(
            "k_bucket", "8-10", 13, condition={"template": "max_window_sum"}
        ),
    ],
)

_SIMPLE_ALGORITHMS_D4 = QuotaSpec(
    hard_constraints={},  # preprocess present enforced via pool gen
    buckets=[
        # template — most_frequent needs 'both' preprocess for D4
        Bucket("template", "most_frequent", 14),
        Bucket("template", "count_pairs_sum", 21),
        Bucket("template", "max_window_sum", 15),
        # preprocess_bucket — most_frequent forces 'both', skewing distribution
        Bucket("preprocess_bucket", "filter_only", 13),
        Bucket("preprocess_bucket", "transform_only", 14),
        Bucket("preprocess_bucket", "both", 23),
        # filter_kind (within those with filter)
        Bucket(
            "filter_kind", "comparison", 10, condition={"has_filter": "true"}
        ),
        Bucket("filter_kind", "mod_eq", 15, condition={"has_filter": "true"}),
        Bucket("filter_kind", "composed", 11, condition={"has_filter": "true"}),
        # pre_transform_complexity (within those with transform)
        Bucket(
            "pre_transform_complexity",
            "atomic",
            11,
            condition={"has_transform": "true"},
        ),
        Bucket(
            "pre_transform_complexity",
            "pipeline4",
            26,
            condition={"has_transform": "true"},
        ),
        # edge_count
        Bucket("edge_count", "1", 40),
        Bucket("edge_count", "2", 10),
    ],
)

_SIMPLE_ALGORITHMS_D5 = QuotaSpec(
    hard_constraints={
        "preprocess_bucket": "both",
    },
    buckets=[
        # template — most_frequent can't reach D5 (max raw=4.1)
        Bucket("template", "count_pairs_sum", 30),
        Bucket("template", "max_window_sum", 20),
        # filter_kind
        Bucket("filter_kind", "mod_eq", 25),
        Bucket("filter_kind", "composed", 25),
        # pre_transform_complexity
        Bucket("pre_transform_complexity", "pipeline5", 50),
        # edge_count — max_window_sum can only have 1 edge (empty_default)
        Bucket(
            "edge_count", "2", 30, condition={"template": "count_pairs_sum"}
        ),
        Bucket("edge_count", "1", 20, condition={"template": "max_window_sum"}),
    ],
)

# ── Stack bytecode quotas ────────────────────────────────────────────────

_STACK_BYTECODE_D1 = QuotaSpec(
    hard_constraints={"control_flow": "linear", "op_complexity": "basic"},
    buckets=[Bucket("size_bucket", "1-3", 50)],
)

_STACK_BYTECODE_D2 = QuotaSpec(
    hard_constraints={"control_flow": "linear", "op_complexity": "arithmetic"},
    buckets=[Bucket("size_bucket", "4-5", 50)],
)

_STACK_BYTECODE_D3 = QuotaSpec(
    hard_constraints={"op_complexity": "stack_logic"},
    buckets=[Bucket("size_bucket", "6-7", 50)],
)

_STACK_BYTECODE_D4 = QuotaSpec(
    hard_constraints={
        "control_flow": "conditional",
        "op_complexity": "control",
    },
    buckets=[Bucket("size_bucket", "8-10", 50)],
)

_STACK_BYTECODE_D5 = QuotaSpec(
    hard_constraints={
        "control_flow": "looped_conditional",
        "op_complexity": "control",
    },
    buckets=[Bucket("size_bucket", "11+", 50)],
)

# ── FSM quotas ───────────────────────────────────────────────────────────

_FSM_D1 = QuotaSpec(
    hard_constraints={
        "machine_type": "moore",
        "output_mode": "final_state_id",
        "undefined_policy": "stay",
    },
    buckets=[Bucket("n_states_bucket", "2", 50)],
)

_FSM_D2 = QuotaSpec(
    hard_constraints={"machine_type": "moore"},
    buckets=[Bucket("n_states_bucket", "2-3", 50)],
)

_FSM_D3 = QuotaSpec(
    hard_constraints={},
    buckets=[Bucket("n_states_bucket", "3-4", 50)],
)

_FSM_D4 = QuotaSpec(
    hard_constraints={
        "machine_type": "mealy",
        "output_mode": "transition_count",
        "undefined_policy": "error",
        "transition_density_bucket": "high",
    },
    buckets=[Bucket("n_states_bucket", "4-5", 50)],
)

_FSM_D5 = QuotaSpec(
    hard_constraints={
        "machine_type": "mealy",
        "output_mode": "transition_count",
        "undefined_policy": "error",
        "transition_density_bucket": "very_high",
    },
    buckets=[Bucket("n_states_bucket", "5-6", 50)],
)

# ── Bitops quotas ───────────────────────────────────────────────────────

_BITOPS_D1 = QuotaSpec(
    hard_constraints={"width_bucket": "8", "op_complexity": "basic"},
    buckets=[Bucket("n_ops_bucket", "1-2", 50)],
)

_BITOPS_D2 = QuotaSpec(
    hard_constraints={"op_complexity": "shift"},
    buckets=[Bucket("n_ops_bucket", "2-3", 50)],
)

_BITOPS_D3 = QuotaSpec(
    hard_constraints={"op_complexity": "rotate"},
    buckets=[Bucket("n_ops_bucket", "3-4", 50)],
)

_BITOPS_D4 = QuotaSpec(
    hard_constraints={"op_complexity": "aggregate"},
    buckets=[Bucket("n_ops_bucket", "4-5", 50)],
)

_BITOPS_D5 = QuotaSpec(
    hard_constraints={"op_complexity": "aggregate"},
    buckets=[Bucket("n_ops_bucket", "6+", 50)],
)

# ── Sequence DP quotas ───────────────────────────────────────────────────

_SEQUENCE_DP_D1 = QuotaSpec(
    hard_constraints={
        "template": "global",
        "output_mode": "score",
        "predicate_kind": "eq",
        "tie_break_bucket": "diag_first",
        "score_profile": "wide",
    },
    buckets=[Bucket("score_profile", "wide", 50)],
)

_SEQUENCE_DP_D2 = QuotaSpec(
    hard_constraints={
        "template": "global",
        "output_mode": "alignment_len",
        "predicate_kind": "abs_diff_le",
        "score_profile": "wide",
    },
    buckets=[
        Bucket("abs_diff_bucket", "0-1", 34),
        Bucket("abs_diff_bucket", "2-3", 16),
        Bucket("tie_break_order", "diag_up_left", 25),
        Bucket("tie_break_order", "diag_left_up", 25),
    ],
)

_SEQUENCE_DP_D3 = QuotaSpec(
    hard_constraints={
        "template": "global",
        "output_mode": "alignment_len",
    },
    buckets=[
        Bucket("predicate_kind", "abs_diff_le", 20),
        Bucket("predicate_kind", "mod_eq", 30),
        Bucket("tie_break_order", "up_diag_left", 25),
        Bucket("tie_break_order", "left_diag_up", 25),
    ],
)

_SEQUENCE_DP_D4 = QuotaSpec(
    hard_constraints={
        "template": "local",
        "predicate_kind": "mod_eq",
    },
    buckets=[
        Bucket("output_mode", "alignment_len", 30),
        Bucket("output_mode", "gap_count", 20),
        Bucket("tie_break_order", "up_left_diag", 25),
        Bucket("tie_break_order", "left_up_diag", 25),
    ],
)

_SEQUENCE_DP_D5 = QuotaSpec(
    hard_constraints={
        "template": "local",
        "output_mode": "gap_count",
        "predicate_kind": "mod_eq",
    },
    buckets=[
        Bucket("score_profile", "tie_heavy", 35),
        Bucket("score_profile", "narrow", 15),
        Bucket("tie_break_order", "left_up_diag", 28),
        Bucket("tie_break_order", "up_left_diag", 22),
    ],
)

# ── Combined lookup ──────────────────────────────────────────────────────

QUOTAS: dict[str, dict[int, QuotaSpec]] = {
    "stringrules": {3: _STRINGRULES_D3, 4: _STRINGRULES_D4, 5: _STRINGRULES_D5},
    "stateful": {3: _STATEFUL_D3, 4: _STATEFUL_D4, 5: _STATEFUL_D5},
    "simple_algorithms": {
        3: _SIMPLE_ALGORITHMS_D3,
        4: _SIMPLE_ALGORITHMS_D4,
        5: _SIMPLE_ALGORITHMS_D5,
    },
    "stack_bytecode": {
        1: _STACK_BYTECODE_D1,
        2: _STACK_BYTECODE_D2,
        3: _STACK_BYTECODE_D3,
        4: _STACK_BYTECODE_D4,
        5: _STACK_BYTECODE_D5,
    },
    "fsm": {
        1: _FSM_D1,
        2: _FSM_D2,
        3: _FSM_D3,
        4: _FSM_D4,
        5: _FSM_D5,
    },
    "bitops": {
        1: _BITOPS_D1,
        2: _BITOPS_D2,
        3: _BITOPS_D3,
        4: _BITOPS_D4,
        5: _BITOPS_D5,
    },
    "sequence_dp": {
        1: _SEQUENCE_DP_D1,
        2: _SEQUENCE_DP_D2,
        3: _SEQUENCE_DP_D3,
        4: _SEQUENCE_DP_D4,
        5: _SEQUENCE_DP_D5,
    },
}
