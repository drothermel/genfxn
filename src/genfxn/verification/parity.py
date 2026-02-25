from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from importlib import resources
from pathlib import Path
from string import Template
from typing import Any

from genfxn.core.models import Task
from genfxn.langs.registry import get_render_fn
from genfxn.langs.types import Language
from genfxn.verification.adapters import validate_spec_for_task
from genfxn.verification.models import (
    VerificationCase,
    VerificationLayer,
    normalize_case_value,
)

_SUBPROCESS_TIMEOUT_SEC = 20.0
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ParityFailure:
    task_id: str
    family: str
    case_id: str
    language: str
    message: str


def _format_subprocess_stream(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace").strip()
    return value.strip()


def _format_subprocess_error(
    exc: subprocess.CalledProcessError | subprocess.TimeoutExpired,
) -> str:
    stderr = _format_subprocess_stream(exc.stderr)
    stdout = _format_subprocess_stream(exc.stdout)
    detail = stderr or stdout
    if isinstance(exc, subprocess.TimeoutExpired):
        cmd = exc.cmd if isinstance(exc.cmd, str) else " ".join(exc.cmd)
        if detail:
            return f"timeout after {exc.timeout}s for '{cmd}': {detail}"
        return f"timeout after {exc.timeout}s for '{cmd}'"
    if detail:
        return f"exit={exc.returncode}: {detail}"
    return f"exit={exc.returncode}"


@lru_cache(maxsize=2)
def _load_runner_template(template_name: str) -> Template:
    template_text = (
        resources.files("genfxn.verification.templates")
        .joinpath(template_name)
        .read_text(encoding="utf-8")
    )
    return Template(template_text)


def _required_tools_for_language(language: Language) -> tuple[str, ...]:
    if language == Language.JAVA:
        return ("javac", "java")
    if language == Language.RUST:
        return ("rustc",)
    return ()


def _ensure_tools(language: Language) -> None:
    missing = [
        tool
        for tool in _required_tools_for_language(language)
        if shutil.which(tool) is None
    ]
    if missing:
        joined = ", ".join(sorted(missing))
        raise RuntimeError(
            f"missing required tool(s) for {language.value} parity: {joined}"
        )


def _encode_int_list(values: list[Any]) -> str:
    return ",".join(str(int(value)) for value in values)


def _encode_intervals(values: list[Any]) -> str:
    pairs: list[str] = []
    for pair in values:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            raise TypeError("interval input must contain 2-item pairs")
        start, end = pair
        pairs.append(f"{int(start)}:{int(end)}")
    return ",".join(pairs)


def _encode_input_args(family: str, input_value: Any) -> list[str]:
    match family:
        case "piecewise" | "bitops":
            if isinstance(input_value, bool) or not isinstance(
                input_value, int
            ):
                raise TypeError(f"{family} input must be int")
            return [str(input_value)]
        case (
            "stateful"
            | "simple_algorithms"
            | "stack_bytecode"
            | "fsm"
            | "temporal_logic"
        ):
            if not isinstance(input_value, list):
                raise TypeError(f"{family} input must be list[int]")
            return [_encode_int_list(input_value)]
        case "stringrules":
            if not isinstance(input_value, str):
                raise TypeError("stringrules input must be str")
            return [input_value]
        case "sequence_dp":
            if not isinstance(input_value, dict):
                raise TypeError("sequence_dp input must be dict")
            left = input_value.get("a")
            right = input_value.get("b")
            if not isinstance(left, list) or not isinstance(right, list):
                raise TypeError("sequence_dp input must include list a/b")
            return [_encode_int_list(left), _encode_int_list(right)]
        case "intervals":
            if not isinstance(input_value, list):
                raise TypeError("intervals input must be list[pair]")
            return [_encode_intervals(input_value)]
        case "graph_queries":
            if not isinstance(input_value, dict):
                raise TypeError("graph_queries input must be dict")
            src = input_value.get("src")
            dst = input_value.get("dst")
            if isinstance(src, bool) or isinstance(dst, bool):
                raise TypeError("graph_queries src/dst must be int")
            if not isinstance(src, int) or not isinstance(dst, int):
                raise TypeError("graph_queries src/dst must be int")
            return [str(src), str(dst)]
        case _:
            raise ValueError(f"Unsupported family for parity input: {family}")


def _decode_output(family: str, output_text: str) -> Any:
    if family == "stringrules":
        return output_text
    if family == "stack_bytecode":
        parts = output_text.strip().split(",", maxsplit=1)
        if len(parts) != 2:
            raise ValueError(f"invalid stack_bytecode output: {output_text!r}")
        return [int(parts[0]), int(parts[1])]
    return int(output_text.strip())


def _java_runner_source(family: str, method_code: str) -> str:
    match family:
        case "piecewise" | "bitops":
            main_body = (
                'long x = Long.parseLong(args.length == 0 ? "0" : args[0]);\n'
                "        System.out.print(f(x));"
            )
        case "stateful" | "simple_algorithms" | "temporal_logic":
            main_body = (
                '        String raw = args.length == 0 ? "" : args[0];\n'
                "        long[] xs = parseLongArray(raw);\n"
                "        System.out.print(f(xs));"
            )
        case "stack_bytecode":
            main_body = (
                '        String raw = args.length == 0 ? "" : args[0];\n'
                "        long[] xs = parseLongArray(raw);\n"
                "        long[] out = f(xs);\n"
                '        System.out.print(out[0] + "," + out[1]);'
            )
        case "fsm":
            main_body = (
                '        String raw = args.length == 0 ? "" : args[0];\n'
                "        int[] xs = parseIntArray(raw);\n"
                "        System.out.print(f(xs));"
            )
        case "stringrules":
            main_body = (
                '        String s = args.length == 0 ? "" : args[0];\n'
                "        System.out.print(f(s));"
            )
        case "sequence_dp":
            main_body = (
                '        String rawA = args.length >= 1 ? args[0] : "";\n'
                '        String rawB = args.length >= 2 ? args[1] : "";\n'
                "        long[] a = parseLongArray(rawA);\n"
                "        long[] b = parseLongArray(rawB);\n"
                "        System.out.print(f(a, b));"
            )
        case "intervals":
            main_body = (
                '        String raw = args.length == 0 ? "" : args[0];\n'
                "        long[][] intervals = parseIntervals(raw);\n"
                "        System.out.print(f(intervals));"
            )
        case "graph_queries":
            main_body = (
                "        int src = Integer.parseInt("
                'args.length >= 1 ? args[0] : "0");\n'
                "        int dst = Integer.parseInt("
                'args.length >= 2 ? args[1] : "0");\n'
                "        System.out.print(f(src, dst));"
            )
        case _:
            raise ValueError(f"Unsupported family for Java parity: {family}")

    return _load_runner_template("Main.java.tpl").substitute(
        method_code=method_code,
        main_body=main_body,
    )


def _rust_runner_source(family: str, function_code: str) -> str:
    match family:
        case "piecewise" | "bitops":
            main_body = (
                "    let x = args\n"
                "        .first()\n"
                "        .map(String::as_str)\n"
                '        .unwrap_or("0")\n'
                "        .parse::<i64>()\n"
                "        .unwrap();\n"
                '    print!("{}", f(x));'
            )
        case "stateful" | "simple_algorithms" | "fsm" | "temporal_logic":
            main_body = (
                "    let raw = args\n"
                "        .first()\n"
                "        .map(String::as_str)\n"
                '        .unwrap_or("");\n'
                "    let xs = parse_i64_vec(raw);\n"
                '    print!("{}", f(&xs));'
            )
        case "stack_bytecode":
            main_body = (
                "    let raw = args\n"
                "        .first()\n"
                "        .map(String::as_str)\n"
                '        .unwrap_or("");\n'
                "    let xs = parse_i64_vec(raw);\n"
                "    let out = f(&xs);\n"
                '    print!("{},{}", out.0, out.1);'
            )
        case "stringrules":
            main_body = (
                '    let s = args.first().map(String::as_str).unwrap_or("");\n'
                '    print!("{}", f(s));'
            )
        case "sequence_dp":
            main_body = (
                "    let raw_a = args\n"
                "        .first()\n"
                "        .map(String::as_str)\n"
                '        .unwrap_or("");\n'
                "    let raw_b = args\n"
                "        .get(1)\n"
                "        .map(String::as_str)\n"
                '        .unwrap_or("");\n'
                "    let a = parse_i64_vec(raw_a);\n"
                "    let b = parse_i64_vec(raw_b);\n"
                '    print!("{}", f(&a, &b));'
            )
        case "intervals":
            main_body = (
                "    let raw = args\n"
                "        .first()\n"
                "        .map(String::as_str)\n"
                '        .unwrap_or("");\n'
                "    let intervals = parse_intervals(raw);\n"
                '    print!("{}", f(&intervals));'
            )
        case "graph_queries":
            main_body = (
                "    let src = args\n"
                "        .first()\n"
                "        .map(String::as_str)\n"
                '        .unwrap_or("0")\n'
                "        .parse::<i64>()\n"
                "        .unwrap();\n"
                "    let dst = args\n"
                "        .get(1)\n"
                "        .map(String::as_str)\n"
                '        .unwrap_or("0")\n'
                "        .parse::<i64>()\n"
                "        .unwrap();\n"
                '    print!("{}", f(src, dst));'
            )
        case _:
            raise ValueError(f"Unsupported family for Rust parity: {family}")

    return _load_runner_template("Main.rs.tpl").substitute(
        function_code=function_code,
        main_body=main_body,
    )


@dataclass(frozen=True)
class _CompiledRunner:
    family: str
    command_prefix: tuple[str, ...]

    def run(self, input_value: Any) -> Any:
        args = _encode_input_args(self.family, input_value)
        command = [*self.command_prefix, *args]
        completed = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=_SUBPROCESS_TIMEOUT_SEC,
        )
        return _decode_output(self.family, completed.stdout)


