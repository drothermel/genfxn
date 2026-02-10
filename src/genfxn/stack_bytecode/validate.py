import ast
import random
from collections.abc import Callable
from typing import cast

from pydantic import TypeAdapter, ValidationError

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.models import Task
from genfxn.core.safe_exec import (
    SafeExecMissingFunctionError,
    execute_code_restricted,
)
from genfxn.core.validate import WRONG_FAMILY, Issue, Severity
from genfxn.stack_bytecode.ast_safety import (
    ALLOWED_ANNOTATION_NAMES,
    ALLOWED_AST_NODES,
    ALLOWED_CALL_NAMES,
    ALLOWED_METHOD_NAMES,
    ALLOWED_VAR_NAMES,
    CALL_ARITIES,
    METHOD_ARITIES,
)
from genfxn.stack_bytecode.eval import eval_stack_bytecode
from genfxn.stack_bytecode.models import StackBytecodeAxes, StackBytecodeSpec

CODE_TASK_ID_MISMATCH = "TASK_ID_MISMATCH"
CODE_SPEC_DESERIALIZE_ERROR = "SPEC_DESERIALIZE_ERROR"
CODE_CODE_PARSE_ERROR = "CODE_CODE_PARSE_ERROR"
CODE_CODE_EXEC_ERROR = "CODE_CODE_EXEC_ERROR"
CODE_CODE_MISSING_FUNC = "CODE_CODE_MISSING_FUNC"
CODE_CODE_RUNTIME_ERROR = "CODE_CODE_RUNTIME_ERROR"
CODE_QUERY_INPUT_TYPE = "CODE_QUERY_INPUT_TYPE"
CODE_QUERY_OUTPUT_TYPE = "CODE_QUERY_OUTPUT_TYPE"
CODE_QUERY_OUTPUT_MISMATCH = "CODE_QUERY_OUTPUT_MISMATCH"
CODE_SEMANTIC_MISMATCH = "CODE_SEMANTIC_MISMATCH"
CODE_SEMANTIC_ISSUES_CAPPED = "CODE_SEMANTIC_ISSUES_CAPPED"
CODE_FUNC_NOT_CALLABLE = "CODE_FUNC_NOT_CALLABLE"
CODE_UNSAFE_AST = "CODE_UNSAFE_AST"
CURRENT_FAMILY = "stack_bytecode"
PYTHON_CODE_KEY = "python"

_spec_adapter = TypeAdapter(StackBytecodeSpec)
_ALLOWED_BUILTINS = {
    "abs": abs,
    "len": len,
    "max": max,
    "min": min,
    "range": range,
}


