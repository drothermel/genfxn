import random

import pytest
from pydantic import ValidationError

from genfxn.core.models import QueryTag
from genfxn.core.predicates import PredicateGt, PredicateModEq, PredicateType
from genfxn.core.transforms import (
    TransformNegate,
    TransformShift,
    TransformType,
)
from genfxn.simple_algorithms.eval import (
    eval_count_pairs_sum,
    eval_max_window_sum,
    eval_most_frequent,
    eval_simple_algorithms,
)
from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    MaxWindowSumSpec,
    MostFrequentSpec,
    SimpleAlgorithmsAxes,
    TemplateType,
    TieBreakMode,
)
from genfxn.simple_algorithms.queries import generate_simple_algorithms_queries
from genfxn.simple_algorithms.render import render_simple_algorithms
from genfxn.simple_algorithms.sampler import sample_simple_algorithms_spec
from genfxn.simple_algorithms.task import generate_simple_algorithms_task

INT32_MAX = (1 << 31) - 1
INT64_MAX = (1 << 63) - 1


class TestMostFrequentEval:
    def test_empty_list(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST, empty_default=0
        )
        assert eval_most_frequent(spec, []) == 0

    def test_single_element(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST, empty_default=0
        )
        assert eval_most_frequent(spec, [5]) == 5

    def test_clear_winner(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST, empty_default=0
        )
        assert eval_most_frequent(spec, [1, 2, 2, 3]) == 2

    def test_tie_break_smallest(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST, empty_default=0
        )
        # 1 and 2 appear equally, smallest wins
        assert eval_most_frequent(spec, [2, 1, 2, 1]) == 1

    def test_tie_break_first_seen(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.FIRST_SEEN, empty_default=0
        )
        # 2 appears first
        assert eval_most_frequent(spec, [2, 1, 2, 1]) == 2
        # 1 appears first
        assert eval_most_frequent(spec, [1, 2, 1, 2]) == 1

    def test_all_unique(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST, empty_default=0
        )
        assert eval_most_frequent(spec, [5, 3, 8, 1]) == 1


class TestCountPairsSumEval:
    def test_empty_list(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.ALL_INDICES
        )
        assert eval_count_pairs_sum(spec, []) == 0

    def test_single_element(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.ALL_INDICES
        )
        assert eval_count_pairs_sum(spec, [5]) == 0

    def test_one_pair(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.ALL_INDICES
        )
        assert eval_count_pairs_sum(spec, [3, 7]) == 1

    def test_no_pairs(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.ALL_INDICES
        )
        assert eval_count_pairs_sum(spec, [1, 2, 3]) == 0

    def test_all_indices_counts_duplicates(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.ALL_INDICES
        )
        # [5, 5, 5] has 3 pairs: (0,1), (0,2), (1,2)
        assert eval_count_pairs_sum(spec, [5, 5, 5]) == 3

    def test_unique_values_ignores_duplicates(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.UNIQUE_VALUES
        )
        # [5, 5, 5] has only 1 unique pair: (5, 5)
        assert eval_count_pairs_sum(spec, [5, 5, 5]) == 1

    def test_all_indices_vs_unique(self) -> None:
        spec_all = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.ALL_INDICES
        )
        spec_unique = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.UNIQUE_VALUES
        )
        # [3, 7, 3, 7] has 4 pairs summing to 10 for ALL_INDICES
        # but only 1 unique pair (3, 7)
        xs = [3, 7, 3, 7]
        assert eval_count_pairs_sum(spec_all, xs) == 4
        assert eval_count_pairs_sum(spec_unique, xs) == 1


