import importlib.util

import pytest

from genfxn.core.difficulty import (
    _expr_type_score,
    _piecewise_difficulty,
    _predicate_score,
    _simple_algorithms_difficulty,
    _stateful_difficulty,
    _string_predicate_score,
    _string_transform_score,
    _stringrules_difficulty,
    _transform_score,
    compute_difficulty,
)


class TestExprTypeScore:
    def test_affine_lowest(self) -> None:
        assert _expr_type_score({"kind": "affine"}) == 1

    def test_abs_medium(self) -> None:
        assert _expr_type_score({"kind": "abs"}) == 2

    def test_mod_higher(self) -> None:
        assert _expr_type_score({"kind": "mod"}) == 3

    def test_quadratic_highest(self) -> None:
        assert _expr_type_score({"kind": "quadratic"}) == 4

    def test_unknown_defaults_to_one(self) -> None:
        assert _expr_type_score({"kind": "unknown"}) == 1


class TestPredicateScore:
    def test_even_odd_simplest(self) -> None:
        assert _predicate_score({"kind": "even"}) == 1
        assert _predicate_score({"kind": "odd"}) == 1

    def test_comparisons_medium(self) -> None:
        assert _predicate_score({"kind": "lt"}) == 2
        assert _predicate_score({"kind": "le"}) == 2
        assert _predicate_score({"kind": "gt"}) == 2
        assert _predicate_score({"kind": "ge"}) == 2

    def test_mod_eq_hardest(self) -> None:
        assert _predicate_score({"kind": "mod_eq"}) == 4

    def test_in_set_medium_high(self) -> None:
        assert _predicate_score({"kind": "in_set"}) == 3


class TestTransformScore:
    def test_identity_simplest(self) -> None:
        assert _transform_score({"kind": "identity"}) == 1

    def test_abs_negate_medium(self) -> None:
        assert _transform_score({"kind": "abs"}) == 2
        assert _transform_score({"kind": "negate"}) == 2

    def test_shift_scale_hardest(self) -> None:
        assert _transform_score({"kind": "shift"}) == 3
        assert _transform_score({"kind": "scale"}) == 3


class TestPiecewiseDifficulty:
    def test_single_branch_affine_simple(self) -> None:
        spec = {
            "branches": [],
            "default_expr": {"kind": "affine", "a": 1, "b": 0},
        }
        assert _piecewise_difficulty(spec) == 1

    def test_two_branches_affine(self) -> None:
        spec = {
            "branches": [
                {
                    "condition": {"kind": "lt", "value": 0},
                    "expr": {"kind": "affine", "a": 1, "b": 0},
                },
            ],
            "default_expr": {"kind": "affine", "a": -1, "b": 0},
        }
        # 2 branches, affine, small coeffs -> low difficulty
        assert _piecewise_difficulty(spec) in (1, 2)

    def test_single_branch_not_scored_as_two_branches(self) -> None:
        spec = {
            "branches": [
                {
                    "condition": {"kind": "lt", "value": 0},
                    "expr": {"kind": "quadratic", "a": 1, "b": 0, "c": 0},
                }
            ],
            "default_expr": {"kind": "affine", "a": 1, "b": 0},
        }
        assert _piecewise_difficulty(spec) == 2

    def test_multiple_branches_increases_difficulty(self) -> None:
        spec_1 = {
            "branches": [],
            "default_expr": {"kind": "affine", "a": 1, "b": 0},
        }
        spec_3 = {
            "branches": [
                {
                    "condition": {"kind": "lt", "value": -10},
                    "expr": {"kind": "affine", "a": 1, "b": 0},
                },
                {
                    "condition": {"kind": "lt", "value": 10},
                    "expr": {"kind": "affine", "a": 2, "b": 0},
                },
            ],
            "default_expr": {"kind": "affine", "a": 3, "b": 0},
        }
        assert _piecewise_difficulty(spec_1) <= _piecewise_difficulty(spec_3)

    def test_quadratic_increases_difficulty(self) -> None:
        spec_affine = {
            "branches": [],
            "default_expr": {"kind": "affine", "a": 1, "b": 0},
        }
        spec_quad = {
            "branches": [],
            "default_expr": {"kind": "quadratic", "a": 1, "b": 0, "c": 0},
        }
        assert _piecewise_difficulty(spec_affine) < _piecewise_difficulty(
            spec_quad
        )

    def test_large_coeffs_increase_difficulty(self) -> None:
        spec_small = {
            "branches": [],
            "default_expr": {"kind": "affine", "a": 1, "b": 1},
        }
        spec_large = {
            "branches": [],
            "default_expr": {"kind": "affine", "a": 10, "b": 10},
        }
        assert _piecewise_difficulty(spec_small) < _piecewise_difficulty(
            spec_large
        )

    def test_difficulty_clamped_1_to_5(self) -> None:
        spec_simple = {
            "branches": [],
            "default_expr": {"kind": "affine", "a": 0, "b": 0},
        }
        spec_complex = {
            "branches": [
                {
                    "condition": {"kind": "lt", "value": i},
                    "expr": {"kind": "quadratic", "a": 10, "b": 10, "c": 10},
                }
                for i in range(5)
            ],
            "default_expr": {"kind": "quadratic", "a": 10, "b": 10, "c": 10},
        }
        assert 1 <= _piecewise_difficulty(spec_simple) <= 5
        assert 1 <= _piecewise_difficulty(spec_complex) <= 5


