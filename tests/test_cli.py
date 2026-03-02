import importlib.util
import os
import re
import stat
from typing import Any, cast

import pytest
import srsly
from typer.testing import CliRunner

import genfxn.cli as cli_module
from genfxn.cli import app
from genfxn.core.models import Task
from genfxn.fsm.models import FsmSpec
from genfxn.fsm.render import render_fsm
from genfxn.fsm.validate import CODE_UNSAFE_AST as FSM_CODE_UNSAFE_AST
from genfxn.fsm.validate import validate_fsm_task
from genfxn.graph_queries.models import GraphQueriesSpec
from genfxn.graph_queries.render import render_graph_queries
from genfxn.graph_queries.validate import (
    CODE_UNSAFE_AST as GRAPH_QUERIES_CODE_UNSAFE_AST,
)
from genfxn.graph_queries.validate import validate_graph_queries_task
from genfxn.sequence_dp.models import SequenceDpSpec
from genfxn.sequence_dp.render import render_sequence_dp
from genfxn.sequence_dp.validate import (
    CODE_UNSAFE_AST as SEQUENCE_DP_CODE_UNSAFE_AST,
)
from genfxn.sequence_dp.validate import validate_sequence_dp_task
from genfxn.stack_bytecode.models import StackBytecodeSpec
from genfxn.stack_bytecode.render import render_stack_bytecode
from genfxn.stack_bytecode.validate import (
    CODE_UNSAFE_AST,
    validate_stack_bytecode_task,
)
from genfxn.temporal_logic.models import TemporalLogicSpec
from genfxn.temporal_logic.render import render_temporal_logic
from genfxn.temporal_logic.validate import (
    CODE_UNSAFE_AST as TEMPORAL_LOGIC_CODE_UNSAFE_AST,
)
from genfxn.temporal_logic.validate import validate_temporal_logic_task

runner = CliRunner()
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    return _ANSI_ESCAPE_RE.sub("", text)


def _task_with_required_ids(task: dict[str, Any]) -> dict[str, Any]:
    task_id = task.get("task_id")
    if not isinstance(task_id, str):
        raise ValueError("task_id must be present as a string")

    task_with_ids = dict(task)
    task_with_ids.setdefault("spec_id", f"{task_id}_spec")
    task_with_ids.setdefault("sem_hash", f"{task_id}_sem")
    task_with_ids.setdefault("ast_id", {"python": f"{task_id}_ast"})
    return task_with_ids


def _tasks_with_required_ids(
    tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    return [_task_with_required_ids(task) for task in tasks]


@pytest.fixture(autouse=True)
def _stub_generated_style_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        cli_module,
        "check_generated_code_quality",
        lambda tasks: None,
    )


def _supports_bitops_family() -> bool:
    return importlib.util.find_spec("genfxn.bitops.task") is not None


def _supports_stack_bytecode_family() -> bool:
    return importlib.util.find_spec("genfxn.stack_bytecode.task") is not None


