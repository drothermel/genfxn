from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from genfxn.core.models import Task
from genfxn.core.task_ids import validate_task_ids
from genfxn.verification.adapters import evaluate_input, validate_spec_for_task
from genfxn.verification.layer1 import generate_layer1_cases
from genfxn.verification.layer2 import generate_layer2_cases
from genfxn.verification.layer3 import generate_layer3_cases
from genfxn.verification.models import (
    VerificationCase,
    VerificationFailure,
    VerificationLayer,
    VerificationMetrics,
    normalize_case_value,
)
from genfxn.verification.parity import run_parity_checks


@dataclass(frozen=True)
class VerificationArtifacts:
    cases: tuple[VerificationCase, ...]
    metrics: tuple[VerificationMetrics, ...]


def _allocate_family_heldout_budgets(
    tasks: Sequence[Task],
    *,
    heldout_mutants_per_family: int,
) -> list[int]:
    allocations = [0] * len(tasks)
    if heldout_mutants_per_family <= 0:
        return allocations

    family_indices: dict[str, list[int]] = defaultdict(list)
    for task_index, task in enumerate(tasks):
        family_indices[task.family].append(task_index)

    for family in sorted(family_indices):
        indices = sorted(
            family_indices[family],
            key=lambda index: (tasks[index].task_id, index),
        )
        if not indices:
            continue
        base = heldout_mutants_per_family // len(indices)
        remainder = heldout_mutants_per_family % len(indices)
        for position, task_index in enumerate(indices):
            allocations[task_index] = base + (1 if position < remainder else 0)

    return allocations


def _ci95_for_rate(rate: float, n: int) -> float:
    if n <= 0:
        return 0.0
    return 1.96 * math.sqrt(rate * (1.0 - rate) / n)


def build_verification_artifacts(
    tasks: list[Task],
    *,
    layer2_case_count: int = 128,
    layer3_mutation_budget: int = 24,
    heldout_mutants: int = 50,
    seed: int = 0,
) -> VerificationArtifacts:
    all_cases: list[VerificationCase] = []
    all_metrics: list[VerificationMetrics] = []
    family_heldout_distinguishable: dict[str, int] = defaultdict(int)
    family_heldout_escapes: dict[str, int] = defaultdict(int)
    family_metric_indices: dict[str, list[int]] = defaultdict(list)
    heldout_allocations = _allocate_family_heldout_budgets(
        tasks,
        heldout_mutants_per_family=heldout_mutants,
    )

    for task_index, task in enumerate(tasks):
        issues = validate_task_ids(task)
        if issues:
            details = "; ".join(
                f"{issue.code}: {issue.message}" for issue in issues
            )
            raise ValueError(
                f"Task {task.task_id} failed id validation: {details}"
            )

        layer1_cases = generate_layer1_cases(task)
        layer2_cases = generate_layer2_cases(
            task,
            count=layer2_case_count,
            seed=seed,
        )
        layer3_summary = generate_layer3_cases(
            task,
            layer1_inputs=[case.input for case in layer1_cases],
            layer2_inputs=[case.input for case in layer2_cases],
            budget=layer3_mutation_budget,
            heldout_mutants=heldout_allocations[task_index],
            seed=seed,
        )

        task_cases = [*layer1_cases, *layer2_cases, *layer3_summary.cases]
        all_cases.extend(task_cases)
        all_metrics.append(
            VerificationMetrics(
                task_id=task.task_id,
                family=task.family,
                n_layer1_cases=len(layer1_cases),
                n_layer2_cases=len(layer2_cases),
                n_layer3_cases=len(layer3_summary.cases),
                mutation_score=layer3_summary.mutation_score,
                mutation_score_curve=layer3_summary.mutation_score_curve,
                heldout_mutant_fpr=0.0,
                heldout_mutant_fpr_ci95=0.0,
            )
        )
        metric_index = len(all_metrics) - 1
        family_metric_indices[task.family].append(metric_index)
        family_heldout_distinguishable[task.family] += (
            layer3_summary.heldout_distinguishable_mutants
        )
        family_heldout_escapes[task.family] += (
            layer3_summary.heldout_mutant_escapes
        )

    for family, metric_indices in family_metric_indices.items():
        total_distinguishable = family_heldout_distinguishable[family]
        total_escapes = family_heldout_escapes[family]
        heldout_mutant_fpr = (
            total_escapes / total_distinguishable
            if total_distinguishable
            else 0.0
        )
        heldout_mutant_fpr_ci95 = _ci95_for_rate(
            heldout_mutant_fpr,
            total_distinguishable,
        )
        for metric_index in metric_indices:
            all_metrics[metric_index].heldout_mutant_fpr = heldout_mutant_fpr
            all_metrics[
                metric_index
            ].heldout_mutant_fpr_ci95 = heldout_mutant_fpr_ci95

    return VerificationArtifacts(
        cases=tuple(all_cases), metrics=tuple(all_metrics)
    )


def _validated_spec_for_task(
    task: Task,
    spec_cache: dict[str, Any],
) -> Any:
    try:
        return spec_cache[task.task_id]
    except KeyError:
        spec_obj = validate_spec_for_task(task.family, task.spec)
        spec_cache[task.task_id] = spec_obj
        return spec_obj


def _verify_case(
    task: Task,
    case: VerificationCase,
    spec_cache: dict[str, Any],
) -> str | None:
    try:
        spec_obj = _validated_spec_for_task(task, spec_cache)
        actual = normalize_case_value(
            evaluate_input(task.family, spec_obj, case.input)
        )
    except Exception as exc:
        return (
            f"failed to execute case {case.case_id}: "
            f"{type(exc).__name__}: {exc}"
        )

    expected = case.expected_output
    if actual != expected:
        return f"expected {expected!r}, got {actual!r} for case {case.case_id}"

    return None


def verify_cases(
    tasks: list[Task],
    cases: Sequence[VerificationCase],
    *,
    full_parity: bool = True,
    parity_case_count: int = 48,
) -> list[VerificationFailure]:
    by_task_id = {task.task_id: task for task in tasks}
    spec_cache: dict[str, Any] = {}
    failures: list[VerificationFailure] = []

    for case in cases:
        task = by_task_id.get(case.task_id)
        if task is None:
            failures.append(
                VerificationFailure(
                    task_id=case.task_id,
                    family=case.family,
                    case_id=case.case_id,
                    message=(
                        "task_id not present in dataset for verification case"
                    ),
                )
            )
            continue

        message = _verify_case(task, case, spec_cache)
        if message is None:
            continue

        failures.append(
            VerificationFailure(
                task_id=case.task_id,
                family=case.family,
                case_id=case.case_id,
                message=message,
            )
        )

    if full_parity and tasks:
        for parity_failure in run_parity_checks(
            tasks,
            cases,
            parity_case_count=parity_case_count,
        ):
            failures.append(
                VerificationFailure(
                    task_id=parity_failure.task_id,
                    family=parity_failure.family,
                    case_id=parity_failure.case_id,
                    message=(
                        f"[{parity_failure.language}] {parity_failure.message}"
                    ),
                )
            )

    return failures


def summarize_case_counts(cases: Sequence[VerificationCase]) -> dict[str, int]:
    counts = {member.value: 0 for member in VerificationLayer}
    for case in cases:
        counts[case.layer.value] += 1
    return counts
