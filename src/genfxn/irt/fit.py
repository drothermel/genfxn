from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from genfxn.irt.io import read_jsonl_models, write_json, write_jsonl
from genfxn.irt.models import (
    AnchorItemParameter,
    AnchorsFile,
    DifficultyBinRow,
    ItemParameterRow,
    RespondentParameterRow,
    ResponseRow,
)


class FitSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    responses_path: Path
    out_dir: Path
    min_item_respondents: int = Field(default=8, ge=1)
    min_respondent_items: int = Field(default=20, ge=1)
    min_item_correct: int = Field(default=1, ge=0)
    min_item_incorrect: int = Field(default=1, ge=0)
    max_iter_1pl: int = Field(default=250, ge=1)
    max_iter_2pl: int = Field(default=350, ge=1)
    regularization: float = Field(default=1e-2, gt=0.0)


@dataclass(frozen=True)
class FitOutput:
    fit_dir: Path
    item_params_1pl_path: Path
    item_params_2pl_path: Path
    respondent_params_1pl_path: Path
    respondent_params_2pl_path: Path
    diagnostics_path: Path
    difficulty_bins_global_path: Path
    difficulty_bins_family_path: Path
    anchors_path: Path


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def _clamp_probability(value: float, *, epsilon: float = 1e-6) -> float:
    return min(1.0 - epsilon, max(epsilon, value))


def _logit(probability: float) -> float:
    p = _clamp_probability(probability)
    return math.log(p / (1.0 - p))


def _base_respondent_id(respondent_id: str) -> str:
    marker = "#r"
    if marker not in respondent_id:
        return respondent_id
    prefix, suffix = respondent_id.rsplit(marker, 1)
    if suffix.isdigit():
        return prefix
    return respondent_id


def _dedupe_rows(rows: list[ResponseRow]) -> list[ResponseRow]:
    latest_by_key: dict[tuple[str, str], ResponseRow] = {}
    for row in rows:
        key = (row.respondent_id, row.item_id)
        previous = latest_by_key.get(key)
        if previous is None or row.timestamp_utc >= previous.timestamp_utc:
            latest_by_key[key] = row
    return sorted(
        latest_by_key.values(),
        key=lambda row: (row.family, row.respondent_id, row.item_id),
    )


def _iterative_filter(
    *,
    rows: list[ResponseRow],
    min_item_respondents: int,
    min_respondent_items: int,
    min_item_correct: int,
    min_item_incorrect: int,
) -> tuple[list[ResponseRow], dict[str, Any]]:
    retained = rows
    dropped_items: set[str] = set()
    dropped_respondents: set[str] = set()

    while True:
        rows_by_item: dict[str, list[ResponseRow]] = defaultdict(list)
        rows_by_respondent: dict[str, list[ResponseRow]] = defaultdict(list)
        for row in retained:
            rows_by_item[row.item_id].append(row)
            rows_by_respondent[row.respondent_id].append(row)

        bad_items = {
            item_id
            for item_id, item_rows in rows_by_item.items()
            if len(item_rows) < min_item_respondents
            or sum(1 for row in item_rows if row.correct) < min_item_correct
            or sum(1 for row in item_rows if not row.correct)
            < min_item_incorrect
        }

        bad_respondents = {
            respondent_id
            for respondent_id, respondent_rows in rows_by_respondent.items()
            if len(respondent_rows) < min_respondent_items
        }

        if not bad_items and not bad_respondents:
            break

        dropped_items.update(bad_items)
        dropped_respondents.update(bad_respondents)
        retained = [
            row
            for row in retained
            if row.item_id not in bad_items
            and row.respondent_id not in bad_respondents
        ]

    summary = {
        "rows_in": len(rows),
        "rows_out": len(retained),
        "dropped_items": sorted(dropped_items),
        "dropped_respondents": sorted(dropped_respondents),
    }
    return retained, summary


