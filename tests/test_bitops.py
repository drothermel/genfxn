import random
from types import ModuleType
from typing import Any

import pytest

from genfxn.core.difficulty import compute_difficulty
from genfxn.core.models import QueryTag

bitops_models = pytest.importorskip("genfxn.bitops.models")
bitops_eval = pytest.importorskip("genfxn.bitops.eval")
bitops_queries = pytest.importorskip("genfxn.bitops.queries")
bitops_sampler = pytest.importorskip("genfxn.bitops.sampler")
bitops_task = pytest.importorskip("genfxn.bitops.task")


def _find_callable(module: ModuleType, *names: str) -> Any:
    for name in names:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate
    for name in dir(module):
        candidate = getattr(module, name)
        if callable(candidate) and any(
            name.startswith(prefix)
            for prefix in ("eval_", "sample_", "generate_")
        ):
            return candidate
    raise AssertionError(f"No expected callable found in {module.__name__}")


def _find_model_class(module: ModuleType, suffix: str) -> Any:
    for name in dir(module):
        candidate = getattr(module, name)
        if (
            isinstance(candidate, type)
            and name.lower().endswith(suffix.lower())
            and hasattr(candidate, "model_validate")
            and hasattr(candidate, "model_dump")
        ):
            return candidate
    raise AssertionError(
        f"No pydantic model class ending with '{suffix}' in {module.__name__}"
    )


def _call_sample(sample_fn: Any, axes: Any, seed: int) -> Any:
    rng = random.Random(seed)
    try:
        return sample_fn(axes, rng)
    except TypeError:
        return sample_fn(axes=axes, rng=rng)


def _call_queries(
    generate_queries_fn: Any,
    spec: Any,
    axes: Any,
    seed: int,
) -> list[Any]:
    rng = random.Random(seed)
    try:
        return generate_queries_fn(spec, axes, rng)
    except TypeError:
        return generate_queries_fn(spec=spec, axes=axes, rng=rng)


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
        f"{model_cls.__name__} did not reject any of the invalid mutations"
    )


SpecCls = _find_model_class(bitops_models, "Spec")
AxesCls = _find_model_class(bitops_models, "Axes")
eval_bitops = _find_callable(bitops_eval, "eval_bitops")
sample_bitops_spec = _find_callable(bitops_sampler, "sample_bitops_spec")
generate_bitops_queries = _find_callable(
    bitops_queries, "generate_bitops_queries"
)
generate_bitops_task = _find_callable(bitops_task, "generate_bitops_task")


def _sample_spec_and_axes(seed: int = 42) -> tuple[Any, Any]:
    axes = _normalize_axes_for_deterministic_sampling(AxesCls(), AxesCls)
    spec = _call_sample(sample_bitops_spec, axes, seed=seed)
    return spec, axes


class TestModels:
    def test_spec_and_axes_roundtrip_model_validation(self) -> None:
        spec, axes = _sample_spec_and_axes(seed=42)
        assert SpecCls.model_validate(spec.model_dump()).model_dump() == (
            spec.model_dump()
        )
        assert AxesCls.model_validate(axes.model_dump()).model_dump() == (
            axes.model_dump()
        )

    def test_spec_and_axes_reject_invalid_mutations(self) -> None:
        spec, axes = _sample_spec_and_axes(seed=43)
        _assert_has_invalid_rejected(SpecCls, spec)
        _assert_has_invalid_rejected(AxesCls, axes)

    def test_width_bits_rejects_64_for_signed_backend_parity(self) -> None:
        bit_instruction_cls = getattr(bitops_models, "BitInstruction")
        bit_op = getattr(bitops_models, "BitOp")
        with pytest.raises(Exception):
            SpecCls(
                width_bits=64,
                operations=[bit_instruction_cls(op=bit_op.NOT)],
            )

    def test_width_choices_rejects_64(self) -> None:
        with pytest.raises(Exception):
            AxesCls(width_choices=[8, 64])


