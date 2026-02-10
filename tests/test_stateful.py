import random

import pytest
from pydantic import ValidationError

from genfxn.core.models import QueryTag
from genfxn.core.predicates import (
    PredicateEven,
    PredicateGt,
    PredicateLt,
    PredicateModEq,
    PredicateOdd,
    PredicateType,
    eval_predicate,
)
from genfxn.core.transforms import (
    TransformAbs,
    TransformIdentity,
    TransformNegate,
    TransformScale,
    TransformShift,
    TransformType,
)
from genfxn.stateful.eval import (
    eval_conditional_linear_sum,
    eval_longest_run,
    eval_resetting_best_prefix_sum,
    eval_stateful,
    eval_toggle_sum,
)
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulAxes,
    TemplateType,
    ToggleSumSpec,
)
from genfxn.stateful.queries import generate_stateful_queries
from genfxn.stateful.render import render_stateful
from genfxn.stateful.sampler import sample_predicate, sample_stateful_spec
from genfxn.stateful.task import generate_stateful_task

INT32_MAX = (1 << 31) - 1
INT64_MAX = (1 << 63) - 1


class TestConditionalLinearSumEval:
    def test_basic_even_odd(self) -> None:
        spec = ConditionalLinearSumSpec(
            predicate=PredicateEven(),
            true_transform=TransformIdentity(),
            false_transform=TransformNegate(),
            init_value=0,
        )
        # Even values get added as-is, odd values get negated
        assert eval_conditional_linear_sum(spec, []) == 0
        assert eval_conditional_linear_sum(spec, [2]) == 2
        assert eval_conditional_linear_sum(spec, [3]) == -3
        assert eval_conditional_linear_sum(spec, [2, 3, 4]) == 2 - 3 + 4

    def test_with_init_value(self) -> None:
        spec = ConditionalLinearSumSpec(
            predicate=PredicateEven(),
            true_transform=TransformIdentity(),
            false_transform=TransformIdentity(),
            init_value=10,
        )
        assert eval_conditional_linear_sum(spec, []) == 10
        assert eval_conditional_linear_sum(spec, [1, 2, 3]) == 10 + 1 + 2 + 3

    def test_with_transforms(self) -> None:
        spec = ConditionalLinearSumSpec(
            predicate=PredicateLt(value=0),
            true_transform=TransformAbs(),
            false_transform=TransformScale(factor=2),
            init_value=0,
        )
        # Negative values: abs(x), non-negative: 2*x
        assert (
            eval_conditional_linear_sum(spec, [-5, 3, -2, 4]) == 5 + 6 + 2 + 8
        )


class TestResettingBestPrefixSumEval:
    def test_basic(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
        )
        # Negative values reset the sum
        assert eval_resetting_best_prefix_sum(spec, []) == 0
        assert eval_resetting_best_prefix_sum(spec, [1, 2, 3]) == 6
        assert eval_resetting_best_prefix_sum(spec, [1, 2, -1, 3]) == 3
        assert eval_resetting_best_prefix_sum(spec, [5, 4, -1, 3, 2]) == 9

    def test_with_init_value(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=5,
        )
        assert eval_resetting_best_prefix_sum(spec, []) == 5
        assert eval_resetting_best_prefix_sum(spec, [1, 2]) == 5 + 1 + 2

    def test_all_reset(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
        )
        assert eval_resetting_best_prefix_sum(spec, [-1, -2, -3]) == 0


class TestLongestRunEval:
    def test_basic(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateGt(value=0))
        assert eval_longest_run(spec, []) == 0
        assert eval_longest_run(spec, [1]) == 1
        assert eval_longest_run(spec, [0]) == 0
        assert eval_longest_run(spec, [1, 2, 3]) == 3
        assert eval_longest_run(spec, [1, 0, 2, 3]) == 2
        assert eval_longest_run(spec, [1, 2, 0, 3, 4, 5]) == 3

    def test_all_matching(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateEven())
        assert eval_longest_run(spec, [2, 4, 6, 8]) == 4

    def test_all_non_matching(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateEven())
        assert eval_longest_run(spec, [1, 3, 5, 7]) == 0

    def test_alternating(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateOdd())
        assert eval_longest_run(spec, [1, 2, 3, 4, 5]) == 1


