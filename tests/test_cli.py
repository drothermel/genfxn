from typing import Any, cast

import srsly
from typer.testing import CliRunner

from genfxn.cli import app

runner = CliRunner()


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
        expected = {"piecewise", "stateful", "simple_algorithms", "stringrules"}
        assert families == expected

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