def _matrix_from_rows(
    rows: list[ResponseRow],
) -> tuple[list[str], list[str], list[list[int | None]]]:
    respondent_ids = sorted({row.respondent_id for row in rows})
    item_ids = sorted({row.item_id for row in rows})
    respondent_index = {
        respondent_id: idx for idx, respondent_id in enumerate(respondent_ids)
    }
    item_index = {item_id: idx for idx, item_id in enumerate(item_ids)}

    matrix: list[list[int | None]] = [
        [None for _ in item_ids] for _ in respondent_ids
    ]
    for row in rows:
        ridx = respondent_index[row.respondent_id]
        iidx = item_index[row.item_id]
        matrix[ridx][iidx] = 1 if row.correct else 0
    return respondent_ids, item_ids, matrix


def _row_mean(values: list[int | None]) -> float:
    observed = [value for value in values if value is not None]
    if not observed:
        return 0.5
    return (sum(observed) + 0.5) / (len(observed) + 1.0)


def _col_mean(matrix: list[list[int | None]], col_idx: int) -> float:
    observed = [row[col_idx] for row in matrix if row[col_idx] is not None]
    int_values = [value for value in observed if value is not None]
    if not int_values:
        return 0.5
    return (sum(int_values) + 0.5) / (len(int_values) + 1.0)


def _fit_1pl(
    matrix: list[list[int | None]],
    *,
    max_iter: int,
    regularization: float,
) -> tuple[list[float], list[float], list[float], list[float], dict[str, Any]]:
    n_respondents = len(matrix)
    n_items = len(matrix[0]) if matrix else 0

    theta = [_logit(_row_mean(matrix[ridx])) for ridx in range(n_respondents)]
    b = [-_logit(_col_mean(matrix, iidx)) for iidx in range(n_items)]

    converged = False
    max_delta = 0.0

    for iteration in range(max_iter):
        max_delta = 0.0

        for ridx in range(n_respondents):
            grad = 0.0
            hess = -regularization
            for iidx in range(n_items):
                y = matrix[ridx][iidx]
                if y is None:
                    continue
                p = _sigmoid(theta[ridx] - b[iidx])
                grad += float(y) - p
                hess -= p * (1.0 - p)
            grad -= regularization * theta[ridx]
            if hess < -1e-9:
                delta = grad / hess
                theta[ridx] -= delta
                max_delta = max(max_delta, abs(delta))

        for iidx in range(n_items):
            grad = 0.0
            hess = -regularization
            for ridx in range(n_respondents):
                y = matrix[ridx][iidx]
                if y is None:
                    continue
                p = _sigmoid(theta[ridx] - b[iidx])
                grad -= float(y) - p
                hess -= p * (1.0 - p)
            grad -= regularization * b[iidx]
            if hess < -1e-9:
                delta = grad / hess
                b[iidx] -= delta
                max_delta = max(max_delta, abs(delta))

        if theta:
            shift = sum(theta) / len(theta)
            theta = [value - shift for value in theta]
            b = [value + shift for value in b]

        if max_delta < 1e-4:
            converged = True
            break

    theta_se: list[float] = []
    b_se: list[float] = []

    for ridx in range(n_respondents):
        info = regularization
        for iidx in range(n_items):
            if matrix[ridx][iidx] is None:
                continue
            p = _sigmoid(theta[ridx] - b[iidx])
            info += p * (1.0 - p)
        theta_se.append(1.0 / math.sqrt(max(info, 1e-9)))

    for iidx in range(n_items):
        info = regularization
        for ridx in range(n_respondents):
            if matrix[ridx][iidx] is None:
                continue
            p = _sigmoid(theta[ridx] - b[iidx])
            info += p * (1.0 - p)
        b_se.append(1.0 / math.sqrt(max(info, 1e-9)))

    metadata = {
        "iterations": iteration + 1,
        "converged": converged,
        "max_delta": max_delta,
    }
    return theta, b, theta_se, b_se, metadata


