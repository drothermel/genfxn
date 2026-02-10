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
pytest_itemcollected = module.pytest_itemcollected
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


def _make_family_full_probe_tests(pytester) -> None:
    probe_dir = Path(str(pytester.mkpydir("probe_family_markers")))
    (probe_dir / "test_piecewise_runtime_parity.py").write_text(
        """
import pytest


@pytest.mark.full
def test_piecewise_runtime_full():
    assert True
""",
        encoding="utf-8",
    )
    (probe_dir / "test_validate_piecewise.py").write_text(
        """
import pytest


@pytest.mark.full
def test_piecewise_validate_full():
    assert True
""",
        encoding="utf-8",
    )
    (probe_dir / "test_stateful_runtime_parity.py").write_text(
        """
import pytest


@pytest.mark.full
def test_stateful_runtime_full():
    assert True
""",
        encoding="utf-8",
    )
    (probe_dir / "test_misc_full.py").write_text(
        """
import pytest


@pytest.mark.full
def test_misc_full():
    assert True
""",
        encoding="utf-8",
    )


def test_standard_skips_full_marked_tests(pytester) -> None:
    _install_repo_verification_hooks(pytester)
    _make_probe_tests(pytester)

    result = pytester.runpytest("--verification-level=standard", "-q")

    result.assert_outcomes(passed=2, skipped=1)


def test_default_verification_level_is_standard(pytester) -> None:
    _install_repo_verification_hooks(pytester)
    _make_probe_tests(pytester)

    result = pytester.runpytest("-q")

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


def test_standard_runs_slow_marked_tests(pytester) -> None:
    _install_repo_verification_hooks(pytester)
    _make_probe_tests(pytester)

    result = pytester.runpytest("--verification-level=standard", "-q")

    result.assert_outcomes(passed=2, skipped=1)


def test_full_family_marker_selects_only_matching_family_full_tests(
    pytester,
) -> None:
    _install_repo_verification_hooks(pytester)
    _make_family_full_probe_tests(pytester)

    result = pytester.runpytest(
        "--verification-level=full",
        "-m",
        "full_piecewise",
        "-q",
    )

    result.assert_outcomes(passed=2, deselected=2)


def test_full_family_marker_respects_standard_full_skip(pytester) -> None:
    _install_repo_verification_hooks(pytester)
    _make_family_full_probe_tests(pytester)

    result = pytester.runpytest(
        "--verification-level=standard",
        "-m",
        "full_piecewise",
        "-q",
    )

    result.assert_outcomes(skipped=2, deselected=2)
