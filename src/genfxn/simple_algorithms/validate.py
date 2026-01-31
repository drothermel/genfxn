import ast
import random
from collections.abc import Callable
from typing import Any, cast

from pydantic import TypeAdapter, ValidationError

from genfxn.core.codegen import task_id_from_spec
from genfxn.core.models import Task
from genfxn.core.validate import WRONG_FAMILY, Issue, Severity
from genfxn.simple_algorithms.ast_safety import (
    ALLOWED_AST_NODES,
    ALLOWED_CALL_NAMES,
    ALLOWED_METHOD_NAMES,
    ALLOWED_VAR_NAMES,
    CALL_ARITIES,
)
from genfxn.simple_algorithms.eval import eval_simple_algorithms
from genfxn.simple_algorithms.models import (
    CountPairsSumSpec,
    CountingMode,
    MostFrequentSpec,
    SimpleAlgorithmsAxes,
    SimpleAlgorithmsSpec,
)

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
CODE_TIE_BREAK_MISMATCH = "TIE_BREAK_MISMATCH"
CODE_COUNTING_MODE_MISMATCH = "COUNTING_MODE_MISMATCH"
CODE_EDGE_CASE_FAILURE = "EDGE_CASE_FAILURE"
CURRENT_FAMILY = "simple_algorithms"

_spec_adapter = TypeAdapter(SimpleAlgorithmsSpec)


