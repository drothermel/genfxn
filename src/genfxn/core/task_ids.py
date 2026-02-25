from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from genfxn.core.ast_hash import compute_ast_id_map
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
        expected = compute_task_ids(task.family, task.spec, task.code)
    except Exception as exc:
        message = (
            "Failed to recompute canonical IDs from task payload: "
            f"{type(exc).__name__}: {exc}"
        )
        return [
            Issue(
                code=CODE_SPEC_ID_MISMATCH,
                severity=Severity.ERROR,
                message=message,
                location="spec_id",
                task_id=task.task_id,
            )
        ]

    if task.spec_id != expected.spec_id:
        issues.append(
            Issue(
                code=CODE_SPEC_ID_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    f"spec_id '{task.spec_id}' does not match recomputed "
                    f"value '{expected.spec_id}'"
                ),
                location="spec_id",
                task_id=task.task_id,
            )
        )

    if task.sem_hash != expected.sem_hash:
        issues.append(
            Issue(
                code=CODE_SEM_HASH_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    f"sem_hash '{task.sem_hash}' does not match recomputed "
                    f"value '{expected.sem_hash}'"
                ),
                location="sem_hash",
                task_id=task.task_id,
            )
        )

    if task.ast_id != expected.ast_id:
        issues.append(
            Issue(
                code=CODE_AST_ID_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    f"ast_id {task.ast_id!r} does not match recomputed "
                    f"value {expected.ast_id!r}"
                ),
                location="ast_id",
                task_id=task.task_id,
            )
        )

    return issues
