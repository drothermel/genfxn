from __future__ import annotations

from pathlib import Path

pytest_plugins = ("pytester",)


def _install_repo_verification_hooks(pytester) -> None:
    repo_conftest = Path(__file__).with_name("conftest.py").resolve()
    pytester.makeconftest(
        f"""
from __future__ import annotations

import importlib.util
from pathlib import Path

repo_conftest = Path({str(repo_conftest)!r})
spec = importlib.util.spec_from_file_location(
    "_repo_verification_conftest",
    repo_conftest,
)
assert spec is not None
assert spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

pytest_addoption = module.pytest_addoption
pytest_collection_modifyitems = module.pytest_collection_modifyitems
"""
    )


def _make_probe_tests(pytester) -> None:
    pytester.makepyfile(
        test_probe="""
import pytest


@pytest.mark.full
def test_full_marked():
    assert True


@pytest.mark.slow
def test_slow_marked():
    assert True


def test_unmarked():
    assert True
"""
    )


def test_standard_skips_full_marked_tests(pytester) -> None:
    _install_repo_verification_hooks(pytester)
    _make_probe_tests(pytester)

    result = pytester.runpytest("--verification-level=standard", "-q")

    result.assert_outcomes(passed=2, skipped=1)


def test_full_runs_full_marked_tests(pytester) -> None:
    _install_repo_verification_hooks(pytester)
    _make_probe_tests(pytester)

    result = pytester.runpytest("--verification-level=full", "-q")

    result.assert_outcomes(passed=3)


def test_fast_skips_slow_and_full_marked_tests(pytester) -> None:
    _install_repo_verification_hooks(pytester)
    _make_probe_tests(pytester)

    result = pytester.runpytest("--verification-level=fast", "-q")

    result.assert_outcomes(passed=1, skipped=2)
