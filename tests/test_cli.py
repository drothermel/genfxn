import importlib.util
import os
import stat
from typing import Any, cast

import pytest
import srsly
from typer.testing import CliRunner

import genfxn.cli as cli_module
from genfxn.cli import _matches_holdout as cli_matches_holdout
from genfxn.cli import _parse_numeric_range, app
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
from genfxn.splits import AxisHoldout, HoldoutType
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


def _supports_bitops_family() -> bool:
    return importlib.util.find_spec("genfxn.bitops.task") is not None


def _supports_stack_bytecode_family() -> bool:
    return (
        importlib.util.find_spec("genfxn.stack_bytecode.task") is not None
    )


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
        assert "Invalid --value-range for graph_queries" in result.output

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

    def test_generate_sequence_dp_honors_shared_ranges(
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
                "sequence_dp",
                "-n",
                "2",
                "--value-range",
                "17,19",
                "--divisor-range",
                "5,5",
                "--list-length-range",
                "10,10",
                "-s",
                "11",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert tasks
        for task in tasks:
            assert task["family"] == "sequence_dp"
            assert task["axes"]["value_range"] == [17, 19]
            assert task["axes"]["divisor_range"] == [5, 5]
            assert task["axes"]["len_a_range"] == [10, 10]
            assert task["axes"]["len_b_range"] == [10, 10]
            for query in cast(list[dict[str, Any]], task["queries"]):
                if query["tag"] != "typical":
                    continue
                query_input = cast(dict[str, list[int]], query["input"])
                assert len(query_input["a"]) == 10
                assert len(query_input["b"]) == 10

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

    def test_generate_bitops_honors_shared_value_range(self, tmp_path) -> None:
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
                "3",
                "--value-range",
                "17,19",
                "-s",
                "11",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        assert tasks
        for task in tasks:
            assert task["family"] == "bitops"
            assert task["axes"]["value_range"] == [17, 19]
            inputs = [
                cast(int, q["input"])
                for q in cast(list[dict[str, Any]], task["queries"])
            ]
            assert 17 in inputs
            assert 19 in inputs
            typical = [
                cast(int, q["input"])
                for q in cast(list[dict[str, Any]], task["queries"])
                if q["tag"] == "typical"
            ]
            assert all(17 <= x <= 19 for x in typical)

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

    def test_generate_all_honors_shared_value_range_for_bitops(
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
                "all",
                "-n",
                "20",
                "--value-range",
                "17,19",
                "-s",
                "13",
            ],
        )

        assert result.exit_code == 0
        tasks = cast(list[dict[str, Any]], list(srsly.read_jsonl(output)))
        bitops_tasks = [t for t in tasks if t["family"] == "bitops"]
        assert bitops_tasks
        for task in bitops_tasks:
            assert task["axes"]["value_range"] == [17, 19]

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

    def test_generate_simple_algorithms_no_i32_wrap(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "simple_algorithms",
                "-d",
                "4",
                "-n",
                "5",
                "-s",
                "42",
                "--no-i32-wrap",
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
        original_render = cli_module._render_task_for_language

        def fail_after_first_render(*args, **kwargs):
            nonlocal render_calls
            render_calls += 1
            if render_calls > 1:
                raise RuntimeError("forced render failure")
            return original_render(*args, **kwargs)

        monkeypatch.setattr(
            cli_module,
            "_render_task_for_language",
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

    def test_generate_fsm_with_difficulty(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "fsm",
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
        assert all(t["family"] == "fsm" for t in tasks)
        assert all(t["difficulty"] in {3, 4, 5} for t in tasks)

    def test_generate_fsm_with_variant(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "fsm",
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
        assert all(t["family"] == "fsm" for t in tasks)

    def test_generate_fsm_invalid_difficulty(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "fsm",
                "-n",
                "1",
                "--difficulty",
                "6",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid difficulty 6 for fsm" in result.output

    def test_generate_sequence_dp_with_difficulty(self, tmp_path) -> None:
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
        assert all(t["family"] == "sequence_dp" for t in tasks)
        assert all(t["difficulty"] in {3, 4, 5} for t in tasks)

    def test_generate_sequence_dp_with_variant(self, tmp_path) -> None:
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
        assert all(t["family"] == "sequence_dp" for t in tasks)

    def test_generate_sequence_dp_invalid_difficulty(
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
                "sequence_dp",
                "-n",
                "1",
                "--difficulty",
                "6",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid difficulty 6 for sequence_dp" in result.output

    def test_generate_graph_queries_with_difficulty(self, tmp_path) -> None:
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
        assert all(t["family"] == "graph_queries" for t in tasks)
        assert all(t["difficulty"] in {3, 4, 5} for t in tasks)

    def test_generate_graph_queries_with_variant(self, tmp_path) -> None:
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
        assert all(t["family"] == "graph_queries" for t in tasks)

    def test_generate_graph_queries_invalid_difficulty(
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
                "--difficulty",
                "6",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid difficulty 6 for graph_queries" in result.output

    def test_generate_temporal_logic_with_difficulty(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "temporal_logic",
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
        assert all(t["family"] == "temporal_logic" for t in tasks)
        assert all(t["difficulty"] in {3, 4, 5} for t in tasks)

    def test_generate_temporal_logic_with_variant(self, tmp_path) -> None:
        output = tmp_path / "tasks.jsonl"
        result = runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(output),
                "-f",
                "temporal_logic",
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
        assert all(t["family"] == "temporal_logic" for t in tasks)

    def test_generate_temporal_logic_invalid_difficulty(
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
                "temporal_logic",
                "-n",
                "1",
                "--difficulty",
                "6",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid difficulty 6 for temporal_logic" in result.output

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


class TestSplit:
    @pytest.mark.parametrize(
        "mode_args",
        [
            ("--random-ratio", "0.5", "--seed", "42"),
            (
                "--holdout-axis",
                "template",
                "--holdout-value",
                "longest_run",
            ),
        ],
    )
    def test_split_rejects_same_train_and_test_path(
        self, tmp_path, mode_args: tuple[str, ...]
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        same_output = tmp_path / "split.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "8",
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
                str(same_output),
                "--test",
                str(same_output),
                *mode_args,
            ],
        )

        assert result.exit_code != 0
        assert (
            "--train and --test must be different output paths"
            in result.output
        )
        assert not same_output.exists()

    @pytest.mark.parametrize(
        ("clashing_option", "expected_error"),
        [
            (
                "--train",
                "Error: input file and --train must be different paths",
            ),
            (
                "--test",
                "Error: input file and --test must be different paths",
            ),
        ],
    )
    def test_split_rejects_input_path_as_output(
        self,
        tmp_path,
        clashing_option: str,
        expected_error: str,
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        other_train = tmp_path / "train.jsonl"
        other_test = tmp_path / "test.jsonl"

        runner.invoke(
            app,
            [
                "generate",
                "-o",
                str(input_file),
                "-f",
                "stateful",
                "-n",
                "4",
                "-s",
                "7",
            ],
        )

        train_target = (
            input_file if clashing_option == "--train" else other_train
        )
        test_target = input_file if clashing_option == "--test" else other_test
        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_target),
                "--test",
                str(test_target),
                "--random-ratio",
                "0.5",
                "--seed",
                "11",
            ],
        )

        assert result.exit_code == 1
        assert expected_error in result.output
        assert "Traceback" not in result.output

    def test_split_rejects_random_and_holdout_options_together(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"
        srsly.write_jsonl(input_file, [])

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
                "0.8",
                "--holdout-axis",
                "template",
                "--holdout-value",
                "sum",
            ],
        )

        assert result.exit_code != 0
        assert (
            "Cannot use both --random-ratio and holdout options"
            in result.output
        )

    def test_split_output_io_error_has_clean_message(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        srsly.write_jsonl(input_file, [])
        missing_dir = tmp_path / "missing"
        train_file = missing_dir / "train.jsonl"
        test_file = missing_dir / "test.jsonl"

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
                "0.5",
            ],
        )

        assert result.exit_code != 0
        assert "file operation failed" in result.output
        assert str(missing_dir) in result.output
        assert "Traceback" not in result.output

    def test_render_os_error_prefers_destination_path(self) -> None:
        err = OSError("No such file or directory")
        err.filename = "/tmp/.train.jsonl.tmp"
        err.filename2 = "/tmp/train.jsonl"
        err.strerror = "No such file or directory"
        rendered = cli_module._render_os_error(err)
        assert "/tmp/train.jsonl" in rendered
        assert "/tmp/.train.jsonl.tmp" not in rendered

    def test_atomic_split_outputs_cleans_up_when_second_tmp_create_fails(
        self, tmp_path
    ) -> None:
        train = tmp_path / "train_dir" / "train.jsonl"
        test = tmp_path / "missing_dir" / "test.jsonl"
        train.parent.mkdir(parents=True)

        with pytest.raises(FileNotFoundError):
            with cli_module._atomic_split_outputs(train, test):
                pass

        leaked = list(train.parent.glob(".train.jsonl.*.tmp"))
        assert leaked == []

    def test_atomic_split_outputs_rolls_back_on_second_replace_failure(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        train = tmp_path / "train.jsonl"
        test = tmp_path / "test.jsonl"
        train.write_text("old-train\n", encoding="utf-8")
        test.write_text("old-test\n", encoding="utf-8")

        original_replace = cli_module.os.replace
        saw_failure = False

        def _flaky_replace(src, dst):
            nonlocal saw_failure
            src_path = src if isinstance(src, str) else str(src)
            dst_path = dst if isinstance(dst, str) else str(dst)
            if (
                not saw_failure
                and dst_path == str(test)
                and src_path.endswith(".tmp")
            ):
                saw_failure = True
                raise OSError("simulated replace failure")
            return original_replace(src, dst)

        monkeypatch.setattr(cli_module.os, "replace", _flaky_replace)

        with pytest.raises(OSError, match="simulated replace failure"):
            with cli_module._atomic_split_outputs(train, test) as (
                train_handle,
                test_handle,
            ):
                train_handle.write("new-train\n")
                test_handle.write("new-test\n")

        assert train.read_text(encoding="utf-8") == "old-train\n"
        assert test.read_text(encoding="utf-8") == "old-test\n"
        assert list(tmp_path.glob(".train.jsonl.*.tmp")) == []
        assert list(tmp_path.glob(".test.jsonl.*.tmp")) == []

    def test_split_requires_random_or_holdout_mode(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"
        srsly.write_jsonl(input_file, [])

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
            ],
        )

        assert result.exit_code != 0
        assert "Must provide --random-ratio or holdout options" in result.output

    @pytest.mark.parametrize(
        "holdout_args",
        [
            ("--holdout-axis", "template"),
            ("--holdout-value", "sum"),
        ],
    )
    def test_split_requires_both_holdout_axis_and_value(
        self, tmp_path, holdout_args: tuple[str, str]
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"
        srsly.write_jsonl(input_file, [])

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file),
                "--test",
                str(test_file),
                *holdout_args,
            ],
        )

        assert result.exit_code != 0
        assert (
            "Both --holdout-axis and --holdout-value are required"
            in result.output
        )

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

    def test_split_holdout_malformed_second_line_no_partial_outputs(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        first_row = {
            "task_id": "task-1",
            "family": "stateful",
            "spec": {"template": "sum"},
            "code": "def f(x):\n    return x\n",
            "queries": [{"input": 1, "output": 1, "tag": "typical"}],
            "description": "valid row",
        }
        input_file.write_text(
            f"{srsly.json_dumps(first_row)}\n" '{"broken":\n',
            encoding="utf-8",
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
                "sum",
                "--holdout-type",
                "exact",
            ],
        )

        assert result.exit_code != 0
        assert "invalid JSONL row" in result.output
        assert "line 2" in result.output
        assert "malformed JSON" in result.output
        assert "Traceback" not in result.output
        assert not train_file.exists()
        assert not test_file.exists()

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

    @pytest.mark.parametrize("bad_range", ["1", "1,2,3", "a,b"])
    def test_split_range_rejects_malformed_range_values(
        self, tmp_path, bad_range: str
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"
        srsly.write_jsonl(input_file, [])

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
                "score",
                "--holdout-value",
                bad_range,
                "--holdout-type",
                "range",
            ],
        )
        assert result.exit_code != 0
        assert "Invalid range" in result.output

    @pytest.mark.parametrize(
        "bad_range",
        ["nan,1", "1,nan", "inf,1", "1,inf", "-inf,1", "1,-inf"],
    )
    def test_split_range_rejects_non_finite_bounds(
        self, tmp_path, bad_range: str
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
                bad_range,
                "--holdout-type",
                "range",
            ],
        )
        assert result.exit_code != 0
        assert "bounds must be finite numbers" in result.output

    @pytest.mark.parametrize("holdout_type", ["exact", "contains"])
    @pytest.mark.parametrize(
        "bad_value",
        ["NaN", "Infinity", "-Infinity", "nan", "inf", "-inf"],
    )
    def test_split_exact_contains_reject_non_finite_holdout_values(
        self, tmp_path, holdout_type: str, bad_value: str
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"
        axis_path = "value" if holdout_type == "exact" else "values"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": 1.0, "values": [1.0, 2.0]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "finite values",
            }
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
                axis_path,
                "--holdout-value",
                bad_value,
                "--holdout-type",
                holdout_type,
            ],
        )
        assert result.exit_code != 0
        assert "non-finite numbers" in result.output
        assert "exact/contains holdouts" in result.output

    @pytest.mark.parametrize("holdout_type", ["exact", "contains"])
    @pytest.mark.parametrize(
        "bad_value",
        ["[1,2", '{"k": 1', '"unterminated'],
    )
    def test_split_exact_contains_reject_malformed_json_like_holdout_values(
        self, tmp_path, holdout_type: str, bad_value: str
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"
        axis_path = "value" if holdout_type == "exact" else "values"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": 1, "values": [1, 2]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "finite values",
            }
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
                axis_path,
                "--holdout-value",
                bad_value,
                "--holdout-type",
                holdout_type,
            ],
        )
        assert result.exit_code != 0
        assert "malformed JSON literal" in result.output

    @pytest.mark.parametrize("holdout_type", ["exact", "contains"])
    @pytest.mark.parametrize(
        "bad_value",
        ["t", "f", "n", "tru", "nul", "01", "+1"],
    )
    def test_split_exact_contains_reject_malformed_json_scalar_holdout_values(
        self, tmp_path, holdout_type: str, bad_value: str
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"
        axis_path = "value" if holdout_type == "exact" else "values"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": "tru", "values": ["tru"]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "string values",
            }
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
                axis_path,
                "--holdout-value",
                bad_value,
                "--holdout-type",
                holdout_type,
            ],
        )
        assert result.exit_code != 0
        assert "malformed JSON scalar" in result.output

    @pytest.mark.parametrize("holdout_type", ["exact", "contains"])
    @pytest.mark.parametrize(
        "bad_value",
        ["True", "False", "Null"],
    )
    def test_split_exact_contains_reject_case_mismatched_json_scalars(
        self, tmp_path, holdout_type: str, bad_value: str
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"
        axis_path = "value" if holdout_type == "exact" else "values"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": True, "values": [True, False]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "boolean values",
            }
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
                axis_path,
                "--holdout-value",
                bad_value,
                "--holdout-type",
                holdout_type,
            ],
        )
        assert result.exit_code != 0
        assert "malformed JSON scalar" in result.output

    def test_split_exact_allows_json_string_nan_literal(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": "nan"},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "string nan",
            },
            {
                "task_id": "task-2",
                "family": "stateful",
                "spec": {"value": "other"},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "string other",
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
                "value",
                "--holdout-value",
                '"nan"',
                "--holdout-type",
                "exact",
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert [task["task_id"] for task in test] == ["task-1"]
        assert [task["task_id"] for task in train] == ["task-2"]

    def test_split_range_parses_float_bounds(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"score": 0.25},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "score 0.25",
            },
            {
                "task_id": "task-2",
                "family": "stateful",
                "spec": {"score": 0.5},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "score 0.5",
            },
            {
                "task_id": "task-3",
                "family": "stateful",
                "spec": {"score": 1.25},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 3, "output": 3, "tag": "typical"}],
                "description": "score 1.25",
            },
            {
                "task_id": "task-4",
                "family": "stateful",
                "spec": {"score": 2.0},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 4, "output": 4, "tag": "typical"}],
                "description": "score 2.0",
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
                "score",
                "--holdout-value",
                "0.5,1.25",
                "--holdout-type",
                "range",
            ],
        )
        assert result.exit_code == 0

        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert {task["task_id"] for task in test} == {"task-2", "task-3"}
        assert {task["task_id"] for task in train} == {"task-1", "task-4"}

    def test_split_range_parses_large_integer_bounds_exactly(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-large",
                "family": "stateful",
                "spec": {"score": 9_223_372_036_854_775_807},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "max int64",
            },
            {
                "task_id": "task-neighbor",
                "family": "stateful",
                "spec": {"score": 9_223_372_036_854_775_806},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "max int64 minus one",
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
                "score",
                "--holdout-value",
                "9223372036854775807,9223372036854775807",
                "--holdout-type",
                "range",
            ],
        )
        assert result.exit_code == 0

        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert [task["task_id"] for task in test] == ["task-large"]
        assert [task["task_id"] for task in train] == ["task-neighbor"]

    def test_parse_numeric_range_scientific_notation_uses_float(self) -> None:
        parsed = _parse_numeric_range("1e3,2.5e3")
        assert parsed is not None
        assert parsed == (1000.0, 2500.0)
        assert isinstance(parsed[0], float)
        assert isinstance(parsed[1], float)

    def test_split_range_bool_axis_values_do_not_match(self, tmp_path) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"flag": False},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "bool false",
            },
            {
                "task_id": "task-2",
                "family": "stateful",
                "spec": {"flag": True},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "bool true",
            },
            {
                "task_id": "task-3",
                "family": "stateful",
                "spec": {"flag": 0},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 3, "output": 3, "tag": "typical"}],
                "description": "int zero",
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
                "0,0",
                "--holdout-type",
                "range",
            ],
        )
        assert result.exit_code == 0

        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert {task["task_id"] for task in test} == {"task-3"}
        assert {task["task_id"] for task in train} == {"task-1", "task-2"}

    def test_split_range_rejects_bool_bounds_in_matcher(self) -> None:
        task = Task.model_validate(
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"score": 0},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "score zero",
            }
        )
        bool_bound_holdout = AxisHoldout(
            axis_path="score",
            holdout_type=HoldoutType.RANGE,
            holdout_value=(False, 1),
        )
        numeric_holdout = AxisHoldout(
            axis_path="score",
            holdout_type=HoldoutType.RANGE,
            holdout_value=(0, 1),
        )

        assert cli_matches_holdout(task, bool_bound_holdout) is False
        assert cli_matches_holdout(task, numeric_holdout) is True

    @pytest.mark.parametrize(
        ("spec_value", "holdout_value", "expected"),
        [
            pytest.param(False, 0, False, id="bool-false-vs-int-zero"),
            pytest.param(0, 0, True, id="int-zero-vs-int-zero"),
            pytest.param(True, 1, False, id="bool-true-vs-int-one"),
            pytest.param(1, 1, True, id="int-one-vs-int-one"),
            pytest.param(1, 1.0, False, id="int-one-vs-float-one"),
            pytest.param(1.0, 1.0, True, id="float-one-vs-float-one"),
            pytest.param("1", 1, False, id="string-one-vs-int-one"),
            pytest.param(1, "1", False, id="int-one-vs-string-one"),
            pytest.param("1", "1", True, id="string-one-vs-string-one"),
            pytest.param(None, None, True, id="none-vs-none"),
        ],
    )
    def test_split_exact_matcher_type_matrix(
        self, spec_value: object, holdout_value: object, expected: bool
    ) -> None:
        task = Task.model_validate(
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": spec_value},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "type matrix",
            }
        )
        holdout = AxisHoldout(
            axis_path="value",
            holdout_type=HoldoutType.EXACT,
            holdout_value=holdout_value,
        )

        assert cli_matches_holdout(task, holdout) is expected

    @pytest.mark.parametrize(
        ("spec_value", "holdout_value", "expected"),
        [
            pytest.param(
                [False],
                0,
                False,
                id="contains-bool-false-vs-int-zero",
            ),
            pytest.param([0], 0, True, id="contains-int-zero-vs-int-zero"),
            pytest.param(
                [0.0],
                0,
                False,
                id="contains-float-zero-vs-int-zero",
            ),
            pytest.param([True], 1, False, id="contains-bool-true-vs-int-one"),
            pytest.param([1], 1, True, id="contains-int-one-vs-int-one"),
        ],
    )
    def test_split_contains_matcher_type_matrix(
        self, spec_value: object, holdout_value: object, expected: bool
    ) -> None:
        task = Task.model_validate(
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": spec_value},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "contains type matrix",
            }
        )
        holdout = AxisHoldout(
            axis_path="value",
            holdout_type=HoldoutType.CONTAINS,
            holdout_value=holdout_value,
        )

        assert cli_matches_holdout(task, holdout) is expected

    def test_split_exact_matcher_nested_type_sensitive(self) -> None:
        task = Task.model_validate(
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": [0]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "nested exact",
            }
        )
        holdout = AxisHoldout(
            axis_path="value",
            holdout_type=HoldoutType.EXACT,
            holdout_value=[False],
        )

        assert cli_matches_holdout(task, holdout) is False

    def test_split_contains_matcher_nested_type_sensitive(self) -> None:
        task = Task.model_validate(
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"value": [[0]]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "nested contains",
            }
        )
        holdout = AxisHoldout(
            axis_path="value",
            holdout_type=HoldoutType.CONTAINS,
            holdout_value=[False],
        )

        assert cli_matches_holdout(task, holdout) is False

    def test_split_exact_matcher_none_does_not_match_missing_path(
        self,
    ) -> None:
        task = Task.model_validate(
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "missing path",
            }
        )
        holdout = AxisHoldout(
            axis_path="value",
            holdout_type=HoldoutType.EXACT,
            holdout_value=None,
        )

        assert cli_matches_holdout(task, holdout) is False

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

    def test_split_exact_distinguishes_bool_false_from_numeric_zero(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-1",
                "family": "stateful",
                "spec": {"flag": False},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "bool false",
            },
            {
                "task_id": "task-2",
                "family": "stateful",
                "spec": {"flag": 0},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "int zero",
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
                "0",
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))

        assert [task["task_id"] for task in test] == ["task-2"]
        assert [task["task_id"] for task in train] == ["task-1"]

    @pytest.mark.parametrize(
        ("holdout_value", "expected_test_id"),
        [
            pytest.param("false", "task-bool-false", id="holdout-bool-false"),
            pytest.param("0", "task-int-zero", id="holdout-int-zero"),
            pytest.param("true", "task-bool-true", id="holdout-bool-true"),
            pytest.param("1", "task-int-one", id="holdout-int-one"),
            pytest.param("1.0", "task-float-one", id="holdout-float-one"),
            pytest.param('"1"', "task-string-one", id="holdout-string-one"),
            pytest.param("null", "task-none", id="holdout-none"),
        ],
    )
    def test_split_exact_type_matrix_end_to_end(
        self, tmp_path, holdout_value: str, expected_test_id: str
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-bool-false",
                "family": "stateful",
                "spec": {"value": False},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "bool false",
            },
            {
                "task_id": "task-int-zero",
                "family": "stateful",
                "spec": {"value": 0},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "int zero",
            },
            {
                "task_id": "task-bool-true",
                "family": "stateful",
                "spec": {"value": True},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 3, "output": 3, "tag": "typical"}],
                "description": "bool true",
            },
            {
                "task_id": "task-int-one",
                "family": "stateful",
                "spec": {"value": 1},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 4, "output": 4, "tag": "typical"}],
                "description": "int one",
            },
            {
                "task_id": "task-float-one",
                "family": "stateful",
                "spec": {"value": 1.0},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 5, "output": 5, "tag": "typical"}],
                "description": "float one",
            },
            {
                "task_id": "task-string-one",
                "family": "stateful",
                "spec": {"value": "1"},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 6, "output": 6, "tag": "typical"}],
                "description": "string one",
            },
            {
                "task_id": "task-none",
                "family": "stateful",
                "spec": {"value": None},
                "code": "def solve(x):\n    return x\n",
                "queries": [{"input": 7, "output": 7, "tag": "typical"}],
                "description": "none",
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
                "value",
                "--holdout-value",
                holdout_value,
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))

        assert [task["task_id"] for task in test] == [expected_test_id]
        assert len(train) == len(tasks) - 1
        assert expected_test_id not in {task["task_id"] for task in train}

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

    def test_split_exact_nested_type_sensitive_end_to_end(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-bool",
                "family": "stateful",
                "spec": {"value": [False]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "nested bool list",
            },
            {
                "task_id": "task-int",
                "family": "stateful",
                "spec": {"value": [0]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "nested int list",
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
                "value",
                "--holdout-value",
                "[false]",
                "--holdout-type",
                "exact",
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert [task["task_id"] for task in test] == ["task-bool"]
        assert [task["task_id"] for task in train] == ["task-int"]

    def test_split_contains_nested_type_sensitive_end_to_end(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-bool",
                "family": "stateful",
                "spec": {"value": [[False], [1]]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "contains nested bool list",
            },
            {
                "task_id": "task-int",
                "family": "stateful",
                "spec": {"value": [[0], [1]]},
                "code": "def f(x):\n    return x\n",
                "queries": [{"input": 2, "output": 2, "tag": "typical"}],
                "description": "contains nested int list",
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
                "value",
                "--holdout-value",
                "[false]",
                "--holdout-type",
                "contains",
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert [task["task_id"] for task in test] == ["task-bool"]
        assert [task["task_id"] for task in train] == ["task-int"]

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

    def test_split_warning_preserves_first_none_axis_value(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks = [
            {
                "task_id": "task-first-none",
                "family": "stateful",
                "spec": {"probe": None},
                "code": "def f(x):\n    return x",
                "queries": [],
                "description": "first has none",
            },
            {
                "task_id": "task-second-five",
                "family": "stateful",
                "spec": {"probe": 5},
                "code": "def f(x):\n    return x",
                "queries": [],
                "description": "second has five",
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
                "probe",
                "--holdout-value",
                "definitely_no_match",
            ],
        )

        assert result.exit_code == 0
        assert "Warning: holdout matched 0 of 2 tasks" in result.output
        assert "First task's value at 'probe': None" in result.output

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

    @pytest.mark.parametrize("ratio", ["nan", "NaN"])
    def test_split_random_ratio_rejects_non_finite_values(
        self, tmp_path, ratio: str
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
                "4",
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
                ratio,
                "--seed",
                "7",
            ],
        )

        assert result.exit_code == 1
        assert "Error: --random-ratio must be in [0, 1]" in result.output
        assert "Traceback" not in result.output

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

    def test_split_random_ratio_is_deterministic_for_fixed_seed(
        self, tmp_path
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file_1 = tmp_path / "train1.jsonl"
        test_file_1 = tmp_path / "test1.jsonl"
        train_file_2 = tmp_path / "train2.jsonl"
        test_file_2 = tmp_path / "test2.jsonl"

        tasks: list[dict[str, Any]] = []
        for i in range(10):
            tasks.append(
                {
                    "task_id": f"task-{i}",
                    "family": "stateful",
                    "spec": {"n": i},
                    "code": "def f(x):\n    return x\n",
                    "queries": [
                        {"input": i, "output": i, "tag": "typical"}
                    ],
                    "description": f"task {i}",
                }
            )
        srsly.write_jsonl(input_file, tasks)

        result = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file_1),
                "--test",
                str(test_file_1),
                "--random-ratio",
                "0.6",
                "--seed",
                "123",
            ],
        )
        result_again = runner.invoke(
            app,
            [
                "split",
                str(input_file),
                "--train",
                str(train_file_2),
                "--test",
                str(test_file_2),
                "--random-ratio",
                "0.6",
                "--seed",
                "123",
            ],
        )

        assert result.exit_code == 0
        assert result_again.exit_code == 0
        train_1 = cast(
            list[dict[str, Any]], list(srsly.read_jsonl(train_file_1))
        )
        test_1 = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file_1)))
        train_2 = cast(
            list[dict[str, Any]], list(srsly.read_jsonl(train_file_2))
        )
        test_2 = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file_2)))

        assert len(train_1) == 6
        assert len(test_1) == 4
        assert [task["task_id"] for task in train_1] == [
            task["task_id"] for task in train_2
        ]
        assert [task["task_id"] for task in test_1] == [
            task["task_id"] for task in test_2
        ]
        assert {task["task_id"] for task in train_1}.isdisjoint(
            {task["task_id"] for task in test_1}
        )
        assert {task["task_id"] for task in train_1}.union(
            {task["task_id"] for task in test_1}
        ) == {task["task_id"] for task in tasks}

    def test_split_random_ratio_does_not_call_library_helper(
        self, tmp_path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        input_file = tmp_path / "tasks.jsonl"
        train_file = tmp_path / "train.jsonl"
        test_file = tmp_path / "test.jsonl"

        tasks: list[dict[str, Any]] = []
        for i in range(8):
            tasks.append(
                {
                    "task_id": f"task-{i}",
                    "family": "stateful",
                    "spec": {"n": i},
                    "code": "def f(x):\n    return x\n",
                    "queries": [
                        {"input": i, "output": i, "tag": "typical"}
                    ],
                    "description": f"task {i}",
                }
            )
        srsly.write_jsonl(input_file, tasks)

        def _raise_random_split(*args: Any, **kwargs: Any) -> Any:
            raise AssertionError("random_split helper should not be used")

        monkeypatch.setattr(
            "genfxn.splits.random_split",
            _raise_random_split,
        )
        monkeypatch.setattr(
            "genfxn.cli.random_split",
            _raise_random_split,
            raising=False,
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
                "0.5",
                "--seed",
                "123",
            ],
        )

        assert result.exit_code == 0
        train = cast(list[dict[str, Any]], list(srsly.read_jsonl(train_file)))
        test = cast(list[dict[str, Any]], list(srsly.read_jsonl(test_file)))
        assert len(train) == 4
        assert len(test) == 4


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
        first_row = {
            "task_id": "task-1",
            "family": "stateful",
            "spec": {"template": "sum"},
            "code": "def f(x):\n    return x\n",
            "queries": [{"input": 1, "output": 1, "tag": "typical"}],
            "description": "valid row",
        }
        input_file.write_text(
            f"{srsly.json_dumps(first_row)}\n" '{"broken":\n',
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
