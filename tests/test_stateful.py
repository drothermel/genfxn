import random

import pytest

from genfxn.core.predicates import (
    PredicateEven,
    PredicateGt,
    PredicateLt,
    PredicateOdd,
    PredicateType,
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
)
from genfxn.stateful.models import (
    ConditionalLinearSumSpec,
    LongestRunSpec,
    ResettingBestPrefixSumSpec,
    StatefulAxes,
    TemplateType,
)
from genfxn.stateful.queries import generate_stateful_queries
from genfxn.stateful.render import render_stateful
from genfxn.stateful.sampler import sample_stateful_spec
from genfxn.stateful.task import generate_stateful_task


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
        assert eval_conditional_linear_sum(spec, [-5, 3, -2, 4]) == 5 + 6 + 2 + 8


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
        assert "x % 2 == 0" in code
        assert "acc +=" in code

    def test_render_resetting_best_prefix_sum(self) -> None:
        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            init_value=0,
        )
        code = render_stateful(spec)
        assert "current_sum" in code
        assert "best_sum" in code
        assert "x < 0" in code

    def test_render_longest_run(self) -> None:
        spec = LongestRunSpec(match_predicate=PredicateGt(value=0))
        code = render_stateful(spec)
        assert "current_run" in code
        assert "longest_run" in code
        assert "x > 0" in code

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
        test_inputs = [[], [1, 2, 3], [1, -1, 2, 3], [-1, -2, -3], [5, 4, -1, 3, 2]]
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
        with pytest.raises(ValueError, match="list_length_range.*>= 0"):
            StatefulAxes(list_length_range=(-1, 10))

    def test_empty_templates(self) -> None:
        with pytest.raises(ValueError, match="templates must not be empty"):
            StatefulAxes(templates=[])

    def test_empty_predicate_types(self) -> None:
        with pytest.raises(ValueError, match="predicate_types must not be empty"):
            StatefulAxes(predicate_types=[])

    def test_empty_transform_types(self) -> None:
        with pytest.raises(ValueError, match="transform_types must not be empty"):
            StatefulAxes(transform_types=[])


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

            namespace: dict = {}
            exec(task.code, namespace)  # noqa: S102
            f = namespace["f"]
            for q in task.queries:
                assert f(q.input) == q.output, f"Template {template}: mismatch"
