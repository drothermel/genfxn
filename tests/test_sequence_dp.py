import random
import re
from collections.abc import Callable
from typing import Any, cast

import pytest

from genfxn.core.models import QueryTag
from genfxn.sequence_dp.eval import eval_sequence_dp
from genfxn.sequence_dp.models import (
    OutputMode,
    PredicateEq,
    PredicateModEq,
    PredicateType,
    SequenceDpAxes,
    SequenceDpSpec,
    TemplateType,
    TieBreakOrder,
)
from genfxn.sequence_dp.queries import generate_sequence_dp_queries
from genfxn.sequence_dp.render import render_sequence_dp
from genfxn.sequence_dp.sampler import sample_sequence_dp_spec
from genfxn.sequence_dp.task import generate_sequence_dp_task


def _call_sample(sample_fn: Any, axes: Any, seed: int) -> Any:
    rng = random.Random(seed)
    try:
        return sample_fn(axes=axes, rng=rng)
    except TypeError:
        return sample_fn(axes, rng)


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


def _call_task(generate_task_fn: Any, axes: Any, seed: int) -> Any:
    rng = random.Random(seed)
    try:
        return generate_task_fn(axes=axes, rng=rng)
    except TypeError:
        return generate_task_fn(axes, rng)


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


def _assert_has_invalid_rejected(model_cls: Any, valid_obj: Any) -> None:
    valid = valid_obj.model_dump()
    for field_name in valid:
        for bad in (None, {}, [], "invalid-value", object()):
            candidate = dict(valid)
            candidate[field_name] = bad
            try:
                model_cls.model_validate(candidate)
            except Exception:
                return
    raise AssertionError(
        f"{model_cls.__name__} did not reject any invalid mutation"
    )


def _sample_spec_and_axes(seed: int = 42) -> tuple[Any, Any]:
    axes = _normalize_axes_for_deterministic_sampling(
        SequenceDpAxes(), SequenceDpAxes
    )
    spec = _call_sample(sample_sequence_dp_spec, axes, seed=seed)
    return spec, axes


