import random
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

import pytest
import srsly
import typer
from helpers import load_script_module

from genfxn.core.describe import describe_task
from genfxn.core.models import Task
from genfxn.core.task_ids import compute_task_ids
from genfxn.piecewise.task import generate_piecewise_task

_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "migrate_dataset_task_ids.py"
)

_SCRIPT_MODULE = load_script_module(
    _SCRIPT, "tests.migrate_dataset_task_ids_script_module"
)
migrate_dataset_task_ids_main = cast(Callable[..., None], _SCRIPT_MODULE.main)


def _read_single_row(path: Path) -> dict[str, Any]:
    rows = list(srsly.read_jsonl(path))
    assert len(rows) == 1
    return cast(dict[str, Any], rows[0])


def test_main_backfills_missing_identity_fields(tmp_path: Path) -> None:
    task = generate_piecewise_task(rng=random.Random(7)).model_dump(mode="json")
    task.pop("spec_id", None)
    task.pop("sem_hash", None)
    task.pop("ast_id", None)
    task.pop("description", None)

    dataset_path = tmp_path / "legacy.jsonl"
    srsly.write_jsonl(dataset_path, [task])

    migrate_dataset_task_ids_main(
        input_file=dataset_path,
        output_file=None,
        overwrite_existing=False,
    )

    migrated = _read_single_row(dataset_path)
    ids = compute_task_ids(
        migrated["family"],
        migrated["spec"],
        migrated["code"],
    )
    assert migrated["spec_id"] == ids.spec_id
    assert migrated["sem_hash"] == ids.sem_hash
    assert migrated["ast_id"] == ids.ast_id
    assert migrated["description"] == describe_task(
        migrated["family"], migrated["spec"]
    )
    Task.model_validate(migrated)


def test_main_preserves_existing_ids_without_overwrite(tmp_path: Path) -> None:
    task = generate_piecewise_task(rng=random.Random(7)).model_dump(mode="json")
    task["spec_id"] = "custom-spec"
    task["sem_hash"] = "custom-sem"
    task["ast_id"] = {"python": "custom-ast"}
    task["description"] = "custom description"

    dataset_path = tmp_path / "legacy.jsonl"
    srsly.write_jsonl(dataset_path, [task])

    migrate_dataset_task_ids_main(
        input_file=dataset_path,
        output_file=None,
        overwrite_existing=False,
    )

    migrated = _read_single_row(dataset_path)
    assert migrated["spec_id"] == "custom-spec"
    assert migrated["sem_hash"] == "custom-sem"
    assert migrated["ast_id"] == {"python": "custom-ast"}
    assert migrated["description"] == "custom description"


def test_main_overwrites_existing_ids_when_flag_set(tmp_path: Path) -> None:
    task = generate_piecewise_task(rng=random.Random(7)).model_dump(mode="json")
    stale_spec_id = "stale-spec-id"
    task["spec_id"] = stale_spec_id
    task["sem_hash"] = "stale-sem-hash"
    task["ast_id"] = {"python": "stale-ast-id"}
    task["description"] = "stale-description"

    dataset_path = tmp_path / "legacy.jsonl"
    srsly.write_jsonl(dataset_path, [task])

    migrate_dataset_task_ids_main(
        input_file=dataset_path,
        output_file=None,
        overwrite_existing=True,
    )

    migrated = _read_single_row(dataset_path)
    ids = compute_task_ids(
        migrated["family"],
        migrated["spec"],
        migrated["code"],
    )
    assert migrated["spec_id"] == ids.spec_id
    assert migrated["sem_hash"] == ids.sem_hash
    assert migrated["ast_id"] == ids.ast_id
    assert migrated["spec_id"] != stale_spec_id
    assert migrated["description"] == describe_task(
        migrated["family"], migrated["spec"]
    )
    assert migrated["description"] != "stale-description"


def test_main_reports_json_decode_errors_with_line_number(
    tmp_path: Path,
) -> None:
    dataset_path = tmp_path / "broken.jsonl"
    dataset_path.write_text("{not json}\n", encoding="utf-8")

    with pytest.raises(typer.BadParameter, match="Line 1: invalid JSON:"):
        migrate_dataset_task_ids_main(
            input_file=dataset_path,
            output_file=None,
            overwrite_existing=False,
        )


def test_main_reports_json_decode_errors_with_correct_line_number(
    tmp_path: Path,
) -> None:
    valid_task = generate_piecewise_task(rng=random.Random(11)).model_dump(
        mode="json"
    )
    dataset_path = tmp_path / "broken_multiline.jsonl"
    dataset_path.write_text(
        srsly.json_dumps(valid_task) + "\n" + "{broken json}\n",
        encoding="utf-8",
    )

    with pytest.raises(typer.BadParameter, match="Line 2: invalid JSON:"):
        migrate_dataset_task_ids_main(
            input_file=dataset_path,
            output_file=None,
            overwrite_existing=False,
        )
