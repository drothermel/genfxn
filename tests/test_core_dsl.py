import random

import pytest

from genfxn.core.codegen import render_tests, task_id_from_spec
from genfxn.core.int32 import INT32_MAX
from genfxn.core.models import Query, QueryTag
from genfxn.core.predicates import (
    PredicateAnd,
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateInSet,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateNot,
    PredicateOdd,
    PredicateOr,
    ThresholdInfo,
    eval_predicate,
    get_threshold,
    render_predicate,
)
from genfxn.core.transforms import (
    TransformAbs,
    TransformClip,
    TransformIdentity,
    TransformNegate,
    TransformPipeline,
    TransformScale,
    TransformShift,
    eval_transform,
    render_transform,
)


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
        with pytest.raises(ValueError, match="divisor must be >= 1"):
            PredicateModEq(divisor=0, remainder=1)

    def test_mod_eq_rejects_negative_remainder(self) -> None:
        with pytest.raises(ValueError, match="remainder must be >= 0"):
            PredicateModEq(divisor=3, remainder=-1)

    def test_mod_eq_rejects_large_remainder(self) -> None:
        with pytest.raises(ValueError, match="remainder must be < divisor"):
            PredicateModEq(divisor=3, remainder=3)

    def test_mod_eq_rejects_divisor_above_int32_max(self) -> None:
        with pytest.raises(
            ValueError,
            match=rf"divisor must be <= {INT32_MAX}",
        ):
            PredicateModEq(divisor=INT32_MAX + 1, remainder=0)

    def test_int32_wrap_mode_wraps_comparison_constants(self) -> None:
        p = PredicateGe(value=3_000_000_005)
        assert eval_predicate(p, 0, int32_wrap=False) is False
        assert eval_predicate(p, 0, int32_wrap=True) is True

    def test_int32_wrap_mode_wraps_input_before_mod_eq(self) -> None:
        p = PredicateModEq(divisor=3, remainder=1)
        x = (1 << 32) + 1
        assert eval_predicate(p, x, int32_wrap=False) is False
        assert eval_predicate(p, x, int32_wrap=True) is True

    def test_in_set(self) -> None:
        p = PredicateInSet(values=frozenset({1, 2, 3}))
        assert eval_predicate(p, 1) is True
        assert eval_predicate(p, 2) is True
        assert eval_predicate(p, 3) is True
        assert eval_predicate(p, 0) is False
        assert eval_predicate(p, 4) is False
        assert render_predicate(p) == "x in {1, 2, 3}"


