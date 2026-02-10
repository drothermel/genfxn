import random

import pytest

from genfxn.core.int32 import INT32_MAX
from genfxn.core.predicates import PredicateLe, PredicateLt
from genfxn.piecewise.eval import eval_expression, eval_piecewise
from genfxn.piecewise.models import (
    Branch,
    ExprAbs,
    ExprAffine,
    ExprMod,
    ExprQuadratic,
    ExprType,
    PiecewiseAxes,
    PiecewiseSpec,
)
from genfxn.piecewise.queries import generate_piecewise_queries
from genfxn.piecewise.render import render_expression, render_piecewise
from genfxn.piecewise.sampler import sample_piecewise_spec
from genfxn.piecewise.task import generate_piecewise_task


class TestExpressionEval:
    def test_affine(self) -> None:
        expr = ExprAffine(a=2, b=3)
        assert eval_expression(expr, 5) == 13
        assert eval_expression(expr, 0) == 3
        assert eval_expression(expr, -2) == -1

    def test_quadratic(self) -> None:
        expr = ExprQuadratic(a=1, b=-2, c=1)
        assert eval_expression(expr, 0) == 1
        assert eval_expression(expr, 1) == 0
        assert eval_expression(expr, 2) == 1
        assert eval_expression(expr, 3) == 4

    def test_abs(self) -> None:
        expr = ExprAbs(a=2, b=1)
        assert eval_expression(expr, 5) == 11
        assert eval_expression(expr, -5) == 11
        assert eval_expression(expr, 0) == 1

    def test_mod(self) -> None:
        expr = ExprMod(divisor=3, a=2, b=1)
        assert eval_expression(expr, 0) == 1
        assert eval_expression(expr, 1) == 3
        assert eval_expression(expr, 3) == 1
        assert eval_expression(expr, 7) == 3

    def test_mod_rejects_divisor_above_int32_max(self) -> None:
        with pytest.raises(ValueError):
            ExprMod(divisor=INT32_MAX + 1, a=1, b=0)


class TestBranchSelection:
    def test_single_branch_lt(self) -> None:
        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateLt(value=5), expr=ExprAffine(a=1, b=0)
                )
            ],
            default_expr=ExprAffine(a=0, b=10),
        )
        assert eval_piecewise(spec, 4) == 4
        assert eval_piecewise(spec, 5) == 10
        assert eval_piecewise(spec, 6) == 10

    def test_single_branch_le(self) -> None:
        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateLe(value=5), expr=ExprAffine(a=1, b=0)
                )
            ],
            default_expr=ExprAffine(a=0, b=10),
        )
        assert eval_piecewise(spec, 4) == 4
        assert eval_piecewise(spec, 5) == 5
        assert eval_piecewise(spec, 6) == 10

    def test_multiple_branches(self) -> None:
        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateLt(value=0), expr=ExprAffine(a=0, b=-1)
                ),
                Branch(
                    condition=PredicateLt(value=10), expr=ExprAffine(a=1, b=0)
                ),
            ],
            default_expr=ExprAffine(a=0, b=100),
        )
        assert eval_piecewise(spec, -5) == -1
        assert eval_piecewise(spec, 0) == 0
        assert eval_piecewise(spec, 5) == 5
        assert eval_piecewise(spec, 10) == 100


class TestQueryGeneration:
    def test_generates_queries(self) -> None:
        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateLt(value=0), expr=ExprAffine(a=1, b=0)
                )
            ],
            default_expr=ExprAffine(a=2, b=0),
        )
        queries = generate_piecewise_queries(spec, (-10, 10), random.Random(42))
        assert len(queries) > 0

    def test_all_queries_valid(self) -> None:
        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateLt(value=0), expr=ExprAffine(a=1, b=0)
                )
            ],
            default_expr=ExprAffine(a=2, b=0),
        )
        queries = generate_piecewise_queries(spec, (-10, 10), random.Random(42))
        for q in queries:
            assert q.output == eval_piecewise(spec, q.input)


