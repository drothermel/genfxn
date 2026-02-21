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
from genfxn.sequence_dp.ast_safety import (
    ALLOWED_ANNOTATION_NAMES,
    ALLOWED_AST_NODES,
    ALLOWED_CALL_NAMES,
    ALLOWED_METHOD_NAMES,
    ALLOWED_VAR_NAMES,
    CALL_ARITIES,
    METHOD_ARITIES,
)
from genfxn.sequence_dp.eval import eval_sequence_dp
from genfxn.sequence_dp.models import SequenceDpAxes, SequenceDpSpec

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
CURRENT_FAMILY = "sequence_dp"
PYTHON_CODE_KEY = "python"

_spec_adapter = TypeAdapter(SequenceDpSpec)
_ALLOWED_BUILTINS = {
    "RuntimeError": RuntimeError,
    "ValueError": ValueError,
    "abs": abs,
    "len": len,
    "max": max,
    "range": range,
}


def _is_int_not_bool(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_ast_whitelist(
    code: str,
    param_names: tuple[str, ...] = ("a", "b"),
) -> tuple[list[Issue], ast.Module | None]:
    allowed_names = ALLOWED_CALL_NAMES | ALLOWED_VAR_NAMES | set(param_names)
    issues: list[Issue] = []

    try:
        tree = ast.parse(code)
    except (SyntaxError, TypeError):
        return [], None

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

    annotation_positions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.annotation is None:
                    continue
                for n in ast.walk(arg.annotation):
                    if hasattr(n, "lineno") and hasattr(n, "col_offset"):
                        annotation_positions.add(
                            cast(tuple[int, int], (n.lineno, n.col_offset))
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
            elif node.attr not in ALLOWED_METHOD_NAMES:
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
    try:
        expected = task_id_from_spec(family=task.family, spec=task.spec)
    except Exception as e:
        return [
            Issue(
                code=CODE_TASK_ID_MISMATCH,
                severity=Severity.ERROR,
                message=f"Failed to compute task_id from spec: {e}",
                location="task_id",
                task_id=task.task_id,
            )
        ]
    if task.task_id == expected:
        return []
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


def _validate_spec_deserialize(
    task: Task,
) -> tuple[list[Issue], SequenceDpSpec | None]:
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
) -> tuple[list[Issue], Callable[[list[int], list[int]], int] | None]:
    if code is None:
        if isinstance(task.code, str):
            code = task.code
        elif isinstance(task.code, dict):
            code = task.code.get(PYTHON_CODE_KEY)

    if code is None:
        return [], None

    if not isinstance(code, str):
        return [
            Issue(
                code=CODE_CODE_PARSE_ERROR,
                severity=Severity.ERROR,
                message=(
                    f"Code payload must be a string, got {type(code).__name__}"
                ),
                location="code",
                task_id=task.task_id,
            )
        ], None

    if parsed_tree is None:
        try:
            parsed_tree = ast.parse(code)
        except (SyntaxError, TypeError) as e:
            return [
                Issue(
                    code=CODE_CODE_PARSE_ERROR,
                    severity=Severity.ERROR,
                    message=f"Failed to parse code: {e}",
                    location="code",
                    task_id=task.task_id,
                )
            ], None
    if not execute_untrusted_code:
        return [], None

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
    except Exception as e:  # pragma: no cover - defensive fallback
        return [
            Issue(
                code=CODE_CODE_EXEC_ERROR,
                severity=Severity.ERROR,
                message=f"Failed to execute code: {e}",
                location="code",
                task_id=task.task_id,
            )
        ], None

    fn_obj = namespace.get("f")
    if fn_obj is None:
        return [
            Issue(
                code=CODE_CODE_MISSING_FUNC,
                severity=Severity.ERROR,
                message="Function 'f' not found in code namespace",
                location="code",
                task_id=task.task_id,
            )
        ], None

    if not callable(fn_obj):
        return [
            Issue(
                code=CODE_FUNC_NOT_CALLABLE,
                severity=Severity.ERROR,
                message=f"Function 'f' is not callable: {type(fn_obj)}",
                location="code.f",
                task_id=task.task_id,
            )
        ], None

    return [], cast(Callable[[list[int], list[int]], int], fn_obj)


def _coerce_query_input(
    input_value: object,
) -> tuple[list[int], list[int]] | None:
    if not isinstance(input_value, dict):
        return None

    keys = set(input_value)
    if keys != {"a", "b"}:
        return None

    typed_input_value = cast(dict[str, object], input_value)
    a_value = typed_input_value.get("a")
    b_value = typed_input_value.get("b")
    if not isinstance(a_value, list) or not all(
        _is_int_not_bool(x) for x in a_value
    ):
        return None
    if not isinstance(b_value, list) or not all(
        _is_int_not_bool(x) for x in b_value
    ):
        return None

    return cast(list[int], a_value), cast(list[int], b_value)


def _validate_query_types(task: Task, strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, query in enumerate(task.queries):
        if _coerce_query_input(query.input) is None:
            issues.append(
                Issue(
                    code=CODE_QUERY_INPUT_TYPE,
                    severity=severity,
                    message=(
                        "Query input must be dict{'a': list[int], "
                        "'b': list[int]}"
                    ),
                    location=f"queries[{i}].input",
                    task_id=task.task_id,
                )
            )
        if not _is_int_not_bool(query.output):
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_TYPE,
                    severity=severity,
                    message="Query output must be int",
                    location=f"queries[{i}].output",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_query_outputs(
    task: Task,
    spec: SequenceDpSpec,
    strict: bool,
) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, query in enumerate(task.queries):
        coerced = _coerce_query_input(query.input)
        if coerced is None:
            continue
        if not _is_int_not_bool(query.output):
            continue

        a, b = coerced
        expected = eval_sequence_dp(spec, a, b)
        if query.output != expected:
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_MISMATCH,
                    severity=severity,
                    message=(
                        f"Expected output {expected} but found "
                        f"{query.output} for input {query.input}"
                    ),
                    location=f"queries[{i}].output",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_semantics(
    task: Task,
    spec: SequenceDpSpec,
    fn: Callable[[list[int], list[int]], int] | None,
    axes: SequenceDpAxes,
    strict: bool,
    semantic_trials: int,
    max_semantic_issues: int,
    rng: random.Random,
) -> list[Issue]:
    if fn is None:
        return []

    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING
    len_a_lo, len_a_hi = axes.len_a_range
    len_b_lo, len_b_hi = axes.len_b_range
    val_lo, val_hi = axes.value_range

    for _ in range(semantic_trials):
        a_len = rng.randint(len_a_lo, len_a_hi)
        b_len = rng.randint(len_b_lo, len_b_hi)
        a = [rng.randint(val_lo, val_hi) for _ in range(a_len)]
        b = [rng.randint(val_lo, val_hi) for _ in range(b_len)]
        expected = eval_sequence_dp(spec, a, b)

        try:
            actual = fn(a, b)
        except Exception as e:
            issues.append(
                Issue(
                    code=CODE_CODE_RUNTIME_ERROR,
                    severity=severity,
                    message=(
                        "Code raised runtime error for input "
                        f"{{'a': {a}, 'b': {b}}}: {e}"
                    ),
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
                        "Semantic mismatch for input "
                        f"{{'a': {a}, 'b': {b}}}: expected {expected}, "
                        f"got {actual}"
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


def validate_sequence_dp_task(
    task: Task,
    axes: SequenceDpAxes | None = None,
    strict: bool = True,
    execute_untrusted_code: bool = False,
    max_semantic_issues: int = 10,
    semantic_trials: int = 16,
    random_seed: int = 0,
) -> list[Issue]:
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
        axes = SequenceDpAxes()

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

    ast_issues: list[Issue] = []
    parsed_tree: ast.Module | None = None
    if code is not None:
        ast_issues, parsed_tree = _validate_ast_whitelist(code)
        issues.extend(ast_issues)

    fn = None
    has_unsafe_ast = any(i.code == CODE_UNSAFE_AST for i in ast_issues)
    if not has_unsafe_ast:
        compile_issues, fn = _validate_code_compile(
            task,
            code=code,
            parsed_tree=parsed_tree,
            execute_untrusted_code=execute_untrusted_code,
        )
        issues.extend(compile_issues)

    try:
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
    finally:
        close = getattr(fn, "close", None)
        if callable(close):
            close()

    return issues
