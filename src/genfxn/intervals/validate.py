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
from genfxn.intervals.ast_safety import (
    ALLOWED_ANNOTATION_NAMES,
    ALLOWED_AST_NODES,
    ALLOWED_CALL_NAMES,
    ALLOWED_METHOD_NAMES,
    ALLOWED_VAR_NAMES,
    CALL_ARITIES,
    METHOD_ARITIES,
)
from genfxn.intervals.eval import eval_intervals
from genfxn.intervals.models import IntervalsAxes, IntervalsSpec

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
CURRENT_FAMILY = "intervals"
PYTHON_CODE_KEY = "python"

_spec_adapter = TypeAdapter(IntervalsSpec)
_ALLOWED_BUILTINS = {
    "ValueError": ValueError,
    "abs": abs,
    "len": len,
    "max": max,
    "min": min,
    "range": range,
    "sorted": sorted,
}


def _validate_ast_whitelist(
    code: str,
    param_name: str = "intervals",
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
                if arg.annotation is None:
                    continue
                for ann_node in ast.walk(arg.annotation):
                    if hasattr(ann_node, "lineno") and hasattr(
                        ann_node, "col_offset"
                    ):
                        annotation_positions.add(
                            cast(
                                tuple[int, int],
                                (ann_node.lineno, ann_node.col_offset),
                            )
                        )
            if node.returns is not None:
                for ann_node in ast.walk(node.returns):
                    if hasattr(ann_node, "lineno") and hasattr(
                        ann_node, "col_offset"
                    ):
                        annotation_positions.add(
                            cast(
                                tuple[int, int],
                                (ann_node.lineno, ann_node.col_offset),
                            )
                        )
        elif isinstance(node, ast.AnnAssign) and node.annotation is not None:
            for ann_node in ast.walk(node.annotation):
                if hasattr(ann_node, "lineno") and hasattr(
                    ann_node, "col_offset"
                ):
                    annotation_positions.add(
                        cast(
                            tuple[int, int],
                            (ann_node.lineno, ann_node.col_offset),
                        )
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
                            f"Disallowed name '{node.id}' at line "
                            f"{node.lineno}"
                        ),
                        location="code",
                    )
                )

    return issues, tree if not issues else None


def _validate_task_id(task: Task) -> list[Issue]:
    expected = task_id_from_spec(family=task.family, spec=task.spec)
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
) -> tuple[list[Issue], IntervalsSpec | None]:
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
) -> tuple[list[Issue], Callable[[list[tuple[int, int]]], int] | None]:
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

    return [], cast(Callable[[list[tuple[int, int]]], int], fn_obj)


def _coerce_query_input(
    input_value: object,
) -> list[tuple[int, int]] | None:
    if not isinstance(input_value, list):
        return None

    intervals: list[tuple[int, int]] = []
    for pair in input_value:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            return None
        left = pair[0]
        right = pair[1]
        if not isinstance(left, int) or not isinstance(right, int):
            return None
        intervals.append((left, right))

    return intervals


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
                        "Query input must be list[tuple[int, int]] "
                        "(tuple/list pairs accepted)"
                    ),
                    location=f"queries[{i}].input",
                    task_id=task.task_id,
                )
            )
        if not isinstance(query.output, int):
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
    spec: IntervalsSpec,
    strict: bool,
) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, query in enumerate(task.queries):
        intervals = _coerce_query_input(query.input)
        if intervals is None:
            continue
        if not isinstance(query.output, int):
            continue

        expected = eval_intervals(spec, intervals)
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


def _clamp(value: int, lo: int, hi: int) -> int:
    return min(max(value, lo), hi)


def _sample_intervals_from_axes(
    axes: IntervalsAxes,
    rng: random.Random,
) -> list[tuple[int, int]]:
    n_lo, n_hi = axes.n_intervals_range
    endpoint_lo, endpoint_hi = axes.endpoint_range
    span_lo, span_hi = axes.max_span_range
    count = rng.randint(n_lo, n_hi)

    span_low = max(0, span_lo)
    span_high = max(span_low, span_hi)
    reverse_prob = rng.uniform(*axes.allow_reversed_interval_prob_range)
    degenerate_prob = rng.uniform(*axes.degenerate_interval_prob_range)
    nested_prob = rng.uniform(*axes.nested_interval_prob_range)

    intervals: list[tuple[int, int]] = []
    for _ in range(count):
        use_nested = len(intervals) > 0 and rng.random() < nested_prob

        if use_nested:
            parent_a, parent_b = intervals[rng.randrange(len(intervals))]
            parent_lo = min(parent_a, parent_b)
            parent_hi = max(parent_a, parent_b)
            start = rng.randint(parent_lo, parent_hi)
            end = rng.randint(start, parent_hi)
        else:
            start = rng.randint(endpoint_lo, endpoint_hi)
            if rng.random() < degenerate_prob:
                end = start
            else:
                span = rng.randint(span_low, span_high)
                direction = -1 if rng.random() < 0.5 else 1
                end = _clamp(start + direction * span, endpoint_lo, endpoint_hi)

        if rng.random() < reverse_prob and start != end:
            start, end = end, start

        intervals.append((start, end))

    return intervals


def _validate_semantics(
    task: Task,
    spec: IntervalsSpec,
    fn: Callable[[list[tuple[int, int]]], int] | None,
    axes: IntervalsAxes,
    strict: bool,
    semantic_trials: int,
    max_semantic_issues: int,
    rng: random.Random,
) -> list[Issue]:
    if fn is None:
        return []

    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for _ in range(semantic_trials):
        intervals = _sample_intervals_from_axes(axes, rng)
        expected = eval_intervals(spec, intervals)

        try:
            actual = fn(list(intervals))
        except Exception as e:
            issues.append(
                Issue(
                    code=CODE_CODE_RUNTIME_ERROR,
                    severity=severity,
                    message=(
                        "Code raised runtime error for input "
                        f"{intervals}: {e}"
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
                        f"Semantic mismatch for input {intervals}: expected "
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


def validate_intervals_task(
    task: Task,
    axes: IntervalsAxes | None = None,
    strict: bool = True,
    execute_untrusted_code: bool = True,
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
        axes = IntervalsAxes()

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
    has_unsafe_ast = any(issue.code == CODE_UNSAFE_AST for issue in ast_issues)
    if not has_unsafe_ast:
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
