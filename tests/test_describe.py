from genfxn.core.describe import (
    _describe_expression,
    _describe_piecewise,
    _describe_predicate,
    _describe_simple_algorithms,
    _describe_stateful,
    _describe_string_predicate,
    _describe_string_transform,
    _describe_stringrules,
    _describe_transform,
    _format_number,
    describe_task,
)
from genfxn.fsm.models import (
    MachineType,
    OutputMode,
    UndefinedTransitionPolicy,
)
from genfxn.stack_bytecode.models import InputMode, JumpTargetMode


class TestFormatNumber:
    def test_positive(self) -> None:
        assert _format_number(5) == "5"
        assert _format_number(100) == "100"

    def test_zero(self) -> None:
        assert _format_number(0) == "0"

    def test_negative(self) -> None:
        assert _format_number(-5) == "negative 5"
        assert _format_number(-100) == "negative 100"


class TestDescribePredicate:
    def test_even(self) -> None:
        result = _describe_predicate({"kind": "even"}, "x")
        assert result == "the x is even"

    def test_odd(self) -> None:
        result = _describe_predicate({"kind": "odd"}, "element")
        assert result == "the element is odd"

    def test_lt_positive(self) -> None:
        result = _describe_predicate({"kind": "lt", "value": 10}, "x")
        assert result == "the x is less than 10"

    def test_lt_negative(self) -> None:
        result = _describe_predicate({"kind": "lt", "value": -5}, "x")
        assert result == "the x is less than negative 5"

    def test_le(self) -> None:
        result = _describe_predicate({"kind": "le", "value": 20}, "x")
        assert result == "the x is at most 20"

    def test_gt(self) -> None:
        result = _describe_predicate({"kind": "gt", "value": 0}, "x")
        assert result == "the x is greater than 0"

    def test_ge(self) -> None:
        result = _describe_predicate({"kind": "ge", "value": -10}, "x")
        assert result == "the x is at least negative 10"

    def test_mod_eq(self) -> None:
        result = _describe_predicate(
            {"kind": "mod_eq", "divisor": 3, "remainder": 1}, "element"
        )
        assert result == "the element mod 3 equals 1"

    def test_in_set(self) -> None:
        result = _describe_predicate(
            {"kind": "in_set", "values": [3, 1, 2]}, "x"
        )
        assert result == "the x is in {1, 2, 3}"


class TestDescribeTransform:
    def test_identity(self) -> None:
        assert _describe_transform({"kind": "identity"}) == "the element"

    def test_abs(self) -> None:
        assert (
            _describe_transform({"kind": "abs"})
            == "the absolute value of the element"
        )

    def test_negate(self) -> None:
        assert (
            _describe_transform({"kind": "negate"})
            == "the negation of the element"
        )

    def test_shift_positive(self) -> None:
        result = _describe_transform({"kind": "shift", "offset": 5})
        assert result == "the element plus 5"

    def test_shift_negative(self) -> None:
        result = _describe_transform({"kind": "shift", "offset": -3})
        assert result == "the element minus 3"

    def test_scale(self) -> None:
        result = _describe_transform({"kind": "scale", "factor": 2})
        assert result == "2 times the element"

    def test_scale_negative(self) -> None:
        result = _describe_transform({"kind": "scale", "factor": -3})
        assert result == "negative 3 times the element"


