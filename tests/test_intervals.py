import random
from collections import defaultdict
from typing import Any

import pytest
from pydantic import ValidationError

from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import QueryTag
from genfxn.intervals.eval import eval_intervals
from genfxn.intervals.models import (
    BoundaryMode,
    IntervalsAxes,
    IntervalsSpec,
    OperationType,
)
from genfxn.intervals.queries import generate_intervals_queries
from genfxn.intervals.render import render_intervals
from genfxn.intervals.sampler import sample_intervals_spec
from genfxn.intervals.task import generate_intervals_task


def _call_sample(sample_fn: Any, axes: Any, seed: int) -> Any:
    rng = random.Random(seed)
    try:
        return sample_fn(axes=axes, rng=rng)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc).lower():
            raise
        return sample_fn(axes, rng)


def _call_task(generate_task_fn: Any, axes: Any, seed: int) -> Any:
    rng = random.Random(seed)
    try:
        return generate_task_fn(axes=axes, rng=rng)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc).lower():
            raise
        return generate_task_fn(axes, rng)


def _call_queries(
    generate_queries_fn: Any,
    spec: Any,
    axes: Any,
    seed: int,
) -> list[Any]:
    rng = random.Random(seed)
    try:
        return generate_queries_fn(spec=spec, axes=axes, rng=rng)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc).lower():
            raise
        return generate_queries_fn(spec, axes, rng)


def _normalize_axes_for_deterministic_sampling(axes: Any, axes_cls: Any) -> Any:
    dump = axes.model_dump()
    changed = False
    for key, value in dump.items():
        if (
            key.endswith("_range")
            and isinstance(value, (tuple, list))
            and len(value) == 2
            and isinstance(value[0], int)
            and isinstance(value[1], int)
        ):
            dump[key] = (value[0], value[0])
            changed = True
    if not changed:
        return axes
    try:
        return axes_cls.model_validate(dump)
    except ValidationError:
        return axes


def _enum_member(enum_cls: Any, *tokens: str) -> Any:
    lowered = [token.lower() for token in tokens]
    for member in enum_cls:
        text = f"{member.name} {member.value}".lower()
        if all(token in text for token in lowered):
            return member
    raise AssertionError(
        f"No member in {enum_cls.__name__} matched tokens {tokens}"
    )


def _enum_by_value(enum_cls: Any, value: str) -> Any:
    for member in enum_cls:
        if member.value == value or member.name.lower() == value.lower():
            return member
    raise AssertionError(
        f"No member in {enum_cls.__name__} matched value {value!r}"
    )


def _set_first_existing(
    data: dict[str, Any],
    candidates: tuple[str, ...],
    value: Any,
) -> bool:
    for key in candidates:
        if key in data:
            data[key] = value
            return True
    return False


def _sample_spec_and_axes(seed: int = 42) -> tuple[Any, Any]:
    axes = _normalize_axes_for_deterministic_sampling(
        IntervalsAxes(), IntervalsAxes
    )
    spec = _call_sample(sample_intervals_spec, axes, seed=seed)
    return spec, axes


def _make_spec(
    *,
    operation: Any,
    boundary_mode: Any,
    merge_touching: bool,
    seed: int,
    endpoint_clip_abs: int | None = None,
) -> Any:
    spec, _ = _sample_spec_and_axes(seed=seed)
    dump = spec.model_dump()

    assert _set_first_existing(
        dump,
        ("operation", "operation_type", "output"),
        operation,
    ), "Unable to set operation field in intervals spec"
    assert _set_first_existing(
        dump,
        ("boundary_mode", "boundary"),
        boundary_mode,
    ), "Unable to set boundary field in intervals spec"
    assert _set_first_existing(
        dump,
        ("merge_touching",),
        merge_touching,
    ), "Unable to set merge_touching field in intervals spec"
    if endpoint_clip_abs is not None:
        assert _set_first_existing(
            dump,
            ("endpoint_clip_abs",),
            endpoint_clip_abs,
        ), "Unable to set endpoint_clip_abs field in intervals spec"
    else:
        assert _set_first_existing(
            dump,
            ("endpoint_clip_abs",),
            20,
        ), "Unable to set endpoint_clip_abs field in intervals spec"
    assert _set_first_existing(
        dump,
        ("endpoint_quantize_step",),
        1,
    ), "Unable to set endpoint_quantize_step field in intervals spec"

    return IntervalsSpec.model_validate(dump)