class TestRender:
    def test_render_affine(self) -> None:
        assert render_expression(ExprAffine(a=2, b=3)) == "2 * x + 3"
        assert render_expression(ExprAffine(a=1, b=0)) == "x"
        assert render_expression(ExprAffine(a=0, b=5)) == "5"
        assert render_expression(ExprAffine(a=-1, b=0)) == "-x"
        assert render_expression(ExprAffine(a=2, b=-3)) == "2 * x - 3"

    def test_render_quadratic(self) -> None:
        assert render_expression(ExprQuadratic(a=1, b=0, c=0)) == "x * x"
        assert (
            render_expression(ExprQuadratic(a=2, b=3, c=4))
            == "2 * x * x + 3 * x + 4"
        )

    def test_render_abs(self) -> None:
        assert render_expression(ExprAbs(a=2, b=3)) == "2 * abs(x) + 3"
        assert render_expression(ExprAbs(a=1, b=0)) == "abs(x)"
        assert render_expression(ExprAbs(a=0, b=5)) == "5"
        assert render_expression(ExprAbs(a=-1, b=0)) == "-abs(x)"
        assert render_expression(ExprAbs(a=2, b=-3)) == "2 * abs(x) - 3"

    def test_render_mod(self) -> None:
        assert (
            render_expression(ExprMod(divisor=3, a=2, b=1)) == "2 * (x % 3) + 1"
        )
        assert render_expression(ExprMod(divisor=5, a=1, b=0)) == "(x % 5)"
        assert render_expression(ExprMod(divisor=7, a=0, b=4)) == "4"
        assert render_expression(ExprMod(divisor=2, a=-1, b=0)) == "-(x % 2)"
        assert (
            render_expression(ExprMod(divisor=3, a=2, b=-1))
            == "2 * (x % 3) - 1"
        )

    def test_render_roundtrip(self) -> None:
        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateLt(value=0), expr=ExprAffine(a=2, b=1)
                ),
                Branch(
                    condition=PredicateLt(value=10),
                    expr=ExprQuadratic(a=1, b=0, c=0),
                ),
            ],
            default_expr=ExprAffine(a=0, b=50),
        )
        code = render_piecewise(spec, func_name="f")
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        for x in range(-20, 30):
            assert f(x) == eval_piecewise(spec, x), f"Mismatch at x={x}"


class TestSampler:
    def test_reproducible(self) -> None:
        axes = PiecewiseAxes(n_branches=2, expr_types=[ExprType.AFFINE])
        spec1 = sample_piecewise_spec(axes, random.Random(42))
        spec2 = sample_piecewise_spec(axes, random.Random(42))
        assert spec1 == spec2

    def test_respects_n_branches(self) -> None:
        for n in [1, 2, 3]:
            axes = PiecewiseAxes(n_branches=n, expr_types=[ExprType.AFFINE])
            spec = sample_piecewise_spec(axes, random.Random(42))
            assert len(spec.branches) == n


class TestAxesValidation:
    def test_invalid_value_range(self) -> None:
        with pytest.raises(ValueError, match="value_range"):
            PiecewiseAxes(value_range=(100, -100))

    def test_invalid_coeff_range(self) -> None:
        with pytest.raises(ValueError, match="coeff_range"):
            PiecewiseAxes(coeff_range=(5, -5))

    def test_invalid_threshold_range(self) -> None:
        with pytest.raises(ValueError, match="threshold_range"):
            PiecewiseAxes(threshold_range=(50, -50))

    def test_invalid_divisor_range(self) -> None:
        with pytest.raises(ValueError, match="divisor_range"):
            PiecewiseAxes(divisor_range=(10, 2))

    def test_divisor_range_low_must_be_positive(self) -> None:
        with pytest.raises(ValueError, match=r"divisor_range: low .*>= 1"):
            PiecewiseAxes(divisor_range=(0, 10))

    def test_divisor_range_high_must_fit_int32(self) -> None:
        with pytest.raises(
            ValueError,
            match=rf"divisor_range: high .*<= {INT32_MAX}",
        ):
            PiecewiseAxes(divisor_range=(2, INT32_MAX + 1))

    def test_n_branches_exceeds_threshold_range(self) -> None:
        with pytest.raises(
            ValueError, match=r"n_branches.*exceeds available thresholds"
        ):
            PiecewiseAxes(n_branches=3, threshold_range=(0, 1))

    def test_empty_expr_types(self) -> None:
        with pytest.raises(ValueError, match="expr_types must not be empty"):
            PiecewiseAxes(expr_types=[])


class TestTaskGeneration:
    def test_full_pipeline(self) -> None:
        axes = PiecewiseAxes(
            n_branches=2, expr_types=[ExprType.AFFINE, ExprType.QUADRATIC]
        )
        task = generate_piecewise_task(axes, random.Random(42))
        assert task.family == "piecewise"
        assert task.task_id.startswith("piecewise_")
        assert len(task.queries) > 0

        assert isinstance(task.code, str)
        namespace: dict = {}
        exec(task.code, namespace)  # noqa: S102
        f = namespace["f"]
        for q in task.queries:
            assert f(q.input) == q.output
