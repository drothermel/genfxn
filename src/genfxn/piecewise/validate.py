import ast
from collections.abc import Callable
from typing import cast

from pydantic import ValidationError

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.models import Task
from genfxn.core.predicates import get_threshold
from genfxn.core.safe_exec import (
    SafeExecMissingFunctionError,
    execute_code_restricted,
)
from genfxn.core.validate import WRONG_FAMILY, Issue, Severity
from genfxn.piecewise.ast_safety import ALLOWED_AST_NODES, ALLOWED_CALL_NAMES
from genfxn.piecewise.eval import eval_piecewise
from genfxn.piecewise.models import PiecewiseAxes, PiecewiseSpec
from genfxn.piecewise.queries import SUPPORTED_CONDITION_KINDS

CODE_TASK_ID_MISMATCH = "TASK_ID_MISMATCH"
CODE_SPEC_DESERIALIZE_ERROR = "SPEC_DESERIALIZE_ERROR"
CODE_CODE_PARSE_ERROR = "CODE_PARSE_ERROR"
CODE_CODE_EXEC_ERROR = "CODE_EXEC_ERROR"
CODE_CODE_MISSING_FUNC = "CODE_MISSING_FUNC"
CODE_CODE_RUNTIME_ERROR = "CODE_RUNTIME_ERROR"
CODE_QUERY_INPUT_TYPE = "QUERY_INPUT_TYPE"
CODE_QUERY_OUTPUT_TYPE = "QUERY_OUTPUT_TYPE"
CODE_QUERY_OUTPUT_MISMATCH = "QUERY_OUTPUT_MISMATCH"
CODE_SEMANTIC_MISMATCH = "SEMANTIC_MISMATCH"
CODE_SEMANTIC_ISSUES_CAPPED = "SEMANTIC_ISSUES_CAPPED"
CODE_SEMANTIC_RANGE_SAMPLED = "SEMANTIC_RANGE_SAMPLED"
CODE_FUNC_NOT_CALLABLE = "FUNC_NOT_CALLABLE"
CODE_NON_MONOTONIC_THRESHOLDS = "NON_MONOTONIC_THRESHOLDS"
CODE_UNSUPPORTED_CONDITION = "UNSUPPORTED_CONDITION"
CODE_UNSAFE_AST = "UNSAFE_AST"
CURRENT_FAMILY = "piecewise"
_ALLOWED_BUILTINS = {"abs": abs, "int": int}
SEMANTIC_SAMPLE_MAX_POINTS = 1000


def _validate_ast_whitelist(
    code: str, param_name: str = "x"
) -> tuple[list[Issue], ast.Module | None]:
    """Reject code containing disallowed AST nodes.

    Returns (issues, tree) where tree is None if parse failed or issues found.
    This prevents accidental bad code and obvious injection vectors,
    but is NOT a security sandbox for adversarial code.
    """
    allowed_names = ALLOWED_CALL_NAMES | {param_name}

    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError):
        return [], None  # Let _validate_code_compile handle syntax errors

    issues: list[Issue] = []
    for node in ast.walk(tree):
        node_type = type(node)

        # Check node type against whitelist
        if node_type not in ALLOWED_AST_NODES:
            issues.append(
                Issue(
                    code=CODE_UNSAFE_AST,
                    severity=Severity.ERROR,
                    message=(
                        f"Disallowed AST node: {node_type.__name__} at line "
                        f"{getattr(node, 'lineno', '?')}"
                    ),
                    location="code",
                )
            )
            continue

        # Strict Call check: only abs(single_arg)
        if isinstance(node, ast.Call):
            valid_call = (
                isinstance(node.func, ast.Name)
                and node.func.id in ALLOWED_CALL_NAMES
                and len(node.args) == 1
                and len(node.keywords) == 0
            )
            if not valid_call:
                issues.append(
                    Issue(
                        code=CODE_UNSAFE_AST,
                        severity=Severity.ERROR,
                        message=(
                            f"Disallowed function call at line "
                            f"{getattr(node, 'lineno', '?')}"
                        ),
                        location="code",
                    )
                )

        # Strict Name check: only param and allowed calls
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in allowed_names:
                issues.append(
                    Issue(
                        code=CODE_UNSAFE_AST,
                        severity=Severity.ERROR,
                        message=(
                            f"Disallowed name '{node.id}' at line {node.lineno}"
                        ),
                        location="code",
                    )
                )

    return issues, tree if not issues else None


def _validate_task_id(task: Task) -> list[Issue]:
    expected = task_id_from_spec(family=task.family, spec=task.spec)
    if task.task_id != expected:
        return [
            Issue(
                code=CODE_TASK_ID_MISMATCH,
                severity=Severity.ERROR,
                message=(
                    f"task_id '{task.task_id}' does not match spec hash "
                    f"'{expected}'"
                ),
                location="task_id",
                task_id=task.task_id,
            )
        ]
    return []


