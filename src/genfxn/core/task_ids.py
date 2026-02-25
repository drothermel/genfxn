from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from genfxn.core.ast_hash import compute_ast_hash, compute_ast_id_map
from genfxn.core.canonicalization import compute_spec_id
from genfxn.core.models import Task
from genfxn.core.semantic_hash import compute_sem_hash
from genfxn.core.validate import Issue, Severity

CODE_MISSING_SPEC_ID = "MISSING_SPEC_ID"
CODE_SPEC_ID_MISMATCH = "SPEC_ID_MISMATCH"
CODE_MISSING_SEM_HASH = "MISSING_SEM_HASH"
CODE_SEM_HASH_MISMATCH = "SEM_HASH_MISMATCH"
CODE_MISSING_AST_ID = "MISSING_AST_ID"
CODE_AST_ID_MISMATCH = "AST_ID_MISMATCH"


@dataclass(frozen=True)
class ComputedTaskIds:
    spec_id: str
    sem_hash: str
    ast_id: dict[str, str]


def compute_task_ids(
    family: str,
    spec: dict[str, Any],
    code: str | dict[str, str],
) -> ComputedTaskIds:
    return ComputedTaskIds(
        spec_id=compute_spec_id(family, spec),
        sem_hash=compute_sem_hash(family, spec),
        ast_id=compute_ast_id_map(code),
    )


def _recompute_ast_id(task: Task) -> dict[str, str]:
    if isinstance(task.code, dict):
        return compute_ast_id_map(task.code)

    if not isinstance(task.code, str):
        raise ValueError("Task code must be a string or language->source map")

    languages = list(task.ast_id)
    if len(languages) != 1:
        raise ValueError(
            "Task with string code must have exactly one ast_id language key"
        )

    language = languages[0]
    return {language: compute_ast_hash(language, task.code)}


def validate_task_ids(task: Task) -> list[Issue]:
    issues: list[Issue] = []

    if not isinstance(task.spec_id, str) or task.spec_id == "":
        issues.append(
            Issue(
                code=CODE_MISSING_SPEC_ID,
                severity=Severity.ERROR,
                message="Task is missing required non-empty spec_id",
                location="spec_id",
                task_id=task.task_id,
            )
        )

    if not isinstance(task.sem_hash, str) or task.sem_hash == "":
        issues.append(
            Issue(
                code=CODE_MISSING_SEM_HASH,
                severity=Severity.ERROR,
                message="Task is missing required non-empty sem_hash",
                location="sem_hash",
                task_id=task.task_id,
            )
        )

    if not isinstance(task.ast_id, dict) or len(task.ast_id) == 0:
        issues.append(
            Issue(
                code=CODE_MISSING_AST_ID,
                severity=Severity.ERROR,
                message="Task is missing required non-empty ast_id map",
                location="ast_id",
                task_id=task.task_id,
            )
        )
    elif not all(
        isinstance(language, str) and isinstance(value, str) and value != ""
        for language, value in task.ast_id.items()
    ):
        issues.append(
            Issue(
                code=CODE_MISSING_AST_ID,
                severity=Severity.ERROR,
                message="Task ast_id must be a map of language->non-empty hash",
                location="ast_id",
                task_id=task.task_id,
            )
        )

    if issues:
        return issues

    try:
        expected_spec_id = compute_spec_id(task.family, task.spec)
    except Exception as exc:
        issues.append(
            Issue(
                code=CODE_SPEC_ID_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    "Failed to recompute spec_id from task payload: "
                    f"{type(exc).__name__}: {exc}"
                ),
                location="spec_id",
                task_id=task.task_id,
            )
        )
        expected_spec_id = None

    if expected_spec_id is not None and task.spec_id != expected_spec_id:
        issues.append(
            Issue(
                code=CODE_SPEC_ID_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    f"spec_id '{task.spec_id}' does not match recomputed "
                    f"value '{expected_spec_id}'"
                ),
                location="spec_id",
                task_id=task.task_id,
            )
        )

    try:
        expected_sem_hash = compute_sem_hash(task.family, task.spec)
    except Exception as exc:
        issues.append(
            Issue(
                code=CODE_SEM_HASH_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    "Failed to recompute sem_hash from task payload: "
                    f"{type(exc).__name__}: {exc}"
                ),
                location="sem_hash",
                task_id=task.task_id,
            )
        )
        expected_sem_hash = None

    if expected_sem_hash is not None and task.sem_hash != expected_sem_hash:
        issues.append(
            Issue(
                code=CODE_SEM_HASH_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    f"sem_hash '{task.sem_hash}' does not match recomputed "
                    f"value '{expected_sem_hash}'"
                ),
                location="sem_hash",
                task_id=task.task_id,
            )
        )

    try:
        expected_ast_id = _recompute_ast_id(task)
    except Exception as exc:
        issues.append(
            Issue(
                code=CODE_AST_ID_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    "Failed to recompute ast_id from task payload: "
                    f"{type(exc).__name__}: {exc}"
                ),
                location="ast_id",
                task_id=task.task_id,
            )
        )
        expected_ast_id = None

    if expected_ast_id is not None and task.ast_id != expected_ast_id:
        issues.append(
            Issue(
                code=CODE_AST_ID_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    f"ast_id {task.ast_id!r} does not match recomputed "
                    f"value {expected_ast_id!r}"
                ),
                location="ast_id",
                task_id=task.task_id,
            )
        )

    return issues