class TestComposedPredicates:
    def test_not_eval(self) -> None:
        p = PredicateNot(operand=PredicateEven())
        assert eval_predicate(p, 3) is True
        assert eval_predicate(p, 4) is False

    def test_not_render(self) -> None:
        p = PredicateNot(operand=PredicateGt(value=5))
        assert render_predicate(p) == "not (x > 5)"

    def test_and_eval(self) -> None:
        p = PredicateAnd(operands=[PredicateGt(value=0), PredicateEven()])
        assert eval_predicate(p, 4) is True
        assert eval_predicate(p, 3) is False
        assert eval_predicate(p, -2) is False

    def test_and_render(self) -> None:
        p = PredicateAnd(operands=[PredicateGt(value=0), PredicateLt(value=10)])
        assert render_predicate(p) == "(x > 0 and x < 10)"

    def test_or_eval(self) -> None:
        p = PredicateOr(operands=[PredicateEven(), PredicateGt(value=10)])
        assert eval_predicate(p, 4) is True
        assert eval_predicate(p, 11) is True
        assert eval_predicate(p, 3) is False

    def test_or_render(self) -> None:
        p = PredicateOr(operands=[PredicateEven(), PredicateOdd()])
        assert render_predicate(p) == "(x % 2 == 0 or x % 2 == 1)"

    def test_serialization_roundtrip(self) -> None:
        p = PredicateNot(operand=PredicateEven())
        data = p.model_dump()
        assert data == {"kind": "not", "operand": {"kind": "even"}}
        restored = PredicateNot.model_validate(data)
        assert restored == p

    def test_and_serialization(self) -> None:
        p = PredicateAnd(operands=[PredicateGt(value=0), PredicateLt(value=10)])
        data = p.model_dump()
        restored = PredicateAnd.model_validate(data)
        assert restored == p

    def test_and_rejects_one_operand(self) -> None:
        with pytest.raises(ValueError, match="and requires 2-3 operands"):
            PredicateAnd(operands=[PredicateEven()])

    def test_and_rejects_four_operands(self) -> None:
        with pytest.raises(ValueError, match="and requires 2-3 operands"):
            PredicateAnd(
                operands=[
                    PredicateEven(),
                    PredicateOdd(),
                    PredicateGt(value=0),
                    PredicateLt(value=10),
                ]
            )

    def test_or_rejects_one_operand(self) -> None:
        with pytest.raises(ValueError, match="or requires 2-3 operands"):
            PredicateOr(operands=[PredicateEven()])

    def test_get_threshold_returns_none(self) -> None:
        assert get_threshold(PredicateNot(operand=PredicateGt(value=5))) is None
        assert (
            get_threshold(
                PredicateAnd(operands=[PredicateGt(value=0), PredicateEven()])
            )
            is None
        )
        assert (
            get_threshold(
                PredicateOr(operands=[PredicateEven(), PredicateOdd()])
            )
            is None
        )

    def test_three_operand_and(self) -> None:
        p = PredicateAnd(
            operands=[
                PredicateGt(value=0),
                PredicateLt(value=100),
                PredicateEven(),
            ]
        )
        assert eval_predicate(p, 50) is True
        assert eval_predicate(p, 51) is False
        assert eval_predicate(p, -2) is False
        assert render_predicate(p) == "(x > 0 and x < 100 and x % 2 == 0)"


class TestGetThreshold:
    def test_lt_returns_threshold_info(self) -> None:
        p = PredicateLt(value=5)
        info = get_threshold(p)
        assert info is not None
        assert info.kind == "lt"
        assert info.value == 5

    def test_le_returns_threshold_info(self) -> None:
        p = PredicateLe(value=10)
        info = get_threshold(p)
        assert info is not None
        assert info.kind == "le"
        assert info.value == 10

    def test_gt_returns_threshold_info(self) -> None:
        p = PredicateGt(value=-3)
        info = get_threshold(p)
        assert info is not None
        assert info.kind == "gt"
        assert info.value == -3

    def test_ge_returns_threshold_info(self) -> None:
        p = PredicateGe(value=0)
        info = get_threshold(p)
        assert info is not None
        assert info.kind == "ge"
        assert info.value == 0

    def test_even_returns_none(self) -> None:
        p = PredicateEven()
        assert get_threshold(p) is None

    def test_odd_returns_none(self) -> None:
        p = PredicateOdd()
        assert get_threshold(p) is None

    def test_mod_eq_returns_none(self) -> None:
        p = PredicateModEq(divisor=3, remainder=1)
        assert get_threshold(p) is None

    def test_in_set_returns_none(self) -> None:
        p = PredicateInSet(values=frozenset({1, 2, 3}))
        assert get_threshold(p) is None

    def test_threshold_info_is_model(self) -> None:
        info = ThresholdInfo(kind="lt", value=5)
        assert info.kind == "lt"
        assert info.value == 5
        # Can serialize
        data = info.model_dump()
        assert data == {"kind": "lt", "value": 5}


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

    def test_clip_int32_wrap_uses_wrapped_bounds(self) -> None:
        t = TransformClip(low=3_000_000_000, high=3_000_000_100)
        assert eval_transform(t, 0, int32_wrap=True) == -1_294_967_196

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