@contextmanager
def _compiled_runner(
    *,
    family: str,
    language: Language,
    rendered_code: str,
) -> Iterator[_CompiledRunner]:
    _ensure_tools(language)

    with tempfile.TemporaryDirectory(
        prefix=f"genfxn-parity-{language.value}-"
    ) as tmp:
        tmp_dir = Path(tmp)

        if language == Language.JAVA:
            source = _java_runner_source(family, rendered_code)
            src_path = tmp_dir / "Main.java"
            src_path.write_text(source, encoding="utf-8")
            try:
                subprocess.run(
                    ["javac", str(src_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=_SUBPROCESS_TIMEOUT_SEC,
                )
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    f"javac compile failed: {_format_subprocess_error(exc)}"
                ) from exc
            yield _CompiledRunner(
                family=family,
                command_prefix=("java", "-cp", str(tmp_dir), "Main"),
            )
            return

        if language == Language.RUST:
            source = _rust_runner_source(family, rendered_code)
            src_path = tmp_dir / "main.rs"
            bin_path = tmp_dir / "main"
            src_path.write_text(source, encoding="utf-8")
            try:
                subprocess.run(
                    [
                        "rustc",
                        "--edition=2021",
                        str(src_path),
                        "-o",
                        str(bin_path),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=_SUBPROCESS_TIMEOUT_SEC,
                )
            except subprocess.CalledProcessError as exc:
                raise RuntimeError(
                    f"rustc compile failed: {_format_subprocess_error(exc)}"
                ) from exc
            yield _CompiledRunner(
                family=family,
                command_prefix=(str(bin_path),),
            )
            return

        raise ValueError(f"Unsupported parity language: {language.value}")


def select_parity_cases(
    task_cases: list[VerificationCase],
    *,
    parity_case_count: int,
) -> list[VerificationCase]:
    if parity_case_count <= 0:
        return []

    layer2 = sorted(
        [
            case
            for case in task_cases
            if case.layer == VerificationLayer.LAYER2_PROPERTY
        ],
        key=lambda case: case.case_id,
    )
    if len(layer2) >= parity_case_count:
        return layer2[:parity_case_count]

    remainder = sorted(
        [
            case
            for case in task_cases
            if case.layer != VerificationLayer.LAYER2_PROPERTY
        ],
        key=lambda case: (case.layer.value, case.case_id),
    )
    return [*layer2, *remainder[: parity_case_count - len(layer2)]]


def run_parity_checks(
    tasks: list[Task],
    cases: list[VerificationCase],
    *,
    parity_case_count: int,
) -> list[ParityFailure]:
    failures: list[ParityFailure] = []
    cases_by_task: dict[str, list[VerificationCase]] = {}
    for case in cases:
        cases_by_task.setdefault(case.task_id, []).append(case)

    for task in tasks:
        selected_cases = select_parity_cases(
            cases_by_task.get(task.task_id, []),
            parity_case_count=parity_case_count,
        )
        if not selected_cases:
            continue

        try:
            spec_obj = validate_spec_for_task(task.family, task.spec)
        except Exception as exc:
            failures.append(
                ParityFailure(
                    task_id=task.task_id,
                    family=task.family,
                    case_id="parity-setup",
                    language="python",
                    message=f"spec validation failed for parity: {exc}",
                )
            )
            continue

        for language in (Language.JAVA, Language.RUST):
            try:
                render_fn = get_render_fn(language, task.family)
            except ValueError as exc:
                logger.debug(
                    "Skipping parity renderer for task %s family=%s "
                    "language=%s: %s",
                    task.task_id,
                    task.family,
                    language.value,
                    exc,
                    exc_info=True,
                )
                continue

            try:
                rendered_code = render_fn(spec_obj, func_name="f")
                with _compiled_runner(
                    family=task.family,
                    language=language,
                    rendered_code=rendered_code,
                ) as runner:
                    for case in selected_cases:
                        try:
                            actual = normalize_case_value(
                                runner.run(case.input)
                            )
                        except (
                            subprocess.CalledProcessError,
                            subprocess.TimeoutExpired,
                        ) as exc:
                            failures.append(
                                ParityFailure(
                                    task_id=task.task_id,
                                    family=task.family,
                                    case_id=case.case_id,
                                    language=language.value,
                                    message=(
                                        "runtime failed: "
                                        f"{_format_subprocess_error(exc)}"
                                    ),
                                )
                            )
                            continue
                        except Exception as exc:
                            failures.append(
                                ParityFailure(
                                    task_id=task.task_id,
                                    family=task.family,
                                    case_id=case.case_id,
                                    language=language.value,
                                    message=f"runtime failed: {exc}",
                                )
                            )
                            continue

                        expected = normalize_case_value(case.expected_output)
                        if actual != expected:
                            failures.append(
                                ParityFailure(
                                    task_id=task.task_id,
                                    family=task.family,
                                    case_id=case.case_id,
                                    language=language.value,
                                    message=(
                                        f"expected {expected!r}, got {actual!r}"
                                    ),
                                )
                            )
            except Exception as exc:
                failures.append(
                    ParityFailure(
                        task_id=task.task_id,
                        family=task.family,
                        case_id="parity-setup",
                        language=language.value,
                        message=str(exc),
                    )
                )

    return failures