class TestDescribeExpression:
    def test_affine_simple(self) -> None:
        result = _describe_expression({"kind": "affine", "a": 2, "b": 3})
        assert result == "2 times x plus 3"

    def test_affine_negative_b(self) -> None:
        result = _describe_expression({"kind": "affine", "a": 1, "b": -5})
        assert result == "x minus 5"

    def test_affine_negative_a(self) -> None:
        result = _describe_expression({"kind": "affine", "a": -2, "b": 0})
        assert result == "negative 2 times x"

    def test_affine_a_is_one(self) -> None:
        result = _describe_expression({"kind": "affine", "a": 1, "b": 0})
        assert result == "x"

    def test_affine_a_is_neg_one(self) -> None:
        result = _describe_expression({"kind": "affine", "a": -1, "b": 0})
        assert result == "negative x"

    def test_affine_only_constant(self) -> None:
        result = _describe_expression({"kind": "affine", "a": 0, "b": 7})
        assert result == "7"

    def test_affine_zero(self) -> None:
        result = _describe_expression({"kind": "affine", "a": 0, "b": 0})
        assert result == "0"

    def test_quadratic_full(self) -> None:
        result = _describe_expression(
            {"kind": "quadratic", "a": 2, "b": 3, "c": 1}
        )
        assert result == "2 times x squared plus 3 times x plus 1"

    def test_quadratic_a_is_one(self) -> None:
        result = _describe_expression(
            {"kind": "quadratic", "a": 1, "b": 0, "c": 0}
        )
        assert result == "x squared"

    def test_quadratic_negative_terms(self) -> None:
        result = _describe_expression(
            {"kind": "quadratic", "a": -1, "b": -2, "c": -3}
        )
        assert result == "negative x squared minus 2 times x minus 3"

    def test_abs_simple(self) -> None:
        result = _describe_expression({"kind": "abs", "a": 2, "b": 1})
        assert result == "2 times the absolute value of x plus 1"

    def test_abs_a_is_one(self) -> None:
        result = _describe_expression({"kind": "abs", "a": 1, "b": 0})
        assert result == "the absolute value of x"

    def test_mod_simple(self) -> None:
        result = _describe_expression(
            {"kind": "mod", "divisor": 7, "a": 1, "b": 0}
        )
        assert result == "x mod 7"

    def test_mod_with_coeff(self) -> None:
        result = _describe_expression(
            {"kind": "mod", "divisor": 3, "a": 2, "b": 5}
        )
        assert result == "2 times x mod 3 plus 5"


class TestDescribePiecewise:
    def test_single_branch(self) -> None:
        spec = {
            "branches": [
                {
                    "condition": {"kind": "lt", "value": 0},
                    "expr": {"kind": "affine", "a": -1, "b": 0},
                },
            ],
            "default_expr": {"kind": "affine", "a": 1, "b": 0},
        }
        result = _describe_piecewise(spec)
        assert "When the x is less than 0, return negative x." in result
        assert "Otherwise, return x." in result

    def test_multiple_branches(self) -> None:
        spec = {
            "branches": [
                {
                    "condition": {"kind": "lt", "value": -10},
                    "expr": {"kind": "affine", "a": 2, "b": 0},
                },
                {
                    "condition": {"kind": "lt", "value": 10},
                    "expr": {"kind": "affine", "a": 1, "b": 0},
                },
            ],
            "default_expr": {"kind": "affine", "a": 3, "b": 0},
        }
        result = _describe_piecewise(spec)
        assert "When the x is less than negative 10" in result
        assert "When the x is less than 10" in result
        assert "Otherwise, return 3 times x." in result


