import importlib.util
from typing import Any, cast

import pytest
import srsly
from typer.testing import CliRunner

from genfxn.cli import app

runner = CliRunner()


def _supports_stack_bytecode_family() -> bool:
    return (
        importlib.util.find_spec("genfxn.stack_bytecode.task") is not None
    )


def _expected_all_families() -> set[str]:
    families = {"piecewise", "stateful", "simple_algorithms", "stringrules"}
    if _supports_stack_bytecode_family():
        families.add("stack_bytecode")
    return families


def _supports_stack_bytecode_rust() -> bool:
    return (
        importlib.util.find_spec("genfxn.stack_bytecode.task") is not None
        and importlib.util.find_spec("genfxn.langs.rust.stack_bytecode")
        is not None
    )


def _supports_stack_bytecode_java() -> bool:
    return (
        importlib.util.find_spec("genfxn.stack_bytecode.task") is not None
        and importlib.util.find_spec("genfxn.langs.java.stack_bytecode")
        is not None
    )


class TestGenerate:
    def test_generate_piecewise(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app, ["generate", "-o", str(output), "-f", "piecewise", "-n", "5"]
        )

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(t["family"] == "piecewise" for t in tasks)

    def test_generate_stateful(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app, ["generate", "-o", str(output), "-f", "stateful", "-n", "5"]
        )

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(t["family"] == "stateful" for t in tasks)

    def test_generate_all(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app, ["generate", "-o", str(output), "-f", "all", "-n", "20"]
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 20

        families = {t["family"] for t in tasks}
        assert families == _expected_all_families()

    def test_generate_all_distributes_remainder_fairly(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "all",
                "-n",
                "6",
                "-s",
                "42",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        counts: dict[str, int] = {}
        for task in tasks:
            fam = cast(str, task["family"])
            counts[fam] = counts.get(fam, 0) + 1

        expected_families = _expected_all_families()
        assert set(counts) == expected_families
        assert sum(counts.values()) == 6
        assert max(counts.values()) - min(counts.values()) <= 1

    def test_generate_with_seed(self, tmp_path) -> None:
        output1 = tmp_path / "tasks1.jsonl"
        output2 = tmp_path / "tasks2.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output1),
                "-f",
                "piecewise",
                "-n",
                "3",
                "-s",
                "42",
            ],
        )
        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output2),
                "-f",
                "piecewise",
                "-n",
                "3",
                "-s",
                "42",
            ],
        )

        tasks1 = cast(list[dict[str, Any]], list(srsly.read_jsonl(output1)))
        tasks2 = cast(list[dict[str, Any]], list(srsly.read_jsonl(output2)))

        assert [t["task_id"] for t in tasks1] == [t["task_id"] for t in tasks2]

    def test_generate_unknown_family(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app, ["generate", "-o", str(output), "-f", "unknown", "-n", "5"]
        )

        assert result.exit_code == 1
        assert "Unknown family" in result.output

    def test_generate_rust_language(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "piecewise",
                "-n",
                "1",
                "--language",
                "rust",
            ],
        )

        assert result.exit_code == 0
        assert output.exists()
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 1
        assert tasks[0]["code"].startswith("fn f(")
        assert "def f(" not in tasks[0]["code"]

    def test_generate_simple_algorithms_rust_language(
        self, tmp_path
    ) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "simple_algorithms",
                "-n",
                "1",
                "--language",
                "rust",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 1
        assert tasks[0]["family"] == "simple_algorithms"
        assert tasks[0]["code"].startswith("fn f(")
        assert "def f(" not in tasks[0]["code"]

    def test_generate_all_rust_language(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "all",
                "-n",
                "8",
                "--language",
                "rust",
            ],
        )

        if (
            _supports_stack_bytecode_family()
            and not _supports_stack_bytecode_rust()
        ):
            assert result.exit_code == 1
            assert "Language 'rust' is not available" in result.output
            return

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 8
        families = {t["family"] for t in tasks}
        assert families == _expected_all_families()
        assert all("def f(" not in cast(str, t["code"]) for t in tasks)

    def test_generate_stack_bytecode_when_available(self, tmp_path) -> None:
        if not _supports_stack_bytecode_family():
            pytest.skip("stack_bytecode family is not available in this build")

        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            ["generate", "-o", str(output), "-f", "stack_bytecode", "-n", "3"],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 3
        assert all(t["family"] == "stack_bytecode" for t in tasks)

    def test_generate_stack_bytecode_with_difficulty(self, tmp_path) -> None:
        if not _supports_stack_bytecode_family():
            pytest.skip("stack_bytecode family is not available in this build")

        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "stack_bytecode",
                "-n",
                "4",
                "--difficulty",
                "4",
                "-s",
                "123",
            ],
        )
        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 4
        assert all(t["family"] == "stack_bytecode" for t in tasks)
        assert all(t["difficulty"] in {3, 4, 5} for t in tasks)

    def test_generate_stack_bytecode_with_variant(self, tmp_path) -> None:
        if not _supports_stack_bytecode_family():
            pytest.skip("stack_bytecode family is not available in this build")

        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "stack_bytecode",
                "-n",
                "2",
                "--difficulty",
                "3",
                "--variant",
                "3A",
                "-s",
                "12",
            ],
        )
        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 2
        assert all(t["family"] == "stack_bytecode" for t in tasks)

    def test_generate_stack_bytecode_invalid_difficulty(self, tmp_path) -> None:
        if not _supports_stack_bytecode_family():
            pytest.skip("stack_bytecode family is not available in this build")

        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "stack_bytecode",
                "-n",
                "1",
                "--difficulty",
                "6",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid difficulty 6 for stack_bytecode" in result.output

    def test_generate_stack_bytecode_rust_language(self, tmp_path) -> None:
        if not _supports_stack_bytecode_family():
            pytest.skip("stack_bytecode family is not available in this build")
        if not _supports_stack_bytecode_rust():
            pytest.skip("stack_bytecode rust renderer is not available")

        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "stack_bytecode",
                "-n",
                "1",
                "--language",
                "rust",
            ],
        )
        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert "fn f(xs: &[i64]) -> (i64, i64)" in tasks[0]["code"]
        output0 = tasks[0]["queries"][0]["output"]
        assert isinstance(output0, list)
        assert len(output0) == 2

    def test_generate_stack_bytecode_java_language(self, tmp_path) -> None:
        if not _supports_stack_bytecode_family():
            pytest.skip("stack_bytecode family is not available in this build")
        if not _supports_stack_bytecode_java():
            pytest.skip("stack_bytecode java renderer is not available")

        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "stack_bytecode",
                "-n",
                "1",
                "--language",
                "java",
            ],
        )
        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert "public static int[] f(int[] xs)" in tasks[0]["code"]
        output0 = tasks[0]["queries"][0]["output"]
        assert isinstance(output0, list)
        assert len(output0) == 2

    def test_generate_java_language(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "piecewise",
                "-n",
                "1",
                "--language",
                "java",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 1
        assert "public static int f(int x)" in tasks[0]["code"]
        assert "def f(" not in tasks[0]["code"]

    def test_generate_python_language(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "piecewise",
                "-n",
                "1",
                "--language",
                "python",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 1
        assert tasks[0]["code"].startswith("def f(")

    def test_generate_unknown_language(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "piecewise",
                "-n",
                "1",
                "--language",
                "go",
            ],
        )

        assert result.exit_code == 1
        assert "Unknown language 'go'" in result.output

    def test_generate_rejects_multiple_languages(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "piecewise",
                "-n",
                "1",
                "--language",
                "python,rust",
            ],
        )

        assert result.exit_code == 1
        assert "exactly one language value" in result.output

    def test_generate_rejects_all_language(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "piecewise",
                "-n",
                "1",
                "--language",
                "all",
            ],
        )

        assert result.exit_code == 1
        assert "Language 'all' is not supported" in result.output

    def test_generate_difficulty_requires_specific_family(
        self, tmp_path
    ) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "all",
                "--difficulty",
                "3",
            ],
        )
        assert result.exit_code == 1
        assert "requires a specific family" in result.output

    def test_generate_variant_requires_difficulty(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "stateful",
                "--variant",
                "3A",
            ],
        )
        assert result.exit_code == 1
        assert "requires --difficulty" in result.output

    def test_generate_stateful_rejects_in_set_predicate(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "stateful",
                "--predicate-types",
                "in_set",
            ],
        )
        assert result.exit_code == 1
        assert "IN_SET is not supported" in result.output

    @pytest.mark.parametrize("bad_range", ["1", "1,2,3", "a,b", "10,1"])
    def test_generate_rejects_bad_range_values(
        self, tmp_path, bad_range: str
    ) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "stateful",
                "--value-range",
                bad_range,
            ],
        )
        assert result.exit_code != 0
        assert (
            "Invalid range" in result.output
            or "low must be <=" in result.output
        )


