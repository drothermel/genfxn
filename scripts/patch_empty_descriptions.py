"""Patch tasks with empty descriptions by recomputing from their spec."""

from pathlib import Path

import srsly
import typer

from genfxn.core.describe import describe_task

app = typer.Typer()


@app.command()
def main(
    data_dir: Path = typer.Argument(..., help="Root of balanced_suites directory"),
    dry_run: bool = typer.Option(False, help="Print what would change without writing"),
) -> None:
    """Recompute empty descriptions in-place for all tasks under data_dir."""
    jsonl_files = sorted(data_dir.glob("*/level_*/all.jsonl"))
    if not jsonl_files:
        typer.echo(f"No all.jsonl files found under {data_dir}")
        raise typer.Exit(1)

    total_patched = 0
    for path in jsonl_files:
        records = list(srsly.read_jsonl(str(path)))
        patched = 0

        for record in records:
            if record.get("description", "") == "":
                family = record["family"]
                spec = record["spec"]
                new_desc = describe_task(family, spec)
                if new_desc:
                    record["description"] = new_desc
                    patched += 1
                else:
                    typer.echo(
                        f"  WARNING: still empty after patch: "
                        f"{record['task_id']} ({family}, {spec.get('template', '?')})"
                    )

        if patched > 0:
            rel = path.relative_to(data_dir)
            typer.echo(f"{rel}: patched {patched}/{len(records)} descriptions")
            if not dry_run:
                srsly.write_jsonl(str(path), records)
        total_patched += patched

    if total_patched == 0:
        typer.echo("No empty descriptions found — nothing to patch.")
    elif dry_run:
        typer.echo(f"\nDry run: {total_patched} tasks would be patched.")
    else:
        typer.echo(f"\nDone: patched {total_patched} tasks.")


if __name__ == "__main__":
    app()