class TestDescribeStateful:
    def test_longest_run(self) -> None:
        spec = {
            "template": "longest_run",
            "match_predicate": {"kind": "even"},
        }
        result = _describe_stateful(spec)
        assert "longest consecutive run" in result
        assert "the element is even" in result
        assert "Return the length" in result

    def test_conditional_linear_sum(self) -> None:
        spec = {
            "template": "conditional_linear_sum",
            "predicate": {"kind": "gt", "value": 0},
            "true_transform": {"kind": "identity"},
            "false_transform": {"kind": "negate"},
            "init_value": -5,
        }
        result = _describe_stateful(spec)
        assert "accumulator of negative 5" in result
        assert "the element is greater than 0" in result
        assert "add the element to the accumulator" in result
        assert "add the negation of the element" in result

    def test_resetting_best_prefix_sum(self) -> None:
        spec = {
            "template": "resetting_best_prefix_sum",
            "reset_predicate": {"kind": "lt", "value": 0},
            "init_value": 0,
        }
        result = _describe_stateful(spec)
        assert "running sum and the best sum" in result
        assert "the element is less than 0" in result
        assert "reset the running sum" in result
        assert "otherwise, add the element to the running sum" in result
        assert "Return the best sum" in result

    def test_resetting_best_prefix_sum_with_value_transform(self) -> None:
        spec = {
            "template": "resetting_best_prefix_sum",
            "reset_predicate": {"kind": "lt", "value": 0},
            "init_value": 0,
            "value_transform": {"kind": "scale", "factor": 2},
        }
        result = _describe_stateful(spec)
        assert "the element is less than 0" in result
        assert "otherwise, add 2 times the element to the running sum" in result
        assert "update best sum if running sum is larger" in result

    def test_toggle_sum(self) -> None:
        spec = {
            "template": "toggle_sum",
            "toggle_predicate": {"kind": "even"},
            "on_transform": {"kind": "identity"},
            "off_transform": {"kind": "negate"},
            "init_value": 0,
        }
        result = _describe_stateful(spec)
        assert result != ""
        assert "toggle" in result
        assert "the element is even" in result
        assert "add the element" in result
        assert "add the negation of the element" in result

    def test_toggle_sum_with_compound_predicate(self) -> None:
        spec = {
            "template": "toggle_sum",
            "toggle_predicate": {
                "kind": "and",
                "operands": [
                    {"kind": "even"},
                    {"kind": "mod_eq", "divisor": 8, "remainder": 0},
                ],
            },
            "on_transform": {
                "kind": "pipeline",
                "steps": [{"kind": "scale", "factor": -3}, {"kind": "abs"}],
            },
            "off_transform": {"kind": "negate"},
            "init_value": -5,
        }
        result = _describe_stateful(spec)
        assert result != ""
        assert "accumulator of negative 5" in result
        assert "even" in result
        assert "mod 8 equals 0" in result

    def test_all_templates_produce_nonempty_descriptions(self) -> None:
        """Guard against new templates being added without describe support."""
        from genfxn.stateful.models import TemplateType

        minimal_specs: dict[str, dict] = {
            "conditional_linear_sum": {
                "template": "conditional_linear_sum",
                "predicate": {"kind": "even"},
                "true_transform": {"kind": "identity"},
                "false_transform": {"kind": "identity"},
                "init_value": 0,
            },
            "resetting_best_prefix_sum": {
                "template": "resetting_best_prefix_sum",
                "reset_predicate": {"kind": "even"},
                "init_value": 0,
            },
            "longest_run": {
                "template": "longest_run",
                "match_predicate": {"kind": "even"},
            },
            "toggle_sum": {
                "template": "toggle_sum",
                "toggle_predicate": {"kind": "even"},
                "on_transform": {"kind": "identity"},
                "off_transform": {"kind": "identity"},
                "init_value": 0,
            },
        }
        for template_type in TemplateType:
            assert template_type.value in minimal_specs, (
                f"Template {template_type.value} has no minimal spec in test — "
                f"add one and ensure _describe_stateful handles it"
            )
            result = _describe_stateful(minimal_specs[template_type.value])
            assert result != "", (
                f"_describe_stateful returned empty string for template "
                f"{template_type.value}"
            )


class TestDescribePredicate_Compound:
    def test_and(self) -> None:
        pred = {
            "kind": "and",
            "operands": [
                {"kind": "even"},
                {"kind": "gt", "value": 5},
            ],
        }
        result = _describe_predicate(pred, "x")
        assert "the x is even" in result
        assert "the x is greater than 5" in result
        assert " and " in result

    def test_or(self) -> None:
        pred = {
            "kind": "or",
            "operands": [
                {"kind": "lt", "value": 0},
                {"kind": "mod_eq", "divisor": 3, "remainder": 0},
            ],
        }
        result = _describe_predicate(pred, "element")
        assert "less than 0" in result
        assert "mod 3 equals 0" in result
        assert " or " in result

    def test_not(self) -> None:
        pred = {"kind": "not", "operand": {"kind": "odd"}}
        result = _describe_predicate(pred, "x")
        assert "not" in result
        assert "the x is odd" in result

    def test_and_three_operands(self) -> None:
        pred = {
            "kind": "and",
            "operands": [
                {"kind": "even"},
                {"kind": "gt", "value": 0},
                {"kind": "lt", "value": 100},
            ],
        }
        result = _describe_predicate(pred, "x")
        assert result.count(" and ") == 2


class TestDescribeTransform_Pipeline:
    def test_pipeline_single_step(self) -> None:
        trans = {"kind": "pipeline", "steps": [{"kind": "abs"}]}
        result = _describe_transform(trans)
        assert "absolute value" in result

    def test_pipeline_scale_then_abs(self) -> None:
        trans = {
            "kind": "pipeline",
            "steps": [{"kind": "scale", "factor": -3}, {"kind": "abs"}],
        }
        result = _describe_transform(trans)
        assert "absolute value" in result
        assert "negative 3" in result

    def test_pipeline_empty_steps(self) -> None:
        trans = {"kind": "pipeline", "steps": []}
        result = _describe_transform(trans)
        assert result == "the element"

    def test_pipeline_shift_then_negate(self) -> None:
        trans = {
            "kind": "pipeline",
            "steps": [{"kind": "shift", "offset": 5}, {"kind": "negate"}],
        }
        result = _describe_transform(trans)
        assert "plus 5" in result
        assert "negation" in result