def _validate_ast_whitelist(
    code: str, param_name: str = "xs"
) -> tuple[list[Issue], ast.Module | None]:
    """Reject code containing disallowed AST nodes."""
    allowed_names = ALLOWED_CALL_NAMES | ALLOWED_VAR_NAMES | {param_name}

    issues: list[Issue] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        msg = e.msg or str(e)
        if e.lineno is not None:
            loc = f" at line {e.lineno}"
            if e.offset is not None:
                loc += f", column {e.offset}"
            message = f"Syntax error in code: {msg}{loc}"
        else:
            message = f"Syntax error in code: {msg}"
        issues.append(
            Issue(
                code=CODE_CODE_PARSE_ERROR,
                severity=Severity.ERROR,
                message=message,
                location="code",
            )
        )
        return issues, None

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

        # Call check: function calls or method calls
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
            elif (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in ALLOWED_METHOD_NAMES
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

        # Name check
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id not in allowed_names:
                issues.append(
                    Issue(
                        code=CODE_UNSAFE_AST,
                        severity=Severity.ERROR,
                        message=f"Bad name '{node.id}' at line {node.lineno}",
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
) -> tuple[list[Issue], SimpleAlgorithmsSpec | None]:
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
) -> tuple[list[Issue], Callable[[list[int]], int] | None]:
    try:
        ast.parse(task.code)
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

    namespace: dict[str, Any] = {}
    try:
        exec(task.code, namespace)  # noqa: S102
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
                    message=f"Output {type(q.output).__name__}, expected int",
                    location=f"queries[{i}].output",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_query_outputs(
    task: Task, spec: SimpleAlgorithmsSpec
) -> list[Issue]:
    issues: list[Issue] = []

    for i, q in enumerate(task.queries):
        if not isinstance(q.input, list):
            continue
        if not all(type(elem) is int for elem in q.input):
            continue
        expected = eval_simple_algorithms(spec, q.input)
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


# Canonical tie-break inputs for most_frequent (same value counts, order differs).
_TIE_BREAK_INPUTS: list[list[int]] = [
    [1, 2, 1, 2],
    [2, 1, 2, 1],
    [1, 1, 1, 2, 2, 2],
]


def _check_tie_break_consistency(
    task: Task, spec: SimpleAlgorithmsSpec
) -> list[Issue]:
    """Emit CODE_TIE_BREAK_MISMATCH when a query's output disagrees with spec tie-break."""
    if not isinstance(spec, MostFrequentSpec):
        return []
    issues: list[Issue] = []
    for i, q in enumerate(task.queries):
        if not isinstance(q.input, list) or not all(
            type(elem) is int for elem in q.input
        ):
            continue
        if q.input not in _TIE_BREAK_INPUTS:
            continue
        expected = eval_simple_algorithms(spec, q.input)
        if q.output != expected:
            issues.append(
                Issue(
                    code=CODE_TIE_BREAK_MISMATCH,
                    severity=Severity.ERROR,
                    message=(
                        f"Query output {q.output} != expected {expected} "
                        f"for tie-break input {q.input} (tie_break={spec.tie_break})"
                    ),
                    location=f"queries[{i}]",
                    task_id=task.task_id,
                )
            )
    return issues


def _check_counting_mode_consistency(
    task: Task, spec: SimpleAlgorithmsSpec
) -> list[Issue]:
    """Emit CODE_COUNTING_MODE_MISMATCH when output matches the wrong counting mode."""
    if not isinstance(spec, CountPairsSumSpec):
        return []
    issues: list[Issue] = []
    other_mode = (
        CountingMode.UNIQUE_VALUES
        if spec.counting_mode == CountingMode.ALL_INDICES
        else CountingMode.ALL_INDICES
    )
    alt_spec = CountPairsSumSpec(
        template="count_pairs_sum",
        target=spec.target,
        counting_mode=other_mode,
    )
    for i, q in enumerate(task.queries):
        if not isinstance(q.input, list) or not all(
            type(elem) is int for elem in q.input
        ):
            continue
        expected = eval_simple_algorithms(spec, q.input)
        if q.output == expected:
            continue
        other_expected = eval_simple_algorithms(alt_spec, q.input)
        if q.output == other_expected:
            issues.append(
                Issue(
                    code=CODE_COUNTING_MODE_MISMATCH,
                    severity=Severity.ERROR,
                    message=(
                        f"Query output {q.output} matches {other_mode}, "
                        f"spec has counting_mode={spec.counting_mode} (expected {expected})"
                    ),
                    location=f"queries[{i}]",
                    task_id=task.task_id,
                )
            )
    return issues


def _check_edge_case_handling(
    task: Task,
    func: Callable[[list[int]], int],
    spec: SimpleAlgorithmsSpec,
    axes: SimpleAlgorithmsAxes,
) -> list[Issue]:
    """Emit CODE_EDGE_CASE_FAILURE when code fails or disagrees on edge-case inputs."""
    issues: list[Issue] = []
    val_lo, val_hi = axes.value_range
    edge_inputs: list[list[int]] = [[], [val_lo], [val_hi]]
    for xs in edge_inputs:
        try:
            actual = func(xs)
        except Exception as e:
            issues.append(
                Issue(
                    code=CODE_EDGE_CASE_FAILURE,
                    severity=Severity.ERROR,
                    message=f"f({xs}) raised {type(e).__name__}: {e}",
                    location="code",
                    task_id=task.task_id,
                )
            )
            continue
        expected = eval_simple_algorithms(spec, xs)
        if actual != expected:
            issues.append(
                Issue(
                    code=CODE_EDGE_CASE_FAILURE,
                    severity=Severity.ERROR,
                    message=f"f({xs}) = {actual}, expected {expected}",
                    location="code",
                    task_id=task.task_id,
                )
            )
    return issues


def _generate_test_inputs(
    axes: SimpleAlgorithmsAxes, rng: random.Random, num_samples: int = 50
) -> list[list[int]]:
    """Generate test inputs including edge cases and random samples."""
    inputs: list[list[int]] = []
    val_lo, val_hi = axes.value_range
    len_lo, len_hi = axes.list_length_range

    # Edge cases
    inputs.append([])
    inputs.append([val_lo])
    inputs.append([val_hi])
    inputs.append([val_lo] * len_lo)
    inputs.append([val_hi] * len_hi)
    inputs.append([1, 2, 1, 2])  # Tie-break test
    inputs.append([2, 1, 2, 1])  # Tie-break test
    inputs.append([1, 1, 1, 2, 2, 2])  # Multi-way tie

    # Random samples (avoid negative range when edge cases >= num_samples)
    to_add = max(0, num_samples - len(inputs))
    for _ in range(to_add):
        length = rng.randint(len_lo, len_hi)
        inputs.append([rng.randint(val_lo, val_hi) for _ in range(length)])

    # Guarantee exactly num_samples: trim if over, duplicate randomly if under
    if len(inputs) > num_samples:
        inputs[:] = rng.sample(inputs, num_samples)
    while len(inputs) < num_samples:
        inputs.append(rng.choice(inputs)[:])

    return inputs


def _validate_semantics(
    task: Task,
    func: Callable[[list[int]], int],
    spec: SimpleAlgorithmsSpec,
    axes: SimpleAlgorithmsAxes,
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

        expected = eval_simple_algorithms(spec, xs)
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


def validate_simple_algorithms_task(
    task: Task,
    axes: SimpleAlgorithmsAxes | None = None,
    strict: bool = True,
    max_semantic_issues: int = 10,
    emit_diagnostics: bool = True,  # noqa: ARG001 - kept for API parity
    paranoid: bool = False,
    rng: random.Random | None = None,
) -> list[Issue]:
    """Validate a simple_algorithms task for correctness.

    Args:
        task: The task to validate.
        axes: Sampling config for semantic testing. Defaults if None.
        strict: If True, type issues are errors; if False, warnings.
        max_semantic_issues: Stop semantic testing after this many issues.
            Use 0 for unlimited.
        emit_diagnostics: Kept for API parity. No diagnostics for this family.
        paranoid: If True, validate AST whitelist before executing code.
        rng: Random generator for semantic testing. Random(42) if None.

    Returns:
        List of validation issues found.
    """
    if task.family != CURRENT_FAMILY:
        return [
            Issue(
                code=WRONG_FAMILY,
                severity=Severity.ERROR,
                message=f"Family '{task.family}' != '{CURRENT_FAMILY}'",
                location="family",
                task_id=task.task_id,
            )
        ]
    if axes is None:
        axes = SimpleAlgorithmsAxes()
    if rng is None:
        rng = random.Random(42)

    issues: list[Issue] = []

    issues.extend(_validate_task_id(task))

    spec_issues, spec = _validate_spec_deserialize(task)
    issues.extend(spec_issues)

    if paranoid:
        ast_issues, _ = _validate_ast_whitelist(task.code)
        if ast_issues:
            issues.extend(ast_issues)
            return issues

    code_issues, func = _validate_code_compile(task)
    issues.extend(code_issues)

    issues.extend(_validate_query_types(task, strict))

    if spec is not None:
        issues.extend(_validate_query_outputs(task, spec))
        issues.extend(_check_tie_break_consistency(task, spec))
        issues.extend(_check_counting_mode_consistency(task, spec))

    if spec is not None and func is not None:
        issues.extend(_check_edge_case_handling(task, func, spec, axes))
        issues.extend(
            _validate_semantics(
                task, func, spec, axes, max_semantic_issues, rng
            )
        )

    return issues