class TestSplit:
    def test_split_exact(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "20",
                "-s",
                "42",
            ],
        )

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "template",
                "--holdout-value",
                "longest_run",
            ],
        )

        assert result.exit_code == 0
        assert "Train:" in result.stdout
        assert "Test:" in result.stdout

        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))

        assert len(train) + len(test) == 20
        assert all(t["spec"]["template"] == "longest_run" for t in test)
        assert all(t["spec"]["template"] != "longest_run" for t in train)

    def test_split_range(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "piecewise",
                "-n",
                "20",
                "-s",
                "42",
            ],
        )

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "branches.0.condition.value",
                "--holdout-value",
                "-10,10",
                "--holdout-type",
                "range",
            ],
        )

        assert result.exit_code == 0

        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))

        assert len(train) + len(test) == 20
        for t in test:
            val = int(t["spec"]["branches"][0]["condition"]["value"])
            assert -10 <= val <= 10

    def test_split_range_rejects_reversed_bounds(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "piecewise",
                "-n",
                "5",
                "-s",
                "42",
            ],
        )

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "branches.0.condition.value",
                "--holdout-value",
                "10,-10",
                "--holdout-type",
                "range",
            ],
        )
        assert result.exit_code != 0
        assert "low must be <= high" in result.output

    def test_split_exact_parses_numeric_holdout_value(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "piecewise",
                "-n",
                "20",
                "-s",
                "42",
            ],
        )

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(input_file)))
        holdout_value = tasks[0]["spec"]["branches"][0]["condition"]["value"]
        holdout_value_str = str(holdout_value)

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "branches.0.condition.value",
                "--holdout-value",
                holdout_value_str,
            ],
        )

        assert result.exit_code == 0
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert len(test) > 0
        assert all(
            t["spec"]["branches"][0]["condition"]["value"] == holdout_value
            for t in test
        )

    def test_split_exact_parses_bool_holdout_value(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"flag": True},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "Task with true flag",
            },
            {
                "task_id": "task-2",
                "family": "stateful",
                "spec": {"flag": False},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "Task with false flag",
            },
        ]
        srsly.write_jsonl(input_file, tasks)

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "flag",
                "--holdout-value",
                "true",
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))

        assert len(test) == 1
        assert test[0]["spec"]["flag"] is True
        assert len(train) == 1
        assert train[0]["spec"]["flag"] is False

    def test_split_contains_holdout_from_cli(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"labels": ["alpha", "beta"]},
                "code": "def f(xs):\n    return 0\n",
                "queries": [{"input": [1], "output": 0, "tag": "typical"}],
                "description": "contains alpha",
            },
            {
                "task_id": "task-2",
                "family": "stateful",
                "spec": {"labels": ["gamma"]},
                "code": "def f(xs):\n    return 0\n",
                "queries": [{"input": [1], "output": 0, "tag": "typical"}],
                "description": "does not contain alpha",
            },
        ]
        srsly.write_jsonl(input_file, tasks)

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "labels",
                "--holdout-value",
                "alpha",
                "--holdout-type",
                "contains",
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert len(test) == 1
        assert test[0]["task_id"] == "task-1"
        assert len(train) == 1
        assert train[0]["task_id"] == "task-2"

    def test_split_emits_warning_when_holdout_matches_none(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "5",
                "-s",
                "42",
            ],
        )

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "template",
                "--holdout-value",
                "definitely_not_a_template",
            ],
        )
        assert result.exit_code == 0
        assert "Warning: holdout matched 0" in result.output

    def test_split_invalid_holdout_type_has_clean_error(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "5",
                "-s",
                "42",
            ],
        )

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "template",
                "--holdout-value",
                "longest_run",
                "--holdout-type",
                "bogus",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid value for '--holdout-type'" in result.output
        assert "Traceback" not in result.output

    def test_split_case_mismatched_holdout_type_has_clean_error(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "5",
                "-s",
                "42",
            ],
        )

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--holdout-axis",
                "template",
                "--holdout-value",
                "longest_run",
                "--holdout-type",
                "Exact",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid value for '--holdout-type'" in result.output
        assert "Traceback" not in result.output

    def test_split_random_ratio_accepts_zero_and_one(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "10",
                "-s",
                "42",
            ],
        )

        result_0 = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--random-ratio",
                "0",
                "--seed",
                "42",
            ],
        )
        assert result_0.exit_code == 0
        train_0 = list(srsly.read_jsonl(train_file))
        test_0 = list(srsly.read_jsonl(test_file))
        assert len(train_0) == 0
        assert len(test_0) == 10

        result_1 = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                "--random-ratio",
                "1",
                "--seed",
                "42",
            ],
        )
        assert result_1.exit_code == 0
        train_1 = list(srsly.read_jsonl(train_file))
        test_1 = list(srsly.read_jsonl(test_file))
        assert len(train_1) == 10
        assert len(test_1) == 0

    def test_split_random_ratio_seed_is_deterministic(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file_1 = tmp_path / "train1.jsonl"
        test_file_1 = tmp_path / "test1.jsonl"
        train_file_2 = tmp_path / "train2.jsonl"
        test_file_2 = tmp_path / "test2.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "20",
                "-s",
                "42",
            ],
        )

        result_1 = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file_1),
                "--test",
                str(test_file_1),
                "--random-ratio",
                "0.5",
                "--seed",
                "123",
            ],
        )
        result_2 = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file_2),
                "--test",
                str(test_file_2),
                "--random-ratio",
                "0.5",
                "--seed",
                "123",
            ],
        )

        assert result_1.exit_code == 0
        assert result_2.exit_code == 0
        train_1 = cast(
            list[dict[str, Any]], list(srsly.read_jsonl(train_file_1))
        )
        train_2 = cast(
            list[dict[str, Any]], list(srsly.read_jsonl(train_file_2))
        )
        test_1 = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file_1)))
        test_2 = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file_2)))

        assert len(train_1) == 10
        assert len(test_1) == 10
        assert [t["task_id"] for t in train_1] == [
            t["task_id"] for t in train_2
        ]
        assert [t["task_id"] for t in test_1] == [t["task_id"] for t in test_2]

    def test_split_random_ratio_uses_floor_count(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "7",
                "-s",
                "42",
            ],
        )

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
                "0.4",
                "--seed",
                "123",
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert len(train) == 2
        assert len(test) == 5


class TestInfo:
    def test_info_output(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "all",
                "-n",
                "20",
                "-s",
                "42",
            ],
        )

        result = runner.invoke(app, ["info", str(input_file)])

        assert result.exit_code == 0
        assert "20 tasks" in result.stdout
        assert "piecewise:" in result.stdout
        assert "stateful:" in result.stdout
        assert "simple_algorithms:" in result.stdout
        assert "stringrules:" in result.stdout
        if _supports_stack_bytecode_family():
            assert "stack_bytecode:" in result.stdout

    def test_info_single_family(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        runner.invoke(
            app,
            ["generate", "-o", str(input_file), "-f", "piecewise", "-n", "7"],
        )

        result = runner.invoke(app, ["info", str(input_file)])

        assert result.exit_code == 0
        assert "7 tasks" in result.stdout
        assert "piecewise: 7" in result.stdout
        assert "stateful" not in result.stdout
