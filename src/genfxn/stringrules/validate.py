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
from genfxn.core.string_predicates import eval_string_predicate
from genfxn.core.validate import WRONG_FAMILY, Issue, Severity
from genfxn.stringrules.ast_safety import (
    ALLOWED_ANNOTATION_NAMES,
    ALLOWED_AST_NODES,
    ALLOWED_CALL_NAMES,
    ALLOWED_METHOD_NAMES,
    ALLOWED_VAR_NAMES,
    CALL_ARITIES,
    METHOD_ARITIES,
)
from genfxn.stringrules.eval import eval_stringrules
from genfxn.stringrules.models import StringRulesAxes, StringRulesSpec
from genfxn.stringrules.utils import _get_charset

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
CODE_SHADOWED_RULE = "SHADOWED_RULE"
CODE_EMPTY_RULESET = "EMPTY_RULESET"
CODE_AXES_INVALID = "AXES_INVALID"
CODE_INVALID_CHARSET = "INVALID_CHARSET"
CURRENT_FAMILY = "stringrules"

DEFAULT_MAX_SEMANTIC_ISSUES = 10
PYTHON_CODE_KEY = "python"

_spec_adapter = TypeAdapter(StringRulesSpec)
_axes_adapter = TypeAdapter(StringRulesAxes)
_ALLOWED_BUILTINS = {"len": len, "str": str}