def _fit_2pl(
    matrix: list[list[int | None]],
    *,
    theta_init: list[float],
    b_init: list[float],
    max_iter: int,
    regularization: float,
) -> tuple[
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
    list[float],
    dict[str, Any],
]:
    n_respondents = len(matrix)
    n_items = len(matrix[0]) if matrix else 0

    theta = list(theta_init)
    b = list(b_init)
    a = [1.0 for _ in range(n_items)]

    converged = False
    max_delta = 0.0

    for iteration in range(max_iter):
        max_delta = 0.0

        for ridx in range(n_respondents):
            grad = 0.0
            hess = -regularization
            for iidx in range(n_items):
                y = matrix[ridx][iidx]
                if y is None:
                    continue
                delta = theta[ridx] - b[iidx]
                p = _sigmoid(a[iidx] * delta)
                grad += a[iidx] * (float(y) - p)
                hess -= (a[iidx] * a[iidx]) * p * (1.0 - p)
            grad -= regularization * theta[ridx]
            if hess < -1e-9:
                step = grad / hess
                theta[ridx] -= step
                max_delta = max(max_delta, abs(step))

        for iidx in range(n_items):
            grad_b = 0.0
            hess_b = -regularization
            grad_a = -regularization * (a[iidx] - 1.0)
            hess_a = -regularization
            for ridx in range(n_respondents):
                y = matrix[ridx][iidx]
                if y is None:
                    continue
                delta = theta[ridx] - b[iidx]
                p = _sigmoid(a[iidx] * delta)
                common = float(y) - p
                grad_b -= a[iidx] * common
                hess_b -= (a[iidx] * a[iidx]) * p * (1.0 - p)
                grad_a += common * delta
                hess_a -= p * (1.0 - p) * (delta * delta)

            if hess_b < -1e-9:
                step_b = grad_b / hess_b
                b[iidx] -= step_b
                max_delta = max(max_delta, abs(step_b))

            if hess_a < -1e-9:
                step_a = grad_a / hess_a
                updated_a = a[iidx] - step_a
                updated_a = max(0.2, min(3.0, updated_a))
                max_delta = max(max_delta, abs(updated_a - a[iidx]))
                a[iidx] = updated_a

        if theta:
            shift = sum(theta) / len(theta)
            theta = [value - shift for value in theta]
            b = [value + shift for value in b]

        if max_delta < 1e-4:
            converged = True
            break

    theta_se: list[float] = []
    b_se: list[float] = []
    a_se: list[float] = []

    for ridx in range(n_respondents):
        info = regularization
        for iidx in range(n_items):
            if matrix[ridx][iidx] is None:
                continue
            p = _sigmoid(a[iidx] * (theta[ridx] - b[iidx]))
            info += (a[iidx] * a[iidx]) * p * (1.0 - p)
        theta_se.append(1.0 / math.sqrt(max(info, 1e-9)))

    for iidx in range(n_items):
        info_b = regularization
        info_a = regularization
        for ridx in range(n_respondents):
            if matrix[ridx][iidx] is None:
                continue
            delta = theta[ridx] - b[iidx]
            p = _sigmoid(a[iidx] * delta)
            info_b += (a[iidx] * a[iidx]) * p * (1.0 - p)
            info_a += (delta * delta) * p * (1.0 - p)
        b_se.append(1.0 / math.sqrt(max(info_b, 1e-9)))
        a_se.append(1.0 / math.sqrt(max(info_a, 1e-9)))

    metadata = {
        "iterations": iteration + 1,
        "converged": converged,
        "max_delta": max_delta,
    }

    return theta, b, a, theta_se, b_se, a_se, metadata


def _quantile_edges(values: list[float]) -> list[float]:
    if not values:
        raise ValueError("cannot compute quantiles for empty values")
    sorted_values = sorted(values)
    quantiles = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
    edges: list[float] = []
    for q in quantiles:
        position = q * (len(sorted_values) - 1)
        lo = int(math.floor(position))
        hi = int(math.ceil(position))
        if lo == hi:
            edges.append(sorted_values[lo])
            continue
        frac = position - lo
        edges.append(
            sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * frac
        )
    return edges


