import random

import pytest

import genfxn.verification.layer3 as layer3_module
from genfxn.piecewise.task import generate_piecewise_task


def test_mutation_score_ignores_likely_equivalent_mutants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = generate_piecewise_task(rng=random.Random(3))
    mutants = [{"kind": "killable"}, {"kind": "equiv"}]
    call_count = 0

    def _fake_generate_valid_mutants(**kwargs):  # noqa: ANN003, ARG001
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return mutants
        return []

    def _fake_distinguishes(
        *,
        family: str,  # noqa: ARG001
        spec_obj: object,  # noqa: ARG001
        mutant_obj: object,
        input_value: object,
    ) -> tuple[bool, int]:
        if (
            isinstance(mutant_obj, dict)
            and mutant_obj.get("kind") == "killable"
            and input_value == 1
        ):
            return True, 17
        return False, 0

    monkeypatch.setattr(
        layer3_module, "_generate_valid_mutants", _fake_generate_valid_mutants
    )
    monkeypatch.setattr(
        layer3_module, "validate_spec_for_task", lambda family, spec: spec
    )
    monkeypatch.setattr(
        layer3_module,
        "generate_layer2_inputs",
        lambda *args, **kwargs: [],  # noqa: ARG005
    )
    monkeypatch.setattr(layer3_module, "_distinguishes", _fake_distinguishes)

    summary = layer3_module.generate_layer3_cases(
        task,
        layer1_inputs=[0],
        layer2_inputs=[1],
        budget=24,
        heldout_mutants=50,
        seed=0,
    )

    assert len(summary.cases) == 1
    assert summary.cases[0].input == 1
    assert summary.mutation_score == 1.0
    assert all(
        point.mutation_score == 1.0 for point in summary.mutation_score_curve
    )


def test_mutation_score_is_vacuously_full_when_no_mutant_is_distinguishable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = generate_piecewise_task(rng=random.Random(11))
    call_count = 0

    def _fake_generate_valid_mutants(**kwargs):  # noqa: ANN003, ARG001
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [{"kind": "equiv-only"}]
        return []

    monkeypatch.setattr(
        layer3_module, "_generate_valid_mutants", _fake_generate_valid_mutants
    )
    monkeypatch.setattr(
        layer3_module, "validate_spec_for_task", lambda family, spec: spec
    )
    monkeypatch.setattr(
        layer3_module,
        "generate_layer2_inputs",
        lambda *args, **kwargs: [],  # noqa: ARG005
    )
    monkeypatch.setattr(
        layer3_module,
        "_distinguishes",
        lambda **kwargs: (False, 0),  # noqa: ARG005
    )

    summary = layer3_module.generate_layer3_cases(
        task,
        layer1_inputs=[0],
        layer2_inputs=[1],
        budget=24,
        heldout_mutants=50,
        seed=0,
    )

    assert summary.cases == []
    assert summary.mutation_score == 1.0
    assert summary.heldout_mutant_escape_rate == 0.0
    assert all(
        point.mutation_score == 1.0 for point in summary.mutation_score_curve
    )
