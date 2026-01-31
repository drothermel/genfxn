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
        assert _piecewise_difficulty(spec_1) < _piecewise_difficulty(spec_3)

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

    def test_unknown_family_defaults_to_3(self) -> None:
        assert compute_difficulty("unknown", {}) == 3