class TestEvaluatorSemantics:
    def test_evaluator_applies_fixed_width_semantics(self) -> None:
        bit_instruction_cls = getattr(bitops_models, "BitInstruction")
        bit_op = getattr(bitops_models, "BitOp")

        spec = SpecCls(
            width_bits=8,
            operations=[
                bit_instruction_cls(op=bit_op.XOR_MASK, arg=0xFF),
                bit_instruction_cls(op=bit_op.SHL, arg=1),
                bit_instruction_cls(op=bit_op.ROTR, arg=2),
                bit_instruction_cls(op=bit_op.POPCOUNT),
                bit_instruction_cls(op=bit_op.PARITY),
            ],
        )

        # x=0b0000_1111
        # xor 0xFF -> 0b1111_0000
        # shl 1 -> 0b1110_0000 (masked to 8 bits)
        # rotr 2 -> 0b0011_1000
        # popcount -> 3
        # parity(3) -> 0
        assert eval_bitops(spec, 0x0F) == 0

    def test_evaluator_is_deterministic_and_pure_for_same_input(self) -> None:
        spec, axes = _sample_spec_and_axes(seed=44)
        queries = _call_queries(generate_bitops_queries, spec, axes, seed=44)
        assert queries

        for q in queries[:5]:
            input_value = q.input
            if isinstance(input_value, list):
                before = list(input_value)
            else:
                before = input_value

            out1 = eval_bitops(spec, input_value)
            out2 = eval_bitops(spec, input_value)
            assert out1 == out2

            if isinstance(input_value, list):
                assert input_value == before
            else:
                assert input_value == before


class TestSampler:
    def test_sampler_is_deterministic_for_seed(self) -> None:
        axes = _normalize_axes_for_deterministic_sampling(AxesCls(), AxesCls)
        spec1 = _call_sample(sample_bitops_spec, axes, seed=99)
        spec2 = _call_sample(sample_bitops_spec, axes, seed=99)
        assert spec1.model_dump() == spec2.model_dump()

    def test_sampler_respects_target_difficulty_axis(self) -> None:
        def _sample_difficulty_average(target: int) -> float:
            axes = AxesCls(target_difficulty=target)
            rng = random.Random(2000 + target)
            scores = []
            for _ in range(120):
                spec = _call_sample(
                    sample_bitops_spec,
                    axes,
                    seed=rng.randint(0, 10**9),
                )
                scores.append(compute_difficulty("bitops", spec.model_dump()))
            return sum(scores) / len(scores)

        averages = {
            target: _sample_difficulty_average(target) for target in range(1, 6)
        }

        for target in range(1, 5):
            assert averages[target + 1] >= averages[target] + 0.1
        assert averages[5] >= averages[1] + 0.7


class TestQueries:
    def test_queries_cover_all_tags_and_match_evaluator_outputs(self) -> None:
        axes = AxesCls(
            width_choices=[8, 16],
            n_ops_range=(3, 4),
            value_range=(-7, 7),
            mask_range=(0, 255),
            shift_range=(0, 7),
        )
        spec = _call_sample(sample_bitops_spec, axes, seed=45)
        queries = _call_queries(generate_bitops_queries, spec, axes, seed=45)
        assert queries

        assert {q.tag for q in queries} == set(QueryTag)

        for q in queries:
            assert q.output == eval_bitops(spec, q.input)

    def test_queries_stay_within_signed_i64_bounds(self) -> None:
        axes = AxesCls(
            width_choices=[63],
            value_range=(-(1 << 80), (1 << 80)),
        )
        spec = SpecCls.model_validate(
            {
                "width_bits": 63,
                "operations": [{"op": "not"}],
            }
        )
        queries = _call_queries(generate_bitops_queries, spec, axes, seed=123)
        assert queries
        for q in queries:
            assert -(1 << 63) <= q.input <= (1 << 63) - 1


class TestTaskGeneration:
    def test_generate_bitops_task_basics(self) -> None:
        axes = _normalize_axes_for_deterministic_sampling(AxesCls(), AxesCls)
        task = _call_task(generate_bitops_task, axes, seed=46)

        assert task.task_id
        assert task.family == "bitops"
        assert task.description
        assert isinstance(task.code, str)
        assert task.queries

        spec = SpecCls.model_validate(task.spec)
        for q in task.queries:
            assert q.output == eval_bitops(spec, q.input)