class TestStatefulDifficulty:
    def test_longest_run_simplest(self) -> None:
        spec = {
            "template": "longest_run",
            "match_predicate": {"kind": "even"},
        }
        assert _stateful_difficulty(spec) == 1

    def test_conditional_linear_sum_medium(self) -> None:
        spec = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "even"},
            "true_transform": {"kind": "identity"},
            "false_transform": {"kind": "identity"},
            "init_value": 0,
        }
        difficulty = _stateful_difficulty(spec)
        assert 2 <= difficulty <= 3

    def test_resetting_best_prefix_sum_harder(self) -> None:
        spec = {
            "template": "resetting_best_prefix_sum",
            "reset_predicate": {"kind": "even"},
            "init_value": 0,
        }
        difficulty = _stateful_difficulty(spec)
        assert difficulty >= 2

    def test_mod_eq_predicate_increases_difficulty(self) -> None:
        spec_even = {
            "template": "longest_run",
            "match_predicate": {"kind": "even"},
        }
        spec_mod = {
            "template": "longest_run",
            "match_predicate": {"kind": "mod_eq", "divisor": 3, "remainder": 1},
        }
        assert _stateful_difficulty(spec_even) < _stateful_difficulty(spec_mod)

    def test_complex_transforms_increase_difficulty(self) -> None:
        spec_identity = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "even"},
            "true_transform": {"kind": "identity"},
            "false_transform": {"kind": "identity"},
        }
        spec_scale = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "mod_eq", "divisor": 3, "remainder": 1},
            "true_transform": {"kind": "scale", "factor": 2},
            "false_transform": {"kind": "shift", "offset": 5},
        }
        # More complex predicate + transforms should increase difficulty
        assert _stateful_difficulty(spec_identity) < _stateful_difficulty(
            spec_scale
        )


class TestStringPredicateScore:
    def test_simple_predicates(self) -> None:
        assert _string_predicate_score({"kind": "is_alpha"}) == 1
        assert _string_predicate_score({"kind": "is_digit"}) == 1
        assert _string_predicate_score({"kind": "is_upper"}) == 1
        assert _string_predicate_score({"kind": "is_lower"}) == 1

    def test_pattern_predicates(self) -> None:
        assert _string_predicate_score({"kind": "starts_with"}) == 2
        assert _string_predicate_score({"kind": "ends_with"}) == 2
        assert _string_predicate_score({"kind": "contains"}) == 2

    def test_length_cmp_predicates(self) -> None:
        assert _string_predicate_score({"kind": "length_cmp", "op": "eq"}) == 2
        assert _string_predicate_score({"kind": "length_cmp", "op": "le"}) == 2
        assert _string_predicate_score({"kind": "length_cmp", "op": "lt"}) == 3
        assert _string_predicate_score({"kind": "length_cmp", "op": "gt"}) == 3


class TestStringTransformScore:
    def test_identity(self) -> None:
        assert _string_transform_score({"kind": "identity"}) == 1

    def test_simple_transforms(self) -> None:
        assert _string_transform_score({"kind": "lowercase"}) == 2
        assert _string_transform_score({"kind": "uppercase"}) == 2
        assert _string_transform_score({"kind": "capitalize"}) == 2
        assert _string_transform_score({"kind": "swapcase"}) == 2
        assert _string_transform_score({"kind": "reverse"}) == 2

    def test_parameterized_transforms(self) -> None:
        assert _string_transform_score({"kind": "replace"}) == 3
        assert _string_transform_score({"kind": "strip"}) == 3
        assert _string_transform_score({"kind": "prepend"}) == 3
        assert _string_transform_score({"kind": "append"}) == 3


