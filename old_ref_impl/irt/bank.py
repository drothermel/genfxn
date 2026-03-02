from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from genfxn.core.family_registry import generate_task_for_family
from genfxn.core.models import Task
from genfxn.core.predicates import PredicateType
from genfxn.core.spec_space import SpecCapacityError, enforce_spec_capacity
from genfxn.core.transforms import TransformType
from genfxn.fsm.models import FsmAxes
from genfxn.irt.io import write_json, write_jsonl
from genfxn.irt.models import EvalCaseExpectedRow, EvalCaseInputRow, ItemRow
from genfxn.irt.stratification import (
    StrataPlan,
    cell_distance,
    get_strata_plan,
    parse_cell_fields,
    primary_axis_value,
)
from genfxn.simple_algorithms.models import SimpleAlgorithmsAxes
from genfxn.stateful.models import StatefulAxes, TemplateType

_CALIBRATION_FAMILIES = (
    "stateful",
    "simple_algorithms",
    "fsm",
    "bitops",
)


class BankBuildSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bank_id: str
    out_dir: Path
    families: list[str] = Field(
        default_factory=lambda: list(_CALIBRATION_FAMILIES)
    )
    per_family_count: int = Field(default=300, ge=1)
    seed: int = 0
    prompt_version: str = "spec_to_outputs_v1"
    max_attempts_per_family: int = Field(default=250_000, ge=1)


@dataclass(frozen=True)
class BankBuildResult:
    bank_root: Path
    items_path: Path
    eval_cases_inputs_path: Path
    eval_cases_expected_path: Path
    manifest_path: Path


def _axes_for_family(family: str) -> Any:
    if family == "stateful":
        return StatefulAxes(
            templates=[
                TemplateType.CONDITIONAL_LINEAR_SUM,
                TemplateType.RESETTING_BEST_PREFIX_SUM,
                TemplateType.LONGEST_RUN,
            ],
            predicate_types=[
                PredicateType.EVEN,
                PredicateType.ODD,
                PredicateType.LT,
                PredicateType.LE,
                PredicateType.GT,
                PredicateType.GE,
                PredicateType.MOD_EQ,
            ],
            transform_types=[
                TransformType.IDENTITY,
                TransformType.ABS,
                TransformType.SHIFT,
                TransformType.NEGATE,
                TransformType.SCALE,
            ],
        )
    if family == "simple_algorithms":
        return SimpleAlgorithmsAxes(
            pre_filter_types=[
                PredicateType.EVEN,
                PredicateType.ODD,
                PredicateType.LT,
                PredicateType.LE,
                PredicateType.GT,
                PredicateType.GE,
                PredicateType.MOD_EQ,
            ],
            pre_transform_types=[
                TransformType.IDENTITY,
                TransformType.ABS,
                TransformType.SHIFT,
                TransformType.NEGATE,
                TransformType.SCALE,
                TransformType.PIPELINE,
            ],
        )
    if family == "fsm":
        return FsmAxes()
    if family == "bitops":
        return None
    raise ValueError(f"unsupported family {family!r} for IRT bank")


def _build_eval_rows(
    task: Task,
) -> tuple[list[EvalCaseInputRow], list[EvalCaseExpectedRow]]:
    case_inputs: list[EvalCaseInputRow] = []
    case_expected: list[EvalCaseExpectedRow] = []
    for idx, query in enumerate(task.queries):
        case_id = f"{task.task_id}-case-{idx:04d}"
        case_inputs.append(
            EvalCaseInputRow(
                item_id=task.task_id,
                case_id=case_id,
                input=query.input,
            )
        )
        case_expected.append(
            EvalCaseExpectedRow(
                item_id=task.task_id,
                case_id=case_id,
                expected_output=query.output,
            )
        )
    return case_inputs, case_expected