class TestTransformPipeline:
    def test_pipeline_eval(self) -> None:
        p = TransformPipeline(
            steps=[TransformShift(offset=3), TransformScale(factor=2)]
        )
        assert eval_transform(p, 5) == 16  # (5 + 3) * 2

    def test_pipeline_render(self) -> None:
        p = TransformPipeline(
            steps=[TransformShift(offset=3), TransformScale(factor=2)]
        )
        assert render_transform(p) == "(x + 3) * 2"

    def test_three_step_pipeline(self) -> None:
        p = TransformPipeline(
            steps=[
                TransformAbs(),
                TransformShift(offset=1),
                TransformScale(factor=3),
            ]
        )
        assert eval_transform(p, -5) == 18  # abs(-5)=5, 5+1=6, 6*3=18
        assert render_transform(p) == "((abs(x)) + 1) * 3"

    def test_pipeline_rejects_one_step(self) -> None:
        with pytest.raises(ValueError, match="pipeline requires 2-3 steps"):
            TransformPipeline(steps=[TransformAbs()])

    def test_pipeline_rejects_four_steps(self) -> None:
        with pytest.raises(ValueError, match="pipeline requires 2-3 steps"):
            TransformPipeline(
                steps=[
                    TransformAbs(),
                    TransformShift(offset=1),
                    TransformScale(factor=2),
                    TransformNegate(),
                ]
            )

    def test_serialization_roundtrip(self) -> None:
        p = TransformPipeline(
            steps=[TransformShift(offset=3), TransformScale(factor=2)]
        )
        data = p.model_dump()
        restored = TransformPipeline.model_validate(data)
        assert restored == p


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

    def test_in_set_order_independent(self) -> None:
        spec1 = {
            "predicate": {"kind": "in_set", "values": frozenset({3, 1, 2})}
        }
        spec2 = {
            "predicate": {"kind": "in_set", "values": frozenset({2, 3, 1})}
        }
        id1 = task_id_from_spec("stateful", spec1)
        id2 = task_id_from_spec("stateful", spec2)
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


class TestCorpusIdUniqueness:
    def test_no_cross_family_collisions(self) -> None:
        """IDs from different families never collide.

        Family is part of the hash.
        """
        from genfxn.piecewise.task import generate_piecewise_task
        from genfxn.simple_algorithms.task import (
            generate_simple_algorithms_task,
        )
        from genfxn.stateful.task import generate_stateful_task
        from genfxn.stringrules.task import generate_stringrules_task

        n = 50
        family_ids: dict[str, set[str]] = {}
        generators = {
            "piecewise": generate_piecewise_task,
            "stateful": generate_stateful_task,
            "simple_algorithms": generate_simple_algorithms_task,
            "stringrules": generate_stringrules_task,
        }

        for name, gen_fn in generators.items():
            ids: set[str] = set()
            for i in range(n):
                task = gen_fn(rng=random.Random(i))
                assert task.task_id.startswith(f"{name}_")
                ids.add(task.task_id)
            family_ids[name] = ids

        # No overlap between any two families
        families = list(family_ids.keys())
        for i, f1 in enumerate(families):
            for f2 in families[i + 1 :]:
                overlap = family_ids[f1] & family_ids[f2]
                assert not overlap, (
                    f"Cross-family collision between {f1} and {f2}: {overlap}"
                )

    def test_unique_specs_produce_unique_ids(self) -> None:
        """Distinct specs within a family produce distinct task_ids."""
        from genfxn.piecewise.models import PiecewiseAxes
        from genfxn.piecewise.sampler import sample_piecewise_spec

        rng = random.Random(42)
        specs: list[dict] = []
        ids: list[str] = []
        for _ in range(100):
            spec = sample_piecewise_spec(PiecewiseAxes(), rng)
            spec_dict = spec.model_dump()
            tid = task_id_from_spec("piecewise", spec_dict)
            specs.append(spec_dict)
            ids.append(tid)

        # Every unique spec should map to a unique ID
        unique_specs = {str(sorted(s.items())) for s in specs}
        unique_ids = set(ids)
        assert len(unique_ids) == len(unique_specs), (
            f"Hash collision: {len(unique_specs)} unique specs but "
            f"{len(unique_ids)} unique IDs"
        )