class TestEvaluatorSemantics:
    def test_boundary_modes_change_coverage(self) -> None:
        total_coverage = _enum_member(OperationType, "total", "coverage")
        cases = [
            ("closed_closed", 3),
            ("closed_open", 2),
            ("open_closed", 2),
            ("open_open", 1),
        ]
        for idx, (boundary_mode, expected) in enumerate(cases):
            spec = _make_spec(
                operation=total_coverage,
                boundary_mode=_enum_by_value(BoundaryMode, boundary_mode),
                merge_touching=True,
                seed=100 + idx,
            )
            assert eval_intervals(spec, [(1, 3)]) == expected

    def test_reversed_endpoints_are_normalized(self) -> None:
        spec = _make_spec(
            operation=_enum_member(OperationType, "total", "coverage"),
            boundary_mode=_enum_member(BoundaryMode, "closed", "closed"),
            merge_touching=True,
            seed=111,
        )
        assert eval_intervals(spec, [(5, 1)]) == 5

    def test_merge_touching_toggle_changes_merged_count(self) -> None:
        operation = _enum_member(OperationType, "merged", "count")
        boundary = _enum_member(BoundaryMode, "closed", "closed")

        spec_merge = _make_spec(
            operation=operation,
            boundary_mode=boundary,
            merge_touching=True,
            seed=120,
        )
        spec_no_merge = _make_spec(
            operation=operation,
            boundary_mode=boundary,
            merge_touching=False,
            seed=121,
        )
        intervals = [(1, 2), (3, 4)]
        assert eval_intervals(spec_merge, intervals) == 1
        assert eval_intervals(spec_no_merge, intervals) == 2

    def test_operation_outputs_match_expected_values(self) -> None:
        boundary = _enum_member(BoundaryMode, "closed", "closed")
        intervals = [(1, 3), (2, 4), (7, 7)]
        op_expectations = [
            (("total", "coverage"), 5),
            (("merged", "count"), 2),
            (("max", "overlap"), 2),
            (("gap", "count"), 1),
        ]
        for idx, (tokens, expected) in enumerate(op_expectations):
            spec = _make_spec(
                operation=_enum_member(OperationType, *tokens),
                boundary_mode=boundary,
                merge_touching=True,
                seed=130 + idx,
            )
            assert eval_intervals(spec, intervals) == expected

    def test_endpoint_clipping_changes_coverage(self) -> None:
        spec = _make_spec(
            operation=_enum_member(OperationType, "total", "coverage"),
            boundary_mode=_enum_member(BoundaryMode, "closed", "closed"),
            merge_touching=True,
            endpoint_clip_abs=3,
            seed=140,
        )
        assert eval_intervals(spec, [(-10, 10)]) == 7

    def test_total_coverage_uses_signed_i64_wrap_semantics(self) -> None:
        i64_max = (1 << 63) - 1
        spec = IntervalsSpec(
            operation=OperationType.TOTAL_COVERAGE,
            boundary_mode=BoundaryMode.CLOSED_CLOSED,
            merge_touching=True,
            endpoint_clip_abs=i64_max,
            endpoint_quantize_step=1,
        )
        assert eval_intervals(spec, [(-i64_max, i64_max)]) == -1

    def test_max_overlap_count_uses_wrapped_end_plus_one_event_key(
        self,
    ) -> None:
        i64_max = (1 << 63) - 1
        spec = IntervalsSpec(
            operation=OperationType.MAX_OVERLAP_COUNT,
            boundary_mode=BoundaryMode.CLOSED_CLOSED,
            merge_touching=False,
            endpoint_clip_abs=i64_max,
            endpoint_quantize_step=1,
        )
        assert eval_intervals(spec, [(i64_max, i64_max)]) == 0


