from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import pstdev

from pydantic import BaseModel, ConfigDict, Field

from genfxn.irt.io import read_jsonl_models, write_json, write_jsonl
from genfxn.irt.models import (
    AnchorsFile,
    ResponseRow,
    ThetaModelSummaryRow,
    ThetaScoreRow,
)


class AnchorScoringSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    anchors_path: Path
    responses_path: Path
    out_dir: Path
    max_iter: int = Field(default=120, ge=1)


@dataclass(frozen=True)
class AnchorScoringOutput:
    fit_dir: Path
    theta_scores_path: Path
    theta_summary_path: Path


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


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


def _estimate_theta(
    entries: list[tuple[float, float, int]],
    *,
    max_iter: int,
) -> tuple[float, float]:
    theta = 0.0
    for _ in range(max_iter):
        grad = 0.0
        hess = 0.0
        for a, b, y in entries:
            p = _sigmoid(a * (theta - b))
            grad += a * (float(y) - p)
            hess -= (a * a) * p * (1.0 - p)
        if hess > -1e-12:
            break
        step = grad / hess
        theta -= step
        if abs(step) < 1e-5:
            break

    info = 0.0
    for a, b, _ in entries:
        p = _sigmoid(a * (theta - b))
        info += (a * a) * p * (1.0 - p)
    theta_se = 1.0 / math.sqrt(max(info, 1e-9))
    return theta, theta_se


def score_with_anchors(settings: AnchorScoringSettings) -> AnchorScoringOutput:
    fit_dir = settings.out_dir / settings.fit_id
    fit_dir.mkdir(parents=True, exist_ok=True)

    anchors = AnchorsFile.model_validate_json(
        settings.anchors_path.read_text(encoding="utf-8")
    )
    anchor_lookup = {
        (item.family, item.item_id): (item.a, item.b) for item in anchors.items
    }

    rows = _dedupe_rows(read_jsonl_models(settings.responses_path, ResponseRow))

    grouped: dict[tuple[str, str], list[tuple[float, float, int]]] = (
        defaultdict(list)
    )
    for row in rows:
        params = anchor_lookup.get((row.family, row.item_id))
        if params is None:
            continue
        grouped[(row.family, row.respondent_id)].append(
            (params[0], params[1], 1 if row.correct else 0)
        )

    theta_rows: list[ThetaScoreRow] = []
    summary_groups: dict[tuple[str, str], list[float]] = defaultdict(list)

    for (family, respondent_id), entries in sorted(grouped.items()):
        if not entries:
            continue
        theta, theta_se = _estimate_theta(entries, max_iter=settings.max_iter)
        base_respondent_id = _base_respondent_id(respondent_id)
        theta_rows.append(
            ThetaScoreRow(
                fit_id=settings.fit_id,
                family=family,
                respondent_id=respondent_id,
                base_respondent_id=base_respondent_id,
                theta=theta,
                theta_se=theta_se,
                n_items=len(entries),
            )
        )
        summary_groups[(family, base_respondent_id)].append(theta)

    summary_rows: list[ThetaModelSummaryRow] = []
    for (family, base_respondent_id), values in sorted(summary_groups.items()):
        mean_theta = sum(values) / len(values)
        std_theta = pstdev(values) if len(values) > 1 else 0.0
        summary_rows.append(
            ThetaModelSummaryRow(
                fit_id=settings.fit_id,
                family=family,
                base_respondent_id=base_respondent_id,
                theta_mean=mean_theta,
                theta_std=std_theta,
                n_repeats=len(values),
            )
        )

    theta_scores_path = fit_dir / "theta_scores.jsonl"
    theta_summary_path = fit_dir / "theta_summary.jsonl"
    write_jsonl(theta_scores_path, theta_rows)
    write_jsonl(theta_summary_path, summary_rows)

    write_json(
        fit_dir / "score_manifest.json",
        {
            "fit_id": settings.fit_id,
            "anchors_path": str(settings.anchors_path),
            "responses_path": str(settings.responses_path),
            "n_theta_rows": len(theta_rows),
            "n_summary_rows": len(summary_rows),
            "n_anchor_items": len(anchors.items),
        },
    )

    return AnchorScoringOutput(
        fit_dir=fit_dir,
        theta_scores_path=theta_scores_path,
        theta_summary_path=theta_summary_path,
    )
