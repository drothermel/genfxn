import random
from typing import Any

import pytest

from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import QueryTag

intervals_models = pytest.importorskip("genfxn.intervals.models")
intervals_eval = pytest.importorskip("genfxn.intervals.eval")
intervals_queries = pytest.importorskip("genfxn.intervals.queries")
intervals_render = pytest.importorskip("genfxn.intervals.render")
intervals_sampler = pytest.importorskip("genfxn.intervals.sampler")
intervals_task = pytest.importorskip("genfxn.intervals.task")

IntervalsAxes = intervals_models.IntervalsAxes
IntervalsSpec = intervals_models.IntervalsSpec
BoundaryMode = intervals_models.BoundaryMode
OperationType = intervals_models.OperationType

eval_intervals = intervals_eval.eval_intervals
generate_intervals_queries = intervals_queries.generate_intervals_queries
render_intervals = intervals_render.render_intervals
sample_intervals_spec = intervals_sampler.sample_intervals_spec
generate_intervals_task = intervals_task.generate_intervals_task


def _call_sample(sample_fn: Any, axes: Any, seed: int) -> Any:
    rng = random.Random(seed)
    try:
        return sample_fn(axes=axes, rng=rng)
    except TypeError:
        return sample_fn(axes, rng)


def _call_task(generate_task_fn: Any, axes: Any, seed: int) -> Any:
    rng = random.Random(seed)
    try:
        return generate_task_fn(axes=axes, rng=rng)
    except TypeError:
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
    except TypeError:
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
    except Exception:
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
        with pytest.raises(Exception):
            IntervalsAxes(operation_types=[])

    def test_axes_reject_invalid_probability_range(self) -> None:
        with pytest.raises(Exception):
            IntervalsAxes(degenerate_interval_prob_range=(-0.1, 0.2))


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

        for target in range(1, 5):
            assert averages[target + 1] >= averages[target] + 0.05
        assert averages[5] >= averages[1] + 1.0


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