class TestModels:
    def test_spec_and_axes_roundtrip_model_validation(self) -> None:
        spec, axes = _sample_spec_and_axes(seed=57)
        assert IntervalsSpec.model_validate(spec.model_dump()).model_dump() == (
            spec.model_dump()
        )
        assert IntervalsAxes.model_validate(axes.model_dump()).model_dump() == (
            axes.model_dump()
        )

    def test_axes_reject_empty_operation_types(self) -> None:
        with pytest.raises(ValidationError):
            IntervalsAxes(operation_types=[])

    def test_axes_reject_invalid_probability_range(self) -> None:
        with pytest.raises(ValidationError):
            IntervalsAxes(degenerate_interval_prob_range=(-0.1, 0.2))

    def test_axes_reject_invalid_endpoint_clip_range(self) -> None:
        with pytest.raises(ValidationError):
            IntervalsAxes(endpoint_clip_abs_range=(0, 5))

    def test_spec_rejects_endpoint_clip_abs_above_i64_max(self) -> None:
        with pytest.raises(ValidationError, match="endpoint_clip_abs"):
            IntervalsSpec(
                operation=OperationType.TOTAL_COVERAGE,
                boundary_mode=BoundaryMode.CLOSED_CLOSED,
                merge_touching=False,
                endpoint_clip_abs=1 << 63,
            )

    def test_spec_rejects_endpoint_quantize_step_above_i64_max(self) -> None:
        with pytest.raises(ValidationError, match="endpoint_quantize_step"):
            IntervalsSpec(
                operation=OperationType.TOTAL_COVERAGE,
                boundary_mode=BoundaryMode.CLOSED_CLOSED,
                merge_touching=False,
                endpoint_quantize_step=1 << 63,
            )

    @pytest.mark.parametrize(
        ("field_name", "range_value"),
        [
            ("n_intervals_range", (False, 5)),
            ("endpoint_range", (-5, True)),
            ("max_span_range", (True, 5)),
            ("endpoint_clip_abs_range", (False, 5)),
            ("endpoint_quantize_step_range", (1, True)),
        ],
    )
    def test_axes_reject_bool_in_int_range_bounds(
        self, field_name: str, range_value: tuple[int | bool, int | bool]
    ) -> None:
        with pytest.raises(
            ValidationError,
            match=rf"{field_name}: bool is not allowed for int range bounds",
        ):
            IntervalsAxes.model_validate({field_name: range_value})

    @pytest.mark.parametrize(
        ("field_name", "range_value"),
        [
            ("endpoint_range", (-(1 << 63) - 1, 0)),
            ("endpoint_range", (0, 1 << 63)),
            ("max_span_range", (0, 1 << 63)),
            ("endpoint_clip_abs_range", (1, 1 << 63)),
            ("endpoint_quantize_step_range", (1, 1 << 63)),
        ],
    )
    def test_axes_reject_i64_out_of_range_bounds(
        self, field_name: str, range_value: tuple[int, int]
    ) -> None:
        with pytest.raises(ValidationError, match=field_name):
            IntervalsAxes.model_validate({field_name: range_value})


class TestSampler:
    def test_sampler_is_deterministic_for_seed(self) -> None:
        axes = _normalize_axes_for_deterministic_sampling(
            IntervalsAxes(), IntervalsAxes
        )
        spec1 = _call_sample(sample_intervals_spec, axes, seed=99)
        spec2 = _call_sample(sample_intervals_spec, axes, seed=99)
        assert spec1.model_dump() == spec2.model_dump()

    def test_sampler_respects_target_difficulty_axis(self) -> None:
        def _sample_difficulty_average(target: int) -> float:
            axes = IntervalsAxes(target_difficulty=target)
            rng = random.Random(3000 + target)
            scores: list[int] = []
            for _ in range(120):
                spec = _call_sample(
                    sample_intervals_spec,
                    axes,
                    seed=rng.randint(0, 10**9),
                )
                scores.append(
                    compute_difficulty("intervals", spec.model_dump())
                )
            return sum(scores) / len(scores)

        averages = {
            target: _sample_difficulty_average(target) for target in range(1, 6)
        }

        assert averages[5] >= averages[1] + 1.0

    def test_sampler_persists_interval_probability_samples(self) -> None:
        axes = IntervalsAxes(
            allow_reversed_interval_prob_range=(0.75, 0.75),
            degenerate_interval_prob_range=(0.5, 0.5),
            nested_interval_prob_range=(0.25, 0.25),
        )
        spec = _call_sample(sample_intervals_spec, axes, seed=404)
        assert spec.allow_reversed_interval_prob == 0.75
        assert spec.degenerate_interval_prob == 0.5
        assert spec.nested_interval_prob == 0.25