def _validate_spec_deserialize(
    task: Task,
) -> tuple[list[Issue], PiecewiseSpec | None]:
    try:
        spec = PiecewiseSpec.model_validate(task.spec, strict=True)
        return [], spec
    except ValidationError as e:
        return [
            Issue(
                code=CODE_SPEC_DESERIALIZE_ERROR,
                severity=Severity.ERROR,
                message=f"Failed to deserialize spec: {e}",
                location="spec",
                task_id=task.task_id,
            )
        ], None


def _validate_condition_support(task: Task, spec: PiecewiseSpec) -> list[Issue]:
    issues: list[Issue] = []
    for i, branch in enumerate(spec.branches):
        kind = branch.condition.kind
        if kind not in SUPPORTED_CONDITION_KINDS:
            supported = ", ".join(sorted(SUPPORTED_CONDITION_KINDS))
            issues.append(
                Issue(
                    code=CODE_UNSUPPORTED_CONDITION,
                    severity=Severity.ERROR,
                    message=(
                        f"Condition kind '{kind}' not supported by query "
                        f"generator (supported: {supported})"
                    ),
                    location=f"spec.branches[{i}].condition",
                    task_id=task.task_id,
                )
            )
    return issues


def _validate_code_compile(
    task: Task,
    parsed_tree: ast.Module | None = None,
    execute_untrusted_code: bool = True,
) -> tuple[list[Issue], Callable[[int], int] | None]:
    if not isinstance(task.code, str):
        return [
            Issue(
                code=CODE_CODE_PARSE_ERROR,
                severity=Severity.ERROR,
                message=(
                    "Task code must be a Python string for this validator, "
                    f"got {type(task.code).__name__}"
                ),
                location="code",
                task_id=task.task_id,
            )
        ], None

    if parsed_tree is None:
        try:
            parsed_tree = ast.parse(task.code)
        except SyntaxError as e:
            return [
                Issue(
                    code=CODE_CODE_PARSE_ERROR,
                    severity=Severity.ERROR,
                    message=f"Syntax error in code: {e}",
                    location="code",
                    task_id=task.task_id,
                )
            ], None
    _ = parsed_tree

    if not execute_untrusted_code:
        return [], None

    namespace: dict[str, object]
    try:
        namespace = execute_code_restricted(
            task.code,
            _ALLOWED_BUILTINS,
            trust_untrusted_code=True,
        )
    except SafeExecMissingFunctionError as e:
        return [
            Issue(
                code=CODE_CODE_MISSING_FUNC,
                severity=Severity.ERROR,
                message=f"Failed to execute code: {e}",
                location="code",
                task_id=task.task_id,
            )
        ], None
    except Exception as e:
        return [
            Issue(
                code=CODE_CODE_EXEC_ERROR,
                severity=Severity.ERROR,
                message=f"Failed to execute code: {e}",
                location="code",
                task_id=task.task_id,
            )
        ], None

    if "f" not in namespace:
        return [
            Issue(
                code=CODE_CODE_MISSING_FUNC,
                severity=Severity.ERROR,
                message="Function 'f' not found in code namespace",
                location="code",
                task_id=task.task_id,
            )
        ], None

    if not callable(namespace["f"]):
        return [
            Issue(
                code=CODE_FUNC_NOT_CALLABLE,
                severity=Severity.ERROR,
                message=f"Function 'f' is not callable: {type(namespace['f'])}",
                location="code.f",
                task_id=task.task_id,
            )
        ], None

    return [], cast(Callable[[int], int], namespace["f"])


