import pytest

from genfxn.core.describe import (
    describe_task,
    _describe_piecewise,
    _describe_stateful,
    _describe_predicate,
    _describe_transform,
    _describe_expression,
    _format_number,
)


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
        result = _describe_predicate({"kind": "mod_eq", "divisor": 3, "remainder": 1}, "element")
        assert result == "the element mod 3 equals 1"

    def test_in_set(self) -> None:
        result = _describe_predicate({"kind": "in_set", "values": [3, 1, 2]}, "x")
        assert result == "the x is in {1, 2, 3}"


class TestDescribeTransform:
    def test_identity(self) -> None:
        assert _describe_transform({"kind": "identity"}) == "the element"

    def test_abs(self) -> None:
        assert _describe_transform({"kind": "abs"}) == "the absolute value of the element"

    def test_negate(self) -> None:
        assert _describe_transform({"kind": "negate"}) == "negative the element"

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
        result = _describe_expression({"kind": "quadratic", "a": 2, "b": 3, "c": 1})
        assert result == "2 times x squared plus 3 times x plus 1"

    def test_quadratic_a_is_one(self) -> None:
        result = _describe_expression({"kind": "quadratic", "a": 1, "b": 0, "c": 0})
        assert result == "x squared"

    def test_quadratic_negative_terms(self) -> None:
        result = _describe_expression({"kind": "quadratic", "a": -1, "b": -2, "c": -3})
        assert result == "negative x squared minus 2 times x minus 3"

    def test_abs_simple(self) -> None:
        result = _describe_expression({"kind": "abs", "a": 2, "b": 1})
        assert result == "2 times the absolute value of x plus 1"

    def test_abs_a_is_one(self) -> None:
        result = _describe_expression({"kind": "abs", "a": 1, "b": 0})
        assert result == "the absolute value of x"

    def test_mod_simple(self) -> None:
        result = _describe_expression({"kind": "mod", "divisor": 7, "a": 1, "b": 0})
        assert result == "x mod 7"

    def test_mod_with_coeff(self) -> None:
        result = _describe_expression({"kind": "mod", "divisor": 3, "a": 2, "b": 5})
        assert result == "2 times x mod 3 plus 5"


class TestDescribePiecewise:
    def test_single_branch(self) -> None:
        spec = {
            "branches": [
                {"condition": {"kind": "lt", "value": 0}, "expr": {"kind": "affine", "a": -1, "b": 0}},
            ],
            "default_expr": {"kind": "affine", "a": 1, "b": 0},
        }
        result = _describe_piecewise(spec)
        assert "When the x is less than 0, return negative x." in result
        assert "Otherwise, return x." in result

    def test_multiple_branches(self) -> None:
        spec = {
            "branches": [
                {"condition": {"kind": "lt", "value": -10}, "expr": {"kind": "affine", "a": 2, "b": 0}},
                {"condition": {"kind": "lt", "value": 10}, "expr": {"kind": "affine", "a": 1, "b": 0}},
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
        assert "add negative the element" in result

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
        assert "Return the best sum" in result


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

    def test_unknown_family_returns_empty(self) -> None:
        assert describe_task("unknown", {}) == ""