class TestMaxWindowSumEval:
    def test_k_greater_than_len(self) -> None:
        spec = MaxWindowSumSpec(k=5, invalid_k_default=-1)
        assert eval_max_window_sum(spec, [1, 2, 3]) == -1

    def test_k_equals_len(self) -> None:
        spec = MaxWindowSumSpec(k=3, invalid_k_default=0)
        assert eval_max_window_sum(spec, [1, 2, 3]) == 6

    def test_k_one(self) -> None:
        spec = MaxWindowSumSpec(k=1, invalid_k_default=0)
        assert eval_max_window_sum(spec, [3, 1, 4, 1, 5]) == 5

    def test_max_at_start(self) -> None:
        spec = MaxWindowSumSpec(k=3, invalid_k_default=0)
        assert eval_max_window_sum(spec, [10, 10, 10, 1, 1, 1]) == 30

    def test_max_at_end(self) -> None:
        spec = MaxWindowSumSpec(k=3, invalid_k_default=0)
        assert eval_max_window_sum(spec, [1, 1, 1, 10, 10, 10]) == 30

    def test_all_negative(self) -> None:
        spec = MaxWindowSumSpec(k=2, invalid_k_default=0)
        # Windows: [-5,-3]=-8, [-3,-7]=-10, [-7,-1]=-8 -> max is -8
        assert eval_max_window_sum(spec, [-5, -3, -7, -1]) == -8


class TestRender:
    def test_most_frequent_smallest(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST, empty_default=0
        )
        code = render_simple_algorithms(spec)
        assert "def f(xs: list[int]) -> int:" in code
        assert "min(candidates)" in code

    def test_most_frequent_first_seen(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.FIRST_SEEN, empty_default=0
        )
        code = render_simple_algorithms(spec)
        assert "for x in xs:" in code

    def test_count_pairs_all_indices(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.ALL_INDICES
        )
        code = render_simple_algorithms(spec)
        assert "count += 1" in code

    def test_count_pairs_unique_values(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.UNIQUE_VALUES
        )
        code = render_simple_algorithms(spec)
        assert "seen_pairs" in code
        assert "tuple(sorted" in code

    def test_max_window_sum(self) -> None:
        spec = MaxWindowSumSpec(k=3, invalid_k_default=0)
        code = render_simple_algorithms(spec)
        assert "window_sum" in code
        assert "max_sum" in code