def _annotation_positions(tree: ast.Module) -> set[tuple[int, int]]:
    """Positions (lineno, col_offset) of nodes inside type annotations."""
    positions: set[tuple[int, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            for arg in node.args.args:
                if arg.annotation is not None:
                    for n in ast.walk(arg.annotation):
                        if hasattr(n, "lineno") and hasattr(n, "col_offset"):
                            positions.add(
                                cast(
                                    tuple[int, int],
                                    (n.lineno, n.col_offset),
                                )
                            )
            if node.returns is not None:
                for n in ast.walk(node.returns):
                    if hasattr(n, "lineno") and hasattr(n, "col_offset"):
                        positions.add(
                            cast(
                                tuple[int, int],
                                (n.lineno, n.col_offset),
                            )
                        )
    return positions


def _validate_ast_whitelist(
    code: str, param_name: str = "s"
) -> tuple[list[Issue], ast.Module | None]:
    """Reject code containing disallowed AST nodes."""
    allowed_names = ALLOWED_CALL_NAMES | ALLOWED_VAR_NAMES | {param_name}

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

    annotation_positions = _annotation_positions(tree)
    issues: list[Issue] = []
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
            arity_error_message: str | None = None
            if (
                isinstance(node.func, ast.Name)
                and node.func.id in ALLOWED_CALL_NAMES
            ):
                func_name = node.func.id
                if func_name not in CALL_ARITIES:
                    raise AssertionError(
                        f"Function '{func_name}' is in ALLOWED_CALL_NAMES but "
                        "has no entry in CALL_ARITIES; add arity metadata in "
                        "ast_safety.CALL_ARITIES."
                    )
                allowed_arities = CALL_ARITIES[func_name]
                if (
                    len(node.args) in allowed_arities
                    and len(node.keywords) == 0
                ):
                    valid_call = True
                elif len(node.keywords) != 0 or allowed_arities:
                    arity_error_message = (
                        f"Function '{func_name}' called with "
                        f"{len(node.args)} argument(s) at line "
                        f"{getattr(node, 'lineno', '?')}; "
                        f"allowed arities: {sorted(allowed_arities)}"
                    )
            elif isinstance(node.func, ast.Attribute):
                method_name = node.func.attr
                if method_name in ALLOWED_METHOD_NAMES:
                    if method_name not in METHOD_ARITIES:
                        raise AssertionError(
                            f"Method '{method_name}' in ALLOWED_METHOD_NAMES "
                            "but missing METHOD_ARITIES; add in ast_safety."
                        )
                    allowed_arities = METHOD_ARITIES[method_name]
                    if (
                        len(node.args) in allowed_arities
                        and len(node.keywords) == 0
                    ):
                        valid_call = True
                    elif len(node.keywords) != 0 or allowed_arities:
                        arity_error_message = (
                            f"Method '{method_name}' called with "
                            f"{len(node.args)} argument(s) at line "
                            f"{getattr(node, 'lineno', '?')}; "
                            f"allowed arities: {sorted(allowed_arities)}"
                        )
            if not valid_call:
                message = (
                    arity_error_message
                    if arity_error_message
                    else (
                        f"Disallowed function call at line "
                        f"{getattr(node, 'lineno', '?')}"
                    )
                )
                issues.append(
                    Issue(
                        code=CODE_UNSAFE_AST,
                        severity=Severity.ERROR,
                        message=message,
                        location="code",
                    )
                )

        # Name check: only Load-context names (runtime use). Names in type
        # annotations (e.g. def f(s: str) -> str:) are allowed if in
        # ALLOWED_ANNOTATION_NAMES.
        elif isinstance(node, ast.Attribute):
            attr = node.attr
            if attr.startswith("__") and attr.endswith("__"):
                issues.append(
                    Issue(
                        code=CODE_UNSAFE_AST,
                        severity=Severity.ERROR,
                        message=(
                            f"Disallowed attribute '{attr}' at line "
                            f"{getattr(node, 'lineno', '?')}"
                        ),
                        location="code",
                    )
                )
            elif attr not in ALLOWED_METHOD_NAMES:
                issues.append(
                    Issue(
                        code=CODE_UNSAFE_AST,
                        severity=Severity.ERROR,
                        message=(
                            f"Disallowed attribute '{attr}' at line "
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
                        message=f"Disallowed name '{node.id}' ({node.lineno})",
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
) -> tuple[list[Issue], StringRulesSpec | None]:
    try:
        spec = _spec_adapter.validate_python(task.spec, strict=True)
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
    else:
        return [], spec


def _validate_code_compile(
    task: Task,
    code: str | None = None,
    parsed_tree: ast.Module | None = None,
    execute_untrusted_code: bool = True,
) -> tuple[list[Issue], Callable[[str], str] | None]:
    if code is None:
        if isinstance(task.code, str):
            code = task.code
        elif isinstance(task.code, dict):
            code = task.code.get(PYTHON_CODE_KEY)

    # Multi-language maps without Python source are valid inputs for this
    # validator; skip code compile/exec validation in that case.
    if code is None:
        return [], None

    if not isinstance(code, str):
        return [
            Issue(
                code=CODE_CODE_PARSE_ERROR,
                severity=Severity.ERROR,
                message=(
                    "Code payload must be a string, got "
                    f"{type(code).__name__}"
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

    return [], cast(Callable[[str], str], namespace["f"])


def _validate_query_types(task: Task, strict: bool) -> list[Issue]:
    issues: list[Issue] = []
    severity = Severity.ERROR if strict else Severity.WARNING

    for i, q in enumerate(task.queries):
        if not isinstance(q.input, str):
            input_type = type(q.input).__name__
            issues.append(
                Issue(
                    code=CODE_QUERY_INPUT_TYPE,
                    severity=severity,
                    message=f"Query input is {input_type}, expected str",
                    location=f"queries[{i}].input",
                    task_id=task.task_id,
                )
            )

        if not isinstance(q.output, str):
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_TYPE,
                    severity=severity,
                    message=f"Output {type(q.output).__name__}, expected str",
                    location=f"queries[{i}].output",
                    task_id=task.task_id,
                )
            )

    return issues


def _validate_query_outputs(task: Task, spec: StringRulesSpec) -> list[Issue]:
    issues: list[Issue] = []

    for i, q in enumerate(task.queries):
        if not isinstance(q.input, str):
            continue
        expected = eval_stringrules(spec, q.input)
        if q.output != expected:
            issues.append(
                Issue(
                    code=CODE_QUERY_OUTPUT_MISMATCH,
                    severity=Severity.ERROR,
                    message=(
                        f"Query output {q.output!r} != expected {expected!r} "
                        f"for input {q.input!r}"
                    ),
                    location=f"queries[{i}]",
                    task_id=task.task_id,
                )
            )

    return issues


def _generate_test_inputs(
    axes: StringRulesAxes, rng: random.Random, num_samples: int = 50
) -> list[str]:
    """Generate test inputs including edge cases and random samples."""
    charset = _get_charset(axes.charset)
    if not charset:
        raise ValueError("axes.charset resolved to an empty character set")
    inputs: list[str] = []
    lo, hi = axes.string_length_range

    # Edge cases
    if lo <= 0 <= hi:
        inputs.append("")
    for candidate in ("a", "A", "1", "abc", "ABC", "123", "AbC123"):
        if lo <= len(candidate) <= hi and all(c in charset for c in candidate):
            inputs.append(candidate)
    if " " in charset:
        if lo <= 1 <= hi:
            inputs.append(" ")
        if lo <= 10 <= hi:
            spaced_literal = "  spaces  "
            if all(ch in charset for ch in spaced_literal):
                inputs.append(spaced_literal)
            else:
                inputs.append(" " * 10)

    # Random samples
    for _ in range(max(0, num_samples - len(inputs))):
        length = rng.randint(lo, hi)
        inputs.append("".join(rng.choice(charset) for _ in range(length)))

    return inputs


def _validate_semantics(
    task: Task,
    func: Callable[[str], str],
    spec: StringRulesSpec,
    axes: StringRulesAxes,
    max_issues: int,
    rng: random.Random,
) -> list[Issue]:
    issues: list[Issue] = []
    try:
        test_inputs = _generate_test_inputs(axes, rng)
    except ValueError as e:
        return [
            Issue(
                code=CODE_AXES_INVALID,
                severity=Severity.ERROR,
                message=f"Invalid axes for semantic validation: {e}",
                location="axes.charset",
                task_id=task.task_id,
            )
        ]

    for s in test_inputs:
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
            actual = func(s)
        except Exception as e:
            issues.append(
                Issue(
                    code=CODE_CODE_RUNTIME_ERROR,
                    severity=Severity.ERROR,
                    message=f"f({s!r}) raised {type(e).__name__}: {e}",
                    location="code",
                    task_id=task.task_id,
                )
            )
            continue

        expected = eval_stringrules(spec, s)
        if actual != expected:
            issues.append(
                Issue(
                    code=CODE_SEMANTIC_MISMATCH,
                    severity=Severity.ERROR,
                    message=f"f({s!r}) = {actual!r}, expected {expected!r}",
                    location="code",
                    task_id=task.task_id,
                )
            )

    return issues


def _first_matching_rule_index(spec: StringRulesSpec, s: str) -> int | None:
    for i, rule in enumerate(spec.rules):
        if eval_string_predicate(rule.predicate, s):
            return i
    return None


def _validate_rule_diagnostics(
    task: Task,
    spec: StringRulesSpec,
    axes: StringRulesAxes,
    rng: random.Random,
) -> list[Issue]:
    issues: list[Issue] = []

    if not spec.rules:
        issues.append(
            Issue(
                code=CODE_EMPTY_RULESET,
                severity=Severity.WARNING,
                message=(
                    "Spec has no rules; default transform handles all inputs"
                ),
                location="spec.rules",
                task_id=task.task_id,
            )
        )
        return issues

    try:
        candidates = _generate_test_inputs(axes, rng, num_samples=100)
    except ValueError as e:
        issues.append(
            Issue(
                code=CODE_INVALID_CHARSET,
                severity=Severity.ERROR,
                message=str(e),
                location="spec.axes",
                task_id=task.task_id,
            )
        )
        return issues

    first_match_by_candidate = {
        s: _first_matching_rule_index(spec, s) for s in candidates
    }

    for i, rule in enumerate(spec.rules):
        reachable = False
        blockers: set[int] = set()
        for s in candidates:
            if not eval_string_predicate(rule.predicate, s):
                continue
            first_index = first_match_by_candidate[s]
            if first_index == i:
                reachable = True
                break
            if first_index is not None and first_index < i:
                blockers.add(first_index)

        if not reachable:
            blocker_text = (
                f"blocked by earlier rule(s) {sorted(blockers)}"
                if blockers
                else "unreachable on sampled inputs"
            )
            issues.append(
                Issue(
                    code=CODE_SHADOWED_RULE,
                    severity=Severity.WARNING,
                    message=(
                        f"Rule {i} is shadowed/unreachable ({blocker_text})"
                    ),
                    location=f"spec.rules[{i}]",
                    task_id=task.task_id,
                )
            )

    return issues


def validate_stringrules_task(
    task: Task,
    axes: StringRulesAxes | None = None,
    strict: bool = True,
    max_semantic_issues: int = DEFAULT_MAX_SEMANTIC_ISSUES,
    emit_diagnostics: bool = True,  # noqa: ARG001 - kept for API parity
    paranoid: bool = False,
    rng: random.Random | None = None,
    execute_untrusted_code: bool = False,
) -> list[Issue]:
    """Validate a stringrules task for correctness.

    Args:
        task: The task to validate.
        axes: Sampling config for semantic testing. Defaults if None.
        strict: If True, type issues are errors; if False, warnings.
        max_semantic_issues: Stop semantic testing after this many issues.
            Use 0 for unlimited.
        emit_diagnostics: Emit non-fatal spec diagnostics.
        paranoid: Deprecated; AST whitelist validation is always enforced.
        rng: Random generator for semantic testing. Random(42) if None.
        execute_untrusted_code: If True, execute task code in the restricted
            runner to obtain ``f`` for semantic validation.

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
        axes = StringRulesAxes()
    else:
        try:
            axes = _axes_adapter.validate_python(axes, strict=True)
        except ValidationError as e:
            err = e.errors()[0] if e.errors() else {}
            loc = err.get("loc", ())
            if isinstance(loc, tuple):
                loc_part = ".".join(str(part) for part in loc) or "value"
            elif isinstance(loc, list):
                loc_part = ".".join(str(part) for part in loc) or "value"
            else:
                loc_part = str(loc) if loc else "value"
            if loc_part == "value" and "charset" in str(e):
                loc_part = "charset"
            return [
                Issue(
                    code=CODE_AXES_INVALID,
                    severity=Severity.ERROR,
                    message=f"Invalid axes: {e}",
                    location=f"axes.{loc_part}",
                    task_id=task.task_id,
                )
            ]
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
            return issues

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

    if spec is not None and emit_diagnostics:
        issues.extend(_validate_rule_diagnostics(task, spec, axes, rng))

    return issues
