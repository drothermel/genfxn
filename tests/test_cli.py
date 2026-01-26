import srsly
from typer.testing import CliRunner

from genfxn.cli import app

runner = CliRunner()


class TestGenerate:
    def test_generate_piecewise(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(app, ["generate", "-o", str(output), "-f", "piecewise", "-n", "5"])

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = list(srsly.read_jsonl(output))
        assert len(tasks) == 5
        assert all(t["family"] == "piecewise" for t in tasks)

    def test_generate_stateful(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(app, ["generate", "-o", str(output), "-f", "stateful", "-n", "5"])

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = list(srsly.read_jsonl(output))
        assert len(tasks) == 5
        assert all(t["family"] == "stateful" for t in tasks)

    def test_generate_all(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(app, ["generate", "-o", str(output), "-f", "all", "-n", "10"])

        assert result.exit_code == 0
        tasks = list(srsly.read_jsonl(output))
        assert len(tasks) == 10

        families = {t["family"] for t in tasks}
        assert families == {"piecewise", "stateful"}

    def test_generate_with_seed(self, tmp_path) -> None:
        output1 = tmp_path / "tasks1.jsonl"
        output2 = tmp_path / "tasks2.jsonl"

        runner.invoke(app, ["generate", "-o", str(output1), "-f", "piecewise", "-n", "3", "-s", "42"])
        runner.invoke(app, ["generate", "-o", str(output2), "-f", "piecewise", "-n", "3", "-s", "42"])

        tasks1 = list(srsly.read_jsonl(output1))
        tasks2 = list(srsly.read_jsonl(output2))

        assert [t["task_id"] for t in tasks1] == [t["task_id"] for t in tasks2]

    def test_generate_unknown_family(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(app, ["generate", "-o", str(output), "-f", "unknown", "-n", "5"])

        assert result.exit_code == 1
        assert "Unknown family" in result.output


class TestSplit:
    def test_split_exact(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(app, ["generate", "-o", str(input_file), "-f", "stateful", "-n", "20", "-s", "42"])

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

        train = list(srsly.read_jsonl(train_file))
        test = list(srsly.read_jsonl(test_file))

        assert len(train) + len(test) == 20
        assert all(t["spec"]["template"] == "longest_run" for t in test)
        assert all(t["spec"]["template"] != "longest_run" for t in train)

    def test_split_range(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        runner.invoke(app, ["generate", "-o", str(input_file), "-f", "piecewise", "-n", "20", "-s", "42"])

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

        train = list(srsly.read_jsonl(train_file))
        test = list(srsly.read_jsonl(test_file))

        assert len(train) + len(test) == 20
        for t in test:
            val = t["spec"]["branches"][0]["condition"]["value"]
            assert -10 <= val <= 10


class TestInfo:
    def test_info_output(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        runner.invoke(app, ["generate", "-o", str(input_file), "-f", "all", "-n", "10", "-s", "42"])

        result = runner.invoke(app, ["info", str(input_file)])

        assert result.exit_code == 0
        assert "10 tasks" in result.stdout
        assert "piecewise: 5" in result.stdout
        assert "stateful: 5" in result.stdout

    def test_info_single_family(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        runner.invoke(app, ["generate", "-o", str(input_file), "-f", "piecewise", "-n", "7"])

        result = runner.invoke(app, ["info", str(input_file)])

        assert result.exit_code == 0
        assert "7 tasks" in result.stdout
        assert "piecewise: 7" in result.stdout
        assert "stateful" not in result.stdout