class TestDescribeStringPredicate:
    def test_starts_with(self) -> None:
        result = _describe_string_predicate(
            {"kind": "starts_with", "prefix": "abc"}
        )
        assert result == "the string starts with 'abc'"

    def test_ends_with(self) -> None:
        result = _describe_string_predicate(
            {"kind": "ends_with", "suffix": "xyz"}
        )
        assert result == "the string ends with 'xyz'"

    def test_contains(self) -> None:
        result = _describe_string_predicate(
            {"kind": "contains", "substring": "test"}
        )
        assert result == "the string contains 'test'"

    def test_is_alpha(self) -> None:
        result = _describe_string_predicate({"kind": "is_alpha"})
        assert result == "the string contains only letters"

    def test_is_digit(self) -> None:
        result = _describe_string_predicate({"kind": "is_digit"})
        assert result == "the string contains only digits"

    def test_is_upper(self) -> None:
        result = _describe_string_predicate({"kind": "is_upper"})
        assert result == "the string is all uppercase"

    def test_is_lower(self) -> None:
        result = _describe_string_predicate({"kind": "is_lower"})
        assert result == "the string is all lowercase"

    def test_length_cmp_lt(self) -> None:
        result = _describe_string_predicate(
            {"kind": "length_cmp", "op": "lt", "value": 5}
        )
        assert result == "the string has fewer than 5 characters"

    def test_length_cmp_le(self) -> None:
        result = _describe_string_predicate(
            {"kind": "length_cmp", "op": "le", "value": 10}
        )
        assert result == "the string has at most 10 characters"

    def test_length_cmp_gt(self) -> None:
        result = _describe_string_predicate(
            {"kind": "length_cmp", "op": "gt", "value": 3}
        )
        assert result == "the string has more than 3 characters"

    def test_length_cmp_ge(self) -> None:
        result = _describe_string_predicate(
            {"kind": "length_cmp", "op": "ge", "value": 8}
        )
        assert result == "the string has at least 8 characters"

    def test_length_cmp_eq(self) -> None:
        result = _describe_string_predicate(
            {"kind": "length_cmp", "op": "eq", "value": 4}
        )
        assert result == "the string has exactly 4 characters"

    def test_not(self) -> None:
        result = _describe_string_predicate(
            {
                "kind": "not",
                "operand": {"kind": "contains", "substring": "x"},
            }
        )
        assert result == "it is not the case that (the string contains 'x')"

    def test_and(self) -> None:
        result = _describe_string_predicate(
            {
                "kind": "and",
                "operands": [
                    {"kind": "starts_with", "prefix": "a"},
                    {"kind": "is_lower"},
                ],
            }
        )
        assert (
            result
            == "(the string starts with 'a') and (the string is all lowercase)"
        )

    def test_or(self) -> None:
        result = _describe_string_predicate(
            {
                "kind": "or",
                "operands": [
                    {"kind": "ends_with", "suffix": "z"},
                    {"kind": "is_digit"},
                ],
            }
        )
        assert (
            result == "(the string ends with 'z') or "
            "(the string contains only digits)"
        )


