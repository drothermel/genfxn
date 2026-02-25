import importlib.util
import shutil
import subprocess
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from types import ModuleType

import pytest

RUNTIME_SUBPROCESS_TIMEOUT_SEC = 30.0


class _FakeTask:
    def __init__(self, task_id: str, family: str | None = None) -> None:
        self.task_id = task_id
        self.family = family


class _FakeMetric:
    def __init__(
        self,
        task_id: str,
        family: str | None,
        mutation_score: float,
    ) -> None:
        self.task_id = task_id
        self.family = family
        self.mutation_score = mutation_score


def load_script_module(script: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, script)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load script module from {script}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _require_runnable_tool(
    *,
    tool_name: str,
    tool_path: str | None,
    version_args: Sequence[str],
) -> str:
    if tool_path is None:
        pytest.fail(f"{tool_name} not available", pytrace=False)

    error_message: str | None = None
    try:
        subprocess.run(  # noqa: S603
            [tool_path, *version_args],  # noqa: S607
            check=True,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        details = ""
        if isinstance(exc, subprocess.CalledProcessError):
            stderr = (exc.stderr or "").strip()
            stdout = (exc.stdout or "").strip()
            output = stderr or stdout
            if output:
                details = f" Output: {output}"
        error_message = (
            f"{tool_name} found at {tool_path} but failed health check "
            f"({type(exc).__name__}: {exc}).{details}"
        )
    if error_message is not None:
        pytest.fail(error_message, pytrace=False)
    return tool_path


@lru_cache(maxsize=1)
def _require_java_runtime_cached(
    javac_path: str | None,
    java_path: str | None,
) -> tuple[str, str]:
    javac = _require_runnable_tool(
        tool_name="javac",
        tool_path=javac_path,
        version_args=("-version",),
    )
    java = _require_runnable_tool(
        tool_name="java",
        tool_path=java_path,
        version_args=("-version",),
    )
    return javac, java


def require_java_runtime() -> tuple[str, str]:
    return _require_java_runtime_cached(
        shutil.which("javac"),
        shutil.which("java"),
    )


@lru_cache(maxsize=4)
def _require_rust_runtime_cached(rustc_path: str | None) -> str:
    return _require_runnable_tool(
        tool_name="rustc",
        tool_path=rustc_path,
        version_args=("--version",),
    )


def require_rust_runtime() -> str:
    return _require_rust_runtime_cached(shutil.which("rustc"))


def _clear_java_runtime_cache() -> None:
    _require_java_runtime_cached.cache_clear()


def _clear_rust_runtime_cache() -> None:
    _require_rust_runtime_cached.cache_clear()


require_java_runtime.cache_clear = _clear_java_runtime_cache  # type: ignore[attr-defined]
require_rust_runtime.cache_clear = _clear_rust_runtime_cache  # type: ignore[attr-defined]


def run_checked_subprocess(
    cmd: Sequence[str],
    *,
    cwd: Path,
    timeout_sec: float = RUNTIME_SUBPROCESS_TIMEOUT_SEC,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603
        list(cmd),
        check=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_sec,
    )
