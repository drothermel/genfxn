import random
from typing import Any

import pytest
from pydantic import ValidationError

from genfxn.core.models import QueryTag
from genfxn.langs.types import Language

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


def _spec(
    formula: dict[str, Any],
    output_mode: TemporalOutputMode = TemporalOutputMode.SAT_COUNT,
) -> TemporalLogicSpec:
    return TemporalLogicSpec(output_mode=output_mode, formula=formula)


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
        spec = _spec(
            {
                "op": "next",
                "child": _atom(PredicateKind.GE, 0),
            },
            output_mode=TemporalOutputMode.SAT_AT_START,
        )
        assert eval_temporal_logic(spec, [5]) == 0

    @pytest.mark.parametrize(
        ("predicate", "expected"),
        [
            (PredicateKind.EQ, 1),
            (PredicateKind.NE, 2),
            (PredicateKind.LT, 1),
            (PredicateKind.LE, 2),
            (PredicateKind.GT, 1),
            (PredicateKind.GE, 2),
        ],
    )
    def test_atom_predicate_kinds(
        self, predicate: PredicateKind, expected: int
    ) -> None:
        spec = _spec(_atom(predicate, 0))
        assert eval_temporal_logic(spec, [-1, 0, 1]) == expected

    def test_boolean_operators(self) -> None:
        xs = [-1, 0, 2]

        not_spec = _spec({"op": "not", "child": _atom(PredicateKind.GE, 0)})
        assert eval_temporal_logic(not_spec, xs) == 1

        and_spec = _spec(
            {
                "op": "and",
                "left": _atom(PredicateKind.GE, 0),
                "right": _atom(PredicateKind.LE, 1),
            }
        )
        assert eval_temporal_logic(and_spec, xs) == 1

        or_spec = _spec(
            {
                "op": "or",
                "left": _atom(PredicateKind.LT, 0),
                "right": _atom(PredicateKind.GT, 1),
            }
        )
        assert eval_temporal_logic(or_spec, xs) == 2

    def test_temporal_future_operators(self) -> None:
        xs = [0, 1, -1]
        next_spec = _spec({"op": "next", "child": _atom(PredicateKind.GT, 0)})
        assert eval_temporal_logic(next_spec, xs) == 1

        eventually_spec = _spec(
            {"op": "eventually", "child": _atom(PredicateKind.LT, 0)}
        )
        assert eval_temporal_logic(eventually_spec, xs) == 3

        always_spec = _spec(
            {"op": "always", "child": _atom(PredicateKind.GE, 0)}
        )
        assert eval_temporal_logic(always_spec, xs) == 0

    def test_until_and_since_semantics(self) -> None:
        xs = [1, 2, -1, 3]
        until_formula = {
            "op": "until",
            "left": _atom(PredicateKind.GE, 0),
            "right": _atom(PredicateKind.LT, 0),
        }
        since_formula = {
            "op": "since",
            "left": _atom(PredicateKind.GE, 0),
            "right": _atom(PredicateKind.LT, 0),
        }
        until_spec = _spec(
            until_formula, output_mode=TemporalOutputMode.SAT_COUNT
        )
        since_spec = _spec(
            since_formula, output_mode=TemporalOutputMode.SAT_COUNT
        )
        assert eval_temporal_logic(until_spec, xs) == 3
        assert eval_temporal_logic(since_spec, xs) == 2

        since_first = _spec(
            since_formula, output_mode=TemporalOutputMode.FIRST_SAT_INDEX
        )
        assert eval_temporal_logic(since_first, xs) == 2

    def test_spec_validation_rejects_invalid_formulas(self) -> None:
        with pytest.raises(
            ValidationError, match="next node must include 'child'"
        ):
            _spec({"op": "next"})

        with pytest.raises(
            ValidationError, match="atom node must include int 'constant'"
        ):
            _spec({"op": "atom", "predicate": "eq"})

        with pytest.raises(
            ValidationError, match="unknown predicate kind 'bad'"
        ):
            _spec({"op": "atom", "predicate": "bad", "constant": 1})

        with pytest.raises(ValidationError, match="unknown operator 'bad_op'"):
            _spec({"op": "bad_op"})

    def test_spec_validation_rejects_excessive_depth(self) -> None:
        deep: dict[str, Any] = _atom(PredicateKind.EQ, 0)
        for _ in range(13):
            deep = {"op": "not", "child": deep}
        with pytest.raises(
            ValidationError, match="formula depth must be <= 12"
        ):
            _spec(deep)

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
        assert task.spec["output_mode"] in task.description
        assert task.description
        assert len(task.queries) > 0
        tags = {query.tag for query in task.queries}
        assert tags == set(QueryTag)

    def test_task_generation_supports_python_language_map(self) -> None:
        task = generate_temporal_logic_task(
            axes=TemporalLogicAxes(formula_depth_range=(1, 1)),
            rng=random.Random(10),
            languages=[Language.PYTHON],
        )
        assert isinstance(task.code, dict)
        assert set(task.code) == {"python"}
        assert "def f(xs: list[int]) -> int:" in task.code["python"]

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

    def test_render_matches_evaluator_across_sampled_specs(self) -> None:
        axes = TemporalLogicAxes(
            formula_depth_range=(1, 4),
            sequence_length_range=(0, 8),
            value_range=(-4, 4),
            predicate_constant_range=(-4, 4),
        )
        for seed in range(300, 315):
            spec = sample_temporal_logic_spec(axes, random.Random(seed))
            code = render_temporal_logic(spec)
            namespace: dict[str, Any] = {}
            exec(code, namespace)  # noqa: S102
            fn = namespace["f"]

            queries = generate_temporal_logic_queries(
                spec,
                axes,
                rng=random.Random(seed + 1),
            )
            assert queries
            assert {query.tag for query in queries} == set(QueryTag)
            for query in queries:
                expected = eval_temporal_logic(spec, query.input)
                assert query.output == expected
                assert fn(query.input) == expected
