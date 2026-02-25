import pytest

import genfxn.suites.generate as suites_generate
from genfxn.core.models import Query, QueryTag, Task
from genfxn.piecewise.models import ExprType, PiecewiseAxes
from genfxn.suites.generate import generate_pool, generate_suite
from genfxn.suites.quotas import QUOTAS


def test_generate_pool_passes_custom_axes_to_task_generator() -> None:
    axes = PiecewiseAxes(
        n_branches=1,
        expr_types=[ExprType.AFFINE],
    )
    candidates, stats = generate_pool(
        family="piecewise",
        seed=7,
        pool_size=80,
        axes=axes,
    )

    assert stats.errors == 0
    assert candidates
    assert all(
        candidate.task.axes is not None
        and candidate.task.axes["n_branches"] == 1
        for candidate in candidates
    )


@pytest.mark.parametrize("max_retries", [0, 1])
def test_generate_suite_passes_custom_axes_to_task_generator(
    max_retries: int,
) -> None:
    axes = PiecewiseAxes(
        n_branches=1,
        expr_types=[ExprType.AFFINE],
    )
    tasks = generate_suite(
        family="piecewise",
        seed=13,
        pool_size=240,
        max_retries=max_retries,
        axes=axes,
    )

    assert len(tasks) == QUOTAS["piecewise"].total
    assert all(
        task.axes is not None and task.axes["n_branches"] == 1 for task in tasks
    )


def test_generate_pool_missing_task_generator_mapping_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(
        suites_generate._TASK_GENERATORS, "piecewise", raising=False
    )
    with pytest.raises(ValueError, match="piecewise.*_TASK_GENERATORS mapping"):
        suites_generate.generate_pool(family="piecewise", pool_size=1)


def test_generate_pool_missing_feature_extractor_mapping_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delitem(
        suites_generate._FEATURE_EXTRACTORS, "piecewise", raising=False
    )
    with pytest.raises(
        ValueError, match="piecewise.*_FEATURE_EXTRACTORS mapping"
    ):
        suites_generate.generate_pool(family="piecewise", pool_size=1)


def test_generate_pool_dedupes_by_sem_hash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _make_task(task_id: str) -> Task:
        return Task(
            task_id=task_id,
            spec_id=task_id,
            sem_hash="same_semantics",
            ast_id={"python": "ast"},
            family="piecewise",
            spec={},
            code="def f(x):\n    return x",
            queries=[Query(input=0, output=0, tag=QueryTag.TYPICAL)],
            description="stub",
        )

    call_count = {"n": 0}

    def _fake_generator(rng, axes):  # noqa: ANN001
        del rng, axes
        call_count["n"] += 1
        return _make_task(f"t-{call_count['n']}")

    monkeypatch.setitem(
        suites_generate._TASK_GENERATORS, "piecewise", _fake_generator
    )
    monkeypatch.setitem(
        suites_generate._FEATURE_EXTRACTORS, "piecewise", lambda _spec: {}
    )

    candidates, stats = suites_generate.generate_pool(
        family="piecewise", seed=1, pool_size=4
    )

    assert len(candidates) == 1
    assert stats.duplicate_sem_hashes == 3
    assert stats.duplicates == 3
    assert stats.semantic_uniqueness_ratio == 0.25
    assert stats.semantic_collapse is True
