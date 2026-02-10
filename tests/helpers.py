import importlib.util
import shutil
import subprocess
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType

import pytest

RUNTIME_SUBPROCESS_TIMEOUT_SEC = 30.0


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


def require_java_runtime() -> tuple[str, str]:
    javac = _require_runnable_tool(
        tool_name="javac",
        tool_path=shutil.which("javac"),
        version_args=("-version",),
    )
    java = _require_runnable_tool(
        tool_name="java",
        tool_path=shutil.which("java"),
        version_args=("-version",),
    )
    return javac, java


def require_rust_runtime() -> str:
    rustc = shutil.which("rustc")
    if not rustc:
        pytest.fail("Rust compiler (rustc) not available")
    assert rustc is not None
    return rustc


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