def _bin_for_value(value: float, edges: list[float]) -> int:
    for idx in range(1, 5):
        if value <= edges[idx]:
            return idx
    return 5


def _build_bins(
    *,
    fit_id: str,
    item_rows: list[ItemParameterRow],
) -> tuple[list[DifficultyBinRow], list[DifficultyBinRow]]:
    global_edges = _quantile_edges([row.b for row in item_rows])
    global_bins: list[DifficultyBinRow] = []
    for row in item_rows:
        global_bins.append(
            DifficultyBinRow(
                fit_id=fit_id,
                scope="global",
                family=row.family,
                item_id=row.item_id,
                b=row.b,
                bin=_bin_for_value(row.b, global_edges),
                quantile_edges=global_edges,
            )
        )

    by_family: dict[str, list[ItemParameterRow]] = defaultdict(list)
    for row in item_rows:
        by_family[row.family].append(row)

    family_bins: list[DifficultyBinRow] = []
    for family, family_rows in sorted(by_family.items()):
        family_edges = _quantile_edges([row.b for row in family_rows])
        for row in family_rows:
            family_bins.append(
                DifficultyBinRow(
                    fit_id=fit_id,
                    scope="family",
                    family=family,
                    item_id=row.item_id,
                    b=row.b,
                    bin=_bin_for_value(row.b, family_edges),
                    quantile_edges=family_edges,
                )
            )

    return global_bins, family_bins


