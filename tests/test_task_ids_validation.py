import random
from collections.abc import Callable

import pytest

from genfxn.bitops.task import generate_bitops_task
from genfxn.cli import _render_task_for_language
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
from genfxn.fsm.task import generate_fsm_task
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.intervals.task import generate_intervals_task
from genfxn.langs.types import Language
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.sequence_dp.task import generate_sequence_dp_task
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stack_bytecode.task import generate_stack_bytecode_task
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.temporal_logic.task import generate_temporal_logic_task

_TASK_FACTORIES: list[Callable[[], Task]] = [
    lambda: generate_piecewise_task(rng=random.Random(1)),
    lambda: generate_stateful_task(rng=random.Random(1)),
    lambda: generate_simple_algorithms_task(rng=random.Random(1)),
    lambda: generate_stringrules_task(rng=random.Random(1)),
    lambda: generate_stack_bytecode_task(rng=random.Random(1)),
    lambda: generate_fsm_task(rng=random.Random(1)),
    lambda: generate_bitops_task(rng=random.Random(1)),
    lambda: generate_sequence_dp_task(rng=random.Random(1)),
    lambda: generate_intervals_task(rng=random.Random(1)),
    lambda: generate_graph_queries_task(rng=random.Random(1)),
    lambda: generate_temporal_logic_task(rng=random.Random(1)),
]


@pytest.mark.parametrize("factory", _TASK_FACTORIES)
def test_generated_tasks_validate_identity_fields(
    factory: Callable[[], Task],
) -> None:
    task = factory()
    issues = validate_task_ids(task)
    assert issues == []


@pytest.mark.parametrize("factory", _TASK_FACTORIES)
def test_missing_fields_are_reported(factory: Callable[[], Task]) -> None:
    task = factory()
    missing = task.model_copy(  # type: ignore[attr-defined]
        update={"spec_id": None, "sem_hash": None, "ast_id": None}
    )
    issues = validate_task_ids(missing)
    codes = {issue.code for issue in issues}
    assert CODE_MISSING_SPEC_ID in codes
    assert CODE_MISSING_SEM_HASH in codes
    assert CODE_MISSING_AST_ID in codes


@pytest.mark.parametrize("factory", _TASK_FACTORIES)
def test_mismatched_fields_are_reported(factory: Callable[[], Task]) -> None:
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
    rendered = _render_task_for_language(task, language)
    assert validate_task_ids(rendered) == []
