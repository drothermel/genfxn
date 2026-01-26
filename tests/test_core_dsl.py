import pytest

from genfxn.core.predicates import (
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateInSet,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateOdd,
    eval_predicate,
    render_predicate,
)
from genfxn.core.transforms import (
    TransformAbs,
    TransformClip,
    TransformIdentity,
    TransformNegate,
    TransformScale,
    TransformShift,
    eval_transform,
    render_transform,
)
from genfxn.core.codegen import render_tests, task_id_from_spec
from genfxn.core.models import Query, QueryTag


class TestPredicates:
    def test_even(self) -> None:
        p = PredicateEven()
        assert eval_predicate(p, 0) is True
        assert eval_predicate(p, 2) is True
        assert eval_predicate(p, -4) is True
        assert eval_predicate(p, 1) is False
        assert eval_predicate(p, 3) is False
        assert render_predicate(p) == "x % 2 == 0"
        assert render_predicate(p, "n") == "n % 2 == 0"

    def test_odd(self) -> None:
        p = PredicateOdd()
        assert eval_predicate(p, 1) is True
        assert eval_predicate(p, 3) is True
        assert eval_predicate(p, -3) is True
        assert eval_predicate(p, -7) is True
        assert eval_predicate(p, 0) is False
        assert eval_predicate(p, 2) is False
        assert eval_predicate(p, -4) is False
        assert render_predicate(p) == "x % 2 == 1"

    def test_lt(self) -> None:
        p = PredicateLt(value=5)
        assert eval_predicate(p, 4) is True
        assert eval_predicate(p, 5) is False
        assert eval_predicate(p, 6) is False
        assert render_predicate(p) == "x < 5"

    def test_le(self) -> None:
        p = PredicateLe(value=5)
        assert eval_predicate(p, 4) is True
        assert eval_predicate(p, 5) is True
        assert eval_predicate(p, 6) is False
        assert render_predicate(p) == "x <= 5"

    def test_gt(self) -> None:
        p = PredicateGt(value=5)
        assert eval_predicate(p, 6) is True
        assert eval_predicate(p, 5) is False
        assert eval_predicate(p, 4) is False
        assert render_predicate(p) == "x > 5"

    def test_ge(self) -> None:
        p = PredicateGe(value=5)
        assert eval_predicate(p, 6) is True
        assert eval_predicate(p, 5) is True
        assert eval_predicate(p, 4) is False
        assert render_predicate(p) == "x >= 5"

    def test_mod_eq(self) -> None:
        p = PredicateModEq(divisor=3, remainder=1)
        assert eval_predicate(p, 1) is True
        assert eval_predicate(p, 4) is True
        assert eval_predicate(p, 7) is True
        assert eval_predicate(p, 0) is False
        assert eval_predicate(p, 2) is False
        assert render_predicate(p) == "x % 3 == 1"

    def test_mod_eq_rejects_zero_divisor(self) -> None:
        with pytest.raises(ValueError, match="divisor must be non-zero"):
            PredicateModEq(divisor=0, remainder=1)

    def test_in_set(self) -> None:
        p = PredicateInSet(values=frozenset({1, 2, 3}))
        assert eval_predicate(p, 1) is True
        assert eval_predicate(p, 2) is True
        assert eval_predicate(p, 3) is True
        assert eval_predicate(p, 0) is False
        assert eval_predicate(p, 4) is False
        assert render_predicate(p) == "x in {1, 2, 3}"


class TestTransforms:
    def test_identity(self) -> None:
        t = TransformIdentity()
        assert eval_transform(t, 5) == 5
        assert eval_transform(t, -3) == -3
        assert render_transform(t) == "x"
        assert render_transform(t, "val") == "val"

    def test_abs(self) -> None:
        t = TransformAbs()
        assert eval_transform(t, 5) == 5
        assert eval_transform(t, -5) == 5
        assert eval_transform(t, 0) == 0
        assert render_transform(t) == "abs(x)"

    def test_shift_positive(self) -> None:
        t = TransformShift(offset=3)
        assert eval_transform(t, 5) == 8
        assert eval_transform(t, -5) == -2
        assert render_transform(t) == "x + 3"

    def test_shift_negative(self) -> None:
        t = TransformShift(offset=-3)
        assert eval_transform(t, 5) == 2
        assert eval_transform(t, -5) == -8
        assert render_transform(t) == "x - 3"

    def test_clip(self) -> None:
        t = TransformClip(low=0, high=10)
        assert eval_transform(t, 5) == 5
        assert eval_transform(t, -5) == 0
        assert eval_transform(t, 15) == 10
        assert eval_transform(t, 0) == 0
        assert eval_transform(t, 10) == 10
        assert render_transform(t) == "max(0, min(10, x))"

    def test_clip_rejects_invalid_bounds(self) -> None:
        with pytest.raises(ValueError, match="low .* must be <= high"):
            TransformClip(low=10, high=0)

    def test_negate(self) -> None:
        t = TransformNegate()
        assert eval_transform(t, 5) == -5
        assert eval_transform(t, -5) == 5
        assert eval_transform(t, 0) == 0
        assert render_transform(t) == "-x"

    def test_scale(self) -> None:
        t = TransformScale(factor=3)
        assert eval_transform(t, 5) == 15
        assert eval_transform(t, -2) == -6
        assert eval_transform(t, 0) == 0
        assert render_transform(t) == "x * 3"


class TestTaskId:
    def test_deterministic(self) -> None:
        spec = {"n_branches": 2, "expr_types": ["affine"]}
        id1 = task_id_from_spec("piecewise", spec)
        id2 = task_id_from_spec("piecewise", spec)
        assert id1 == id2
        assert id1.startswith("piecewise_")

    def test_different_specs(self) -> None:
        spec1 = {"n_branches": 2, "expr_types": ["affine"]}
        spec2 = {"n_branches": 3, "expr_types": ["affine"]}
        id1 = task_id_from_spec("piecewise", spec1)
        id2 = task_id_from_spec("piecewise", spec2)
        assert id1 != id2

    def test_different_families(self) -> None:
        spec = {"key": "value"}
        id1 = task_id_from_spec("piecewise", spec)
        id2 = task_id_from_spec("stateful", spec)
        assert id1 != id2
        assert id1.startswith("piecewise_")
        assert id2.startswith("stateful_")

    def test_order_independent(self) -> None:
        spec1 = {"a": 1, "b": 2}
        spec2 = {"b": 2, "a": 1}
        id1 = task_id_from_spec("test", spec1)
        id2 = task_id_from_spec("test", spec2)
        assert id1 == id2


class TestRenderTests:
    def test_render_tests(self) -> None:
        queries = [
            Query(input=5, output=10, tag=QueryTag.TYPICAL),
            Query(input=-3, output=3, tag=QueryTag.BOUNDARY),
        ]
        result = render_tests("my_func", queries)
        assert "assert my_func(5) == 10" in result
        assert "assert my_func(-3) == 3" in result
        assert "query 0 (typical)" in result
        assert "query 1 (boundary)" in result

    def test_render_tests_empty(self) -> None:
        result = render_tests("f", [])
        assert result == ""
