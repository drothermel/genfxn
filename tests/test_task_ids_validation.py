import random
from collections.abc import Callable

import pytest

from genfxn.cli import render_task_for_language
from genfxn.core.models import Task
from genfxn.core.task_ids import (
    CODE_AST_ID_MISMATCH,
    CODE_MISSING_AST_ID,
    CODE_MISSING_SEM_HASH,
    CODE_MISSING_SPEC_ID,
    CODE_SEM_HASH_MISMATCH,
    CODE_SPEC_ID_MISMATCH,
    validate_task_ids,
)
from genfxn.langs.types import Language
from genfxn.piecewise.task import generate_piecewise_task


def test_generated_tasks_validate_identity_fields(
    task_factories: tuple[Callable[[], Task], ...],
) -> None:
    for factory in task_factories:
        task = factory()
        issues = validate_task_ids(task)
        assert issues == []


def test_missing_fields_are_reported(
    task_factories: tuple[Callable[[], Task], ...],
) -> None:
    for factory in task_factories:
        task = factory()
        missing = task.model_copy(  # type: ignore[attr-defined]
            update={"spec_id": None, "sem_hash": None, "ast_id": None}
        )
        issues = validate_task_ids(missing)
        codes = {issue.code for issue in issues}
        assert CODE_MISSING_SPEC_ID in codes
        assert CODE_MISSING_SEM_HASH in codes
        assert CODE_MISSING_AST_ID in codes


def test_mismatched_fields_are_reported(
    task_factories: tuple[Callable[[], Task], ...],
) -> None:
    for factory in task_factories:
        task = factory()
        corrupted = task.model_copy(  # type: ignore[attr-defined]
            update={
                "spec_id": "bad",
                "sem_hash": "bad",
                "ast_id": {"python": "bad"},
            }
        )
        issues = validate_task_ids(corrupted)
        codes = {issue.code for issue in issues}
        assert CODE_SPEC_ID_MISMATCH in codes
        assert CODE_SEM_HASH_MISMATCH in codes
        assert CODE_AST_ID_MISMATCH in codes


@pytest.mark.parametrize("language", [Language.JAVA, Language.RUST])
def test_single_language_rendered_tasks_recompute_ast_by_language_key(
    language: Language,
) -> None:
    task = generate_piecewise_task(rng=random.Random(7))
    rendered = render_task_for_language(task, language)
    assert validate_task_ids(rendered) == []