def _hash_manifest_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _feature_cell_key(family: str, features: dict[str, str]) -> str:
    if family == "stateful":
        return (
            f"{features['template']}|{features['predicate_class']}|"
            f"{features['transform_complexity']}"
        )
    if family == "simple_algorithms":
        template = features["template"]
        if template == "most_frequent":
            return (
                f"{template}|{features['tie_break']}|"
                f"{features['preprocess_bucket']}"
            )
        if template == "count_pairs_sum":
            return (
                f"{template}|{features['counting_mode']}|"
                f"{features['preprocess_bucket']}"
            )
        return (
            f"{template}|{features['k_bucket']}|{features['preprocess_bucket']}"
        )
    if family == "fsm":
        return (
            f"{features['output_mode']}|"
            f"{features['undefined_transition_policy']}|"
            f"{features['n_states_bucket']}"
        )
    if family == "bitops":
        return (
            f"{features['width_bits_bucket']}|{features['n_ops_bucket']}|"
            f"{features['op_mix_bucket']}"
        )
    raise ValueError(f"unsupported family for feature cell key: {family}")


def _redistribute_deficits(
    *,
    family: str,
    plan: StrataPlan,
    target_counts: dict[str, int],
    current_counts: dict[str, int],
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    deficits = {
        cell: max(0, target_counts[cell] - current_counts.get(cell, 0))
        for cell in target_counts
        if target_counts[cell] > current_counts.get(cell, 0)
    }
    redistributed = dict(target_counts)
    redistribution_log: dict[str, dict[str, int]] = {}

    for deficit_cell, deficit_count in deficits.items():
        if deficit_count <= 0:
            continue
        redistributed[deficit_cell] -= deficit_count
        source_fields = parse_cell_fields(family, deficit_cell)
        primary_value = primary_axis_value(plan, source_fields)

        same_primary = [
            cell
            for cell in redistributed
            if cell != deficit_cell
            and primary_axis_value(plan, parse_cell_fields(family, cell))
            == primary_value
        ]
        fallback = [cell for cell in redistributed if cell != deficit_cell]
        recipients = same_primary if same_primary else fallback
        if not recipients:
            raise ValueError(
                "cannot redistribute deficits for "
                f"family={family}: no recipients"
            )

        recipients.sort(
            key=lambda cell: (
                cell_distance(source_fields, parse_cell_fields(family, cell)),
                cell,
            )
        )
        log_counts: dict[str, int] = {}
        for idx in range(deficit_count):
            chosen = recipients[idx % len(recipients)]
            redistributed[chosen] = redistributed.get(chosen, 0) + 1
            log_counts[chosen] = log_counts.get(chosen, 0) + 1
        redistribution_log[deficit_cell] = dict(sorted(log_counts.items()))

    if sum(redistributed.values()) != sum(target_counts.values()):
        raise ValueError(
            "deficit redistribution changed total target count unexpectedly"
        )

    return redistributed, redistribution_log


def _sample_family_tasks(
    *,
    family: str,
    plan: StrataPlan,
    rng: random.Random,
    axes: Any,
    per_family_count: int,
    max_attempts: int,
    global_seen_task_ids: set[str],
    log: Callable[[str], None] | None = None,
) -> tuple[
    list[Task],
    dict[str, int],
    int,
    dict[str, dict[str, int]],
]:
    target_counts = dict(plan.target_counts)
    current_counts = {cell: 0 for cell in target_counts}
    accepted_tasks: list[Task] = []
    attempts = 0

    def can_accept(task: Task, cell: str) -> bool:  # noqa: ARG001
        return current_counts.get(cell, 0) < target_counts[cell]

    while len(accepted_tasks) < per_family_count and attempts < max_attempts:
        attempts += 1
        if log and attempts % 10_000 == 0:
            active = sum(
                1
                for c in target_counts
                if current_counts.get(c, 0) < target_counts[c]
            )
            status = (
                f"  {family}: {len(accepted_tasks)}/{per_family_count} accepted"
            )
            log(
                status
                + (
                    f" ({attempts} attempts, {active}/{len(target_counts)} "
                    "cells open)"
                )
            )
        task = generate_task_for_family(family, rng=rng, axes=axes)
        if task.task_id in global_seen_task_ids or not task.queries:
            continue
        try:
            cell, _ = plan.classify(task)
        except ValueError:
            continue
        if cell not in target_counts or not can_accept(task, cell):
            continue

        accepted_tasks.append(task)
        global_seen_task_ids.add(task.task_id)
        current_counts[cell] += 1

    redistribution_log: dict[str, dict[str, int]] = {}
    if len(accepted_tasks) < per_family_count:
        if log:
            log(
                f"  {family}: redistribution triggered "
                f"({len(accepted_tasks)}/{per_family_count} filled "
                f"after {attempts} attempts)"
            )
        target_counts, redistribution_log = _redistribute_deficits(
            family=family,
            plan=plan,
            target_counts=target_counts,
            current_counts=current_counts,
        )
        while len(accepted_tasks) < per_family_count and attempts < (
            max_attempts * 2
        ):
            attempts += 1
            if log and attempts % 10_000 == 0:
                active = sum(
                    1
                    for c in target_counts
                    if current_counts.get(c, 0) < target_counts[c]
                )
                log(
                    f"  {family}: {len(accepted_tasks)}/{per_family_count} "
                    f"accepted ({attempts} attempts, "
                    f"{active}/{len(target_counts)} cells open) [redistrib]"
                )
            task = generate_task_for_family(family, rng=rng, axes=axes)
            if task.task_id in global_seen_task_ids or not task.queries:
                continue
            try:
                cell, _ = plan.classify(task)
            except ValueError:
                continue
            if cell not in target_counts or not can_accept(task, cell):
                continue

            accepted_tasks.append(task)
            global_seen_task_ids.add(task.task_id)
            current_counts[cell] = current_counts.get(cell, 0) + 1

    return (
        accepted_tasks,
        target_counts,
        attempts,
        redistribution_log,
    )


def build_stratified_item_bank(
    settings: BankBuildSettings,
    log: Callable[[str], None] | None = None,
) -> BankBuildResult:
    bank_root = settings.out_dir / settings.bank_id
    items_path = bank_root / "items.jsonl"
    eval_cases_inputs_path = bank_root / "eval_cases_inputs.jsonl"
    eval_cases_expected_path = bank_root / "eval_cases_expected.jsonl"
    manifest_path = bank_root / "bank_manifest.json"

    all_items: list[ItemRow] = []
    all_case_inputs: list[EvalCaseInputRow] = []
    all_case_expected: list[EvalCaseExpectedRow] = []
    manifest_families: dict[str, Any] = {}
    global_seen_task_ids: set[str] = set()

    n_families = len(settings.families)
    for family_idx, family in enumerate(settings.families):
        plan = get_strata_plan(family, settings.per_family_count)
        rng = random.Random(settings.seed + (family_idx * 1_000_000))
        axes = _axes_for_family(family)

        def feature_partitioner(features: Mapping[str, str]) -> str:
            return _feature_cell_key(family, dict(features))

        try:
            capacity_report = enforce_spec_capacity(
                family=family,
                axes=axes,
                requested_total=settings.per_family_count,
                requested_partition_counts=plan.target_counts,
                feature_partitioner=feature_partitioner,
                require_exact=True,
            )
        except SpecCapacityError as exc:
            raise ValueError(
                "spec-space preflight failed before sampling: "
                f"family={family}; {exc}"
            ) from exc

        if log:
            log(
                f"[{family_idx + 1}/{n_families}] {family}: "
                f"sampling {settings.per_family_count} items "
                f"(max {settings.max_attempts_per_family} attempts, "
                f"{len(plan.target_counts)} cells) ..."
            )
            log(
                f"  {family}: exact unique spec capacity "
                f"{capacity_report.total_unique}"
            )

        (
            accepted_tasks,
            target_counts,
            attempts,
            redistribution_log,
        ) = _sample_family_tasks(
            family=family,
            plan=plan,
            rng=rng,
            axes=axes,
            per_family_count=settings.per_family_count,
            max_attempts=settings.max_attempts_per_family,
            global_seen_task_ids=global_seen_task_ids,
            log=log,
        )

        if log:
            log(
                f"  {family}: done — "
                f"{len(accepted_tasks)}/{settings.per_family_count} "
                f"accepted in {attempts} attempts"
            )

        if len(accepted_tasks) != settings.per_family_count:
            raise ValueError(
                "failed to fill family quota for IRT bank "
                f"family={family} accepted={len(accepted_tasks)} "
                f"target={settings.per_family_count} attempts={attempts}"
            )

        family_items: list[ItemRow] = []
        family_case_inputs: list[EvalCaseInputRow] = []
        family_case_expected: list[EvalCaseExpectedRow] = []
        actual_counts: dict[str, int] = {cell: 0 for cell in target_counts}

        for task in accepted_tasks:
            cell, fields = plan.classify(task)
            actual_counts[cell] = actual_counts.get(cell, 0) + 1
            family_items.append(
                ItemRow(
                    item_id=task.task_id,
                    task_id=task.task_id,
                    family=family,
                    spec_id=task.spec_id,
                    sem_hash=task.sem_hash,
                    stratum_cell=cell,
                    stratum_fields=fields,
                    spec=task.spec,
                    description=task.description,
                )
            )
            case_inputs, case_expected = _build_eval_rows(task)
            family_case_inputs.extend(case_inputs)
            family_case_expected.extend(case_expected)

        all_items.extend(family_items)
        all_case_inputs.extend(family_case_inputs)
        all_case_expected.extend(family_case_expected)

        manifest_families[family] = {
            "target_count": settings.per_family_count,
            "accepted_count": len(family_items),
            "attempts": attempts,
            "spec_space": {
                "mode": capacity_report.mode,
                "total_unique": capacity_report.total_unique,
                "partition_unique": (
                    dict(sorted(capacity_report.partition_unique.items()))
                    if capacity_report.partition_unique is not None
                    else None
                ),
            },
            "quota_policy": {
                "core_cell_targets": dict(
                    sorted(plan.core_target_counts.items())
                ),
                "repair_budget": plan.repair_budget,
            },
            "target_counts_by_cell": dict(sorted(target_counts.items())),
            "actual_counts_by_cell": dict(sorted(actual_counts.items())),
            "deficit_redistribution": redistribution_log,
        }

    if log:
        log(
            f"Writing {len(all_items)} items, "
            f"{len(all_case_inputs)} eval cases ..."
        )
    write_jsonl(items_path, all_items)
    write_jsonl(eval_cases_inputs_path, all_case_inputs)
    write_jsonl(eval_cases_expected_path, all_case_expected)

    if log:
        log("Writing manifest ...")
    manifest_payload = {
        "schema_version": "irt_bank_v1",
        "bank_id": settings.bank_id,
        "seed": settings.seed,
        "families": settings.families,
        "per_family_count": settings.per_family_count,
        "prompt_version": settings.prompt_version,
        "items_path": str(items_path),
        "eval_cases_inputs_path": str(eval_cases_inputs_path),
        "eval_cases_expected_path": str(eval_cases_expected_path),
        "family_summaries": manifest_families,
    }
    manifest_payload["manifest_hash"] = _hash_manifest_payload(manifest_payload)
    write_json(manifest_path, manifest_payload)

    return BankBuildResult(
        bank_root=bank_root,
        items_path=items_path,
        eval_cases_inputs_path=eval_cases_inputs_path,
        eval_cases_expected_path=eval_cases_expected_path,
        manifest_path=manifest_path,
    )