def _validate_ast_whitelist(
    code: str, param_name: str = "xs"
) -> tuple[list[Issue], ast.Module | None]:
    allowed_names = ALLOWED_CALL_NAMES | ALLOWED_VAR_NAMES | {param_name}
    issues: list[Issue] = []

    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError):
        return [], None

    annotation_positions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.annotation is not None:
                    for n in ast.walk(arg.annotation):
                        if hasattr(n, "lineno") and hasattr(
                            n, "col_offset"
                        ):
                            annotation_positions.add(
                                cast(
                                    tuple[int, int], (n.lineno, n.col_offset)
                                )
                            )
            if node.returns is not None:
                for n in ast.walk(node.returns):
                    if hasattr(n, "lineno") and hasattr(n, "col_offset"):
                        annotation_positions.add(
                            cast(tuple[int, int], (n.lineno, n.col_offset))
                        )
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            for n in ast.walk(node.annotation):
                if hasattr(n, "lineno") and hasattr(n, "col_offset"):
                    annotation_positions.add(
                        cast(tuple[int, int], (n.lineno, n.col_offset))
                    )

    for node in ast.walk(tree):
        node_type = type(node)
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

        if isinstance(node, ast.Call):
            valid_call = False
            if isinstance(node.func, ast.Name):
                call_name = node.func.id
                allowed_arities = CALL_ARITIES.get(call_name, set())
                if (
                    call_name in ALLOWED_CALL_NAMES
                    and len(node.args) in allowed_arities
                    and len(node.keywords) == 0
                ):
                    valid_call = True
            elif isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                allowed_arities = METHOD_ARITIES.get(method_name, set())
                if (
                    method_name in ALLOWED_METHOD_NAMES
                    and len(node.args) in allowed_arities
                    and len(node.keywords) == 0
                ):
                    valid_call = True

            if not valid_call:
                issues.append(
                    Issue(
                        code=CODE_UNSAFE_AST,
                        severity=Severity.ERROR,
                        message=(
                            "Disallowed function call at line "
                            f"{getattr(node, 'lineno', '?')}"
                        ),
                        location="code",
                    )
                )
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                issues.append(
                    Issue(
                        code=CODE_UNSAFE_AST,
                        severity=Severity.ERROR,
                        message=(
                            f"Disallowed attribute '{node.attr}' at line "
                            f"{getattr(node, 'lineno', '?')}"
                        ),
                        location="code",
                    )
                )
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            in_annotation = (
                node.lineno,
                node.col_offset,
            ) in annotation_positions
            if in_annotation and node.id in ALLOWED_ANNOTATION_NAMES:
                continue
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
) -> tuple[list[Issue], StackBytecodeSpec | None]:
    try:
        spec = _spec_adapter.validate_python(task.spec, strict=True)
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
) -> tuple[list[Issue], Callable[[list[int]], tuple[int, int]] | None]:
    if code is None:
        if isinstance(task.code, str):
            code = task.code
        elif isinstance(task.code, dict):
            code = task.code.get(PYTHON_CODE_KEY)

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
        if "Function 'f' not found in code namespace" in str(e):
            return [
                Issue(
                    code=CODE_CODE_MISSING_FUNC,
                    severity=Severity.ERROR,
                    message="Function 'f' not found in code namespace",
                    location="code",
                    task_id=task.task_id,
                )
            ], None
        return [
            Issue(
                code=CODE_CODE_EXEC_ERROR,
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

    f = namespace.get("f")
    if f is None:
        return [
            Issue(
                code=CODE_CODE_MISSING_FUNC,
                severity=Severity.ERROR,
                message="Function 'f' not found in code namespace",
                location="code",
                task_id=task.task_id,
            )
        ], None

    if not callable(f):
        return [
            Issue(
                code=CODE_FUNC_NOT_CALLABLE,
                severity=Severity.ERROR,
                message=f"Function 'f' is not callable: {type(f)}",
                location="code.f",
                task_id=task.task_id,
            )
        ], None

    return [], cast(Callable[[list[int]], tuple[int, int]], f)


def _validate_query_types(task: Task, strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, q in enumerate(task.queries):
        if not isinstance(q.input, list) or not all(
            isinstance(x, int) for x in q.input
        ):
            issues.append(
                Issue(
                    code=CODE_QUERY_INPUT_TYPE,
                    severity=severity,
                    message="Query input must be list[int]",
                    location=f"queries[{i}].input",
                    task_id=task.task_id,
                )
            )

        if _coerce_query_output(q.output) is None:
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_TYPE,
                    severity=severity,
                    message=(
                        "Query output must be tuple[int, int] "
                        "or list[int, int]"
                    ),
                    location=f"queries[{i}].output",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_query_outputs(
    task: Task,
    spec: StackBytecodeSpec,
    strict: bool,
) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, q in enumerate(task.queries):
        if not isinstance(q.input, list) or not all(
            isinstance(x, int) for x in q.input
        ):
            continue
        actual = _coerce_query_output(q.output)
        if actual is None:
            continue
        expected = eval_stack_bytecode(spec, q.input)
        if actual != expected:
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_MISMATCH,
                    severity=severity,
                    message=(
                        f"Expected output {expected} but found {q.output} "
                        f"for input {q.input}"
                    ),
                    location=f"queries[{i}].output",
                    task_id=task.task_id,
                )
            )
    return issues


def _coerce_query_output(output: object) -> tuple[int, int] | None:
    if isinstance(output, (tuple, list)) and len(output) == 2:
        if isinstance(output[0], int) and isinstance(output[1], int):
            return (output[0], output[1])
    return None


def _validate_semantics(
    task: Task,
    spec: StackBytecodeSpec,
    fn: Callable[[list[int]], tuple[int, int]] | None,
    axes: StackBytecodeAxes,
    strict: bool,
    semantic_trials: int,
    max_semantic_issues: int,
    rng: random.Random,
) -> list[Issue]:
    if fn is None:
        return []

    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING
    len_lo, len_hi = axes.list_length_range
    val_lo, val_hi = axes.value_range

    for _ in range(semantic_trials):
        n = rng.randint(len_lo, len_hi)
        xs = [rng.randint(val_lo, val_hi) for _ in range(n)]
        expected = eval_stack_bytecode(spec, xs)

        try:
            actual = fn(xs)
        except Exception as e:
            issues.append(
                Issue(
                    code=CODE_CODE_RUNTIME_ERROR,
                    severity=severity,
                    message=f"Code raised runtime error for input {xs}: {e}",
                    location="code",
                    task_id=task.task_id,
                )
            )
            continue

        if actual != expected:
            issues.append(
                Issue(
                    code=CODE_SEMANTIC_MISMATCH,
                    severity=severity,
                    message=(
                        f"Semantic mismatch for input {xs}: expected "
                        f"{expected}, got {actual}"
                    ),
                    location="code",
                    task_id=task.task_id,
                )
            )
            if len(issues) >= max_semantic_issues:
                issues.append(
                    Issue(
                        code=CODE_SEMANTIC_ISSUES_CAPPED,
                        severity=severity,
                        message=(
                            "Semantic checks stopped after "
                            f"{max_semantic_issues} issues"
                        ),
                        location="code",
                        task_id=task.task_id,
                    )
                )
                break

    return issues


def validate_stack_bytecode_task(
    task: Task,
    axes: StackBytecodeAxes | None = None,
    strict: bool = True,
    execute_untrusted_code: bool = True,
    max_semantic_issues: int = 10,
    semantic_trials: int = 16,
    random_seed: int = 0,
) -> list[Issue]:
    """Validate a stack_bytecode task for consistency and semantics."""
    if task.family != CURRENT_FAMILY:
        return [
            Issue(
                code=WRONG_FAMILY,
                severity=Severity.ERROR,
                message=(
                    f"Expected family '{CURRENT_FAMILY}', got '{task.family}'"
                ),
                location="family",
                task_id=task.task_id,
            )
        ]

    if axes is None:
        axes = StackBytecodeAxes()

    issues: list[Issue] = []
    issues.extend(_validate_query_types(task, strict=strict))
    issues.extend(_validate_task_id(task))

    spec_issues, spec = _validate_spec_deserialize(task)
    issues.extend(spec_issues)
    if spec is None:
        return issues

    code: str | None = None
    if isinstance(task.code, str):
        code = task.code
    elif isinstance(task.code, dict):
        code = task.code.get(PYTHON_CODE_KEY)

    parsed_tree: ast.Module | None = None
    if code is not None:
        ast_issues, parsed_tree = _validate_ast_whitelist(code)
        issues.extend(ast_issues)

    compile_issues, fn = _validate_code_compile(
        task,
        code=code,
        parsed_tree=parsed_tree,
        execute_untrusted_code=execute_untrusted_code,
    )
    issues.extend(compile_issues)

    issues.extend(_validate_query_outputs(task, spec, strict=strict))

    rng = random.Random(random_seed)
    issues.extend(
        _validate_semantics(
            task,
            spec,
            fn,
            axes,
            strict=strict,
            semantic_trials=semantic_trials,
            max_semantic_issues=max_semantic_issues,
            rng=rng,
        )
    )

    return issues