class TestEvaluatorInputValidation:
    def test_eval_stateful_rejects_bool_values(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateGt(value=0))
        with pytest.raises(ValueError, match=r"xs\[0\] must be int, got bool"):
            eval_stateful(spec, [True, 1])

    @pytest.mark.parametrize(
        ("evaluator", "spec"),
        [
            (
                eval_conditional_linear_sum,
                ConditionalLinearSumSpec(
                    predicate=PredicateEven(),
                    true_transform=TransformIdentity(),
                    false_transform=TransformIdentity(),
                    init_value=0,
                ),
            ),
            (
                eval_resetting_best_prefix_sum,
                ResettingBestPrefixSumSpec(
                    reset_predicate=PredicateLt(value=0),
                    init_value=0,
                ),
            ),
            (
                eval_longest_run,
                LongestRunSpec(match_predicate=PredicateGt(value=0)),
            ),
            (
                eval_toggle_sum,
                ToggleSumSpec(
                    toggle_predicate=PredicateEven(),
                    on_transform=TransformIdentity(),
                    off_transform=TransformIdentity(),
                    init_value=0,
                ),
            ),
        ],
    )
    def test_direct_evaluators_reject_bool_values(
        self, evaluator, spec
    ) -> None:
        with pytest.raises(ValueError, match=r"xs\[1\] must be int, got bool"):
            evaluator(spec, [1, False])


class TestEmptyListHandling:
    def test_conditional_linear_sum_empty(self) -> None:
        spec = ConditionalLinearSumSpec(
            predicate=PredicateEven(),
            true_transform=TransformIdentity(),
            false_transform=TransformIdentity(),
            init_value=42,
        )
        assert eval_stateful(spec, []) == 42

    def test_resetting_best_prefix_sum_empty(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=7,
        )
        assert eval_stateful(spec, []) == 7

    def test_longest_run_empty(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateGt(value=0))
        assert eval_stateful(spec, []) == 0


class TestQueryGeneration:
    def test_generates_queries(self) -> None:
        spec = ConditionalLinearSumSpec(
            predicate=PredicateEven(),
            true_transform=TransformIdentity(),
            false_transform=TransformNegate(),
            init_value=0,
        )
        axes = StatefulAxes()
        queries = generate_stateful_queries(spec, axes, random.Random(42))
        assert len(queries) > 0

    def test_all_queries_valid(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateGt(value=5))
        axes = StatefulAxes()
        queries = generate_stateful_queries(spec, axes, random.Random(42))
        for q in queries:
            assert q.output == eval_stateful(spec, q.input)

    def test_coverage_includes_empty(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
        )
        axes = StatefulAxes()
        queries = generate_stateful_queries(spec, axes, random.Random(42))
        inputs = [q.input for q in queries]
        assert [] in inputs

    def test_unsatisfiable_predicate_skips_boundary_queries(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateLt(value=-100))
        axes = StatefulAxes(value_range=(0, 10))
        queries = generate_stateful_queries(spec, axes, random.Random(42))
        assert not any(q.tag == QueryTag.BOUNDARY for q in queries)

    def test_boundary_and_adversarial_queries_respect_small_length_range(
        self,
    ) -> None:
        spec = LongestRunSpec(match_predicate=PredicateEven())
        axes = StatefulAxes(list_length_range=(1, 3), value_range=(0, 10))
        queries = generate_stateful_queries(spec, axes, random.Random(42))
        lo, hi = axes.list_length_range
        constrained = [
            q
            for q in queries
            if q.tag in (QueryTag.BOUNDARY, QueryTag.ADVERSARIAL)
        ]
        assert constrained
        assert all(lo <= len(q.input) <= hi for q in constrained)

    def test_mod_eq_boundary_uses_wrapped_predicate_truth(self) -> None:
        pred = PredicateModEq(divisor=5, remainder=3)
        spec = LongestRunSpec(match_predicate=pred)
        axes = StatefulAxes(
            value_range=(2_147_483_648, 2_147_483_660),
            list_length_range=(5, 5),
        )

        queries = generate_stateful_queries(spec, axes, random.Random(0))
        boundary_values = [
            x for q in queries if q.tag == QueryTag.BOUNDARY for x in q.input
        ]
        assert boundary_values

        truths = [
            eval_predicate(pred, x, int32_wrap=True) for x in boundary_values
        ]
        assert any(truths)
        assert not all(truths)


