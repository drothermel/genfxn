import random

import pytest

import genfxn.verification.layer3 as layer3_module
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.verification.adapters.base import Layer3MutantCandidate


def test_mutation_score_ignores_likely_equivalent_mutants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = generate_piecewise_task(rng=random.Random(3))
    mutants = [
        Layer3MutantCandidate(
            mutant_spec={"kind": "killable"},
            mutant_kind="test_mutant",
            rule_id="piecewise.test.killable",
            metadata={"source": "unit"},
        ),
        Layer3MutantCandidate(
            mutant_spec={"kind": "equiv"},
            mutant_kind="test_mutant",
            rule_id="piecewise.test.equiv",
            metadata={"source": "unit"},
        ),
    ]

    def _fake_generate_layer3_mutants(
        family: str,  # noqa: ARG001
        *,
        task_id: str,  # noqa: ARG001
        spec_obj: object,  # noqa: ARG001
        spec_dict: dict[str, object],  # noqa: ARG001
        budget: int,  # noqa: ARG001
        seed: int,  # noqa: ARG001
        mode: str,
    ) -> list[Layer3MutantCandidate]:
        if mode == "train":
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
        layer3_module, "generate_layer3_mutants", _fake_generate_layer3_mutants
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
    assert summary.cases[0].source_detail["mutant_kind"] == "test_mutant"
    assert (
        summary.cases[0].source_detail["rule_id"] == "piecewise.test.killable"
    )
    assert summary.mutation_score == 1.0
    assert all(
        point.mutation_score == 1.0 for point in summary.mutation_score_curve
    )


def test_mutation_score_is_vacuously_full_when_no_mutant_is_distinguishable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = generate_piecewise_task(rng=random.Random(11))
    train_mutants = [
        Layer3MutantCandidate(
            mutant_spec={"kind": "equiv-only"},
            mutant_kind="test_mutant",
            rule_id="piecewise.test.equiv_only",
            metadata={},
        )
    ]

    def _fake_generate_layer3_mutants(
        family: str,  # noqa: ARG001
        *,
        task_id: str,  # noqa: ARG001
        spec_obj: object,  # noqa: ARG001
        spec_dict: dict[str, object],  # noqa: ARG001
        budget: int,  # noqa: ARG001
        seed: int,  # noqa: ARG001
        mode: str,
    ) -> list[Layer3MutantCandidate]:
        if mode == "train":
            return train_mutants
        return []

    monkeypatch.setattr(
        layer3_module, "generate_layer3_mutants", _fake_generate_layer3_mutants
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
    assert summary.heldout_mutant_fpr == 0.0
    assert all(
        point.mutation_score == 1.0 for point in summary.mutation_score_curve
    )
