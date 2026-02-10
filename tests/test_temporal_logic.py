import random
from typing import Any

import pytest

from genfxn.core.models import QueryTag

temporal_models = pytest.importorskip("genfxn.temporal_logic.models")
temporal_eval = pytest.importorskip("genfxn.temporal_logic.eval")
temporal_queries = pytest.importorskip("genfxn.temporal_logic.queries")
temporal_render = pytest.importorskip("genfxn.temporal_logic.render")
temporal_sampler = pytest.importorskip("genfxn.temporal_logic.sampler")
temporal_task = pytest.importorskip("genfxn.temporal_logic.task")

PredicateKind = temporal_models.PredicateKind
TemporalLogicAxes = temporal_models.TemporalLogicAxes
TemporalLogicSpec = temporal_models.TemporalLogicSpec
TemporalOutputMode = temporal_models.TemporalOutputMode

eval_temporal_logic = temporal_eval.eval_temporal_logic
generate_temporal_logic_queries = (
    temporal_queries.generate_temporal_logic_queries
)
render_temporal_logic = temporal_render.render_temporal_logic
sample_temporal_logic_spec = temporal_sampler.sample_temporal_logic_spec
generate_temporal_logic_task = temporal_task.generate_temporal_logic_task


def _call_sample(sample_fn: Any, axes: Any, seed: int) -> Any:
    rng = random.Random(seed)
    try:
        return sample_fn(axes=axes, rng=rng)
    except TypeError as exc:
        if "unexpected keyword" not in str(exc).lower():
            raise
        return sample_fn(axes, rng)


def _atom(predicate: PredicateKind, constant: int) -> dict[str, Any]:
    return {
        "op": "atom",
        "predicate": predicate.value,
        "constant": constant,
    }


class TestTemporalLogicSemantics:
    def test_empty_sequence_semantics(self) -> None:
        formula = _atom(PredicateKind.GE, 0)

        sat_at_start = TemporalLogicSpec(
            output_mode=TemporalOutputMode.SAT_AT_START,
            formula=formula,
        )
        assert eval_temporal_logic(sat_at_start, []) == 0

        sat_count = TemporalLogicSpec(
            output_mode=TemporalOutputMode.SAT_COUNT,
            formula=formula,
        )
        assert eval_temporal_logic(sat_count, []) == 0

        first_sat = TemporalLogicSpec(
            output_mode=TemporalOutputMode.FIRST_SAT_INDEX,
            formula=formula,
        )
        assert eval_temporal_logic(first_sat, []) == -1

    def test_next_on_single_element_is_false(self) -> None:
        spec = TemporalLogicSpec(
            output_mode=TemporalOutputMode.SAT_AT_START,
            formula={
                "op": "next",
                "child": _atom(PredicateKind.GE, 0),
            },
        )
        assert eval_temporal_logic(spec, [5]) == 0

    def test_sampler_is_deterministic_for_fixed_seed(self) -> None:
        axes = TemporalLogicAxes(
            formula_depth_range=(2, 2),
            sequence_length_range=(0, 5),
            value_range=(-3, 3),
            predicate_constant_range=(-2, 2),
        )
        first = _call_sample(sample_temporal_logic_spec, axes, seed=123)
        second = _call_sample(sample_temporal_logic_spec, axes, seed=123)
        assert first.model_dump() == second.model_dump()

    def test_task_generation_smoke_and_query_tags(self) -> None:
        axes = TemporalLogicAxes(
            formula_depth_range=(2, 2),
            sequence_length_range=(0, 4),
            value_range=(-2, 2),
            predicate_constant_range=(-1, 1),
        )
        task = generate_temporal_logic_task(axes=axes, rng=random.Random(9))

        assert task.family == "temporal_logic"
        assert isinstance(task.code, str)
        assert task.description
        assert len(task.queries) > 0
        tags = {query.tag for query in task.queries}
        assert tags == set(QueryTag)

    def test_render_matches_evaluator_on_queries(self) -> None:
        axes = TemporalLogicAxes(
            formula_depth_range=(2, 2),
            sequence_length_range=(0, 5),
            value_range=(-3, 3),
            predicate_constant_range=(-2, 2),
        )
        spec = sample_temporal_logic_spec(axes, rng=random.Random(44))
        queries = generate_temporal_logic_queries(
            spec,
            axes,
            rng=random.Random(45),
        )

        code = render_temporal_logic(spec)
        namespace: dict[str, Any] = {}
        exec(code, namespace)  # noqa: S102
        fn = namespace["f"]

        for query in queries:
            assert fn(query.input) == eval_temporal_logic(spec, query.input)
            assert query.output == eval_temporal_logic(spec, query.input)
