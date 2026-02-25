"""Backfill task identity fields for legacy JSONL datasets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import typer

from genfxn.core.task_ids import compute_task_ids
from genfxn.verification.io import write_jsonl_atomically

app = typer.Typer()


@app.command()
def main(
    input_file: Path = typer.Argument(help="Input legacy dataset JSONL"),
    output_file: Path | None = typer.Option(
        None,
        help="Output JSONL path (defaults to in-place update).",
    ),
    overwrite_existing: bool = typer.Option(
        False,
        help="Overwrite existing spec_id/sem_hash/ast_id when present.",
    ),
) -> None:
    target = output_file or input_file
    rows: list[dict[str, Any]] = []

    with input_file.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                row = json.loads(stripped)
            except json.JSONDecodeError as err:
                raise typer.BadParameter(
                    f"Line {line_number}: invalid JSON: {err}"
                ) from err
            family = row.get("family")
            spec = row.get("spec")
            code = row.get("code")
            if not isinstance(family, str) or not isinstance(spec, dict):
                raise typer.BadParameter(
                    f"Line {line_number}: expected fields family(str), "
                    "spec(dict), code(str|dict)."
                )
            if not isinstance(code, (str, dict)):
                raise typer.BadParameter(
                    f"Line {line_number}: expected code as str or dict"
                )

            ids = compute_task_ids(family, spec, code)
            if overwrite_existing or not row.get("spec_id"):
                row["spec_id"] = ids.spec_id
            if overwrite_existing or not row.get("sem_hash"):
                row["sem_hash"] = ids.sem_hash
            if overwrite_existing or not row.get("ast_id"):
                row["ast_id"] = ids.ast_id

            rows.append(row)

    write_jsonl_atomically(target, rows)
    typer.echo(f"Wrote migrated dataset with {len(rows)} task(s) to {target}")


if __name__ == "__main__":
    app()
