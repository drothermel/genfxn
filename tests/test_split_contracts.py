from pathlib import Path
from typing import Any, cast

import srsly
from typer.testing import CliRunner

from genfxn.cli import app
from genfxn.core.models import Task
from genfxn.splits import random_split

runner = CliRunner()


def _build_task_records(count: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for i in range(count):
        records.append(
            {
                "task_id": f"task-{i}",
                "family": "stateful",
                "spec": {"n": i},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": i, "output": i, "tag": "typical"}],
                "description": f"task {i}",
            }
        )
    return records


def _assert_partition_contract(
    *,
    train_ids: list[str],
    test_ids: list[str],
    all_ids: set[str],
    expected_train_count: int,
) -> None:
    assert len(train_ids) == expected_train_count
    assert len(test_ids) == len(all_ids) - expected_train_count
    assert set(train_ids).isdisjoint(set(test_ids))
    assert set(train_ids).union(set(test_ids)) == all_ids


def _run_cli_random_split(
    *,
    input_file: Path,
    train_file: Path,
    test_file: Path,
    ratio: float,
    seed: int,
) -> tuple[list[str], list[str]]:
    result = runner.invoke(
        app,
        [
            "split",
            str(input_file),
            "--train",
            str(train_file),
            "--test",
            str(test_file),
            "--random-ratio",
            str(ratio),
            "--seed",
            str(seed),
        ],
    )
    assert result.exit_code == 0

    train_rows = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
    test_rows = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
    return (
        [row["task_id"] for row in train_rows],
        [row["task_id"] for row in test_rows],
    )


def test_library_random_split_contract_is_deterministic() -> None:
    count = 11
    ratio = 0.6
    seed = 123
    records = _build_task_records(count)
    tasks = [Task.model_validate(record) for record in records]
    all_ids = {record["task_id"] for record in records}

    result_1 = random_split(tasks, train_ratio=ratio, seed=seed)
    result_2 = random_split(tasks, train_ratio=ratio, seed=seed)

    train_1 = [task.task_id for task in result_1.train]
    test_1 = [task.task_id for task in result_1.test]
    train_2 = [task.task_id for task in result_2.train]
    test_2 = [task.task_id for task in result_2.test]

    assert train_1 == train_2
    assert test_1 == test_2
    _assert_partition_contract(
        train_ids=train_1,
        test_ids=test_1,
        all_ids=all_ids,
        expected_train_count=int(count * ratio),
    )


def test_cli_random_split_contract_is_deterministic(
    tmp_path: Path,
) -> None:
    count = 11
    ratio = 0.6
    seed = 123
    records = _build_task_records(count)
    all_ids = {record["task_id"] for record in records}
    input_file = tmp_path / "tasks.jsonl"
    srsly.write_jsonl(input_file, records)

    train_1, test_1 = _run_cli_random_split(
        input_file=input_file,
        train_file=tmp_path / "train_1.jsonl",
        test_file=tmp_path / "test_1.jsonl",
        ratio=ratio,
        seed=seed,
    )
    train_2, test_2 = _run_cli_random_split(
        input_file=input_file,
        train_file=tmp_path / "train_2.jsonl",
        test_file=tmp_path / "test_2.jsonl",
        ratio=ratio,
        seed=seed,
    )

    assert train_1 == train_2
    assert test_1 == test_2
    _assert_partition_contract(
        train_ids=train_1,
        test_ids=test_1,
        all_ids=all_ids,
        expected_train_count=int(count * ratio),
    )


def test_cli_and_library_random_split_share_contract_invariants(
    tmp_path: Path,
) -> None:
    count = 23
    ratio = 0.35
    seed = 77
    records = _build_task_records(count)
    tasks = [Task.model_validate(record) for record in records]
    all_ids = {record["task_id"] for record in records}
    input_file = tmp_path / "tasks.jsonl"
    srsly.write_jsonl(input_file, records)

    lib_result = random_split(tasks, train_ratio=ratio, seed=seed)
    lib_train = [task.task_id for task in lib_result.train]
    lib_test = [task.task_id for task in lib_result.test]
    cli_train, cli_test = _run_cli_random_split(
        input_file=input_file,
        train_file=tmp_path / "train_cli.jsonl",
        test_file=tmp_path / "test_cli.jsonl",
        ratio=ratio,
        seed=seed,
    )
    expected_train_count = int(count * ratio)

    _assert_partition_contract(
        train_ids=lib_train,
        test_ids=lib_test,
        all_ids=all_ids,
        expected_train_count=expected_train_count,
    )
    _assert_partition_contract(
        train_ids=cli_train,
        test_ids=cli_test,
        all_ids=all_ids,
        expected_train_count=expected_train_count,
    )
    # Contract parity intentionally does not require identical membership.
    assert len(lib_train) == len(cli_train) == expected_train_count
    assert len(lib_test) == len(cli_test) == len(all_ids) - expected_train_count
