import ast
import random
from collections.abc import Callable
from typing import cast

from pydantic import TypeAdapter, ValidationError

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.int32 import (
    i32_abs,
    i32_add,
    i32_clip,
    i32_mod,
    i32_mul,
    i32_neg,
    wrap_i32,
)
from genfxn.core.models import Task
from genfxn.core.safe_exec import (
    SafeExecMissingFunctionError,
    execute_code_restricted,
)
from genfxn.core.validate import WRONG_FAMILY, Issue, Severity
from genfxn.stateful.ast_safety import (
    ALLOWED_AST_NODES,
    ALLOWED_CALL_NAMES,
    ALLOWED_VAR_NAMES,
    CALL_ARITIES,
)
from genfxn.stateful.eval import eval_stateful
from genfxn.stateful.models import StatefulAxes, StatefulSpec

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
CODE_FUNC_NOT_CALLABLE = "FUNC_NOT_CALLABLE"
CODE_UNSAFE_AST = "UNSAFE_AST"
CURRENT_FAMILY = "stateful"
PYTHON_CODE_KEY = "python"

_stateful_spec_adapter = TypeAdapter(StatefulSpec)
_ALLOWED_BUILTINS = {
    "abs": abs,
    "int": int,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "set": set,
    "ValueError": ValueError,
    "__i32_wrap": wrap_i32,
    "__i32_add": i32_add,
    "__i32_mul": i32_mul,
    "__i32_neg": i32_neg,
    "__i32_abs": i32_abs,
    "__i32_clip": i32_clip,
    "__i32_mod": i32_mod,
}


def _validate_ast_whitelist(
    code: str, param_name: str = "xs"
) -> tuple[list[Issue], ast.Module | None]:
    """Reject code containing disallowed AST nodes.

    Returns (issues, tree) where tree is None if parse failed or issues found.
    This prevents accidental bad code and obvious injection vectors,
    but is NOT a security sandbox for adversarial code.
    """
    allowed_names = ALLOWED_CALL_NAMES | ALLOWED_VAR_NAMES | {param_name}

    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError):
        return [], None  # Let _validate_code_compile handle syntax errors

    for stmt in tree.body:
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue
        if not isinstance(stmt, ast.FunctionDef):
            return [
                Issue(
                    code=CODE_UNSAFE_AST,
                    severity=Severity.ERROR,
                    message=(
                        "Top-level statement "
                        f"{type(stmt).__name__} at line "
                        f"{getattr(stmt, 'lineno', '?')} is not allowed; "
                        "only function definitions are permitted"
                    ),
                    location="code",
                )
            ], None

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

        # Strict Call check: only allowed functions with correct arity
        if isinstance(node, ast.Call):
            valid_call = False
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in ALLOWED_CALL_NAMES
            ):
                func_name = node.func.id
                allowed_arities = CALL_ARITIES.get(func_name, set())
                if (
                    len(node.args) in allowed_arities
                    and len(node.keywords) == 0
                ):
                    valid_call = True
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

        # Strict Name check: only param and allowed calls/vars
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
) -> tuple[list[Issue], StatefulSpec | None]:
    try:
        spec = _stateful_spec_adapter.validate_python(task.spec, strict=True)
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


def _validate_code_compile(
    task: Task,
    code: str | None = None,
    parsed_tree: ast.Module | None = None,
    execute_untrusted_code: bool = True,
) -> tuple[list[Issue], Callable[[list[int]], int] | None]:
    if code is None:
        if isinstance(task.code, str):
            code = task.code
        elif isinstance(task.code, dict):
            code = task.code.get(PYTHON_CODE_KEY)

    # Multi-language maps without Python source are valid inputs for this
    # validator; skip code compile/exec validation in that case.
    if code is None:
        return [], None

    if parsed_tree is None:
        try:
            parsed_tree = ast.parse(code)
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
            code,
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

    return [], cast(Callable[[list[int]], int], namespace["f"])


