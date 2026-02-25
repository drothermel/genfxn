import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from genfxn.piecewise.task import generate_piecewise_task
from genfxn.stack_bytecode.task import generate_stack_bytecode_task
from genfxn.verification.io import (
    load_verification_sidecars,
    write_verification_sidecars,
)
from genfxn.verification.models import VerificationCase, VerificationLayer
from genfxn.verification.parity import select_parity_cases
from genfxn.verification.runner import (
    build_verification_artifacts,
    summarize_case_counts,
    verify_cases,
)


def test_build_verification_artifacts_is_deterministic_for_same_seed() -> None:
    task = generate_piecewise_task(rng=random.Random(3))

    first = build_verification_artifacts([task], seed=17)
    second = build_verification_artifacts([task], seed=17)

    assert [case.model_dump(mode="json") for case in first.cases] == [
        case.model_dump(mode="json") for case in second.cases
    ]
    assert [metric.model_dump(mode="json") for metric in first.metrics] == [
        metric.model_dump(mode="json") for metric in second.metrics
    ]


def test_sidecar_roundtrip_keeps_cases_verifiable(tmp_path: Path) -> None:
    task = generate_stack_bytecode_task(rng=random.Random(9))
    artifacts = build_verification_artifacts([task], seed=5)

    cases_path = tmp_path / "cases.jsonl"
    metrics_path = tmp_path / "metrics.jsonl"
    write_verification_sidecars(
        cases_path,
        metrics_path,
        cases=artifacts.cases,
        metrics=artifacts.metrics,
    )

    loaded_cases, loaded_metrics = load_verification_sidecars(
        cases_path,
        metrics_path,
    )
    assert loaded_metrics
    assert verify_cases([task], loaded_cases) == []


def test_select_parity_cases_prioritizes_layer2() -> None:
    task_id = "task-1"
    family = "piecewise"
    cases = [
        VerificationCase(
            task_id=task_id,
            family=family,
            layer=VerificationLayer.LAYER1_SPEC_BOUNDARY,
            case_id="layer1-0001",
            input=1,
            expected_output=1,
        ),
        VerificationCase(
            task_id=task_id,
            family=family,
            layer=VerificationLayer.LAYER2_PROPERTY,
            case_id="layer2-0002",
            input=2,
            expected_output=2,
        ),
        VerificationCase(
            task_id=task_id,
            family=family,
            layer=VerificationLayer.LAYER2_PROPERTY,
            case_id="layer2-0001",
            input=3,
            expected_output=3,
        ),
    ]

    selected = select_parity_cases(cases, parity_case_count=2)
    assert [case.case_id for case in selected] == [
        "layer2-0001",
        "layer2-0002",
    ]


def test_verify_cases_includes_parity_failures_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = generate_piecewise_task(rng=random.Random(3))
    artifacts = build_verification_artifacts([task], seed=11)

    monkeypatch.setattr(
        "genfxn.verification.runner.run_parity_checks",
        lambda tasks, cases, parity_case_count: [  # noqa: ARG005
            SimpleNamespace(
                task_id=task.task_id,
                family=task.family,
                case_id="layer2-0001",
                language="java",
                message="mismatch",
            )
        ],
    )

    failures = verify_cases(
        [task],
        artifacts.cases,
        full_parity=True,
        parity_case_count=1,
    )
    assert failures
    assert "[java] mismatch" in failures[0].message


def test_summarize_case_counts_initializes_from_enum() -> None:
    counts = summarize_case_counts([])
    assert counts == {
        VerificationLayer.LAYER1_SPEC_BOUNDARY.value: 0,
        VerificationLayer.LAYER2_PROPERTY.value: 0,
        VerificationLayer.LAYER3_MUTATION.value: 0,
    }
