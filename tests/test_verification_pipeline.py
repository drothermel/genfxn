import random
from pathlib import Path
from types import SimpleNamespace

import pytest
import srsly

from genfxn.core.models import Query, QueryTag
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.stack_bytecode.task import generate_stack_bytecode_task
from genfxn.stateful.task import generate_stateful_task
from genfxn.verification.io import (
    load_verification_sidecars,
    write_verification_sidecars,
)
from genfxn.verification.layer1 import generate_layer1_cases
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
    layer2_cases = [
        case
        for case in first.cases
        if case.layer == VerificationLayer.LAYER2_PROPERTY
    ]
    assert layer2_cases
    assert all(
        case.source_detail.get("generator") == "hypothesis"
        for case in layer2_cases
    )


def test_layer1_generation_is_independent_of_task_queries() -> None:
    task = generate_piecewise_task(rng=random.Random(12))
    original_cases = generate_layer1_cases(task)
    task_with_tampered_queries = task.model_copy(
        update={
            "queries": [
                Query(
                    input=12345,
                    output=-99999,
                    tag=QueryTag.TYPICAL,
                )
            ]
        }
    )

    tampered_cases = generate_layer1_cases(task_with_tampered_queries)
    assert [case.model_dump(mode="json") for case in original_cases] == [
        case.model_dump(mode="json") for case in tampered_cases
    ]


def test_layer1_generation_produces_cases_when_queries_empty() -> None:
    task = generate_piecewise_task(rng=random.Random(13))
    task_without_queries = task.model_copy(update={"queries": []})

    cases = generate_layer1_cases(task_without_queries)
    assert len(cases) > 0
    assert all(
        case.layer == VerificationLayer.LAYER1_SPEC_BOUNDARY for case in cases
    )


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
    assert verify_cases([task], loaded_cases, full_parity=False) == []


def test_load_sidecars_accepts_legacy_heldout_escape_metric_fields(
    tmp_path: Path,
) -> None:
    task = generate_piecewise_task(rng=random.Random(13))
    artifacts = build_verification_artifacts([task], seed=7)

    cases_path = tmp_path / "cases.jsonl"
    metrics_path = tmp_path / "metrics.jsonl"
    write_verification_sidecars(
        cases_path,
        metrics_path,
        cases=artifacts.cases,
        metrics=artifacts.metrics,
    )

    metrics_rows = list(srsly.read_jsonl(metrics_path))
    assert metrics_rows
    row = dict(metrics_rows[0])
    row["heldout_mutant_escape_rate"] = row.pop("heldout_mutant_fpr")
    row["heldout_mutant_escape_ci95"] = row.pop("heldout_mutant_fpr_ci95")
    srsly.write_jsonl(metrics_path, [row])

    _, loaded_metrics = load_verification_sidecars(cases_path, metrics_path)
    assert (
        loaded_metrics[0].heldout_mutant_fpr
        == row["heldout_mutant_escape_rate"]
    )
    assert (
        loaded_metrics[0].heldout_mutant_fpr_ci95
        == row["heldout_mutant_escape_ci95"]
    )


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


def test_verify_cases_runs_parity_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = generate_piecewise_task(rng=random.Random(3))
    artifacts = build_verification_artifacts([task], seed=11)
    calls: list[int] = []

    def _fake_run_parity_checks(tasks, cases, parity_case_count):  # noqa: ANN001
        calls.append(parity_case_count)
        return []

    monkeypatch.setattr(
        "genfxn.verification.runner.run_parity_checks",
        _fake_run_parity_checks,
    )

    failures = verify_cases([task], artifacts.cases)
    assert failures == []
    assert calls == [48]


