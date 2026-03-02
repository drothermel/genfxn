from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel


def write_jsonl[TModelType: BaseModel](
    path: Path,
    rows: list[TModelType],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(row.model_dump_json())
            handle.write("\n")


def read_jsonl_models[TModelType: BaseModel](
    path: Path,
    model_type: type[TModelType],
) -> list[TModelType]:
    rows: list[TModelType] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(model_type.model_validate_json(stripped))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
