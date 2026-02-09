import importlib.util
import shutil
from pathlib import Path
from types import ModuleType

import pytest


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
        pytest.skip("Java runtime tools (javac/java) not available")
    assert javac is not None
    assert java is not None
    return javac, java


def require_rust_runtime() -> str:
    rustc = shutil.which("rustc")
    if not rustc:
        pytest.skip("Rust compiler (rustc) not available")
    assert rustc is not None
    return rustc
