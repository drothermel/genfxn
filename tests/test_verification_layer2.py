import random

import pytest

from genfxn.piecewise.task import generate_piecewise_task
from genfxn.verification.layer2 import generate_layer2_cases
from genfxn.verification.models import VerificationLayer


def test_layer2_generation_is_deterministic_for_same_seed() -> None:
    task = generate_piecewise_task(rng=random.Random(9))
    first = generate_layer2_cases(task, seed=23)
    second = generate_layer2_cases(task, seed=23)
    assert [case.model_dump(mode="json") for case in first] == [
        case.model_dump(mode="json") for case in second
    ]
    assert len(first) == 128


def test_layer2_generation_changes_with_seed() -> None:
    task = generate_piecewise_task(rng=random.Random(9))
    first = generate_layer2_cases(task, seed=23)
    second = generate_layer2_cases(task, seed=24)
    assert [case.input for case in first] != [case.input for case in second]


def test_layer2_cases_have_expected_metadata() -> None:
    task = generate_piecewise_task(rng=random.Random(11))
    cases = generate_layer2_cases(task, seed=3)
    assert all(
        case.layer == VerificationLayer.LAYER2_PROPERTY for case in cases
    )
    assert all(
        case.source_detail.get("generator") == "hypothesis" for case in cases
    )


def test_layer2_generation_fails_when_budget_cannot_be_filled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = generate_piecewise_task(rng=random.Random(7))
    monkeypatch.setattr(
        "genfxn.verification.layer2.generate_layer2_inputs",
        lambda *args, **kwargs: [],  # noqa: ARG005
    )
    with pytest.raises(ValueError, match="Unable to generate"):
        _ = generate_layer2_cases(task, count=8, seed=0)
