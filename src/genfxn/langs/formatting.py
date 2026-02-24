"""Optional language-specific code formatting for generated render output."""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

from genfxn.langs.types import Language

_FORMAT_TIMEOUT_SEC = 15.0
GOOGLE_JAVA_FORMATTER = shutil.which("google-java-format")
RUST_FORMATTER = shutil.which("rustfmt")


def indent_java_method(code: str) -> str:
    lines = code.splitlines()
    if not lines:
        return ""
    return "\n".join(f"  {line}" if line else "" for line in lines)


# Backward-compatible alias for older imports.
_indent_java_method = indent_java_method


def _extract_java_method(formatted_wrapper: str) -> str:
    match = re.fullmatch(
        r"\s*public\s+final\s+class\s+Main\s*\{(?P<body>.*)\}\s*",
        formatted_wrapper,
        flags=re.DOTALL,
    )
    if match is None:
        raise ValueError("Unexpected google-java-format wrapper output")

    body = match.group("body").strip("\n")
    lines = body.splitlines()
    unindented = [line[2:] if line.startswith("  ") else line for line in lines]
    return "\n".join(unindented).rstrip()


@lru_cache(maxsize=2048)
def format_java_rendered_method(code: str) -> str:
    """Format a rendered Java method when google-java-format is available."""
    formatter = GOOGLE_JAVA_FORMATTER
    if formatter is None:
        return code

    wrapped = f"public final class Main {{\n{indent_java_method(code)}\n}}\n"
    with tempfile.TemporaryDirectory() as tmp_dir:
        src = Path(tmp_dir) / "Main.java"
        src.write_text(wrapped, encoding="utf-8")
        try:
            subprocess.run(  # noqa: S603
                [formatter, "--replace", str(src)],  # noqa: S607
                check=True,
                capture_output=True,
                text=True,
                timeout=_FORMAT_TIMEOUT_SEC,
            )
            return _extract_java_method(src.read_text(encoding="utf-8"))
        except (OSError, subprocess.SubprocessError, ValueError):
            return code


@lru_cache(maxsize=2048)
def format_rust_rendered_code(code: str) -> str:
    """Format rendered Rust code when rustfmt is available."""
    formatter = RUST_FORMATTER
    if formatter is None:
        return code

    with tempfile.TemporaryDirectory() as tmp_dir:
        src = Path(tmp_dir) / "snippet.rs"
        src.write_text(code.rstrip() + "\n", encoding="utf-8")
        try:
            subprocess.run(  # noqa: S603
                [formatter, "--edition", "2021", str(src)],  # noqa: S607
                check=True,
                capture_output=True,
                text=True,
                timeout=_FORMAT_TIMEOUT_SEC,
            )
            return src.read_text(encoding="utf-8").rstrip()
        except (OSError, subprocess.SubprocessError):
            return code


def format_rendered_code(language: Language, code: str) -> str:
    """Format generated code for supported languages when tools exist."""
    if language == Language.JAVA:
        return format_java_rendered_method(code)
    if language == Language.RUST:
        return format_rust_rendered_code(code)
    return code