def _enum_member(enum_cls: Any, *tokens: str) -> Any:
    lowered = [token.lower() for token in tokens]
    for member in enum_cls:
        text = f"{member.name} {member.value}".lower()
        if all(token in text for token in lowered):
            return member
    raise AssertionError(
        f"No member in {enum_cls.__name__} matched tokens {tokens}"
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


def _set_predicate_type(data: dict[str, Any], predicate_type: Any) -> None:
    if _set_first_existing(
        data,
        (
            "predicate_type",
            "match_predicate_type",
            "predicate",
        ),
        predicate_type,
    ):
        return

    predicate_value = getattr(predicate_type, "value", predicate_type)
    predicate_payload: dict[str, Any]
    if predicate_value == "eq":
        predicate_payload = {"kind": "eq"}
    elif predicate_value == "abs_diff_le":
        predicate_payload = {"kind": "abs_diff_le", "max_diff": 0}
    elif predicate_value == "mod_eq":
        predicate_payload = {
            "kind": "mod_eq",
            "divisor": 2,
            "remainder": 0,
        }
    else:
        predicate_payload = {"kind": str(predicate_value)}

    if _set_first_existing(
        data,
        ("match_predicate",),
        predicate_payload,
    ):
        return

    predicate = data.get("predicate")
    if isinstance(predicate, dict):
        data["predicate"] = dict(predicate_payload)
        return

    raise AssertionError("Unable to set sequence_dp predicate field")


def _set_scores(
    data: dict[str, Any],
    *,
    match_score: int,
    mismatch_score: int,
    gap_score: int,
) -> None:
    direct_set = [
        _set_first_existing(data, ("match_score",), match_score),
        _set_first_existing(data, ("mismatch_score",), mismatch_score),
        _set_first_existing(data, ("gap_score",), gap_score),
    ]
    if all(direct_set):
        return

    scoring = data.get("scoring")
    if isinstance(scoring, dict):
        scoring_copy = dict(scoring)
        scoring_copy["match_score"] = match_score
        scoring_copy["mismatch_score"] = mismatch_score
        scoring_copy["gap_score"] = gap_score
        data["scoring"] = scoring_copy
        return

    raise AssertionError("Unable to set sequence_dp scoring fields")


def _make_spec(
    *,
    template: Any,
    output_mode: Any,
    predicate_type: Any,
    match_score: int,
    mismatch_score: int,
    gap_score: int,
    tie_break: Any,
    seed: int,
) -> Any:
    spec, _ = _sample_spec_and_axes(seed=seed)
    dump = spec.model_dump()

    if not _set_first_existing(dump, ("template",), template):
        _set_first_existing(dump, ("template_type",), template)

    if not _set_first_existing(dump, ("output_mode",), output_mode):
        _set_first_existing(dump, ("mode",), output_mode)

    _set_predicate_type(dump, predicate_type)
    _set_scores(
        dump,
        match_score=match_score,
        mismatch_score=mismatch_score,
        gap_score=gap_score,
    )

    if not _set_first_existing(
        dump,
        (
            "step_tie_break",
            "tie_break_order",
            "tie_break",
        ),
        tie_break,
    ):
        traceback = dump.get("traceback")
        if isinstance(traceback, dict):
            tb_copy = dict(traceback)
            tb_copy["step_tie_break"] = tie_break
            dump["traceback"] = tb_copy
        else:
            raise AssertionError("Unable to set sequence_dp tie-break field")

    return SequenceDpSpec.model_validate(dump)


def _tie_break_steps(order: Any) -> list[str]:
    value = getattr(order, "value", order)
    text = f"{order.name} {value}".lower()
    return re.findall(r"diag|up|left|gap", text)


def _pair_from_input(input_value: Any) -> tuple[Any, Any]:
    if isinstance(input_value, dict):
        if "a" in input_value and "b" in input_value:
            return input_value["a"], input_value["b"]
        if "left" in input_value and "right" in input_value:
            return input_value["left"], input_value["right"]

    if isinstance(input_value, (tuple, list)) and len(input_value) == 2:
        return input_value[0], input_value[1]

    if hasattr(input_value, "a") and hasattr(input_value, "b"):
        return input_value.a, input_value.b

    raise AssertionError(
        "Query input is not a recognized sequence pair shape: "
        f"{type(input_value).__name__}"
    )


class TestModels:
    def test_spec_and_axes_roundtrip(self) -> None:
        spec, axes = _sample_spec_and_axes(seed=42)

        validated_spec = SequenceDpSpec.model_validate(spec.model_dump())
        validated_axes = SequenceDpAxes.model_validate(axes.model_dump())

        assert validated_spec.model_dump() == spec.model_dump()
        assert validated_axes.model_dump() == axes.model_dump()

    def test_axes_reject_bad_mutation(self) -> None:
        _, axes = _sample_spec_and_axes(seed=43)
        dump = axes.model_dump()

        for key, value in dump.items():
            if (
                key.endswith("_range")
                and isinstance(value, (tuple, list))
                and len(value) == 2
                and all(isinstance(x, int) for x in value)
            ):
                lo, hi = int(value[0]), int(value[1])
                bad = dict(dump)
                bad[key] = (max(lo, hi) + 1, min(lo, hi))
                with pytest.raises(Exception):
                    SequenceDpAxes.model_validate(bad)
                return

        _assert_has_invalid_rejected(SequenceDpAxes, axes)

    @pytest.mark.parametrize(
        ("field_name", "range_value"),
        [
            ("len_a_range", (False, 3)),
            ("len_b_range", (0, True)),
            ("value_range", (False, 5)),
            ("match_score_range", (0, True)),
            ("mismatch_score_range", (False, 0)),
            ("gap_score_range", (0, True)),
            ("abs_diff_range", (False, 2)),
            ("divisor_range", (2, True)),
        ],
    )
    def test_axes_reject_bool_in_int_range_bounds(
        self, field_name: str, range_value: tuple[int | bool, int | bool]
    ) -> None:
        with pytest.raises(
            Exception,
            match=rf"{field_name}: bool is not allowed for int range bounds",
        ):
            SequenceDpAxes.model_validate({field_name: range_value})

    @pytest.mark.parametrize(
        ("field_name", "value"),
        [
            ("match_score", 1 << 63),
            ("mismatch_score", -(1 << 63) - 1),
            ("gap_score", 1 << 63),
        ],
    )
    def test_spec_rejects_i64_out_of_range_scores(
        self, field_name: str, value: int
    ) -> None:
        payload = {
            "template": "global",
            "output_mode": "score",
            "match_predicate": {"kind": "eq"},
            "match_score": 1,
            "mismatch_score": 0,
            "gap_score": 0,
            "step_tie_break": TieBreakOrder.DIAG_UP_LEFT.value,
        }
        payload[field_name] = value
        with pytest.raises(Exception, match=field_name):
            SequenceDpSpec.model_validate(payload)

    def test_spec_rejects_i64_out_of_range_predicate_constants(self) -> None:
        with pytest.raises(Exception, match="max_diff"):
            SequenceDpSpec.model_validate(
                {
                    "template": "global",
                    "output_mode": "score",
                    "match_predicate": {
                        "kind": "abs_diff_le",
                        "max_diff": 1 << 63,
                    },
                    "match_score": 1,
                    "mismatch_score": 0,
                    "gap_score": 0,
                    "step_tie_break": TieBreakOrder.DIAG_UP_LEFT.value,
                }
            )
        with pytest.raises(Exception, match="divisor"):
            SequenceDpSpec.model_validate(
                {
                    "template": "global",
                    "output_mode": "score",
                    "match_predicate": {
                        "kind": "mod_eq",
                        "divisor": 1 << 63,
                        "remainder": 0,
                    },
                    "match_score": 1,
                    "mismatch_score": 0,
                    "gap_score": 0,
                    "step_tie_break": TieBreakOrder.DIAG_UP_LEFT.value,
                }
            )

    @pytest.mark.parametrize(
        ("field_name", "range_value"),
        [
            ("value_range", (-(1 << 63) - 1, 0)),
            ("value_range", (0, 1 << 63)),
            ("match_score_range", (-(1 << 63) - 1, 0)),
            ("mismatch_score_range", (0, 1 << 63)),
            ("gap_score_range", (0, 1 << 63)),
            ("abs_diff_range", (0, 1 << 63)),
            ("divisor_range", (1, 1 << 63)),
        ],
    )
    def test_axes_reject_i64_out_of_range_bounds(
        self, field_name: str, range_value: tuple[int, int]
    ) -> None:
        with pytest.raises(Exception, match=field_name):
            SequenceDpAxes.model_validate({field_name: range_value})


class TestEvaluatorSemantics:
    def test_global_eq_scoring_known_small_case(self) -> None:
        global_template = _enum_member(TemplateType, "global")
        score_mode = _enum_member(OutputMode, "score")
        eq_predicate = _enum_member(PredicateType, "eq")
        tie_break = list(TieBreakOrder)[0]

        spec = _make_spec(
            template=global_template,
            output_mode=score_mode,
            predicate_type=eq_predicate,
            match_score=2,
            mismatch_score=-1,
            gap_score=-2,
            tie_break=tie_break,
            seed=50,
        )

        # a=[1,2], b=[1,3] under global alignment gives final score 1.
        assert eval_sequence_dp(spec, [1, 2], [1, 3]) == 1

    def test_local_all_negative_returns_zero(self) -> None:
        local_template = _enum_member(TemplateType, "local")
        score_mode = _enum_member(OutputMode, "score")
        eq_predicate = _enum_member(PredicateType, "eq")
        tie_break = list(TieBreakOrder)[0]

        spec = _make_spec(
            template=local_template,
            output_mode=score_mode,
            predicate_type=eq_predicate,
            match_score=-1,
            mismatch_score=-2,
            gap_score=-3,
            tie_break=tie_break,
            seed=51,
        )

        assert eval_sequence_dp(spec, [1, 2], [1, 2]) == 0

    def test_score_accumulation_uses_i64_wrap_semantics(self) -> None:
        min_i64 = -(1 << 63)
        spec = SequenceDpSpec(
            template=TemplateType.GLOBAL,
            output_mode=OutputMode.SCORE,
            match_predicate=PredicateEq(),
            match_score=1,
            mismatch_score=-1,
            gap_score=min_i64,
            step_tie_break=TieBreakOrder.DIAG_UP_LEFT,
        )

        # Two forced global gap steps: min_i64 + min_i64 wraps to 0.
        assert eval_sequence_dp(spec, [7, 8], []) == 0

    def test_mod_eq_predicate_subtraction_uses_i64_wrap(self) -> None:
        max_i64 = (1 << 63) - 1
        spec = SequenceDpSpec(
            template=TemplateType.GLOBAL,
            output_mode=OutputMode.SCORE,
            match_predicate=PredicateModEq(divisor=3, remainder=1),
            match_score=9,
            mismatch_score=-4,
            gap_score=-2,
            step_tie_break=TieBreakOrder.DIAG_UP_LEFT,
        )

        # (max_i64 - (-1)) wraps to min_i64, floorMod(min_i64, 3) == 1.
        assert eval_sequence_dp(spec, [max_i64], [-1]) == 9

    def test_tie_break_order_changes_traceback_output_deterministically(
        self,
    ) -> None:
        global_template = _enum_member(TemplateType, "global")
        alignment_len_mode = _enum_member(OutputMode, "alignment", "len")
        eq_predicate = _enum_member(PredicateType, "eq")

        diag_first = None
        non_diag_first = None
        for order in TieBreakOrder:
            steps = _tie_break_steps(order)
            if not steps:
                continue
            if steps[0] == "diag" and diag_first is None:
                diag_first = order
            if steps[0] in {"up", "left", "gap"} and non_diag_first is None:
                non_diag_first = order

        if diag_first is None or non_diag_first is None:
            pytest.skip(
                "Need both diag-first and non-diag-first tie-break orders"
            )

        spec_diag = _make_spec(
            template=global_template,
            output_mode=alignment_len_mode,
            predicate_type=eq_predicate,
            match_score=0,
            mismatch_score=0,
            gap_score=0,
            tie_break=diag_first,
            seed=52,
        )
        spec_non_diag = _make_spec(
            template=global_template,
            output_mode=alignment_len_mode,
            predicate_type=eq_predicate,
            match_score=0,
            mismatch_score=0,
            gap_score=0,
            tie_break=non_diag_first,
            seed=53,
        )

        out_diag = eval_sequence_dp(spec_diag, [7], [9])
        out_non_diag = eval_sequence_dp(spec_non_diag, [7], [9])

        # With all-zero scores on 1x1, diag-first takes one step; gap-first
        # style takes two.
        assert out_diag == 1
        assert out_non_diag == 2
        assert out_diag != out_non_diag


class TestSampler:
    def test_sampler_is_deterministic_for_seed(self) -> None:
        axes = _normalize_axes_for_deterministic_sampling(
            SequenceDpAxes(), SequenceDpAxes
        )
        spec1 = _call_sample(sample_sequence_dp_spec, axes, seed=99)
        spec2 = _call_sample(sample_sequence_dp_spec, axes, seed=99)

        assert spec1.model_dump() == spec2.model_dump()

    def test_sampler_produces_varied_templates_and_modes(self) -> None:
        axes = SequenceDpAxes()
        specs = [
            _call_sample(
                sample_sequence_dp_spec, axes, seed=5000 + i
            ).model_dump()
            for i in range(24)
        ]
        signatures = {
            (
                spec["template"],
                spec["output_mode"],
                spec["match_predicate"]["kind"],
            )
            for spec in specs
        }
        assert len(signatures) >= 6


class TestQueries:
    def test_queries_cover_all_tags_and_match_evaluator(self) -> None:
        spec, axes = _sample_spec_and_axes(seed=60)
        queries = _call_queries(
            generate_sequence_dp_queries,
            spec,
            axes,
            seed=60,
        )

        assert queries
        assert {q.tag for q in queries} == set(QueryTag)

        for q in queries:
            a, b = _pair_from_input(q.input)
            assert q.output == eval_sequence_dp(spec, a, b)

    def test_queries_and_tasks_match_eval_across_multiple_seeds(self) -> None:
        axes = _normalize_axes_for_deterministic_sampling(
            SequenceDpAxes(), SequenceDpAxes
        )

        for seed in range(200, 212):
            spec = _call_sample(sample_sequence_dp_spec, axes, seed=seed)
            queries = _call_queries(
                generate_sequence_dp_queries,
                spec,
                axes,
                seed=seed,
            )

            assert queries
            assert {q.tag for q in queries} == set(QueryTag)
            for q in queries:
                a, b = _pair_from_input(q.input)
                assert q.output == eval_sequence_dp(spec, a, b)

        for seed in range(300, 312):
            task = _call_task(generate_sequence_dp_task, axes, seed=seed)
            spec = SequenceDpSpec.model_validate(task.spec)

            assert task.queries
            assert {q.tag for q in task.queries} == set(QueryTag)
            for q in task.queries:
                a, b = _pair_from_input(q.input)
                assert q.output == eval_sequence_dp(spec, a, b)

    def test_queries_respect_value_range_for_narrow_axes(self) -> None:
        axes = SequenceDpAxes(
            len_a_range=(12, 12),
            len_b_range=(12, 12),
            value_range=(17, 19),
        )
        spec = _call_sample(sample_sequence_dp_spec, axes, seed=901)
        queries = _call_queries(
            generate_sequence_dp_queries,
            spec,
            axes,
            seed=901,
        )

        lo, hi = axes.value_range
        for q in queries:
            a, b = _pair_from_input(q.input)
            assert all(lo <= v <= hi for v in a)
            assert all(lo <= v <= hi for v in b)


class TestTaskGeneration:
    def test_generate_sequence_dp_task_basics_and_query_outputs(self) -> None:
        axes = _normalize_axes_for_deterministic_sampling(
            SequenceDpAxes(), SequenceDpAxes
        )
        task = _call_task(generate_sequence_dp_task, axes, seed=61)

        assert task.family == "sequence_dp"
        assert task.task_id
        assert task.code
        assert task.queries

        spec = SequenceDpSpec.model_validate(task.spec)
        for q in task.queries:
            a, b = _pair_from_input(q.input)
            assert q.output == eval_sequence_dp(spec, a, b)

    def test_rendered_python_matches_evaluator(self) -> None:
        spec, axes = _sample_spec_and_axes(seed=62)
        code = render_sequence_dp(spec, func_name="f")
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        fn_obj = namespace["f"]
        assert callable(fn_obj)
        fn = cast(Callable[[list[int], list[int]], int], fn_obj)

        queries = _call_queries(
            generate_sequence_dp_queries,
            spec,
            axes,
            seed=62,
        )
        for q in queries:
            a, b = _pair_from_input(q.input)
            expected = eval_sequence_dp(spec, a, b)
            actual = fn(a, b)
            assert actual == expected

    def test_rendered_python_matches_evaluator_overflow_score_case(
        self,
    ) -> None:
        spec = SequenceDpSpec.model_validate(
            {
                "template": "global",
                "output_mode": "score",
                "match_predicate": {"kind": "eq"},
                "match_score": (1 << 63) - 1,
                "mismatch_score": 0,
                "gap_score": 0,
                "step_tie_break": TieBreakOrder.DIAG_UP_LEFT.value,
            }
        )
        code = render_sequence_dp(spec, func_name="f")
        namespace: dict[str, object] = {}
        exec(code, namespace)  # noqa: S102
        fn_obj = namespace["f"]
        assert callable(fn_obj)
        fn = cast(Callable[[list[int], list[int]], int], fn_obj)

        a = [1, 1]
        b = [1, 1]
        assert fn(a, b) == eval_sequence_dp(spec, a, b)