class TestRenderRoundtrip:
    def test_most_frequent_roundtrip(self) -> None:
        for tie_break in TieBreakMode:
            spec = MostFrequentSpec(tie_break=tie_break, empty_default=0)
            code = render_simple_algorithms(spec)
            namespace: dict = {}
            exec(code, namespace)  # noqa: S102
            f = namespace["f"]
            test_inputs = [[], [1], [1, 2, 1], [2, 1, 2, 1], [1, 2, 3, 1, 2, 3]]
            for xs in test_inputs:
                assert f(xs) == eval_simple_algorithms(spec, xs), (
                    f"tie_break={tie_break}, xs={xs}"
                )

    def test_count_pairs_roundtrip(self) -> None:
        for mode in CountingMode:
            spec = CountPairsSumSpec(target=10, counting_mode=mode)
            code = render_simple_algorithms(spec)
            namespace: dict = {}
            exec(code, namespace)  # noqa: S102
            f = namespace["f"]
            test_inputs = [[], [5], [3, 7], [5, 5, 5], [2, 8, 2, 8]]
            for xs in test_inputs:
                assert f(xs) == eval_simple_algorithms(spec, xs), (
                    f"mode={mode}, xs={xs}"
                )

    def test_max_window_roundtrip(self) -> None:
        for k in [1, 2, 3]:
            spec = MaxWindowSumSpec(k=k, invalid_k_default=0)
            code = render_simple_algorithms(spec)
            namespace: dict = {}
            exec(code, namespace)  # noqa: S102
            f = namespace["f"]
            test_inputs = [
                [],
                [1],
                [1, 2, 3, 4, 5],
                [-1, -2, -3],
                [10, 1, 1, 10],
            ]
            for xs in test_inputs:
                assert f(xs) == eval_simple_algorithms(spec, xs), (
                    f"k={k}, xs={xs}"
                )

    def test_count_pairs_roundtrip_large_value_sum_comparison(self) -> None:
        spec = CountPairsSumSpec(
            target=-294_967_296,
            counting_mode=CountingMode.ALL_INDICES,
        )
        code = render_simple_algorithms(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        xs = [2_000_000_000, 2_000_000_000]
        assert f(xs) == eval_simple_algorithms(spec, xs)

    def test_max_window_roundtrip_int32_large_values(self) -> None:
        spec = MaxWindowSumSpec(k=2, invalid_k_default=0)
        code = render_simple_algorithms(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        xs = [2_000_000_000, 2_000_000_000, 0]
        assert f(xs) == eval_simple_algorithms(spec, xs)


class TestSampler:
    def test_reproducible(self) -> None:
        axes = SimpleAlgorithmsAxes(templates=[TemplateType.MOST_FREQUENT])
        spec1 = sample_simple_algorithms_spec(axes, random.Random(42))
        spec2 = sample_simple_algorithms_spec(axes, random.Random(42))
        assert spec1 == spec2

    def test_respects_template_filter(self) -> None:
        for template in TemplateType:
            axes = SimpleAlgorithmsAxes(templates=[template])
            spec = sample_simple_algorithms_spec(axes, random.Random(42))
            assert spec.template == template.value


class TestQueryGeneration:
    def test_generates_queries(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST, empty_default=0
        )
        axes = SimpleAlgorithmsAxes()
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        assert len(queries) > 0

    def test_all_queries_valid(self) -> None:
        spec = CountPairsSumSpec(
            target=10, counting_mode=CountingMode.ALL_INDICES
        )
        axes = SimpleAlgorithmsAxes()
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        for q in queries:
            assert q.output == eval_simple_algorithms(spec, q.input)

    def test_includes_empty_list(self) -> None:
        spec = MaxWindowSumSpec(k=3, invalid_k_default=0)
        axes = SimpleAlgorithmsAxes(
            list_length_range=(0, 20),
            window_size_range=(1, 10),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        inputs = [q.input for q in queries]
        assert [] in inputs

    def test_max_window_empty_query_uses_empty_default_when_set(self) -> None:
        spec = MaxWindowSumSpec(k=3, invalid_k_default=-1, empty_default=-99)
        axes = SimpleAlgorithmsAxes(
            list_length_range=(0, 20),
            window_size_range=(1, 10),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        empty_queries = [q for q in queries if q.input == []]
        assert empty_queries
        assert empty_queries[0].output == eval_simple_algorithms(spec, [])

    def test_max_window_queries_respect_list_length_upper_bound(self) -> None:
        spec = MaxWindowSumSpec(k=3, invalid_k_default=-1)
        axes = SimpleAlgorithmsAxes(
            list_length_range=(1, 3),
            window_size_range=(1, 3),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        assert queries
        assert all(len(q.input) <= axes.list_length_range[1] for q in queries)

    def test_max_window_queries_respect_list_length_lower_bound(self) -> None:
        spec = MaxWindowSumSpec(k=2, invalid_k_default=-1)
        axes = SimpleAlgorithmsAxes(
            list_length_range=(2, 3),
            window_size_range=(1, 3),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        assert queries
        assert all(len(q.input) >= axes.list_length_range[0] for q in queries)

    def test_max_window_k_minus_one_query_uses_eval_with_empty_default(
        self,
    ) -> None:
        spec = MaxWindowSumSpec(
            k=3,
            invalid_k_default=-1,
            empty_default=-99,
            pre_filter=PredicateGt(value=100),
            pre_transform=TransformShift(offset=1),
        )
        axes = SimpleAlgorithmsAxes(
            list_length_range=(0, 20),
            window_size_range=(1, 10),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        k_minus_one_queries = [
            q
            for q in queries
            if len(q.input) == spec.k - 1 and q.tag == QueryTag.BOUNDARY
        ]
        assert k_minus_one_queries
        for q in k_minus_one_queries:
            assert q.output == eval_simple_algorithms(spec, q.input)
            assert q.output == -99

    def test_count_pairs_no_pairs_query_has_no_valid_pair(self) -> None:
        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.ALL_INDICES,
        )
        axes = SimpleAlgorithmsAxes(
            value_range=(0, 15),
            list_length_range=(2, 5),
            window_size_range=(1, 5),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        no_pair_queries = [
            q
            for q in queries
            if q.tag == QueryTag.TYPICAL
            and eval_count_pairs_sum(spec, q.input) == 0
        ]
        assert no_pair_queries
        for q in no_pair_queries:
            assert all(
                q.input[i] + q.input[j] != spec.target
                for i in range(len(q.input))
                for j in range(i + 1, len(q.input))
            )

    def test_count_pairs_queries_respect_list_length_when_max_len_under_two(
        self,
    ) -> None:
        """When axes allow only length 0–1, no 'no pairs' list is possible; no error."""
        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.ALL_INDICES,
        )
        axes = SimpleAlgorithmsAxes(
            value_range=(0, 15),
            list_length_range=(0, 1),
            window_size_range=(1, 1),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(99)
        )
        len_hi = axes.list_length_range[1]
        for q in queries:
            assert len(q.input) <= len_hi, (
                f"query input length {len(q.input)} exceeds list_length_range high {len_hi}"
            )


class TestAxesValidation:
    def test_invalid_value_range(self) -> None:
        with pytest.raises(ValueError, match="value_range"):
            SimpleAlgorithmsAxes(value_range=(100, -100))

    def test_invalid_window_size_range(self) -> None:
        with pytest.raises(ValueError, match="window_size_range"):
            SimpleAlgorithmsAxes(window_size_range=(10, 5))

    def test_zero_window_size(self) -> None:
        with pytest.raises(ValueError, match=r"window_size_range.*>= 1"):
            SimpleAlgorithmsAxes(window_size_range=(0, 5))

    def test_window_size_high_cannot_exceed_list_length_high(self) -> None:
        with pytest.raises(
            ValueError,
            match=r"window_size_range: high .*<= list_length_range high",
        ):
            SimpleAlgorithmsAxes(
                list_length_range=(1, 3), window_size_range=(1, 5)
            )

    def test_window_size_range_high_must_fit_int32(self) -> None:
        with pytest.raises(
            ValueError,
            match=rf"window_size_range: high .* must be <= {INT32_MAX}",
        ):
            SimpleAlgorithmsAxes(
                list_length_range=(1, INT32_MAX + 1),
                window_size_range=(1, INT32_MAX + 1),
            )

    def test_value_range_rejects_values_above_signed_i64(self) -> None:
        with pytest.raises(
            ValueError,
            match=rf"value_range: high .* must be <= {INT64_MAX}",
        ):
            SimpleAlgorithmsAxes(value_range=(0, INT64_MAX + 1))

    def test_empty_templates(self) -> None:
        with pytest.raises(ValueError, match="templates must not be empty"):
            SimpleAlgorithmsAxes(templates=[])

    def test_empty_pre_filter_types(self) -> None:
        with pytest.raises(
            ValueError, match="pre_filter_types must not be empty"
        ):
            SimpleAlgorithmsAxes(pre_filter_types=[])

    def test_empty_pre_transform_types(self) -> None:
        with pytest.raises(
            ValueError, match="pre_transform_types must not be empty"
        ):
            SimpleAlgorithmsAxes(pre_transform_types=[])

    def test_non_empty_preprocess_type_lists(self) -> None:
        axes = SimpleAlgorithmsAxes(
            pre_filter_types=[PredicateType.MOD_EQ],
            pre_transform_types=[TransformType.SHIFT],
        )
        assert axes.pre_filter_types == [PredicateType.MOD_EQ]
        assert axes.pre_transform_types == [TransformType.SHIFT]

    def test_unsupported_pre_filter_type(self) -> None:
        with pytest.raises(
            ValueError, match="pre_filter_types contains unsupported"
        ):
            SimpleAlgorithmsAxes(pre_filter_types=[PredicateType.IN_SET])

    def test_unsupported_pre_transform_type(self) -> None:
        with pytest.raises(
            ValueError, match="pre_transform_types contains unsupported"
        ):
            SimpleAlgorithmsAxes(pre_transform_types=[TransformType.CLIP])

    @pytest.mark.parametrize(
        ("field_name", "range_value"),
        [
            ("value_range", (False, 5)),
            ("list_length_range", (1, True)),
            ("target_range", (True, 5)),
            ("window_size_range", (1, False)),
            ("empty_default_range", (False, 0)),
            ("tie_default_range", (0, True)),
            ("no_result_default_range", (False, 0)),
            ("short_list_default_range", (0, True)),
            ("empty_default_for_empty_range", (False, 0)),
        ],
    )
    def test_rejects_bool_in_int_range_bounds(
        self, field_name: str, range_value: tuple[int | bool, int | bool]
    ) -> None:
        with pytest.raises(
            ValidationError,
            match=rf"{field_name}: bool is not allowed for int range bounds",
        ):
            SimpleAlgorithmsAxes.model_validate({field_name: range_value})

    def test_max_window_sum_rejects_k_above_int32(self) -> None:
        with pytest.raises(ValueError, match="2147483647"):
            MaxWindowSumSpec(k=INT32_MAX + 1)


class TestTaskGeneration:
    def test_full_pipeline(self) -> None:
        axes = SimpleAlgorithmsAxes(templates=[TemplateType.MOST_FREQUENT])
        task = generate_simple_algorithms_task(axes, random.Random(42))
        assert task.family == "simple_algorithms"
        assert task.task_id.startswith("simple_algorithms_")
        assert len(task.queries) > 0

        assert isinstance(task.code, str)
        namespace: dict = {}
        exec(task.code, namespace)  # noqa: S102
        f = namespace["f"]
        for q in task.queries:
            assert f(q.input) == q.output

    def test_each_template(self) -> None:
        for template in TemplateType:
            axes = SimpleAlgorithmsAxes(templates=[template])
            task = generate_simple_algorithms_task(axes, random.Random(42))
            assert task.spec["template"] == template.value

            assert isinstance(task.code, str)
            namespace: dict = {}
            exec(task.code, namespace)  # noqa: S102
            f = namespace["f"]
            for q in task.queries:
                assert f(q.input) == q.output, f"Template {template}: mismatch"


class TestPreprocessFilter:
    def test_most_frequent_with_filter(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=-1,
            pre_filter=PredicateGt(value=0),
        )
        # Filter keeps only positive: [3, 1, 3] -> most frequent = 3
        assert eval_most_frequent(spec, [-5, 3, -2, 1, 3]) == 3

    def test_filter_removes_all(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=-99,
            pre_filter=PredicateGt(value=100),
        )
        # Nothing passes the filter
        assert eval_most_frequent(spec, [1, 2, 3]) == -99

    def test_count_pairs_with_filter(self) -> None:
        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.ALL_INDICES,
            pre_filter=PredicateGt(value=0),
        )
        # Filter to positives: [3, 7] -> 1 pair
        assert eval_count_pairs_sum(spec, [-1, 3, -2, 7]) == 1

    def test_max_window_with_filter(self) -> None:
        spec = MaxWindowSumSpec(
            k=2,
            invalid_k_default=-1,
            pre_filter=PredicateGt(value=0),
        )
        # Filter to positives: [3, 7, 1] -> windows [3,7]=10, [7,1]=8 -> max=10
        assert eval_max_window_sum(spec, [-5, 3, -2, 7, 1]) == 10


class TestPreprocessTransform:
    def test_most_frequent_with_transform(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
            pre_transform=TransformNegate(),
        )
        # Negate: [1, 2, 1] -> [-1, -2, -1] -> most frequent = -1
        assert eval_most_frequent(spec, [1, 2, 1]) == -1

    def test_count_pairs_with_transform(self) -> None:
        spec = CountPairsSumSpec(
            target=0,
            counting_mode=CountingMode.ALL_INDICES,
            pre_transform=TransformShift(offset=5),
        )
        # Shift by 5: [-5, -5] -> [0, 0] -> 1 pair summing to 0
        assert eval_count_pairs_sum(spec, [-5, -5]) == 1


class TestTieDefault:
    def test_tie_default_used(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
            tie_default=-999,
        )
        # 1 and 2 appear equally -> tie -> return tie_default
        assert eval_most_frequent(spec, [1, 2, 1, 2]) == -999

    def test_tie_default_not_used_when_clear_winner(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
            tie_default=-999,
        )
        assert eval_most_frequent(spec, [1, 2, 2]) == 2

    def test_tie_default_none_uses_tie_break(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
            tie_default=None,
        )
        assert eval_most_frequent(spec, [2, 1, 2, 1]) == 1


class TestNoResultDefault:
    def test_no_result_default_used(self) -> None:
        spec = CountPairsSumSpec(
            target=100,
            counting_mode=CountingMode.ALL_INDICES,
            no_result_default=-1,
        )
        assert eval_count_pairs_sum(spec, [1, 2, 3]) == -1

    def test_no_result_default_not_used_when_pairs_found(self) -> None:
        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.ALL_INDICES,
            no_result_default=-1,
        )
        assert eval_count_pairs_sum(spec, [3, 7]) == 1


class TestShortListDefault:
    def test_short_list_default_empty(self) -> None:
        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.ALL_INDICES,
            short_list_default=-5,
        )
        assert eval_count_pairs_sum(spec, []) == -5

    def test_short_list_default_single(self) -> None:
        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.ALL_INDICES,
            short_list_default=-5,
        )
        assert eval_count_pairs_sum(spec, [5]) == -5


class TestEmptyDefault:
    def test_empty_default_used(self) -> None:
        spec = MaxWindowSumSpec(
            k=3,
            invalid_k_default=-1,
            empty_default=-99,
        )
        assert eval_max_window_sum(spec, []) == -99

    def test_empty_default_none_falls_to_invalid_k(self) -> None:
        spec = MaxWindowSumSpec(
            k=3,
            invalid_k_default=-1,
            empty_default=None,
        )
        # Empty list with no empty_default -> falls through to len < k check
        assert eval_max_window_sum(spec, []) == -1


class TestPreprocessRenderRoundtrip:
    def test_most_frequent_with_filter_roundtrip(self) -> None:
        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=-1,
            pre_filter=PredicateGt(value=0),
            tie_default=-99,
        )
        code = render_simple_algorithms(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = [[], [1], [-1, 2, -3, 2], [1, 2, 1, 2], [5]]
        for xs in test_inputs:
            assert f(xs) == eval_simple_algorithms(spec, xs), f"xs={xs}"

    def test_count_pairs_with_transform_roundtrip(self) -> None:
        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.UNIQUE_VALUES,
            pre_transform=TransformShift(offset=5),
            no_result_default=-1,
            short_list_default=-5,
        )
        code = render_simple_algorithms(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = [[], [1], [0, 5], [2, 3, 2, 3]]
        for xs in test_inputs:
            assert f(xs) == eval_simple_algorithms(spec, xs), f"xs={xs}"

    def test_max_window_with_filter_roundtrip(self) -> None:
        spec = MaxWindowSumSpec(
            k=2,
            invalid_k_default=-1,
            pre_filter=PredicateModEq(divisor=2, remainder=0),
            empty_default=-99,
        )
        code = render_simple_algorithms(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = [[], [1, 3, 5], [2, 4, 6], [1, 2, 3, 4, 5, 6]]
        for xs in test_inputs:
            assert f(xs) == eval_simple_algorithms(spec, xs), f"xs={xs}"