class TestDescribeStringTransform:
    def test_identity(self) -> None:
        assert (
            _describe_string_transform({"kind": "identity"})
            == "return it unchanged"
        )

    def test_lowercase(self) -> None:
        assert (
            _describe_string_transform({"kind": "lowercase"})
            == "convert to lowercase"
        )

    def test_uppercase(self) -> None:
        assert (
            _describe_string_transform({"kind": "uppercase"})
            == "convert to uppercase"
        )

    def test_capitalize(self) -> None:
        assert (
            _describe_string_transform({"kind": "capitalize"})
            == "capitalize the first letter"
        )

    def test_swapcase(self) -> None:
        assert (
            _describe_string_transform({"kind": "swapcase"})
            == "swap the case of each letter"
        )

    def test_reverse(self) -> None:
        assert (
            _describe_string_transform({"kind": "reverse"})
            == "reverse the string"
        )

    def test_replace(self) -> None:
        result = _describe_string_transform(
            {"kind": "replace", "old": "a", "new": "b"}
        )
        assert result == "replace 'a' with 'b'"

    def test_strip_whitespace(self) -> None:
        result = _describe_string_transform({"kind": "strip", "chars": None})
        assert result == "strip whitespace"

    def test_strip_chars(self) -> None:
        result = _describe_string_transform({"kind": "strip", "chars": "xy"})
        assert result == "strip 'xy'"

    def test_prepend(self) -> None:
        result = _describe_string_transform(
            {"kind": "prepend", "prefix": "pre_"}
        )
        assert result == "prepend 'pre_'"

    def test_append(self) -> None:
        result = _describe_string_transform(
            {"kind": "append", "suffix": "_end"}
        )
        assert result == "append '_end'"

    def test_pipeline(self) -> None:
        result = _describe_string_transform(
            {
                "kind": "pipeline",
                "steps": [
                    {"kind": "strip", "chars": None},
                    {"kind": "lowercase"},
                    {"kind": "append", "suffix": "!"},
                ],
            }
        )
        assert result == (
            "apply in order: strip whitespace, then convert to lowercase, "
            "then append '!'"
        )


class TestDescribeSimpleAlgorithms:
    def test_most_frequent_smallest(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": 0,
        }
        result = _describe_simple_algorithms(spec)
        assert "most frequently occurring value" in result
        assert "the smallest value" in result
        assert "empty after preprocessing, return 0" in result

    def test_most_frequent_first_seen(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "first_seen",
            "empty_default": -1,
        }
        result = _describe_simple_algorithms(spec)
        assert "the first value seen" in result
        assert "empty after preprocessing, return negative 1" in result

    def test_most_frequent_with_preprocess_and_tie_default(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": -7,
            "pre_filter": {"kind": "gt", "value": 0},
            "pre_transform": {"kind": "shift", "offset": 2},
            "tie_default": 99,
        }
        result = _describe_simple_algorithms(spec)
        assert (
            "keep only elements where the element is greater than 0" in result
        )
        assert (
            "replace each remaining element with the element plus 2" in result
        )
        assert "tie for highest frequency, return 99" in result
        assert "empty after preprocessing, return negative 7" in result

    def test_count_pairs_sum_all_indices(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 10,
            "counting_mode": "all_indices",
        }
        result = _describe_simple_algorithms(spec)
        assert "pairs that sum to 10" in result
        assert "all index pairs (i, j) where i < j" in result

    def test_count_pairs_sum_with_preprocess_and_defaults(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": 10,
            "counting_mode": "unique_values",
            "pre_filter": {"kind": "mod_eq", "divisor": 2, "remainder": 0},
            "pre_transform": {"kind": "abs"},
            "short_list_default": -5,
            "no_result_default": -1,
        }
        result = _describe_simple_algorithms(spec)
        assert "keep only elements where the element mod 2 equals 0" in result
        assert (
            "replace each remaining element with the absolute value of the "
            "element" in result
        )
        assert "unique value pairs only" in result
        assert "fewer than 2 elements remain after preprocessing" in result
        assert "return negative 5" in result
        assert "Otherwise, if no pairs match, return negative 1." in result

    def test_count_pairs_sum_unique_values(self) -> None:
        spec = {
            "template": "count_pairs_sum",
            "target": -5,
            "counting_mode": "unique_values",
        }
        result = _describe_simple_algorithms(spec)
        assert "pairs that sum to negative 5" in result
        assert "unique value pairs only" in result

    def test_max_window_sum(self) -> None:
        spec = {
            "template": "max_window_sum",
            "k": 3,
            "invalid_k_default": 0,
        }
        result = _describe_simple_algorithms(spec)
        assert "maximum sum of any 3 consecutive elements" in result
        assert (
            "fewer than 3 elements remain after preprocessing, return 0"
            in result
        )

    def test_max_window_sum_with_preprocess_and_empty_default(self) -> None:
        spec = {
            "template": "max_window_sum",
            "k": 3,
            "invalid_k_default": -4,
            "pre_filter": {"kind": "even"},
            "pre_transform": {"kind": "negate"},
            "empty_default": 10,
        }
        result = _describe_simple_algorithms(spec)
        assert "keep only elements where the element is even" in result
        assert (
            "replace each remaining element with the negation of the element"
            in result
        )
        assert "If no elements remain after preprocessing, return 10." in result
        assert (
            "Otherwise, if fewer than 3 elements remain after preprocessing, "
            "return negative 4." in result
        )