class TestSimpleAlgorithmsDifficulty:
    def test_most_frequent_simple(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": 0,
        }
        difficulty = _simple_algorithms_difficulty(spec)
        assert 1 <= difficulty <= 2

    def test_most_frequent_first_seen_harder(self) -> None:
        spec_smallest = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": 0,
        }
        spec_first_seen = {
            "template": "most_frequent",
            "tie_break": "first_seen",
            "empty_default": 0,
        }
        assert _simple_algorithms_difficulty(
            spec_smallest
        ) <= _simple_algorithms_difficulty(spec_first_seen)

    def test_count_pairs_sum_medium(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 10,
            "counting_mode": "all_indices",
        }
        difficulty = _simple_algorithms_difficulty(spec)
        assert 2 <= difficulty <= 3

    def test_unique_values_harder(self) -> None:
        spec_all = {
            "template": "count_pairs_sum",
            "target": 10,
            "counting_mode": "all_indices",
        }
        spec_unique = {
            "template": "count_pairs_sum",
            "target": 10,
            "counting_mode": "unique_values",
        }
        assert _simple_algorithms_difficulty(
            spec_all
        ) <= _simple_algorithms_difficulty(spec_unique)

    def test_max_window_sum_small_k(self) -> None:
        spec = {
            "template": "max_window_sum",
            "k": 2,
            "invalid_k_default": 0,
        }
        difficulty = _simple_algorithms_difficulty(spec)
        assert 1 <= difficulty <= 2

    def test_max_window_sum_large_k_harder(self) -> None:
        spec_small = {
            "template": "max_window_sum",
            "k": 2,
            "invalid_k_default": 0,
        }
        spec_large = {
            "template": "max_window_sum",
            "k": 8,
            "invalid_k_default": 0,
        }
        assert _simple_algorithms_difficulty(
            spec_small
        ) <= _simple_algorithms_difficulty(spec_large)