class TestQueries:
    def test_queries_cover_all_tags_and_match_evaluator_outputs(self) -> None:
        axes = IntervalsAxes(
            n_intervals_range=(1, 7),
            endpoint_range=(-12, 12),
            max_span_range=(0, 8),
        )

        for seed in range(410, 422):
            spec = _call_sample(sample_intervals_spec, axes, seed=seed)
            queries = _call_queries(
                generate_intervals_queries,
                spec,
                axes,
                seed=seed,
            )
            assert queries
            assert {q.tag for q in queries} == set(QueryTag)
            for query in queries:
                assert query.output == eval_intervals(spec, query.input)

    def test_query_input_uniqueness_contract_is_per_tag(self) -> None:
        axes = IntervalsAxes(
            n_intervals_range=(1, 1),
            endpoint_range=(0, 0),
            max_span_range=(0, 0),
            allow_reversed_interval_prob_range=(0.0, 0.0),
            degenerate_interval_prob_range=(1.0, 1.0),
            nested_interval_prob_range=(0.0, 0.0),
        )
        spec = _call_sample(sample_intervals_spec, axes, seed=0)
        queries = _call_queries(generate_intervals_queries, spec, axes, seed=0)

        seen_by_tag: dict[QueryTag, set[tuple[tuple[int, int], ...]]] = {
            tag: set() for tag in QueryTag
        }
        tags_by_input: dict[tuple[tuple[int, int], ...], set[QueryTag]] = (
            defaultdict(set)
        )
        for query in queries:
            frozen = tuple((int(a), int(b)) for a, b in query.input)
            assert frozen not in seen_by_tag[query.tag]
            seen_by_tag[query.tag].add(frozen)
            tags_by_input[frozen].add(query.tag)

        assert any(len(tags) > 1 for tags in tags_by_input.values())

    def test_queries_respect_narrow_endpoint_range(self) -> None:
        axes = IntervalsAxes(
            n_intervals_range=(1, 4),
            endpoint_range=(0, 0),
            max_span_range=(0, 2),
        )
        spec = _call_sample(sample_intervals_spec, axes, seed=501)
        queries = _call_queries(
            generate_intervals_queries,
            spec,
            axes,
            seed=501,
        )
        for query in queries:
            for start, end in query.input:
                assert 0 <= start <= 0
                assert 0 <= end <= 0

    def test_queries_use_degenerate_probability_for_typical_cases(self) -> None:
        axes = IntervalsAxes(
            n_intervals_range=(3, 3),
            endpoint_range=(-8, 8),
            max_span_range=(1, 6),
            allow_reversed_interval_prob_range=(0.0, 0.0),
            degenerate_interval_prob_range=(1.0, 1.0),
            nested_interval_prob_range=(0.0, 0.0),
        )
        spec = _call_sample(sample_intervals_spec, axes, seed=601)
        queries = _call_queries(
            generate_intervals_queries,
            spec,
            axes,
            seed=601,
        )
        typical_queries = [q for q in queries if q.tag == QueryTag.TYPICAL]
        assert typical_queries
        for query in typical_queries:
            assert query.input
            assert all(a == b for a, b in query.input)

    def test_queries_respect_zero_max_span_range_for_typical_cases(
        self,
    ) -> None:
        axes = IntervalsAxes(
            n_intervals_range=(3, 3),
            endpoint_range=(-8, 8),
            max_span_range=(0, 0),
            allow_reversed_interval_prob_range=(0.0, 0.0),
            degenerate_interval_prob_range=(0.0, 0.0),
            nested_interval_prob_range=(0.0, 0.0),
        )
        spec = _call_sample(sample_intervals_spec, axes, seed=605)
        queries = _call_queries(
            generate_intervals_queries,
            spec,
            axes,
            seed=605,
        )
        typical_queries = [q for q in queries if q.tag == QueryTag.TYPICAL]
        assert typical_queries
        for query in typical_queries:
            assert query.input
            assert all(a == b for a, b in query.input)

    def test_queries_use_reverse_probability_for_typical_cases(self) -> None:
        common_axes: dict[str, Any] = dict(
            n_intervals_range=(3, 3),
            endpoint_range=(-8, 8),
            max_span_range=(1, 6),
            degenerate_interval_prob_range=(0.0, 0.0),
            nested_interval_prob_range=(0.0, 0.0),
        )

        forward_axes = IntervalsAxes(
            **common_axes,
            allow_reversed_interval_prob_range=(0.0, 0.0),
        )
        forward_spec = _call_sample(
            sample_intervals_spec,
            forward_axes,
            seed=602,
        )
        forward_queries = _call_queries(
            generate_intervals_queries,
            forward_spec,
            forward_axes,
            seed=602,
        )
        forward_typical = [
            q for q in forward_queries if q.tag == QueryTag.TYPICAL
        ]
        assert forward_typical
        for query in forward_typical:
            assert all(a <= b for a, b in query.input)

        reversed_axes = IntervalsAxes(
            **common_axes,
            allow_reversed_interval_prob_range=(1.0, 1.0),
        )
        reversed_spec = _call_sample(
            sample_intervals_spec,
            reversed_axes,
            seed=603,
        )
        reversed_queries = _call_queries(
            generate_intervals_queries,
            reversed_spec,
            reversed_axes,
            seed=603,
        )
        reversed_typical = [
            q for q in reversed_queries if q.tag == QueryTag.TYPICAL
        ]
        assert reversed_typical
        for query in reversed_typical:
            assert all(a > b for a, b in query.input)

    def test_queries_use_nested_probability_for_typical_cases(self) -> None:
        axes = IntervalsAxes(
            n_intervals_range=(4, 4),
            endpoint_range=(-8, 8),
            max_span_range=(1, 6),
            allow_reversed_interval_prob_range=(0.0, 0.0),
            degenerate_interval_prob_range=(0.0, 0.0),
            nested_interval_prob_range=(1.0, 1.0),
        )
        spec = _call_sample(sample_intervals_spec, axes, seed=604)
        queries = _call_queries(
            generate_intervals_queries,
            spec,
            axes,
            seed=604,
        )
        typical_queries = [q for q in queries if q.tag == QueryTag.TYPICAL]
        assert typical_queries

        for query in typical_queries:
            for idx, (a, b) in enumerate(query.input):
                if idx == 0:
                    continue
                lo = min(a, b)
                hi = max(a, b)
                assert any(
                    min(parent_a, parent_b) <= lo
                    and hi <= max(parent_a, parent_b)
                    for parent_a, parent_b in query.input[:idx]
                )


class TestTaskGeneration:
    def test_generate_intervals_task_smoke(self) -> None:
        axes = _normalize_axes_for_deterministic_sampling(
            IntervalsAxes(), IntervalsAxes
        )
        task = _call_task(generate_intervals_task, axes, seed=222)
        assert task.task_id
        assert task.family == "intervals"
        assert task.description
        assert isinstance(task.code, str)
        assert task.queries
        assert {q.tag for q in task.queries} == set(QueryTag)

        spec = IntervalsSpec.model_validate(task.spec)
        assert task.difficulty == compute_difficulty("intervals", task.spec)
        for query in task.queries:
            assert query.output == eval_intervals(spec, query.input)

    def test_rendered_python_matches_evaluator(self) -> None:
        spec, axes = _sample_spec_and_axes(seed=333)
        code = render_intervals(spec, func_name="f")
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        fn_obj = namespace["f"]
        assert callable(fn_obj)

        queries = _call_queries(
            generate_intervals_queries,
            spec,
            axes,
            seed=333,
        )
        for query in queries:
            expected = eval_intervals(spec, query.input)
            actual = fn_obj(query.input)  # type: ignore[misc]
            assert actual == expected