class TestDescribeStringrules:
    def test_single_rule(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "is_alpha"},
                    "transform": {"kind": "lowercase"},
                },
            ],
            "default_transform": {"kind": "identity"},
        }
        result = _describe_stringrules(spec)
        assert "transform it according to these rules" in result
        assert "contains only letters" in result
        assert "convert to lowercase" in result
        assert "Otherwise, return it unchanged." in result

    def test_multiple_rules(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {"kind": "starts_with", "prefix": "a"},
                    "transform": {"kind": "uppercase"},
                },
                {
                    "predicate": {"kind": "ends_with", "suffix": "z"},
                    "transform": {"kind": "reverse"},
                },
            ],
            "default_transform": {"kind": "capitalize"},
        }
        result = _describe_stringrules(spec)
        assert "starts with 'a'" in result
        assert "convert to uppercase" in result
        assert "ends with 'z'" in result
        assert "reverse the string" in result
        assert "capitalize the first letter" in result

    def test_composed_predicate_and_pipeline_transform(self) -> None:
        spec = {
            "rules": [
                {
                    "predicate": {
                        "kind": "and",
                        "operands": [
                            {"kind": "starts_with", "prefix": "A"},
                            {"kind": "not", "operand": {"kind": "is_lower"}},
                        ],
                    },
                    "transform": {
                        "kind": "pipeline",
                        "steps": [
                            {"kind": "strip", "chars": None},
                            {"kind": "lowercase"},
                        ],
                    },
                }
            ],
            "default_transform": {"kind": "identity"},
        }
        result = _describe_stringrules(spec)
        assert "(the string starts with 'A')" in result
        assert "it is not the case that (the string is all lowercase)" in result
        assert (
            "apply in order: strip whitespace, then convert to lowercase"
            in result
        )


class TestDescribeTask:
    def test_piecewise_family(self) -> None:
        spec = {
            "branches": [],
            "default_expr": {"kind": "affine", "a": 1, "b": 0},
        }
        result = describe_task("piecewise", spec)
        assert "Otherwise, return x." in result

    def test_stateful_family(self) -> None:
        spec = {
            "template": "longest_run",
            "match_predicate": {"kind": "odd"},
        }
        result = describe_task("stateful", spec)
        assert "the element is odd" in result

    def test_simple_algorithms_family(self) -> None:
        spec = {
            "template": "most_frequent",
            "tie_break": "smallest",
            "empty_default": 0,
        }
        result = describe_task("simple_algorithms", spec)
        assert "most frequently occurring value" in result

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
        result = describe_task("stringrules", spec)
        assert "transform it according to these rules" in result

    def test_unknown_family_returns_empty(self) -> None:
        assert describe_task("unknown", {}) == ""

    def test_stack_bytecode_family_is_self_contained(self) -> None:
        spec = {
            "program": [
                {"op": "load_input", "index": 0},
                {"op": "halt"},
            ],
            "input_mode": InputMode.DIRECT,
            "jump_target_mode": JumpTargetMode.ERROR,
            "max_step_count": 90,
        }
        result = describe_task("stack_bytecode", spec)
        assert "Implement f(xs: list[int]) -> tuple[int, int]" in result
        assert "input_mode 'direct'" in result
        assert "jump_target_mode 'error'" in result
        assert "status codes 0=ok, 1=step_limit" in result
        assert "On status 0, value is the top of stack at halt" in result

    def test_fsm_family_is_self_contained(self) -> None:
        spec = {
            "machine_type": MachineType.MOORE,
            "output_mode": OutputMode.ACCEPT_BOOL,
            "undefined_transition_policy": UndefinedTransitionPolicy.SINK,
            "start_state_id": 0,
            "states": [
                {"id": 0, "transitions": [], "is_accept": True},
                {"id": 1, "transitions": [], "is_accept": False},
            ],
        }
        result = describe_task("fsm", spec)
        assert "Implement f(xs: list[int]) -> int" in result
        assert "deterministic moore finite-state machine" in result
        assert "move to sink state (max_state_id + 1)" in result
        assert "Use output_mode 'accept_bool'" in result
        assert "accepting states: 0" in result
