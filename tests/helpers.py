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


def require_java_runtime() -> tuple[str, str]:
    javac = shutil.which("javac")
    java = shutil.which("java")
    if not javac or not java:
        pytest.fail("Java runtime tools (javac/java) not available")
    assert javac is not None
    assert java is not None
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