def _expected_all_families() -> set[str]:
    families = {
        "piecewise",
        "stateful",
        "simple_algorithms",
        "stringrules",
        "intervals",
        "fsm",
        "graph_queries",
        "sequence_dp",
        "temporal_logic",
    }
    if _supports_bitops_family():
        families.add("bitops")
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

    def test_generate_runs_generated_style_checks_by_default(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = tmp_path / "tasks.jsonl"
        seen_task_counts: list[int] = []

        def _fake_check(tasks: list[Task]) -> None:
            seen_task_counts.append(len(tasks))

        monkeypatch.setattr(
            cli_module, "check_generated_code_quality", _fake_check
        )

        result = runner.invoke(
            app,
            ["generate", "-o", str(output), "-f", "piecewise", "-n", "3"],
        )

        assert result.exit_code == 0
        assert seen_task_counts == [3]

    def test_generate_skip_generated_style_checks(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = tmp_path / "tasks.jsonl"

        def _fail_if_called(tasks: list[Task]) -> None:  # noqa: ARG001
            raise AssertionError("generated style checks should be skipped")

        monkeypatch.setattr(
            cli_module, "check_generated_code_quality", _fail_if_called
        )

        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "piecewise",
                "-n",
                "2",
                "--skip-generated-style-checks",
            ],
        )

        assert result.exit_code == 0

    def test_generate_quality_check_failure_does_not_write_output(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = tmp_path / "tasks.jsonl"

        def _raise_quality_error(tasks: list[Task]) -> None:  # noqa: ARG001
            raise cli_module.GeneratedCodeQualityError("bad generated code")

        monkeypatch.setattr(
            cli_module, "check_generated_code_quality", _raise_quality_error
        )

        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "piecewise",
                "-n",
                "2",
            ],
        )

        assert result.exit_code == 1
        assert "bad generated code" in result.output
        assert not output.exists()

    def test_generate_rejects_negative_count(self, tmp_path) -> None:
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
                "-3",
            ],
        )

        assert result.exit_code == 1
        assert "Error: --count must be >= 0" in result.output
        assert "Traceback" not in result.output

    def test_generate_output_io_error_has_clean_message(self, tmp_path) -> None:
        missing_dir = tmp_path / "missing"
        output = missing_dir / "tasks.jsonl"
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
            ],
        )

        assert result.exit_code == 1
        assert "file operation failed" in result.output
        assert str(missing_dir) in result.output
        assert "Traceback" not in result.output

    def test_generate_invalid_enum_option_has_clean_error(
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
                "stateful",
                "--templates",
                "not_a_template",
            ],
        )

        assert result.exit_code == 1
        assert "not_a_template" in result.output
        assert "TemplateType" in result.output
        assert "Traceback" not in result.output

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

    def test_generate_fsm(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app, ["generate", "-o", str(output), "-f", "fsm", "-n", "5"]
        )

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(t["family"] == "fsm" for t in tasks)
        for task in tasks:
            spec = FsmSpec.model_validate(task["spec"])
            assert task["code"] == render_fsm(spec)
            task_obj = Task.model_validate(task).model_copy(
                update={"spec": spec.model_dump()}
            )
            issues = validate_fsm_task(task_obj)
            assert not any(i.code == FSM_CODE_UNSAFE_AST for i in issues)

    def test_generate_sequence_dp(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app, ["generate", "-o", str(output), "-f", "sequence_dp", "-n", "5"]
        )

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(t["family"] == "sequence_dp" for t in tasks)
        for task in tasks:
            spec = SequenceDpSpec.model_validate(task["spec"])
            assert task["code"] == render_sequence_dp(spec)
            task_obj = Task.model_validate(task).model_copy(
                update={"spec": spec.model_dump()}
            )
            issues = validate_sequence_dp_task(task_obj)
            assert not any(
                i.code == SEQUENCE_DP_CODE_UNSAFE_AST for i in issues
            )

    def test_generate_intervals(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app, ["generate", "-o", str(output), "-f", "intervals", "-n", "5"]
        )

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(t["family"] == "intervals" for t in tasks)

    def test_generate_graph_queries(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            ["generate", "-o", str(output), "-f", "graph_queries", "-n", "5"],
        )

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(t["family"] == "graph_queries" for t in tasks)
        for task in tasks:
            spec = GraphQueriesSpec.model_validate(task["spec"])
            assert task["code"] == render_graph_queries(spec)
            task_obj = Task.model_validate(task).model_copy(
                update={"spec": spec.model_dump()}
            )
            issues = validate_graph_queries_task(task_obj)
            assert not any(
                i.code == GRAPH_QUERIES_CODE_UNSAFE_AST for i in issues
            )

    def test_generate_graph_queries_honors_value_range(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "graph_queries",
                "-n",
                "3",
                "--value-range",
                "2,4",
                "-s",
                "11",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert tasks
        for task in tasks:
            assert task["family"] == "graph_queries"
            assert task["axes"]["weight_range"] == [2, 4]

    def test_generate_graph_queries_clamps_negative_low_value_range(
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
                "graph_queries",
                "-n",
                "3",
                "--value-range",
                "-5,3",
                "-s",
                "11",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert tasks
        for task in tasks:
            assert task["family"] == "graph_queries"
            assert task["axes"]["weight_range"] == [0, 3]

    def test_generate_graph_queries_rejects_negative_only_value_range(
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
                "graph_queries",
                "-n",
                "1",
                "--value-range",
                "-9,-1",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid --value-range for graph_queries" in _strip_ansi(
            result.output
        )

    def test_generate_temporal_logic(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            ["generate", "-o", str(output), "-f", "temporal_logic", "-n", "5"],
        )

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(t["family"] == "temporal_logic" for t in tasks)
        for task in tasks:
            spec = TemporalLogicSpec.model_validate(task["spec"])
            assert task["code"] == render_temporal_logic(spec)
            task_obj = Task.model_validate(task).model_copy(
                update={"spec": spec.model_dump()}
            )
            issues = validate_temporal_logic_task(task_obj)
            assert not any(
                i.code == TEMPORAL_LOGIC_CODE_UNSAFE_AST for i in issues
            )

    def test_generate_sequence_dp_honors_divisor_range(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "sequence_dp",
                "-n",
                "2",
                "--divisor-range",
                "5,5",
                "-s",
                "11",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert tasks
        for task in tasks:
            assert task["family"] == "sequence_dp"
            assert task["axes"]["divisor_range"] == [5, 5]

    def test_generate_bitops_when_available(self, tmp_path) -> None:
        if not _supports_bitops_family():
            pytest.skip("bitops family is not available in this build")

        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app, ["generate", "-o", str(output), "-f", "bitops", "-n", "5"]
        )

        assert result.exit_code == 0
        assert "Generated 5 tasks" in result.stdout

        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(t["family"] == "bitops" for t in tasks)

    def test_generate_bitops_ignores_unrelated_range_options(
        self, tmp_path
    ) -> None:
        if not _supports_bitops_family():
            pytest.skip("bitops family is not available in this build")

        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "bitops",
                "-n",
                "2",
                "--threshold-range",
                "9,1",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert tasks
        assert all(task["family"] == "bitops" for task in tasks)

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
        expected_families = _expected_all_families()
        count = len(expected_families) + 1
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
                str(count),
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

        assert set(counts) == expected_families
        assert sum(counts.values()) == count
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

    def test_generate_simple_algorithms_rust_language(self, tmp_path) -> None:
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

    def test_generate_simple_algorithms_python_output(self, tmp_path) -> None:
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
                "5",
                "-s",
                "42",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert len(tasks) == 5
        assert all(task["family"] == "simple_algorithms" for task in tasks)
        assert all("__i32_" not in cast(str, task["code"]) for task in tasks)
        for task in tasks:
            namespace: dict[str, Any] = {}
            exec(cast(str, task["code"]), namespace)  # noqa: S102
            fn = namespace["f"]
            for query in cast(list[dict[str, Any]], task["queries"]):
                assert fn(query["input"]) == query["output"]

    def test_generate_all_rust_language(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        n_families = len(_expected_all_families())
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "all",
                "-n",
                str(n_families),
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
        assert len(tasks) == n_families
        families = {t["family"] for t in tasks}
        assert families == _expected_all_families()
        assert all("def f(" not in cast(str, t["code"]) for t in tasks)

    def test_generate_removes_partial_output_on_failure(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output = tmp_path / "tasks.jsonl"
        render_calls = 0
        original_render = cli_module.render_task_for_language

        def fail_after_first_render(*args, **kwargs):
            nonlocal render_calls
            render_calls += 1
            if render_calls > 1:
                raise RuntimeError("forced render failure")
            return original_render(*args, **kwargs)

        monkeypatch.setattr(
            cli_module,
            "render_task_for_language",
            fail_after_first_render,
        )

        result = runner.invoke(
            app,
            ["generate", "-o", str(output), "-f", "all", "-n", "3"],
        )

        assert result.exit_code == 1
        assert not output.exists()
        assert not list(tmp_path.glob(f".{output.name}.*.tmp"))

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
        for task in tasks:
            spec = StackBytecodeSpec.model_validate(task["spec"])
            assert task["code"] == render_stack_bytecode(spec)
            task_obj = Task.model_validate(task).model_copy(
                update={"spec": spec.model_dump()}
            )
            issues = validate_stack_bytecode_task(task_obj)
            assert not any(i.code == CODE_UNSAFE_AST for i in issues)

    def test_generate_stack_bytecode_honors_query_ranges(
        self, tmp_path
    ) -> None:
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
                "--value-range",
                "-3,4",
                "--list-length-range",
                "10,12",
                "-s",
                "9",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert tasks
        for task in tasks:
            for query in cast(list[dict[str, Any]], task["queries"]):
                xs = cast(list[int], query["input"])
                assert 10 <= len(xs) <= 12
                assert all(-3 <= value <= 4 for value in xs)

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
        assert "public static long[] f(long[] xs)" in tasks[0]["code"]
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
        assert "public static long f(long x)" in tasks[0]["code"]
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
        assert "def f(" in tasks[0]["code"]

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

    def test_atomic_output_file_uses_default_new_file_mode(
        self, tmp_path
    ) -> None:
        output = tmp_path / "tasks.jsonl"
        with cli_module._atomic_output_file(output) as handle:
            handle.write("{}\n")

        mode = stat.S_IMODE(output.stat().st_mode)
        current_umask = os.umask(0)
        os.umask(current_umask)
        assert mode == (0o666 & ~current_umask)

    def test_atomic_output_file_preserves_existing_file_mode(
        self, tmp_path
    ) -> None:
        output = tmp_path / "tasks.jsonl"
        output.write_text("before\n", encoding="utf-8")
        os.chmod(output, 0o640)

        with cli_module._atomic_output_file(output) as handle:
            handle.write("after\n")

        mode = stat.S_IMODE(output.stat().st_mode)
        assert mode == 0o640


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
        assert "intervals:" in result.stdout
        assert "fsm:" in result.stdout
        assert "graph_queries:" in result.stdout
        assert "sequence_dp:" in result.stdout
        assert "temporal_logic:" in result.stdout
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

    def test_info_malformed_row_has_clean_error(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        first_row = _task_with_required_ids(
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"template": "sum"},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "valid row",
            }
        )
        input_file.write_text(
            f'{srsly.json_dumps(first_row)}\n{{"broken":\n',
            encoding="utf-8",
        )

        result = runner.invoke(app, ["info", str(input_file)])

        assert result.exit_code != 0
        assert "invalid JSONL row" in result.output
        assert "line 2" in result.output
        assert "malformed JSON" in result.output
        assert "Traceback" not in result.output

    def test_info_missing_file_has_clean_error(self, tmp_path) -> None:
        missing_file = tmp_path / "missing.jsonl"

        result = runner.invoke(app, ["info", str(missing_file)])

        assert result.exit_code != 0
        assert "file operation failed" in result.output
        assert "Traceback" not in result.output