class TestStringrulesDifficulty:
    def test_single_rule_simple(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        difficulty = _stringrules_difficulty(spec)
        assert difficulty == 1

    def test_more_rules_increase_difficulty(self) -> None:
        spec_1 = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        spec_3 = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "identity"},
                },
                {
                    "predicate": {"kind": "is_digit"},
                    "transform": {"kind": "identity"},
                },
                {
                    "predicate": {"kind": "is_upper"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        assert _stringrules_difficulty(spec_1) < _stringrules_difficulty(spec_3)

    def test_complex_predicates_increase_difficulty(self) -> None:
        spec_simple = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "lowercase"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        spec_complex = {
            "rules": [
                {
                    "predicate": {"kind": "length_cmp", "op": "gt", "value": 5},
                    "transform": {"kind": "lowercase"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        assert _stringrules_difficulty(spec_simple) < _stringrules_difficulty(
            spec_complex
        )

    def test_parameterized_transforms_increase_difficulty(self) -> None:
        spec_simple = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "lowercase"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        spec_param = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "replace", "old": "a", "new": "b"},
                },
            ],
            "default_transform": {"kind": "append", "suffix": "!"},
        }
        assert _stringrules_difficulty(spec_simple) < _stringrules_difficulty(
            spec_param
        )


class TestComposedPredicateScore:
    def test_not_predicate(self) -> None:
        assert _predicate_score({"kind": "not"}) == 4

    def test_and_two_operands(self) -> None:
        assert _predicate_score({"kind": "and", "operands": [{}, {}]}) == 4

    def test_and_three_operands(self) -> None:
        assert _predicate_score({"kind": "and", "operands": [{}, {}, {}]}) == 5

    def test_or_two_operands(self) -> None:
        assert _predicate_score({"kind": "or", "operands": [{}, {}]}) == 4

    def test_or_three_operands(self) -> None:
        assert _predicate_score({"kind": "or", "operands": [{}, {}, {}]}) == 5


class TestPipelineTransformScore:
    def test_two_step_no_param(self) -> None:
        spec = {
            "kind": "pipeline",
            "steps": [{"kind": "abs"}, {"kind": "negate"}],
        }
        assert _transform_score(spec) == 3

    def test_two_step_one_param(self) -> None:
        spec = {
            "kind": "pipeline",
            "steps": [{"kind": "abs"}, {"kind": "shift", "offset": 1}],
        }
        assert _transform_score(spec) == 4

    def test_two_step_two_param(self) -> None:
        spec = {
            "kind": "pipeline",
            "steps": [
                {"kind": "shift", "offset": 1},
                {"kind": "scale", "factor": 2},
            ],
        }
        assert _transform_score(spec) == 5

    def test_three_step(self) -> None:
        spec = {
            "kind": "pipeline",
            "steps": [{"kind": "abs"}, {"kind": "negate"}, {"kind": "abs"}],
        }
        assert _transform_score(spec) == 5


class TestStringComposedPredicateScore:
    def test_not(self) -> None:
        assert _string_predicate_score({"kind": "not"}) == 4

    def test_and_two_operands(self) -> None:
        assert (
            _string_predicate_score({"kind": "and", "operands": [{}, {}]}) == 4
        )

    def test_and_three_operands(self) -> None:
        assert (
            _string_predicate_score({"kind": "and", "operands": [{}, {}, {}]})
            == 5
        )

    def test_or_two_operands(self) -> None:
        assert (
            _string_predicate_score({"kind": "or", "operands": [{}, {}]}) == 4
        )

    def test_or_three_operands(self) -> None:
        assert (
            _string_predicate_score({"kind": "or", "operands": [{}, {}, {}]})
            == 5
        )


class TestStringPipelineTransformScore:
    def test_two_step_no_param(self) -> None:
        spec = {
            "kind": "pipeline",
            "steps": [{"kind": "lowercase"}, {"kind": "reverse"}],
        }
        assert _string_transform_score(spec) == 3

    def test_two_step_one_param(self) -> None:
        spec = {
            "kind": "pipeline",
            "steps": [
                {"kind": "lowercase"},
                {"kind": "replace", "old": "a", "new": "b"},
            ],
        }
        assert _string_transform_score(spec) == 4

    def test_two_step_two_param(self) -> None:
        spec = {
            "kind": "pipeline",
            "steps": [
                {"kind": "replace", "old": "a", "new": "b"},
                {"kind": "append", "suffix": "!"},
            ],
        }
        assert _string_transform_score(spec) == 5

    def test_three_step(self) -> None:
        spec = {
            "kind": "pipeline",
            "steps": [
                {"kind": "lowercase"},
                {"kind": "reverse"},
                {"kind": "uppercase"},
            ],
        }
        assert _string_transform_score(spec) == 5


class TestToggleSumDifficulty:
    def test_toggle_sum_template_score(self) -> None:
        spec = {
            "template": "toggle_sum",
            "toggle_predicate": {"kind": "even"},
            "on_transform": {"kind": "identity"},
            "off_transform": {"kind": "identity"},
            "init_value": 0,
        }
        # toggle_sum=4, even=1, identity avg=1
        # 0.4*4 + 0.3*1 + 0.3*1 = 1.6+0.3+0.3 = 2.2 -> 2
        assert _stateful_difficulty(spec) == 2

    def test_toggle_sum_with_composed_pred_two_operands(self) -> None:
        spec = {
            "template": "toggle_sum",
            "toggle_predicate": {"kind": "and", "operands": [{}, {}]},
            "on_transform": {"kind": "shift", "offset": 1},
            "off_transform": {"kind": "scale", "factor": 2},
            "init_value": 0,
        }
        # toggle_sum=4, and(2 ops)=4, shift+scale avg=3
        # 0.4*4 + 0.3*4 + 0.3*3 = 1.6+1.2+0.9 = 3.7 -> 4
        assert _stateful_difficulty(spec) == 4

    def test_toggle_sum_with_composed_pred_three_operands(self) -> None:
        spec = {
            "template": "toggle_sum",
            "toggle_predicate": {"kind": "and", "operands": [{}, {}, {}]},
            "on_transform": {"kind": "shift", "offset": 1},
            "off_transform": {"kind": "scale", "factor": 2},
            "init_value": 0,
        }
        # toggle_sum=4, and(3 ops)=5, shift+scale avg=3
        # 0.4*4 + 0.3*5 + 0.3*3 = 1.6+1.5+0.9 = 4.0 -> 4
        assert _stateful_difficulty(spec) == 4


class TestSimpleAlgoWithPreprocess:
    def test_legacy_scoring_unchanged(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": 0,
        }
        # Legacy: 0.5*2 + 0.3*1 + 0.2*1 = 1.5 -> 2
        assert _simple_algorithms_difficulty(spec) == 2

    def test_with_pre_filter(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "first_seen",
            "empty_default": 0,
            "pre_filter": {"kind": "mod_eq", "divisor": 3, "remainder": 0},
        }
        # Extended: template=2+1=3, mode=max(2, 4)=4, edge=1
        # 0.5*3 + 0.3*4 + 0.2*1 = 1.5+1.2+0.2 = 2.9 -> 3
        assert _simple_algorithms_difficulty(spec) == 3

    def test_with_pre_filter_and_transform(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 10,
            "counting_mode": "unique_values",
            "pre_filter": {"kind": "and"},
            "pre_transform": {
                "kind": "pipeline",
                "steps": [
                    {"kind": "shift", "offset": 1},
                    {"kind": "scale", "factor": 2},
                ],
            },
            "no_result_default": -1,
            "short_list_default": 0,
        }
        # Extended: template=3+2=5, mode=max(3, max(5,5))=5, edge=1+2=3
        # 0.5*5 + 0.3*5 + 0.2*3 = 2.5+1.5+0.6 = 4.6 -> 5
        assert _simple_algorithms_difficulty(spec) == 5


class TestComputeDifficulty:
    def test_piecewise_family(self) -> None:
        spec = {
            "branches": [],
            "default_expr": {"kind": "affine", "a": 1, "b": 0},
        }
        assert compute_difficulty("piecewise", spec) == 1

    def test_stateful_family(self) -> None:
        spec = {
            "template": "longest_run",
            "match_predicate": {"kind": "even"},
        }
        assert compute_difficulty("stateful", spec) == 1

    def test_simple_algorithms_family(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": 0,
        }
        difficulty = compute_difficulty("simple_algorithms", spec)
        assert 1 <= difficulty <= 5

    def test_stringrules_family(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "identity"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        difficulty = compute_difficulty("stringrules", spec)
        assert 1 <= difficulty <= 5

    def test_stack_bytecode_family_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.stack_bytecode.task") is None:
            pytest.skip("stack_bytecode family is not available")
        spec = {
            "program": [
                {"op": "push_const", "value": 2},
                {"op": "push_const", "value": 3},
                {"op": "mul"},
                {"op": "halt"},
            ],
            "max_step_count": 64,
            "jump_target_mode": "error",
            "input_mode": "direct",
        }
        difficulty = compute_difficulty("stack_bytecode", spec)
        assert 1 <= difficulty <= 5

    def test_bitops_family_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.bitops.task") is None:
            pytest.skip("bitops family is not available")
        spec = {
            "width_bits": 16,
            "operations": [
                {"op": "xor_mask", "arg": 255},
                {"op": "shl", "arg": 2},
                {"op": "rotr", "arg": 3},
                {"op": "parity", "arg": None},
            ],
        }
        difficulty = compute_difficulty("bitops", spec)
        assert 1 <= difficulty <= 5

    def test_sequence_dp_family(self) -> None:
        spec = {
            "template": "global",
            "output_mode": "score",
            "match_predicate": {"kind": "eq"},
            "match_score": 4,
            "mismatch_score": -2,
            "gap_score": -2,
            "step_tie_break": "diag_up_left",
        }
        difficulty = compute_difficulty("sequence_dp", spec)
        assert 1 <= difficulty <= 5

    def test_graph_queries_simple_vs_hard_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.graph_queries.task") is None:
            pytest.skip("graph_queries family is not available")

        simple = {
            "query_type": "reachable",
            "directed": False,
            "weighted": False,
            "n_nodes": 3,
            "edges": [{"u": 0, "v": 1, "w": 1}],
        }
        hard = {
            "query_type": "shortest_path_cost",
            "directed": True,
            "weighted": True,
            "n_nodes": 12,
            "edges": [
                {"u": 0, "v": 1, "w": 3},
                {"u": 0, "v": 2, "w": 4},
                {"u": 0, "v": 3, "w": 5},
                {"u": 1, "v": 4, "w": 2},
                {"u": 2, "v": 4, "w": 6},
                {"u": 3, "v": 5, "w": 2},
                {"u": 4, "v": 6, "w": 1},
                {"u": 5, "v": 6, "w": 7},
                {"u": 6, "v": 7, "w": 1},
                {"u": 7, "v": 8, "w": 2},
                {"u": 8, "v": 9, "w": 2},
                {"u": 9, "v": 10, "w": 3},
                {"u": 10, "v": 11, "w": 1},
                {"u": 1, "v": 9, "w": 8},
                {"u": 2, "v": 10, "w": 9},
                {"u": 3, "v": 11, "w": 10},
                {"u": 4, "v": 8, "w": 4},
                {"u": 5, "v": 9, "w": 5},
            ],
        }

        try:
            easy_score = compute_difficulty("graph_queries", simple)
            hard_score = compute_difficulty("graph_queries", hard)
        except ValueError as exc:
            if "Unknown family: graph_queries" in str(exc):
                pytest.skip(
                    "compute_difficulty('graph_queries', ...) is not available"
                )
            raise

        assert 1 <= easy_score <= 5
        assert 1 <= hard_score <= 5
        assert hard_score >= easy_score

    def test_sequence_dp_monotonic_examples(self) -> None:
        specs = [
            {
                "template": "global",
                "output_mode": "score",
                "match_predicate": {"kind": "eq"},
                "match_score": 5,
                "mismatch_score": -3,
                "gap_score": -3,
                "step_tie_break": "diag_up_left",
            },
            {
                "template": "global",
                "output_mode": "score",
                "match_predicate": {"kind": "abs_diff_le", "max_diff": 1},
                "match_score": 4,
                "mismatch_score": -2,
                "gap_score": -2,
                "step_tie_break": "diag_left_up",
            },
            {
                "template": "global",
                "output_mode": "alignment_len",
                "match_predicate": {"kind": "abs_diff_le", "max_diff": 3},
                "match_score": 3,
                "mismatch_score": -1,
                "gap_score": -1,
                "step_tie_break": "up_diag_left",
            },
            {
                "template": "local",
                "output_mode": "gap_count",
                "match_predicate": {
                    "kind": "mod_eq",
                    "divisor": 3,
                    "remainder": 1,
                },
                "match_score": 2,
                "mismatch_score": 0,
                "gap_score": -1,
                "step_tie_break": "up_left_diag",
            },
            {
                "template": "local",
                "output_mode": "gap_count",
                "match_predicate": {
                    "kind": "mod_eq",
                    "divisor": 9,
                    "remainder": 2,
                },
                "match_score": 1,
                "mismatch_score": 1,
                "gap_score": 1,
                "step_tie_break": "left_up_diag",
            },
        ]
        scores = [compute_difficulty("sequence_dp", spec) for spec in specs]
        assert scores == sorted(scores)

    def test_sequence_dp_difficulty_clamped(self) -> None:
        very_simple = {
            "template": "global",
            "output_mode": "score",
            "match_predicate": {"kind": "eq"},
            "match_score": 100,
            "mismatch_score": -100,
            "gap_score": -100,
            "step_tie_break": "diag_up_left",
        }
        tie_heavy = {
            "template": "local",
            "output_mode": "gap_count",
            "match_predicate": {
                "kind": "mod_eq",
                "divisor": 50,
                "remainder": 0,
            },
            "match_score": 0,
            "mismatch_score": 0,
            "gap_score": 0,
            "step_tie_break": "left_up_diag",
        }
        easy_score = compute_difficulty("sequence_dp", very_simple)
        hard_score = compute_difficulty("sequence_dp", tie_heavy)
        assert easy_score == 1
        assert hard_score == 5
        assert 1 <= easy_score <= 5
        assert 1 <= hard_score <= 5

    def test_intervals_family_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.intervals.task") is None:
            pytest.skip("intervals family is not available")
        spec = {
            "operation": "merged_count",
            "boundary_mode": "closed_open",
            "merge_touching": True,
            "endpoint_clip_abs": 12,
        }
        difficulty = compute_difficulty("intervals", spec)
        assert 1 <= difficulty <= 5

    def test_intervals_monotonic_examples_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.intervals.task") is None:
            pytest.skip("intervals family is not available")

        specs = [
            {
                "operation": "total_coverage",
                "boundary_mode": "closed_closed",
                "merge_touching": False,
                "endpoint_clip_abs": 20,
            },
            {
                "operation": "merged_count",
                "boundary_mode": "closed_open",
                "merge_touching": False,
                "endpoint_clip_abs": 14,
            },
            {
                "operation": "merged_count",
                "boundary_mode": "open_closed",
                "merge_touching": True,
                "endpoint_clip_abs": 10,
            },
            {
                "operation": "max_overlap_count",
                "boundary_mode": "open_closed",
                "merge_touching": True,
                "endpoint_clip_abs": 7,
            },
            {
                "operation": "gap_count",
                "boundary_mode": "open_open",
                "merge_touching": True,
                "endpoint_clip_abs": 4,
            },
        ]
        scores = [compute_difficulty("intervals", spec) for spec in specs]
        assert scores == sorted(scores)

    def test_intervals_difficulty_clamped_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.intervals.task") is None:
            pytest.skip("intervals family is not available")

        very_simple = {
            "operation": "total_coverage",
            "boundary_mode": "closed_closed",
            "merge_touching": False,
            "endpoint_clip_abs": 20,
        }
        hard = {
            "operation": "gap_count",
            "boundary_mode": "open_open",
            "merge_touching": True,
            "endpoint_clip_abs": 3,
        }
        easy_score = compute_difficulty("intervals", very_simple)
        hard_score = compute_difficulty("intervals", hard)
        assert easy_score == 1
        assert hard_score == 5
        assert 1 <= easy_score <= 5
        assert 1 <= hard_score <= 5

    def test_intervals_bool_like_merge_coercion_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.intervals.task") is None:
            pytest.skip("intervals family is not available")

        bool_spec = {
            "operation": "merged_count",
            "boundary_mode": "closed_open",
            "merge_touching": False,
            "endpoint_clip_abs": 12,
            "endpoint_quantize_step": 1,
        }
        string_spec = {
            "operation": "merged_count",
            "boundary_mode": "closed_open",
            "merge_touching": "false",
            "endpoint_clip_abs": 12,
            "endpoint_quantize_step": 1,
        }

        string_score = compute_difficulty("intervals", string_spec)
        bool_score = compute_difficulty("intervals", bool_spec)
        assert string_score == bool_score

    def test_intervals_quantize_step_affects_difficulty_when_available(
        self,
    ) -> None:
        if importlib.util.find_spec("genfxn.intervals.task") is None:
            pytest.skip("intervals family is not available")

        base = {
            "operation": "total_coverage",
            "boundary_mode": "closed_closed",
            "merge_touching": True,
            "endpoint_clip_abs": 20,
        }
        easy_score = compute_difficulty(
            "intervals",
            {**base, "endpoint_quantize_step": 1},
        )
        harder_score = compute_difficulty(
            "intervals",
            {**base, "endpoint_quantize_step": 6},
        )

        assert easy_score < harder_score

    def test_temporal_logic_family_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.temporal_logic.task") is None:
            pytest.skip("temporal_logic family is not available")

        spec = {
            "output_mode": "sat_count",
            "formula": {
                "op": "eventually",
                "child": {
                    "op": "atom",
                    "predicate": "gt",
                    "constant": 0,
                },
            },
        }
        difficulty = compute_difficulty("temporal_logic", spec)
        assert 1 <= difficulty <= 5

    def test_temporal_logic_monotonic_examples_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.temporal_logic.task") is None:
            pytest.skip("temporal_logic family is not available")

        specs = [
            {
                "output_mode": "sat_at_start",
                "formula": {
                    "op": "atom",
                    "predicate": "eq",
                    "constant": 0,
                },
            },
            {
                "output_mode": "sat_count",
                "formula": {
                    "op": "not",
                    "child": {
                        "op": "atom",
                        "predicate": "ge",
                        "constant": 0,
                    },
                },
            },
            {
                "output_mode": "sat_count",
                "formula": {
                    "op": "always",
                    "child": {
                        "op": "or",
                        "left": {
                            "op": "atom",
                            "predicate": "lt",
                            "constant": -1,
                        },
                        "right": {
                            "op": "atom",
                            "predicate": "gt",
                            "constant": 1,
                        },
                    },
                },
            },
            {
                "output_mode": "first_sat_index",
                "formula": {
                    "op": "until",
                    "left": {
                        "op": "atom",
                        "predicate": "ge",
                        "constant": 0,
                    },
                    "right": {
                        "op": "atom",
                        "predicate": "lt",
                        "constant": 0,
                    },
                },
            },
            {
                "output_mode": "first_sat_index",
                "formula": {
                    "op": "since",
                    "left": {
                        "op": "until",
                        "left": {
                            "op": "atom",
                            "predicate": "ge",
                            "constant": -2,
                        },
                        "right": {
                            "op": "atom",
                            "predicate": "lt",
                            "constant": -3,
                        },
                    },
                    "right": {
                        "op": "always",
                        "child": {
                            "op": "atom",
                            "predicate": "gt",
                            "constant": 2,
                        },
                    },
                },
            },
        ]
        scores = [compute_difficulty("temporal_logic", spec) for spec in specs]
        assert scores == sorted(scores)

    def test_temporal_logic_difficulty_clamped_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.temporal_logic.task") is None:
            pytest.skip("temporal_logic family is not available")

        easy = {
            "output_mode": "sat_at_start",
            "formula": {
                "op": "atom",
                "predicate": "eq",
                "constant": 0,
            },
        }
        hard = {
            "output_mode": "first_sat_index",
            "formula": {
                "op": "since",
                "left": {
                    "op": "until",
                    "left": {
                        "op": "always",
                        "child": {
                            "op": "atom",
                            "predicate": "ge",
                            "constant": 1,
                        },
                    },
                    "right": {
                        "op": "eventually",
                        "child": {
                            "op": "atom",
                            "predicate": "lt",
                            "constant": -1,
                        },
                    },
                },
                "right": {
                    "op": "and",
                    "left": {
                        "op": "next",
                        "child": {
                            "op": "atom",
                            "predicate": "gt",
                            "constant": 4,
                        },
                    },
                    "right": {
                        "op": "atom",
                        "predicate": "le",
                        "constant": -4,
                    },
                },
            },
        }
        easy_score = compute_difficulty("temporal_logic", easy)
        hard_score = compute_difficulty("temporal_logic", hard)
        assert 1 <= easy_score <= 5
        assert 1 <= hard_score <= 5
        assert hard_score >= easy_score

    def test_stack_bytecode_monotonic_examples_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.stack_bytecode.task") is None:
            pytest.skip("stack_bytecode family is not available")

        specs = [
            {
                "program": [
                    {"op": "push_const", "value": 1},
                    {"op": "halt"},
                ],
                "max_step_count": 20,
                "jump_target_mode": "error",
                "input_mode": "direct",
            },
            {
                "program": [
                    {"op": "load_input", "index": 0},
                    {"op": "is_zero"},
                    {"op": "jump_if_zero", "target": 5},
                    {"op": "push_const", "value": 1},
                    {"op": "jump", "target": 6},
                    {"op": "push_const", "value": 2},
                    {"op": "halt"},
                ],
                "max_step_count": 40,
                "jump_target_mode": "error",
                "input_mode": "direct",
            },
            {
                "program": [
                    {"op": "push_const", "value": 3},
                    {"op": "dup"},
                    {"op": "is_zero"},
                    {"op": "jump_if_nonzero", "target": 8},
                    {"op": "push_const", "value": 1},
                    {"op": "sub"},
                    {"op": "jump", "target": 1},
                    {"op": "push_const", "value": 99},
                    {"op": "halt"},
                ],
                "max_step_count": 70,
                "jump_target_mode": "error",
                "input_mode": "direct",
            },
            {
                "program": [
                    {"op": "load_input", "index": 0},
                    {"op": "dup"},
                    {"op": "is_zero"},
                    {"op": "jump_if_nonzero", "target": 12},
                    {"op": "push_const", "value": 2},
                    {"op": "mod"},
                    {"op": "is_zero"},
                    {"op": "jump_if_zero", "target": 10},
                    {"op": "push_const", "value": 3},
                    {"op": "mul"},
                    {"op": "jump", "target": 1},
                    {"op": "push_const", "value": 7},
                    {"op": "halt"},
                ],
                "max_step_count": 110,
                "jump_target_mode": "clamp",
                "input_mode": "cyclic",
            },
            {
                "program": [
                    {"op": "load_input", "index": -2},
                    {"op": "dup"},
                    {"op": "push_const", "value": 5},
                    {"op": "gt"},
                    {"op": "jump_if_zero", "target": 11},
                    {"op": "push_const", "value": -3},
                    {"op": "add"},
                    {"op": "push_const", "value": 2},
                    {"op": "div"},
                    {"op": "jump", "target": 1},
                    {"op": "push_const", "value": 13},
                    {"op": "halt"},
                ],
                "max_step_count": 160,
                "jump_target_mode": "wrap",
                "input_mode": "cyclic",
            },
        ]

        scores = [compute_difficulty("stack_bytecode", spec) for spec in specs]
        assert scores == sorted(scores)
        assert len(set(scores)) >= 3

    def test_stack_bytecode_difficulty_clamped_when_available(self) -> None:
        if importlib.util.find_spec("genfxn.stack_bytecode.task") is None:
            pytest.skip("stack_bytecode family is not available")

        simple = {
            "program": [{"op": "halt"}],
            "max_step_count": 5,
            "jump_target_mode": "error",
            "input_mode": "direct",
        }
        complex_spec = {
            "program": [
                {"op": "load_input", "index": -99},
                {"op": "dup"},
                {"op": "push_const", "value": 10},
                {"op": "mod"},
                {"op": "is_zero"},
                {"op": "jump_if_zero", "target": 15},
                {"op": "push_const", "value": -7},
                {"op": "add"},
                {"op": "push_const", "value": 3},
                {"op": "mul"},
                {"op": "push_const", "value": 2},
                {"op": "div"},
                {"op": "jump", "target": 1},
                {"op": "push_const", "value": 1},
                {"op": "eq"},
                {"op": "halt"},
            ],
            "max_step_count": 1000,
            "jump_target_mode": "wrap",
            "input_mode": "cyclic",
        }
        assert 1 <= compute_difficulty("stack_bytecode", simple) <= 5
        assert 1 <= compute_difficulty("stack_bytecode", complex_spec) <= 5

    def test_unknown_family_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown family: unknown"):
            compute_difficulty("unknown", {})


class TestFsmDifficulty:
    def test_fsm_difficulty_reaches_level_five_for_hard_specs(self) -> None:
        spec = {
            "machine_type": "mealy",
            "output_mode": "transition_count",
            "undefined_transition_policy": "error",
            "states": [
                {
                    "id": state_id,
                    "is_accept": state_id == 0,
                    "transitions": [
                        {
                            "predicate": {
                                "kind": "mod_eq",
                                "divisor": 7,
                                "remainder": (state_id + i) % 7,
                            },
                            "target_state_id": (state_id + i + 1) % 6,
                        }
                        for i in range(5)
                    ],
                }
                for state_id in range(6)
            ],
        }
        assert compute_difficulty("fsm", spec) == 5