def _validate_query_types(task: Task, strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, q in enumerate(task.queries):
        if type(q.input) is not int:
            issues.append(
                Issue(
                    code=CODE_QUERY_INPUT_TYPE,
                    severity=severity,
                    message=(
                        f"Query input is {type(q.input).__name__}, expected int"
                    ),
                    location=f"queries[{i}].input",
                    task_id=task.task_id,
                )
            )
        if type(q.output) is not int:
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_TYPE,
                    severity=severity,
                    message=(
                        f"Query output is {type(q.output).__name__}, "
                        f"expected int"
                    ),
                    location=f"queries[{i}].output",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_query_outputs(task: Task, spec: PiecewiseSpec) -> list[Issue]:
    issues: list[Issue] = []

    for i, q in enumerate(task.queries):
        if type(q.input) is not int:
            continue
        expected = eval_piecewise(spec, q.input)
        if q.output != expected:
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_MISMATCH,
                    severity=Severity.ERROR,
                    message=(
                        f"Query output {q.output} != expected {expected} "
                        f"for input {q.input}"
                    ),
                    location=f"queries[{i}]",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_semantics(
    task: Task,
    func: Callable[[int], int],
    spec: PiecewiseSpec,
    value_range: tuple[int, int],
    max_issues: int,
) -> list[Issue]:
    issues: list[Issue] = []
    lo, hi = value_range
    total_points = hi - lo + 1
    if total_points <= SEMANTIC_SAMPLE_MAX_POINTS:
        sampled_points = list(range(lo, hi + 1))
    else:
        span = hi - lo
        sampled_points = [
            lo + (span * i) // (SEMANTIC_SAMPLE_MAX_POINTS - 1)
            for i in range(SEMANTIC_SAMPLE_MAX_POINTS)
        ]
        issues.append(
            Issue(
                code=CODE_SEMANTIC_RANGE_SAMPLED,
                severity=Severity.WARNING,
                message=(
                    "Semantic validation sampled "
                    f"{SEMANTIC_SAMPLE_MAX_POINTS} of {total_points} points "
                    f"across range [{lo}, {hi}]"
                ),
                location="code",
                task_id=task.task_id,
            )
        )

    for x in sampled_points:
        if max_issues > 0 and len(issues) >= max_issues:
            issues.append(
                Issue(
                    code=CODE_SEMANTIC_ISSUES_CAPPED,
                    severity=Severity.WARNING,
                    message=f"Stopped after {max_issues} semantic issues",
                    location="code",
                    task_id=task.task_id,
                )
            )
            break

        try:
            actual = func(x)
        except Exception as e:
            issues.append(
                Issue(
                    code=CODE_CODE_RUNTIME_ERROR,
                    severity=Severity.ERROR,
                    message=f"f({x}) raised {type(e).__name__}: {e}",
                    location="code",
                    task_id=task.task_id,
                )
            )
            continue

        expected = eval_piecewise(spec, x)
        if actual != expected:
            issues.append(
                Issue(
                    code=CODE_SEMANTIC_MISMATCH,
                    severity=Severity.ERROR,
                    message=f"f({x}) = {actual}, expected {expected}",
                    location="code",
                    task_id=task.task_id,
                )
            )

    return issues


def _check_monotonic_thresholds(task: Task, spec: PiecewiseSpec) -> list[Issue]:
    thresholds: list[int] = []
    for branch in spec.branches:
        info = get_threshold(branch.condition)
        if info is not None:
            thresholds.append(info.value)

    if len(thresholds) < 2:
        return []

    is_monotonic = all(
        thresholds[i] < thresholds[i + 1] for i in range(len(thresholds) - 1)
    )
    if not is_monotonic:
        return [
            Issue(
                code=CODE_NON_MONOTONIC_THRESHOLDS,
                severity=Severity.WARNING,
                message=(
                    f"Branch thresholds are not strictly increasing: "
                    f"{thresholds}"
                ),
                location="spec.branches",
                task_id=task.task_id,
            )
        ]

    return []


def validate_piecewise_task(
    task: Task,
    value_range: tuple[int, int] | None = None,
    strict: bool = True,
    max_semantic_issues: int = 10,
    emit_diagnostics: bool = True,
    paranoid: bool = False,
    execute_untrusted_code: bool = False,
) -> list[Issue]:
    if task.family != CURRENT_FAMILY:
        return [
            Issue(
                code=WRONG_FAMILY,
                severity=Severity.ERROR,
                message=(
                    f"Task family '{task.family}' is not '{CURRENT_FAMILY}'"
                ),
                location="family",
                task_id=task.task_id,
            )
        ]
    if value_range is None:
        value_range = PiecewiseAxes().value_range
    _ = paranoid

    issues: list[Issue] = []

    issues.extend(_validate_task_id(task))

    spec_issues, spec = _validate_spec_deserialize(task)
    issues.extend(spec_issues)

    if spec is not None:
        issues.extend(_validate_condition_support(task, spec))

    tree: ast.Module | None = None
    if isinstance(task.code, str):
        ast_issues, tree = _validate_ast_whitelist(task.code)
        if ast_issues:
            issues.extend(ast_issues)
            return issues  # Bail early, don't exec unsafe code

    code_issues, func = _validate_code_compile(
        task,
        parsed_tree=tree,
        execute_untrusted_code=execute_untrusted_code,
    )
    issues.extend(code_issues)

    issues.extend(_validate_query_types(task, strict))

    if spec is not None:
        issues.extend(_validate_query_outputs(task, spec))

    if func is not None:
        try:
            if spec is not None:
                issues.extend(
                    _validate_semantics(
                        task, func, spec, value_range, max_semantic_issues
                    )
                )
        finally:
            close = getattr(func, "close", None)
            if callable(close):
                close()

    if spec is not None and emit_diagnostics:
        issues.extend(_check_monotonic_thresholds(task, spec))

    return issues