def test_verify_cases_caches_validated_spec_per_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = generate_piecewise_task(rng=random.Random(3))
    cases = [
        VerificationCase(
            task_id=task.task_id,
            family=task.family,
            layer=VerificationLayer.LAYER1_SPEC_BOUNDARY,
            case_id="layer1-0000",
            input=1,
            expected_output=1,
        ),
        VerificationCase(
            task_id=task.task_id,
            family=task.family,
            layer=VerificationLayer.LAYER1_SPEC_BOUNDARY,
            case_id="layer1-0001",
            input=2,
            expected_output=2,
        ),
    ]
    validate_calls: list[str] = []

    monkeypatch.setattr(
        "genfxn.verification.runner.validate_spec_for_task",
        lambda family, spec: validate_calls.append(task.task_id) or spec,  # noqa: ARG005
    )
    monkeypatch.setattr(
        "genfxn.verification.runner.evaluate_input",
        lambda family, spec_obj, input_value: input_value,  # noqa: ARG005
    )

    failures = verify_cases([task], cases, full_parity=False)
    assert failures == []
    assert validate_calls == [task.task_id]


def test_summarize_case_counts_initializes_from_enum() -> None:
    counts = summarize_case_counts([])
    assert counts == {
        VerificationLayer.LAYER1_SPEC_BOUNDARY.value: 0,
        VerificationLayer.LAYER2_PROPERTY.value: 0,
        VerificationLayer.LAYER3_MUTATION.value: 0,
    }


def test_build_verification_artifacts_uses_family_level_heldout_metrics(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    piecewise_a = generate_piecewise_task(rng=random.Random(3))
    piecewise_b = generate_piecewise_task(rng=random.Random(5))
    stateful = generate_stateful_task(rng=random.Random(7))
    tasks = [piecewise_a, piecewise_b, stateful]
    seen_heldout_budgets: dict[str, int] = {}

    monkeypatch.setattr(
        "genfxn.verification.runner.generate_layer1_cases",
        lambda task: [],  # noqa: ARG005
    )
    monkeypatch.setattr(
        "genfxn.verification.runner.generate_layer2_cases",
        lambda task, count, seed: [],  # noqa: ARG005
    )

    def _fake_generate_layer3_cases(
        task,  # noqa: ANN001
        *,
        layer1_inputs,  # noqa: ARG001
        layer2_inputs,  # noqa: ARG001
        budget,  # noqa: ARG001
        heldout_mutants,  # noqa: ANN001
        seed,  # noqa: ARG001
    ) -> SimpleNamespace:
        seen_heldout_budgets[task.task_id] = heldout_mutants
        if task.family == "piecewise":
            escapes = (
                0 if task.task_id == piecewise_a.task_id else heldout_mutants
            )
            distinguishable = heldout_mutants
        else:
            distinguishable = heldout_mutants
            escapes = heldout_mutants // 5
        return SimpleNamespace(
            cases=[],
            mutation_score=1.0,
            mutation_score_curve=[],
            heldout_mutant_fpr=0.0,
            heldout_mutant_fpr_ci95=0.0,
            heldout_distinguishable_mutants=distinguishable,
            heldout_mutant_escapes=escapes,
        )

    monkeypatch.setattr(
        "genfxn.verification.runner.generate_layer3_cases",
        _fake_generate_layer3_cases,
    )

    artifacts = build_verification_artifacts(tasks, heldout_mutants=50, seed=11)
    metrics_by_task_id = {
        metric.task_id: metric for metric in artifacts.metrics
    }

    assert seen_heldout_budgets[piecewise_a.task_id] == 25
    assert seen_heldout_budgets[piecewise_b.task_id] == 25
    assert seen_heldout_budgets[stateful.task_id] == 50

    piecewise_a_metric = metrics_by_task_id[piecewise_a.task_id]
    piecewise_b_metric = metrics_by_task_id[piecewise_b.task_id]
    stateful_metric = metrics_by_task_id[stateful.task_id]

    assert piecewise_a_metric.heldout_mutant_fpr == pytest.approx(0.5)
    assert piecewise_b_metric.heldout_mutant_fpr == pytest.approx(0.5)
    assert piecewise_a_metric.heldout_mutant_fpr_ci95 == pytest.approx(
        piecewise_b_metric.heldout_mutant_fpr_ci95
    )
    assert stateful_metric.heldout_mutant_fpr == pytest.approx(0.2)
