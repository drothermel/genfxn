from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from genfxn.verification.models import VerificationCase, VerificationMetrics

DEFAULT_VERIFICATION_OUTPUT_DIR = Path("data/verification_cases")


def verification_sidecar_paths(
    dataset_path: Path,
    *,
    output_dir: Path = DEFAULT_VERIFICATION_OUTPUT_DIR,
) -> tuple[Path, Path]:
    stem = dataset_path.stem
    return (
        output_dir / f"{stem}.verification_cases.jsonl",
        output_dir / f"{stem}.verification_metrics.jsonl",
    )


def _write_jsonl_atomically(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False))
                handle.write("\n")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


write_jsonl_atomically = _write_jsonl_atomically


def write_verification_sidecars(
    cases_path: Path,
    metrics_path: Path,
    *,
    cases: list[VerificationCase],
    metrics: list[VerificationMetrics],
) -> None:
    _write_jsonl_atomically(
        cases_path,
        [case.model_dump(mode="json") for case in cases],
    )
    _write_jsonl_atomically(
        metrics_path,
        [metric.model_dump(mode="json") for metric in metrics],
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            records.append(json.loads(stripped))
    return records


def load_verification_sidecars(
    cases_path: Path,
    metrics_path: Path,
) -> tuple[list[VerificationCase], list[VerificationMetrics]]:
    cases = [
        VerificationCase.model_validate(row) for row in _load_jsonl(cases_path)
    ]
    metrics = [
        VerificationMetrics.model_validate(row)
        for row in _load_jsonl(metrics_path)
    ]
    return cases, metrics