def _validate_query_types(task: Task, strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, q in enumerate(task.queries):
        # Input must be a list
        if not isinstance(q.input, list):
            input_type = type(q.input).__name__
            issues.append(
                Issue(
                    code=CODE_QUERY_INPUT_TYPE,
                    severity=severity,
                    message=f"Query input is {input_type}, expected list",
                    location=f"queries[{i}].input",
                    task_id=task.task_id,
                )
            )
        else:
            # Each element must be an int
            for j, elem in enumerate(q.input):
                if type(elem) is not int:
                    issues.append(
                        Issue(
                            code=CODE_QUERY_INPUT_TYPE,
                            severity=severity,
                            message=(
                                f"Query input[{j}] is {type(elem).__name__}, "
                                f"expected int"
                            ),
                            location=f"queries[{i}].input[{j}]",
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


def _validate_query_outputs(task: Task, spec: StatefulSpec) -> list[Issue]:
    issues: list[Issue] = []

    for i, q in enumerate(task.queries):
        if not isinstance(q.input, list):
            continue
        if not all(type(elem) is int for elem in q.input):
            continue
        expected = eval_stateful(spec, q.input)
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


def _generate_test_inputs(
    axes: StatefulAxes, rng: random.Random, num_samples: int = 50
) -> list[list[int]]:
    """Generate test inputs including edge cases and random samples."""
    inputs: list[list[int]] = []
    val_lo, val_hi = axes.value_range
    len_lo, len_hi = axes.list_length_range

    # Edge cases
    inputs.append([])  # empty list
    inputs.append([val_lo])  # single min value
    inputs.append([val_hi])  # single max value
    inputs.append([val_lo] * len_lo)  # min-length list of min values
    inputs.append([val_hi] * len_hi)  # max-length list of max values

    # Random samples
    for _ in range(num_samples - len(inputs)):
        length = rng.randint(len_lo, len_hi)
        inputs.append([rng.randint(val_lo, val_hi) for _ in range(length)])

    return inputs


def _validate_semantics(
    task: Task,
    func: Callable[[list[int]], int],
    spec: StatefulSpec,
    axes: StatefulAxes,
    max_issues: int,
    rng: random.Random,
) -> list[Issue]:
    issues: list[Issue] = []
    test_inputs = _generate_test_inputs(axes, rng)

    for xs in test_inputs:
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
            actual = func(xs)
        except Exception as e:
            issues.append(
                Issue(
                    code=CODE_CODE_RUNTIME_ERROR,
                    severity=Severity.ERROR,
                    message=f"f({xs}) raised {type(e).__name__}: {e}",
                    location="code",
                    task_id=task.task_id,
                )
            )
            continue

        expected = eval_stateful(spec, xs)
        if actual != expected:
            issues.append(
                Issue(
                    code=CODE_SEMANTIC_MISMATCH,
                    severity=Severity.ERROR,
                    message=f"f({xs}) = {actual}, expected {expected}",
                    location="code",
                    task_id=task.task_id,
                )
            )

    return issues


def validate_stateful_task(
    task: Task,
    axes: StatefulAxes | None = None,
    strict: bool = True,
    max_semantic_issues: int = 10,
    emit_diagnostics: bool = True,  # noqa: ARG001 - kept for API parity
    paranoid: bool = False,
    rng: random.Random | None = None,
    execute_untrusted_code: bool = False,
) -> list[Issue]:
    """Validate a stateful task for correctness.

    Args:
        task: The task to validate.
        axes: Sampling config for semantic testing. Defaults if None.
        strict: If True, type issues are errors; if False, warnings.
        max_semantic_issues: Stop semantic testing after this many issues.
            Use 0 for unlimited.
        emit_diagnostics: Kept for API parity with piecewise validator.
            Stateful has no diagnostic checks currently.
        paranoid: Deprecated; AST whitelist validation is always enforced.
        rng: Random generator for semantic testing. Random(42) if None.

    Returns:
        List of validation issues found.
    """
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
    if axes is None:
        axes = StatefulAxes()
    if rng is None:
        rng = random.Random(42)
    _ = paranoid

    issues: list[Issue] = []

    issues.extend(_validate_task_id(task))

    spec_issues, spec = _validate_spec_deserialize(task)
    issues.extend(spec_issues)

    tree: ast.Module | None = None
    code_to_validate: str | None = None
    if isinstance(task.code, str):
        code_to_validate = task.code
    elif isinstance(task.code, dict):
        code_to_validate = task.code.get(PYTHON_CODE_KEY)

    if code_to_validate is not None:
        ast_issues, tree = _validate_ast_whitelist(code_to_validate)
        if ast_issues:
            issues.extend(ast_issues)
            return issues  # Bail early, don't exec unsafe code

    code_issues, func = _validate_code_compile(
        task,
        code=code_to_validate,
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
                        task, func, spec, axes, max_semantic_issues, rng
                    )
                )
        finally:
            close = getattr(func, "close", None)
            if callable(close):
                close()

    return issues
