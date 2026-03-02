from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from genfxn.irt.io import read_jsonl_models, write_json
from genfxn.irt.models import (
    ItemParameterRow,
    RespondentParameterRow,
    ResponseRow,
)


class DiagnosticsSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    fit_dir: Path
    responses_path: Path
    out_dir: Path | None = None
    local_dependence_threshold: float = Field(default=0.2, ge=0.0)


@dataclass(frozen=True)
class DiagnosticsOutput:
    diagnostics_dir: Path
    icc_path: Path
    item_information_path: Path
    local_dependence_path: Path
    summary_path: Path


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True))
            handle.write("\n")


def _pearson(x_values: list[float], y_values: list[float]) -> float | None:
    if len(x_values) != len(y_values) or len(x_values) < 3:
        return None
    mean_x = sum(x_values) / len(x_values)
    mean_y = sum(y_values) / len(y_values)
    centered_x = [value - mean_x for value in x_values]
    centered_y = [value - mean_y for value in y_values]
    numerator = sum(x * y for x, y in zip(centered_x, centered_y, strict=False))
    denom_x = math.sqrt(sum(x * x for x in centered_x))
    denom_y = math.sqrt(sum(y * y for y in centered_y))
    denominator = denom_x * denom_y
    if denominator <= 1e-12:
        return None
    return numerator / denominator


def run_fit_diagnostics(settings: DiagnosticsSettings) -> DiagnosticsOutput:
    diagnostics_dir = (
        settings.out_dir
        if settings.out_dir is not None
        else settings.fit_dir / "diagnostics"
    )
    diagnostics_dir.mkdir(parents=True, exist_ok=True)

    item_params = read_jsonl_models(
        settings.fit_dir / "item_params_2pl.jsonl", ItemParameterRow
    )
    respondent_params = read_jsonl_models(
        settings.fit_dir / "respondent_params_2pl.jsonl",
        RespondentParameterRow,
    )
    responses = read_jsonl_models(settings.responses_path, ResponseRow)

    item_by_key = {(row.family, row.item_id): row for row in item_params}
    theta_by_key = {
        (row.family, row.respondent_id): row.theta for row in respondent_params
    }

    rows_by_family: dict[str, list[ResponseRow]] = {}
    for row in responses:
        rows_by_family.setdefault(row.family, []).append(row)

    icc_rows: list[dict[str, Any]] = []
    info_rows: list[dict[str, Any]] = []
    local_dependence_rows: list[dict[str, Any]] = []
    summary: dict[str, Any] = {
        "fit_id": settings.fit_id,
        "families": {},
        "schema_version": "irt_diagnostics_v1",
    }

    theta_grid = [(-3.0 + idx * 0.5) for idx in range(13)]

    for family, family_rows in sorted(rows_by_family.items()):
        per_item_pairs: dict[str, list[tuple[float, int]]] = {}
        per_item_residuals: dict[str, dict[str, float]] = {}

        for row in family_rows:
            theta = theta_by_key.get((row.family, row.respondent_id))
            item = item_by_key.get((row.family, row.item_id))
            if theta is None or item is None:
                continue
            y = 1 if row.correct else 0
            per_item_pairs.setdefault(row.item_id, []).append((theta, y))
            p = _sigmoid((item.a or 1.0) * (theta - item.b))
            per_item_residuals.setdefault(row.item_id, {})[
                row.respondent_id
            ] = float(y) - p

        non_monotone_items: list[str] = []
        for item_id, pairs in sorted(per_item_pairs.items()):
            item = item_by_key[(family, item_id)]
            pairs_sorted = sorted(pairs, key=lambda pair: pair[0])
            if not pairs_sorted:
                continue
            bin_size = max(1, len(pairs_sorted) // 10)
            prev_rate: float | None = None
            for bin_idx in range(10):
                start = bin_idx * bin_size
                stop = (
                    len(pairs_sorted)
                    if bin_idx == 9
                    else (bin_idx + 1) * bin_size
                )
                chunk = pairs_sorted[start:stop]
                if not chunk:
                    continue
                mean_theta = sum(theta for theta, _ in chunk) / len(chunk)
                observed_rate = sum(y for _, y in chunk) / len(chunk)
                predicted_rate = _sigmoid(
                    (item.a or 1.0) * (mean_theta - item.b)
                )
                icc_rows.append(
                    {
                        "fit_id": settings.fit_id,
                        "family": family,
                        "item_id": item_id,
                        "bin_index": bin_idx,
                        "n": len(chunk),
                        "mean_theta": mean_theta,
                        "observed_rate": observed_rate,
                        "predicted_rate": predicted_rate,
                    }
                )
                if prev_rate is not None and (observed_rate + 0.15) < prev_rate:
                    non_monotone_items.append(item_id)
                prev_rate = observed_rate

            for theta_value in theta_grid:
                p = _sigmoid((item.a or 1.0) * (theta_value - item.b))
                info_rows.append(
                    {
                        "fit_id": settings.fit_id,
                        "family": family,
                        "item_id": item_id,
                        "theta": theta_value,
                        "item_information": ((item.a or 1.0) ** 2)
                        * p
                        * (1.0 - p),
                    }
                )

        item_ids = sorted(per_item_residuals)
        for idx, left_item_id in enumerate(item_ids):
            left = per_item_residuals[left_item_id]
            for right_item_id in item_ids[idx + 1 :]:
                right = per_item_residuals[right_item_id]
                shared = sorted(set(left) & set(right))
                if len(shared) < 5:
                    continue
                left_values = [left[respondent_id] for respondent_id in shared]
                right_values = [
                    right[respondent_id] for respondent_id in shared
                ]
                corr = _pearson(left_values, right_values)
                if corr is None:
                    continue
                if abs(corr) >= settings.local_dependence_threshold:
                    local_dependence_rows.append(
                        {
                            "fit_id": settings.fit_id,
                            "family": family,
                            "item_left": left_item_id,
                            "item_right": right_item_id,
                            "n_shared": len(shared),
                            "residual_corr": corr,
                            "flagged": True,
                        }
                    )

        family_local_count = sum(
            1 for row in local_dependence_rows if row["family"] == family
        )
        summary["families"][family] = {
            "n_items": len(per_item_pairs),
            "n_non_monotone_items": len(set(non_monotone_items)),
            "non_monotone_items": sorted(set(non_monotone_items)),
            "n_local_dependence_flags": family_local_count,
        }

    local_dependence_rows = sorted(
        local_dependence_rows,
        key=lambda row: (
            row["family"],
            -abs(float(row["residual_corr"])),
            row["item_left"],
            row["item_right"],
        ),
    )

    icc_path = diagnostics_dir / "icc_points.jsonl"
    item_information_path = diagnostics_dir / "item_information.jsonl"
    local_dependence_path = diagnostics_dir / "local_dependence_pairs.jsonl"
    summary_path = diagnostics_dir / "summary.json"

    _write_jsonl(icc_path, icc_rows)
    _write_jsonl(item_information_path, info_rows)
    _write_jsonl(local_dependence_path, local_dependence_rows)
    write_json(summary_path, summary)

    return DiagnosticsOutput(
        diagnostics_dir=diagnostics_dir,
        icc_path=icc_path,
        item_information_path=item_information_path,
        local_dependence_path=local_dependence_path,
        summary_path=summary_path,
    )