def fit_irt_models(settings: FitSettings) -> FitOutput:
    fit_dir = settings.out_dir / settings.fit_id
    fit_dir.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl_models(settings.responses_path, ResponseRow)
    deduped_rows = _dedupe_rows(rows)

    rows_by_family: dict[str, list[ResponseRow]] = defaultdict(list)
    for row in deduped_rows:
        rows_by_family[row.family].append(row)

    item_params_1pl: list[ItemParameterRow] = []
    item_params_2pl: list[ItemParameterRow] = []
    respondent_params_1pl: list[RespondentParameterRow] = []
    respondent_params_2pl: list[RespondentParameterRow] = []

    diagnostics: dict[str, Any] = {
        "schema_version": "irt_fit_v1",
        "fit_id": settings.fit_id,
        "responses_path": str(settings.responses_path),
        "families": {},
        "pooled": {
            "rows_in": len(rows),
            "rows_deduped": len(deduped_rows),
            "accuracy": (
                sum(1 for row in deduped_rows if row.correct)
                / len(deduped_rows)
                if deduped_rows
                else 0.0
            ),
        },
    }

    for family, family_rows in sorted(rows_by_family.items()):
        filtered_rows, filter_summary = _iterative_filter(
            rows=family_rows,
            min_item_respondents=settings.min_item_respondents,
            min_respondent_items=settings.min_respondent_items,
            min_item_correct=settings.min_item_correct,
            min_item_incorrect=settings.min_item_incorrect,
        )
        if not filtered_rows:
            diagnostics["families"][family] = {
                "skipped": True,
                "reason": "all rows filtered",
                "filter_summary": filter_summary,
            }
            continue

        respondent_ids, item_ids, matrix = _matrix_from_rows(filtered_rows)
        theta_1pl, b_1pl, theta_se_1pl, b_se_1pl, meta_1pl = _fit_1pl(
            matrix,
            max_iter=settings.max_iter_1pl,
            regularization=settings.regularization,
        )
        (
            theta_2pl,
            b_2pl,
            a_2pl,
            theta_se_2pl,
            b_se_2pl,
            a_se_2pl,
            meta_2pl,
        ) = _fit_2pl(
            matrix,
            theta_init=theta_1pl,
            b_init=b_1pl,
            max_iter=settings.max_iter_2pl,
            regularization=settings.regularization,
        )

        for iidx, item_id in enumerate(item_ids):
            item_params_1pl.append(
                ItemParameterRow(
                    fit_id=settings.fit_id,
                    model_type="1pl",
                    family=family,
                    item_id=item_id,
                    b=b_1pl[iidx],
                    b_se=b_se_1pl[iidx],
                    a=1.0,
                    a_se=None,
                )
            )
            item_params_2pl.append(
                ItemParameterRow(
                    fit_id=settings.fit_id,
                    model_type="2pl",
                    family=family,
                    item_id=item_id,
                    b=b_2pl[iidx],
                    b_se=b_se_2pl[iidx],
                    a=a_2pl[iidx],
                    a_se=a_se_2pl[iidx],
                )
            )

        for ridx, respondent_id in enumerate(respondent_ids):
            base_respondent_id = _base_respondent_id(respondent_id)
            respondent_params_1pl.append(
                RespondentParameterRow(
                    fit_id=settings.fit_id,
                    model_type="1pl",
                    family=family,
                    respondent_id=respondent_id,
                    theta=theta_1pl[ridx],
                    theta_se=theta_se_1pl[ridx],
                    base_respondent_id=base_respondent_id,
                )
            )
            respondent_params_2pl.append(
                RespondentParameterRow(
                    fit_id=settings.fit_id,
                    model_type="2pl",
                    family=family,
                    respondent_id=respondent_id,
                    theta=theta_2pl[ridx],
                    theta_se=theta_se_2pl[ridx],
                    base_respondent_id=base_respondent_id,
                )
            )

        diagnostics["families"][family] = {
            "skipped": False,
            "rows": len(filtered_rows),
            "n_items": len(item_ids),
            "n_respondents": len(respondent_ids),
            "filter_summary": filter_summary,
            "fit_1pl": meta_1pl,
            "fit_2pl": meta_2pl,
        }

    if not item_params_2pl:
        raise ValueError(
            "fit produced no item parameters; check response matrix"
        )

    global_bins, family_bins = _build_bins(
        fit_id=settings.fit_id,
        item_rows=item_params_2pl,
    )
    anchors = AnchorsFile(
        fit_id=settings.fit_id,
        schema_version="irt_anchor_v1",
        model_type="2pl",
        items=[
            AnchorItemParameter(
                family=row.family,
                item_id=row.item_id,
                a=row.a if row.a is not None else 1.0,
                b=row.b,
            )
            for row in item_params_2pl
        ],
    )

    item_params_1pl_path = fit_dir / "item_params_1pl.jsonl"
    item_params_2pl_path = fit_dir / "item_params_2pl.jsonl"
    respondent_params_1pl_path = fit_dir / "respondent_params_1pl.jsonl"
    respondent_params_2pl_path = fit_dir / "respondent_params_2pl.jsonl"
    diagnostics_path = fit_dir / "fit_diagnostics.json"
    difficulty_bins_global_path = fit_dir / "difficulty_bins_global.jsonl"
    difficulty_bins_family_path = fit_dir / "difficulty_bins_family.jsonl"
    anchors_path = fit_dir / "anchors.json"

    write_jsonl(item_params_1pl_path, item_params_1pl)
    write_jsonl(item_params_2pl_path, item_params_2pl)
    write_jsonl(respondent_params_1pl_path, respondent_params_1pl)
    write_jsonl(respondent_params_2pl_path, respondent_params_2pl)
    write_jsonl(difficulty_bins_global_path, global_bins)
    write_jsonl(difficulty_bins_family_path, family_bins)
    write_json(diagnostics_path, diagnostics)
    write_json(
        anchors_path,
        anchors.model_dump(mode="json", exclude_computed_fields=True),
    )

    return FitOutput(
        fit_dir=fit_dir,
        item_params_1pl_path=item_params_1pl_path,
        item_params_2pl_path=item_params_2pl_path,
        respondent_params_1pl_path=respondent_params_1pl_path,
        respondent_params_2pl_path=respondent_params_2pl_path,
        diagnostics_path=diagnostics_path,
        difficulty_bins_global_path=difficulty_bins_global_path,
        difficulty_bins_family_path=difficulty_bins_family_path,
        anchors_path=anchors_path,
    )