class TestRender:
    def test_render_conditional_linear_sum(self) -> None:
        spec = ConditionalLinearSumSpec(
            predicate=PredicateEven(),
            true_transform=TransformIdentity(),
            false_transform=TransformAbs(),
            init_value=0,
        )
        code = render_stateful(spec)
        assert "def f(xs: list[int]) -> int:" in code
        assert "__i32_wrap(x) % 2 == 0" in code
        assert "__i32_add(" in code

    def test_render_resetting_best_prefix_sum(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
        )
        code = render_stateful(spec)
        assert "current_sum" in code
        assert "best_sum" in code
        assert "__i32_wrap(x) < __i32_wrap(0)" in code

    def test_render_longest_run(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateGt(value=0))
        code = render_stateful(spec)
        assert "current_run" in code
        assert "longest_run" in code
        assert "__i32_wrap(x) > __i32_wrap(0)" in code

    def test_render_roundtrip_conditional_linear_sum(self) -> None:
        spec = ConditionalLinearSumSpec(
            predicate=PredicateEven(),
            true_transform=TransformShift(offset=1),
            false_transform=TransformScale(factor=2),
            init_value=5,
        )
        code = render_stateful(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = [[], [1], [2], [1, 2, 3, 4, 5]]
        for xs in test_inputs:
            assert f(xs) == eval_stateful(spec, xs), f"Mismatch at xs={xs}"

    def test_render_roundtrip_resetting_best_prefix_sum(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
        )
        code = render_stateful(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = [
            [],
            [1, 2, 3],
            [1, -1, 2, 3],
            [-1, -2, -3],
            [5, 4, -1, 3, 2],
        ]
        for xs in test_inputs:
            assert f(xs) == eval_stateful(spec, xs), f"Mismatch at xs={xs}"

    def test_render_roundtrip_longest_run(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateOdd())
        code = render_stateful(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = [[], [1], [2], [1, 3, 5], [1, 2, 3, 4, 5], [2, 4, 6]]
        for xs in test_inputs:
            assert f(xs) == eval_stateful(spec, xs), f"Mismatch at xs={xs}"

    def test_render_roundtrip_int32_large_values(self) -> None:
        spec = ConditionalLinearSumSpec(
            predicate=PredicateLt(value=0),
            true_transform=TransformIdentity(),
            false_transform=TransformIdentity(),
            init_value=0,
        )
        code = render_stateful(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        xs = [2_000_000_000, 2_000_000_000]
        assert f(xs) == eval_stateful(spec, xs)


class TestSampler:
    def test_reproducible(self) -> None:
        axes = StatefulAxes(templates=[TemplateType.CONDITIONAL_LINEAR_SUM])
        spec1 = sample_stateful_spec(axes, random.Random(42))
        spec2 = sample_stateful_spec(axes, random.Random(42))
        assert spec1 == spec2

    def test_respects_template_filter(self) -> None:
        for template in TemplateType:
            axes = StatefulAxes(templates=[template])
            spec = sample_stateful_spec(axes, random.Random(42))
            assert spec.template == template.value


class TestAxesValidation:
    def test_invalid_value_range(self) -> None:
        with pytest.raises(ValueError, match="value_range"):
            StatefulAxes(value_range=(100, -100))

    def test_invalid_list_length_range(self) -> None:
        with pytest.raises(ValueError, match="list_length_range"):
            StatefulAxes(list_length_range=(20, 5))

    def test_negative_list_length(self) -> None:
        with pytest.raises(ValueError, match=r"list_length_range.*>= 0"):
            StatefulAxes(list_length_range=(-1, 10))

    def test_empty_templates(self) -> None:
        with pytest.raises(ValueError, match="templates must not be empty"):
            StatefulAxes(templates=[])

    def test_empty_predicate_types(self) -> None:
        with pytest.raises(
            ValueError, match="predicate_types must not be empty"
        ):
            StatefulAxes(predicate_types=[])

    def test_empty_transform_types(self) -> None:
        with pytest.raises(
            ValueError, match="transform_types must not be empty"
        ):
            StatefulAxes(transform_types=[])

    def test_zero_divisor(self) -> None:
        with pytest.raises(ValueError, match=r"divisor_range.*>= 1"):
            StatefulAxes(divisor_range=(0, 5))

    def test_negative_divisor(self) -> None:
        with pytest.raises(ValueError, match=r"divisor_range.*>= 1"):
            StatefulAxes(divisor_range=(-1, 5))

    def test_divisor_range_high_must_fit_int32(self) -> None:
        with pytest.raises(
            ValueError,
            match=rf"divisor_range: high .* must be <= {INT32_MAX}",
        ):
            StatefulAxes(divisor_range=(2, INT32_MAX + 1))

    def test_threshold_range_rejects_values_above_signed_i64(self) -> None:
        with pytest.raises(
            ValueError,
            match=rf"threshold_range: high .* must be <= {INT64_MAX}",
        ):
            StatefulAxes(threshold_range=(0, INT64_MAX + 1))

    @pytest.mark.parametrize(
        ("field_name", "range_value"),
        [
            ("value_range", (False, 5)),
            ("list_length_range", (1, True)),
            ("threshold_range", (True, 5)),
            ("divisor_range", (2, True)),
            ("shift_range", (False, 5)),
            ("scale_range", (1, False)),
        ],
    )
    def test_rejects_bool_in_int_range_bounds(
        self, field_name: str, range_value: tuple[int | bool, int | bool]
    ) -> None:
        with pytest.raises(
            ValidationError,
            match=rf"{field_name}: bool is not allowed for int range bounds",
        ):
            StatefulAxes.model_validate({field_name: range_value})

    def test_conditional_linear_sum_rejects_init_value_above_signed_i64(
        self,
    ) -> None:
        with pytest.raises(ValueError, match="9223372036854775807"):
            ConditionalLinearSumSpec(
                predicate=PredicateEven(),
                true_transform=TransformIdentity(),
                false_transform=TransformIdentity(),
                init_value=INT64_MAX + 1,
            )

    def test_min_composed_operands_rejected_for_and_or(self) -> None:
        with pytest.raises(ValueError, match=r"min_composed_operands.*<= 3"):
            StatefulAxes(
                predicate_types=[PredicateType.AND],
                min_composed_operands=4,
            )

    def test_min_composed_operands_allowed_when_not_used(self) -> None:
        axes = StatefulAxes(
            predicate_types=[PredicateType.EVEN],
            min_composed_operands=5,
        )
        assert axes.min_composed_operands == 5


class TestSamplerGuards:
    def test_and_rejects_unsupported_min_operands(self) -> None:
        with pytest.raises(ValueError, match=r"AND requires min_operands <= 3"):
            sample_predicate(
                PredicateType.AND,
                threshold_range=(-5, 5),
                divisor_range=(2, 5),
                rng=random.Random(42),
                min_operands=4,
            )

    def test_or_rejects_unsupported_min_operands(self) -> None:
        with pytest.raises(ValueError, match=r"OR requires min_operands <= 3"):
            sample_predicate(
                PredicateType.OR,
                threshold_range=(-5, 5),
                divisor_range=(2, 5),
                rng=random.Random(42),
                min_operands=4,
            )


class TestTaskGeneration:
    def test_full_pipeline(self) -> None:
        axes = StatefulAxes(
            templates=[TemplateType.CONDITIONAL_LINEAR_SUM],
            predicate_types=[PredicateType.EVEN],
            transform_types=[TransformType.IDENTITY],
        )
        task = generate_stateful_task(axes, random.Random(42))
        assert task.family == "stateful"
        assert task.task_id.startswith("stateful_")
        assert len(task.queries) > 0

        assert isinstance(task.code, str)
        namespace: dict = {}
        exec(task.code, namespace)  # noqa: S102
        f = namespace["f"]
        for q in task.queries:
            assert f(q.input) == q.output

    def test_each_template(self) -> None:
        for template in TemplateType:
            axes = StatefulAxes(templates=[template])
            task = generate_stateful_task(axes, random.Random(42))
            assert task.spec["template"] == template.value

            assert isinstance(task.code, str)
            namespace: dict = {}
            exec(task.code, namespace)  # noqa: S102
            f = namespace["f"]
            for q in task.queries:
                assert f(q.input) == q.output, f"Template {template}: mismatch"


class TestToggleSumEval:
    def test_basic(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateLt(value=0),
            on_transform=TransformIdentity(),
            off_transform=TransformNegate(),
            init_value=0,
        )
        # Start off: x=1, 1<0? No, off -> acc += -1 = -1
        # x=-1, -1<0? Yes, toggle on -> acc += -1 = -2
        # x=2, 2<0? No, on -> acc += 2 = 0
        # x=-3, -3<0? Yes, toggle off -> acc += 3 = 3
        # x=4, 4<0? No, off -> acc += -4 = -1
        assert eval_toggle_sum(spec, [1, -1, 2, -3, 4]) == -1

    def test_empty_list(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateEven(),
            on_transform=TransformIdentity(),
            off_transform=TransformIdentity(),
            init_value=10,
        )
        assert eval_toggle_sum(spec, []) == 10

    def test_always_off(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateLt(value=-999),
            on_transform=TransformIdentity(),
            off_transform=TransformNegate(),
            init_value=0,
        )
        # Never toggles, stays off -> all negated
        assert eval_toggle_sum(spec, [1, 2, 3]) == -6

    def test_init_value(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateLt(value=-999),
            on_transform=TransformIdentity(),
            off_transform=TransformIdentity(),
            init_value=100,
        )
        assert eval_toggle_sum(spec, [1, 2, 3]) == 106

    def test_with_transforms(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateEven(),
            on_transform=TransformScale(factor=2),
            off_transform=TransformShift(offset=10),
            init_value=0,
        )
        # Start off:
        # x=1 (off): acc += 1+10 = 11
        # x=2 (toggle on): acc += 2*2 = 15
        # x=3 (on): acc += 3*2 = 21
        # x=4 (toggle off): acc += 4+10 = 35
        assert eval_toggle_sum(spec, [1, 2, 3, 4]) == 35

    def test_via_dispatcher(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateEven(),
            on_transform=TransformIdentity(),
            off_transform=TransformNegate(),
            init_value=0,
        )
        assert eval_stateful(spec, [2, 3]) == eval_toggle_sum(spec, [2, 3])


class TestResettingValueTransform:
    def test_with_value_transform(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
            value_transform=TransformScale(factor=2),
        )
        # x=1: current_sum += 2*1 = 2, best=2
        # x=2: current_sum += 2*2 = 6, best=6
        # x=-1: reset, best stays 6
        # x=3: current_sum += 2*3 = 6, best=6
        assert eval_resetting_best_prefix_sum(spec, [1, 2, -1, 3]) == 6

    def test_value_transform_none(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
            value_transform=None,
        )
        # Without value_transform, same as original behavior
        assert eval_resetting_best_prefix_sum(spec, [1, 2, -1, 3]) == 3


class TestToggleSumRender:
    def test_render_toggle_sum(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateEven(),
            on_transform=TransformIdentity(),
            off_transform=TransformNegate(),
            init_value=0,
        )
        code = render_stateful(spec)
        assert "on = False" in code
        assert "on = not on" in code
        assert "acc" in code

    def test_render_roundtrip(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateGt(value=5),
            on_transform=TransformShift(offset=1),
            off_transform=TransformScale(factor=2),
            init_value=3,
        )
        code = render_stateful(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = [[], [1], [6], [1, 6, 2, 8, 3]]
        for xs in test_inputs:
            assert f(xs) == eval_stateful(spec, xs), f"Mismatch at xs={xs}"


class TestResettingValueTransformRender:
    def test_render_with_value_transform(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
            value_transform=TransformScale(factor=2),
        )
        code = render_stateful(spec)
        assert "__i32_mul(x, 2)" in code or "__i32_mul(2, x)" in code

    def test_render_roundtrip(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
            value_transform=TransformShift(offset=3),
        )
        code = render_stateful(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = [[], [1, 2, 3], [1, -1, 2, 3], [-1, -2, -3]]
        for xs in test_inputs:
            assert f(xs) == eval_stateful(spec, xs), f"Mismatch at xs={xs}"


class TestToggleSumQueries:
    def test_generates_queries(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateEven(),
            on_transform=TransformIdentity(),
            off_transform=TransformNegate(),
            init_value=0,
        )
        axes = StatefulAxes(templates=[TemplateType.TOGGLE_SUM])
        queries = generate_stateful_queries(spec, axes, random.Random(42))
        assert len(queries) > 0

    def test_all_queries_valid(self) -> None:
        spec = ToggleSumSpec(
            toggle_predicate=PredicateGt(value=0),
            on_transform=TransformShift(offset=1),
            off_transform=TransformScale(factor=-1),
            init_value=5,
        )
        axes = StatefulAxes(templates=[TemplateType.TOGGLE_SUM])
        queries = generate_stateful_queries(spec, axes, random.Random(42))
        for q in queries:
            assert q.output == eval_stateful(spec, q.input)
