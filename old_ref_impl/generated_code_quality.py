"""Checks generated Java/Rust code for formatting and lint compliance."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from pydantic import TypeAdapter

from genfxn.bitops.models import BitopsSpec
from genfxn.core.models import Task
from genfxn.fsm.models import FsmSpec
from genfxn.graph_queries.models import GraphQueriesSpec
from genfxn.intervals.models import IntervalsSpec
from genfxn.langs.formatting import indent_java_method
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.piecewise.models import PiecewiseSpec
from genfxn.sequence_dp.models import SequenceDpSpec
from genfxn.simple_algorithms.models import SimpleAlgorithmsSpec
from genfxn.stack_bytecode.models import StackBytecodeSpec
from genfxn.stateful.models import StatefulSpec
from genfxn.stringrules.models import StringRulesSpec
from genfxn.temporal_logic.models import TemporalLogicSpec

_CHECK_LANGUAGES: tuple[Language, ...] = (Language.JAVA, Language.RUST)
_REQUIRED_TOOLS = (
    "cargo",
    "cargo-clippy",
    "google-java-format",
    "javac",
    "rustfmt",
)
_SUBPROCESS_TIMEOUT_SEC = 30.0
_CHECK_FAIL_HINT = (
    "Use --skip-generated-style-checks to bypass locally if needed."
)

# Keep this registry in sync with task families:
# add new families as "<family_name>": TypeAdapter(<FamilySpec>).
_SPEC_ADAPTERS: dict[str, TypeAdapter[Any]] = {
    "bitops": TypeAdapter(BitopsSpec),
    "fsm": TypeAdapter(FsmSpec),
    "graph_queries": TypeAdapter(GraphQueriesSpec),
    "intervals": TypeAdapter(IntervalsSpec),
    "piecewise": TypeAdapter(PiecewiseSpec),
    "sequence_dp": TypeAdapter(SequenceDpSpec),
    "simple_algorithms": TypeAdapter(SimpleAlgorithmsSpec),
    "stack_bytecode": TypeAdapter(StackBytecodeSpec),
    "stateful": TypeAdapter(StatefulSpec),
    "stringrules": TypeAdapter(StringRulesSpec),
    "temporal_logic": TypeAdapter(TemporalLogicSpec),
}


class GeneratedCodeQualityError(ValueError):
    """Raised when generated language quality checks fail."""


def _validate_required_tools() -> None:
    missing = [tool for tool in _REQUIRED_TOOLS if shutil.which(tool) is None]
    if missing:
        missing_list = ", ".join(sorted(missing))
        raise GeneratedCodeQualityError(
            "Generated-code quality checks require missing tool(s): "
            f"{missing_list}. {_CHECK_FAIL_HINT}"
        )


def _validate_spec_for_task(task: Task) -> Any:
    adapter = _SPEC_ADAPTERS.get(task.family)
    if adapter is None:
        raise GeneratedCodeQualityError(
            f"Unsupported family for generated-code checks: {task.family}"
        )
    try:
        return adapter.validate_python(task.spec, strict=True)
    except Exception as exc:
        raise GeneratedCodeQualityError(
            f"Spec validation failed for task {task.task_id} "
            f"(family={task.family}): {exc}"
        ) from exc


def _run_checked_subprocess(cmd: list[str], *, cwd: Path) -> None:
    try:
        subprocess.run(
            cmd,
            cwd=cwd,
            check=True,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SEC,
        )
    except subprocess.TimeoutExpired as exc:
        timeout_stdout = (exc.stdout or "").strip()
        timeout_stderr = (exc.stderr or "").strip()
        timeout_output = timeout_stderr or timeout_stdout
        timeout_suffix = f" Output: {timeout_output}" if timeout_output else ""
        raise subprocess.SubprocessError(
            "tool timed out after "
            f"{_SUBPROCESS_TIMEOUT_SEC:.1f}s while running: {' '.join(cmd)}."
            f"{timeout_suffix}"
        ) from exc


def _java_source(code: str) -> str:
    return f"public final class Main {{\n{indent_java_method(code)}\n}}\n"


def _rust_source(code: str) -> str:
    rendered = code.rstrip()
    return (
        "#![deny(warnings)]\n"
        "#![allow(dead_code)]\n\n"
        f"{rendered}\n\n"
        "fn main() {}\n"
    )


def _check_java_code(code: str) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src = tmp / "Main.java"
        src.write_text(_java_source(code), encoding="utf-8")
        _run_checked_subprocess(
            [
                "google-java-format",
                "--dry-run",
                "--set-exit-if-changed",
                str(src),
            ],
            cwd=tmp,
        )
        _run_checked_subprocess(
            ["javac", "-Xlint:all", "-Werror", str(src)],
            cwd=tmp,
        )


def _check_rust_code(code: str) -> None:
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src_dir = tmp / "src"
        src_dir.mkdir(parents=True, exist_ok=True)
        src = src_dir / "main.rs"
        src.write_text(_rust_source(code), encoding="utf-8")

        cargo_toml = tmp / "Cargo.toml"
        cargo_toml.write_text(
            (
                "[package]\n"
                'name = "generated_code_quality_check"\n'
                'version = "0.1.0"\n'
                'edition = "2021"\n'
            ),
            encoding="utf-8",
        )

        _run_checked_subprocess(["cargo", "fmt", "--", "--check"], cwd=tmp)
        _run_checked_subprocess(
            [
                "cargo",
                "clippy",
                "--quiet",
                "--",
                "-D",
                "warnings",
            ],
            cwd=tmp,
        )


def validate_generated_code_quality_tools() -> None:
    """Validate that external tool prerequisites are available."""
    _validate_required_tools()


def _render_code(
    task: Task,
    language: Language,
    spec_obj: Any,
    *,
    render_fn: Any | None = None,
) -> str:
    if render_fn is None:
        render_fn = get_render_fn(language, task.family)
    return render_fn(spec_obj, func_name="f")


def _format_subprocess_failure(exc: subprocess.CalledProcessError) -> str:
    stderr = (exc.stderr or "").strip()
    stdout = (exc.stdout or "").strip()
    output = stderr or stdout
    if not output:
        return f"command failed with exit code {exc.returncode}"
    return f"exit code {exc.returncode}: {output}"


def check_generated_code_quality(
    tasks: list[Task],
    *,
    families: set[str] | None = None,
    validate_tools: bool = True,
) -> None:
    """Validate generated Java/Rust formatting and lint contracts."""
    if not tasks:
        return

    if validate_tools:
        validate_generated_code_quality_tools()

    failures: list[str] = []
    for task in tasks:
        if families is not None and task.family not in families:
            continue
        spec_obj = _validate_spec_for_task(task)
        for language in _CHECK_LANGUAGES:
            try:
                render_fn = get_render_fn(language, task.family)
            except ValueError:
                # Family/language pair not supported by registry.
                continue
            try:
                rendered = _render_code(
                    task,
                    language,
                    spec_obj,
                    render_fn=render_fn,
                )
            except Exception as exc:
                failures.append(
                    f"{task.task_id} ({task.family}/{language.value}) "
                    f"render failed: {exc}"
                )
                continue

            try:
                if language == Language.JAVA:
                    _check_java_code(rendered)
                elif language == Language.RUST:
                    _check_rust_code(rendered)
                else:
                    raise RuntimeError(
                        f"Unsupported check language: {language!r}"
                    )
            except subprocess.CalledProcessError as exc:
                failures.append(
                    f"{task.task_id} ({task.family}/{language.value}) "
                    f"{' '.join(exc.cmd)} :: {_format_subprocess_failure(exc)}"
                )
            except (OSError, subprocess.SubprocessError) as exc:
                failures.append(
                    f"{task.task_id} ({task.family}/{language.value}) "
                    f"tool execution failed: {exc}"
                )

    if failures:
        details = "\n".join(f"- {entry}" for entry in failures[:20])
        suffix = ""
        if len(failures) > 20:
            suffix = f"\n- ... and {len(failures) - 20} more"
        raise GeneratedCodeQualityError(
            "Generated-code quality checks failed:\n"
            f"{details}{suffix}\n{_CHECK_FAIL_HINT}"
        )
