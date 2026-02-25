"""Tests for Rust rendering modules."""

import importlib.util
import random
import tempfile
from pathlib import Path
from typing import Any, Literal

import pytest
from helpers import (
    require_java_runtime,
    require_rust_runtime,
    run_checked_subprocess,
)

from genfxn.bitops.models import BitInstruction, BitOp, BitopsSpec
from genfxn.bitops.task import generate_bitops_task
from genfxn.core.models import Task
from genfxn.core.predicates import (
    PredicateAnd,
    PredicateEven,
    PredicateGe,
    PredicateGt,
    PredicateInSet,
    PredicateLe,
    PredicateLt,
    PredicateModEq,
    PredicateNot,
    PredicateOdd,
    PredicateOr,
)
from genfxn.core.safe_exec import execute_code_restricted
from genfxn.core.string_predicates import (
    StringPredicateAnd,
    StringPredicateContains,
    StringPredicateEndsWith,
    StringPredicateIsAlpha,
    StringPredicateIsDigit,
    StringPredicateIsLower,
    StringPredicateIsUpper,
    StringPredicateLengthCmp,
    StringPredicateNot,
    StringPredicateOr,
    StringPredicateStartsWith,
)
from genfxn.core.string_transforms import (
    StringTransformAppend,
    StringTransformCapitalize,
    StringTransformIdentity,
    StringTransformLowercase,
    StringTransformPipeline,
    StringTransformPrepend,
    StringTransformReplace,
    StringTransformReverse,
    StringTransformStrip,
    StringTransformSwapcase,
    StringTransformUppercase,
)
from genfxn.core.transforms import (
    TransformAbs,
    TransformClip,
    TransformIdentity,
    TransformNegate,
    TransformPipeline,
    TransformScale,
    TransformShift,
)
from genfxn.fsm.task import generate_fsm_task
from genfxn.graph_queries.models import (
    GraphEdge,
    GraphQueriesSpec,
    GraphQueryType,
)
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.intervals.models import BoundaryMode, IntervalsSpec, OperationType
from genfxn.intervals.task import generate_intervals_task
from genfxn.langs.rust._helpers import rust_i64_literal, rust_string_literal
from genfxn.langs.rust.expressions import render_expression_rust
from genfxn.langs.rust.graph_queries import render_graph_queries
from genfxn.langs.rust.intervals import (
    render_intervals as render_intervals_rust,
)
from genfxn.langs.rust.predicates import render_predicate_rust
from genfxn.langs.rust.string_predicates import render_string_predicate_rust
from genfxn.langs.rust.string_transforms import render_string_transform_rust
from genfxn.langs.rust.transforms import render_transform_rust
from genfxn.langs.types import Language
from genfxn.piecewise.models import ExprAbs, ExprAffine, ExprMod, ExprQuadratic
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.sequence_dp.task import generate_sequence_dp_task
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.temporal_logic.task import generate_temporal_logic_task


def _code_map(task: Task) -> dict[str, str]:
    assert isinstance(task.code, dict)
    return task.code


def seeded_rng(seed: int) -> random.Random:  # noqa: S311
    return random.Random(seed)


_ALLOWED_BUILTINS = {
    "abs": abs,
    "all": all,
    "any": any,
    "dict": dict,
    "enumerate": enumerate,
    "int": int,
    "isinstance": isinstance,
    "len": len,
    "list": list,
    "max": max,
    "min": min,
    "range": range,
    "set": set,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "zip": zip,
}


def _supports_stack_bytecode_rust() -> bool:
    return (
        importlib.util.find_spec("genfxn.stack_bytecode.task") is not None
        and importlib.util.find_spec("genfxn.langs.rust.stack_bytecode")
        is not None
    )


# ── Helpers ────────────────────────────────────────────────────────────


class TestRustStringLiteral:
    def test_simple(self) -> None:
        assert rust_string_literal("hello") == '"hello"'

    def test_escapes_backslash(self) -> None:
        assert rust_string_literal("a\\b") == '"a\\\\b"'

    def test_escapes_quote(self) -> None:
        assert rust_string_literal('say "hi"') == '"say \\"hi\\""'

    def test_escapes_newline(self) -> None:
        assert rust_string_literal("a\nb") == '"a\\nb"'

    def test_escapes_carriage_return(self) -> None:
        assert rust_string_literal("a\rb") == '"a\\rb"'

    def test_escapes_tab(self) -> None:
        assert rust_string_literal("a\tb") == '"a\\tb"'


class TestRustI64Literal:
    def test_small_i64(self) -> None:
        assert rust_i64_literal(123) == "123i64"

    def test_i64_min_uses_constant(self) -> None:
        assert rust_i64_literal(-(1 << 63)) == "i64::MIN"

    def test_i64_max_value(self) -> None:
        assert rust_i64_literal((1 << 63) - 1) == "9223372036854775807i64"

    def test_rejects_values_outside_i64_range(self) -> None:
        with pytest.raises(ValueError, match="signed 64-bit range"):
            rust_i64_literal(1 << 63)
        with pytest.raises(ValueError, match="signed 64-bit range"):
            rust_i64_literal(-(1 << 63) - 1)


# ── Predicates ─────────────────────────────────────────────────────────


class TestPredicateRust:
    def test_even(self) -> None:
        assert render_predicate_rust(PredicateEven()) == "x % 2 == 0"

    def test_odd(self) -> None:
        assert render_predicate_rust(PredicateOdd()) == "x % 2 != 0"

    def test_lt(self) -> None:
        assert render_predicate_rust(PredicateLt(value=5)) == "x < 5"

    def test_le(self) -> None:
        assert render_predicate_rust(PredicateLe(value=10)) == "x <= 10"

    def test_gt(self) -> None:
        assert render_predicate_rust(PredicateGt(value=-3)) == "x > -3"

    def test_ge(self) -> None:
        assert render_predicate_rust(PredicateGe(value=0)) == "x >= 0"

    def test_mod_eq_uses_rem_euclid(self) -> None:
        result = render_predicate_rust(PredicateModEq(divisor=3, remainder=1))
        assert result == "x.rem_euclid(3) == 1"

    def test_in_set(self) -> None:
        result = render_predicate_rust(
            PredicateInSet(values=frozenset({3, 1, 2}))
        )
        assert result == "[1, 2, 3].contains(&x)"

    def test_not(self) -> None:
        result = render_predicate_rust(PredicateNot(operand=PredicateEven()))
        assert result == "!(x % 2 == 0)"

    def test_and(self) -> None:
        result = render_predicate_rust(
            PredicateAnd(operands=[PredicateGt(value=0), PredicateLt(value=10)])
        )
        assert result == "(x > 0 && x < 10)"

    def test_or(self) -> None:
        result = render_predicate_rust(
            PredicateOr(operands=[PredicateEven(), PredicateGt(value=5)])
        )
        assert result == "(x % 2 == 0 || x > 5)"

    def test_custom_var(self) -> None:
        assert render_predicate_rust(PredicateEven(), var="n") == "n % 2 == 0"


class TestIntervalsRust:
    def test_wrapping_i64_arithmetic(self) -> None:
        spec = IntervalsSpec(
            operation=OperationType.TOTAL_COVERAGE,
            boundary_mode=BoundaryMode.OPEN_OPEN,
            merge_touching=True,
            endpoint_clip_abs=20,
            endpoint_quantize_step=1,
        )
        code = render_intervals_rust(spec)
        assert "hi.wrapping_sub(1)" in code
        assert "lo.wrapping_add(1)" in code
        assert "prev_end.wrapping_add(1)" in code
        assert "end.wrapping_sub(start).wrapping_add(1)" in code
        assert "end.wrapping_add(1)" in code
        assert "active = active.wrapping_add(*delta);" in code


class TestGraphQueriesRust:
    def test_shortest_path_cost_uses_saturating_i64_add(self) -> None:
        spec = GraphQueriesSpec(
            query_type=GraphQueryType.SHORTEST_PATH_COST,
            directed=True,
            weighted=True,
            n_nodes=3,
            edges=[
                GraphEdge(u=0, v=1, w=1),
                GraphEdge(u=1, v=2, w=2),
            ],
        )
        code = render_graph_queries(spec)
        assert "if cost > i64::MAX - weight" in code
        assert "i64::MAX" in code

    def test_rejects_invalid_edge_endpoints_at_runtime(self) -> None:
        spec = GraphQueriesSpec(
            query_type=GraphQueryType.MIN_HOPS,
            directed=True,
            weighted=False,
            n_nodes=2,
            edges=[GraphEdge(u=0, v=1, w=1)],
        )
        # Mutate post-validation to exercise runtime edge checks.
        spec.edges[0].v = 99

        code = render_graph_queries(spec)
        assert "if raw_u_i64 < 0" in code
        assert "|| raw_u_i64 >= n_nodes as i64" in code
        assert "|| raw_v_i64 < 0" in code
        assert "|| raw_v_i64 >= n_nodes as i64" in code
        assert (
            'panic!("edge endpoint out of range for '
            'n_nodes={}", n_nodes);' in code
        )


# ── Transforms ─────────────────────────────────────────────────────────


class TestTransformRust:
    def test_identity(self) -> None:
        assert render_transform_rust(TransformIdentity()) == "x"

    def test_abs(self) -> None:
        assert render_transform_rust(TransformAbs()) == "x.abs()"

    def test_shift_positive(self) -> None:
        assert render_transform_rust(TransformShift(offset=3)) == "x + 3"

    def test_shift_negative(self) -> None:
        assert render_transform_rust(TransformShift(offset=-5)) == "x - 5"

    def test_clip(self) -> None:
        result = render_transform_rust(TransformClip(low=-10, high=10))
        assert result == "x.max(-10).min(10)"

    def test_negate(self) -> None:
        assert render_transform_rust(TransformNegate()) == "-x"

    def test_scale(self) -> None:
        assert render_transform_rust(TransformScale(factor=2)) == "x * 2"

    def test_pipeline(self) -> None:
        pipe = TransformPipeline(
            steps=[TransformAbs(), TransformShift(offset=1)]
        )
        result = render_transform_rust(pipe)
        assert result == "(x.abs()) + 1"


# ── Expressions ────────────────────────────────────────────────────────


class TestExpressionRust:
    def test_affine_simple(self) -> None:
        assert render_expression_rust(ExprAffine(a=2, b=3)) == "2 * x + 3"

    def test_affine_identity(self) -> None:
        assert render_expression_rust(ExprAffine(a=1, b=0)) == "x"

    def test_affine_constant(self) -> None:
        assert render_expression_rust(ExprAffine(a=0, b=7)) == "7"

    def test_affine_negative_b(self) -> None:
        assert render_expression_rust(ExprAffine(a=1, b=-5)) == "x - 5"

    def test_quadratic(self) -> None:
        result = render_expression_rust(ExprQuadratic(a=1, b=-2, c=1))
        assert result == "x * x - 2 * x + 1"

    def test_abs_uses_method(self) -> None:
        result = render_expression_rust(ExprAbs(a=1, b=0))
        assert result == "x.abs()"

    def test_mod_uses_rem_euclid(self) -> None:
        result = render_expression_rust(ExprMod(divisor=3, a=1, b=0))
        assert result == "x.rem_euclid(3)"

    def test_mod_with_coeff(self) -> None:
        result = render_expression_rust(ExprMod(divisor=5, a=2, b=1))
        assert result == "2 * x.rem_euclid(5) + 1"


# ── String Predicates ──────────────────────────────────────────────────


class TestStringPredicateRust:
    def test_starts_with(self) -> None:
        result = render_string_predicate_rust(
            StringPredicateStartsWith(prefix="hello")
        )
        assert result == 's.starts_with("hello")'

    def test_ends_with(self) -> None:
        result = render_string_predicate_rust(
            StringPredicateEndsWith(suffix="world")
        )
        assert result == 's.ends_with("world")'

    def test_contains(self) -> None:
        result = render_string_predicate_rust(
            StringPredicateContains(substring="foo")
        )
        assert result == 's.contains("foo")'

    def test_is_alpha(self) -> None:
        result = render_string_predicate_rust(StringPredicateIsAlpha())
        assert result == "!s.is_empty() && s.chars().all(|c| c.is_alphabetic())"

    def test_is_digit(self) -> None:
        result = render_string_predicate_rust(StringPredicateIsDigit())
        assert result == (
            "!s.is_empty() && s.chars().all(&__genfxn_is_python_digit)"
        )

    def test_is_digit_uses_python_authoritative_digit_helper(self) -> None:
        result = render_string_predicate_rust(StringPredicateIsDigit())
        assert "__genfxn_is_python_digit" in result

    def test_is_upper(self) -> None:
        result = render_string_predicate_rust(StringPredicateIsUpper())
        assert "!s.is_empty()" in result
        assert "lower != upper" in result
        assert "lower == upper || c.is_uppercase()" in result

    def test_is_lower(self) -> None:
        result = render_string_predicate_rust(StringPredicateIsLower())
        assert "!s.is_empty()" in result
        assert "lower != upper" in result
        assert "lower == upper || c.is_lowercase()" in result

    @pytest.mark.parametrize(
        ("op", "expected_op"),
        [
            ("lt", "<"),
            ("le", "<="),
            ("gt", ">"),
            ("ge", ">="),
            ("eq", "=="),
        ],
    )
    def test_length_cmp(
        self,
        op: Literal["lt", "le", "gt", "ge", "eq"],
        expected_op: str,
    ) -> None:
        result = render_string_predicate_rust(
            StringPredicateLengthCmp(op=op, value=5)
        )
        assert result == f"s.chars().count() {expected_op} 5"

    def test_not(self) -> None:
        result = render_string_predicate_rust(
            StringPredicateNot(operand=StringPredicateIsAlpha())
        )
        assert "!(" in result

    def test_and(self) -> None:
        result = render_string_predicate_rust(
            StringPredicateAnd(
                operands=[
                    StringPredicateIsAlpha(),
                    StringPredicateLengthCmp(op="gt", value=3),
                ]
            )
        )
        assert "&&" in result

    def test_or(self) -> None:
        result = render_string_predicate_rust(
            StringPredicateOr(
                operands=[
                    StringPredicateStartsWith(prefix="a"),
                    StringPredicateEndsWith(suffix="z"),
                ]
            )
        )
        assert "||" in result


# ── String Transforms ──────────────────────────────────────────────────


class TestStringTransformRust:
    def test_identity(self) -> None:
        assert (
            render_string_transform_rust(StringTransformIdentity())
            == "s.to_string()"
        )

    def test_lowercase(self) -> None:
        assert (
            render_string_transform_rust(StringTransformLowercase())
            == "s.to_lowercase()"
        )

    def test_uppercase(self) -> None:
        assert (
            render_string_transform_rust(StringTransformUppercase())
            == "s.to_uppercase()"
        )

    def test_capitalize(self) -> None:
        result = render_string_transform_rust(StringTransformCapitalize())
        assert "match _chars.next()" in result
        assert "String::new()" in result
        assert "to_uppercase().collect::<String>()" in result
        assert "_chars.as_str().to_lowercase()" in result
        assert "[..1]" not in result
        assert "[1..]" not in result

    def test_swapcase(self) -> None:
        result = render_string_transform_rust(StringTransformSwapcase())
        assert "chars().flat_map(" in result
        assert "is_uppercase()" in result
        assert "to_lowercase()" in result
        assert "to_uppercase()" in result
        assert "to_ascii_lowercase()" not in result
        assert "to_ascii_uppercase()" not in result
        assert "collect::<String>()" in result

    def test_reverse(self) -> None:
        result = render_string_transform_rust(StringTransformReverse())
        assert result == "s.chars().rev().collect::<String>()"

    def test_replace(self) -> None:
        result = render_string_transform_rust(
            StringTransformReplace(old="a", new="b")
        )
        assert result == 's.replace("a", "b")'

    def test_strip_none(self) -> None:
        result = render_string_transform_rust(StringTransformStrip(chars=None))
        assert result == "s.trim().to_string()"

    def test_strip_chars(self) -> None:
        result = render_string_transform_rust(StringTransformStrip(chars="xy"))
        assert "trim_matches" in result
        assert '"xy"' in result
        assert ".contains(c)" in result
        assert ".to_string()" in result

    def test_prepend(self) -> None:
        result = render_string_transform_rust(
            StringTransformPrepend(prefix="hi_")
        )
        assert "format!" in result
        assert '"hi_"' in result

    def test_append(self) -> None:
        result = render_string_transform_rust(
            StringTransformAppend(suffix="_end")
        )
        assert "format!" in result
        assert '"_end"' in result

    def test_pipeline(self) -> None:
        pipe = StringTransformPipeline(
            steps=[
                StringTransformLowercase(),
                StringTransformReverse(),
            ]
        )
        result = render_string_transform_rust(pipe)
        assert "to_lowercase()" in result
        assert "chars().rev().collect::<String>()" in result


# ── Family Renderers ───────────────────────────────────────────────────


class TestPiecewiseRust:
    def test_renders_fn_signature(self) -> None:
        from genfxn.langs.rust.piecewise import render_piecewise
        from genfxn.piecewise.models import Branch, PiecewiseSpec

        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateGt(value=0),
                    expr=ExprAffine(a=2, b=0),
                )
            ],
            default_expr=ExprAffine(a=0, b=-1),
        )
        code = render_piecewise(spec)
        assert "fn f(x: i64) -> i64" in code
        assert "if x > 0 {" in code
        assert "2 * x" in code
        assert "-1" in code

    def test_no_branches(self) -> None:
        from genfxn.langs.rust.piecewise import render_piecewise
        from genfxn.piecewise.models import PiecewiseSpec

        spec = PiecewiseSpec(branches=[], default_expr=ExprAffine(a=1, b=0))
        code = render_piecewise(spec)
        assert "x" in code
        assert "if" not in code

    def test_multi_branch(self) -> None:
        from genfxn.langs.rust.piecewise import render_piecewise
        from genfxn.piecewise.models import Branch, PiecewiseSpec

        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateLt(value=-5),
                    expr=ExprAffine(a=0, b=0),
                ),
                Branch(
                    condition=PredicateGt(value=5),
                    expr=ExprAffine(a=0, b=1),
                ),
            ],
            default_expr=ExprAffine(a=1, b=0),
        )
        code = render_piecewise(spec)
        assert "if x < -5 {" in code
        assert "} else if x > 5 {" in code
        assert "} else {" in code

    def test_in_set_condition_uses_array_contains(self) -> None:
        from genfxn.langs.rust.piecewise import render_piecewise
        from genfxn.piecewise.models import Branch, PiecewiseSpec

        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateInSet(values=frozenset({1, 2})),
                    expr=ExprAffine(a=1, b=0),
                )
            ],
            default_expr=ExprAffine(a=0, b=0),
        )
        code = render_piecewise(spec)
        assert "[1, 2].contains(&x)" in code


class TestBitopsRust:
    def test_renders_fixed_width_operations(self) -> None:
        from genfxn.langs.rust.bitops import render_bitops

        spec = BitopsSpec(
            width_bits=8,
            operations=[
                BitInstruction(op=BitOp.SHR_LOGICAL, arg=3),
                BitInstruction(op=BitOp.ROTL, arg=9),
                BitInstruction(op=BitOp.POPCOUNT),
                BitInstruction(op=BitOp.PARITY),
            ],
        )
        code = render_bitops(spec)
        assert "fn f(x: i64) -> i64" in code
        assert "let mask: u64 = (1u64 << width_bits) - 1;" in code
        assert "arg.rem_euclid(width_bits as i64)" in code
        assert ">> amt" in code
        assert ".count_ones()" in code
        assert "& 1;" in code

    def test_custom_signature(self) -> None:
        from genfxn.langs.rust.bitops import render_bitops

        spec = BitopsSpec(
            width_bits=16,
            operations=[BitInstruction(op=BitOp.NOT)],
        )
        code = render_bitops(spec, func_name="g", var="n")
        assert "fn g(n: i64) -> i64" in code
        assert "value = (!value) & mask;" in code

    def test_renderer_only_includes_used_ops(self) -> None:
        from genfxn.langs.rust.bitops import render_bitops

        spec = BitopsSpec(
            width_bits=8,
            operations=[BitInstruction(op=BitOp.NOT)],
        )
        code = render_bitops(spec)
        assert 'if op == "not" {' in code
        assert 'op == "rotl"' not in code
        assert 'op == "parity"' not in code
        assert 'panic!("Unsupported op");' in code

    def test_renderer_deduplicates_ops_and_keeps_first_seen_order(self) -> None:
        from genfxn.bitops.render import render_bitops as render_bitops_python
        from genfxn.langs.java.bitops import render_bitops as render_bitops_java
        from genfxn.langs.rust.bitops import render_bitops

        spec = BitopsSpec(
            width_bits=8,
            operations=[
                BitInstruction(op=BitOp.XOR_MASK, arg=3),
                BitInstruction(op=BitOp.XOR_MASK, arg=7),
                BitInstruction(op=BitOp.SHL, arg=1),
            ],
        )
        code = render_bitops(spec)
        assert code.count('op == "xor_mask"') == 1
        assert code.count('op == "shl"') == 1
        assert code.index('if op == "xor_mask" {') < code.index(
            '} else if op == "shl" {'
        )

        python_code = render_bitops_python(spec, func_name="f")
        java_code = render_bitops_java(spec, func_name="f")
        rust_code = render_bitops(spec, func_name="f")

        python_f = _execute_python_code(python_code)
        javac, java = require_java_runtime()
        rustc = require_rust_runtime()

        for x in (0, 1, -1, 7, -13, 255):
            python_output = int(python_f(x))
            java_output = _run_java_code(javac, java, java_code, "bitops", x)
            rust_output = _run_rust_code(rustc, rust_code, "bitops", x)
            assert java_output == python_output
            assert rust_output == python_output
            assert java_output == rust_output


class TestStatefulRust:
    def test_conditional_linear_sum(self) -> None:
        from genfxn.langs.rust.stateful import render_stateful
        from genfxn.stateful.models import ConditionalLinearSumSpec

        spec = ConditionalLinearSumSpec(
            predicate=PredicateEven(),
            true_transform=TransformIdentity(),
            false_transform=TransformNegate(),
            init_value=0,
        )
        code = render_stateful(spec)
        assert "fn f(xs: &[i64]) -> i64" in code
        assert "for &x in xs" in code
        assert "x % 2 == 0" in code
        assert "-x" in code

    def test_longest_run(self) -> None:
        from genfxn.langs.rust.stateful import render_stateful
        from genfxn.stateful.models import LongestRunSpec

        spec = LongestRunSpec(match_predicate=PredicateGt(value=0))
        code = render_stateful(spec)
        assert "longest_run" in code
        assert "current_run" in code
        assert "longest_run.max(current_run)" in code

    def test_toggle_sum(self) -> None:
        from genfxn.langs.rust.stateful import render_stateful
        from genfxn.stateful.models import ToggleSumSpec

        spec = ToggleSumSpec(
            toggle_predicate=PredicateOdd(),
            on_transform=TransformIdentity(),
            off_transform=TransformAbs(),
            init_value=0,
        )
        code = render_stateful(spec)
        assert "let mut on = false" in code
        assert "on = !on" in code

    def test_resetting_best_prefix(self) -> None:
        from genfxn.langs.rust.stateful import render_stateful
        from genfxn.stateful.models import ResettingBestPrefixSumSpec

        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            value_transform=None,
            init_value=0,
        )
        code = render_stateful(spec)
        assert "best_sum" in code
        assert "current_sum" in code
        assert "best_sum.max(current_sum)" in code


class TestStringrulesRust:
    def test_basic_if_else(self) -> None:
        from genfxn.langs.rust.stringrules import render_stringrules
        from genfxn.stringrules.models import StringRule, StringRulesSpec

        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="a"),
                    transform=StringTransformUppercase(),
                )
            ],
            default_transform=StringTransformIdentity(),
        )
        code = render_stringrules(spec)
        assert "fn f(s: &str) -> String" in code
        assert 's.starts_with("a")' in code
        assert "s.to_uppercase()" in code
        assert "return s.to_uppercase();" in code

    def test_no_rules(self) -> None:
        from genfxn.langs.rust.stringrules import render_stringrules
        from genfxn.stringrules.models import StringRulesSpec

        spec = StringRulesSpec(
            rules=[],
            default_transform=StringTransformLowercase(),
        )
        code = render_stringrules(spec)
        assert "s.to_lowercase()" in code
        assert "if" not in code


class TestSimpleAlgorithmsRust:
    def test_most_frequent_smallest(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            MostFrequentSpec,
            TieBreakMode,
        )

        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
        )
        code = render_simple_algorithms(spec)
        assert "fn f(xs: &[i64]) -> i64" in code
        assert "HashMap<i64, i64>" in code
        assert "or_insert(0)" in code
        assert "candidates.iter().min()" in code

    def test_most_frequent_first_seen(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            MostFrequentSpec,
            TieBreakMode,
        )

        spec = MostFrequentSpec(
            tie_break=TieBreakMode.FIRST_SEEN,
            empty_default=0,
        )
        code = render_simple_algorithms(spec)
        assert "HashSet<i64>" in code
        assert "candidates.contains(&x)" in code

    def test_count_pairs_all_indices(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            CountingMode,
            CountPairsSumSpec,
        )

        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.ALL_INDICES,
        )
        code = render_simple_algorithms(spec)
        assert "x_i + x_j == 10" in code
        assert "count += 1" in code

    def test_count_pairs_unique(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            CountingMode,
            CountPairsSumSpec,
        )

        spec = CountPairsSumSpec(
            target=5,
            counting_mode=CountingMode.UNIQUE_VALUES,
        )
        code = render_simple_algorithms(spec)
        assert "seen_pairs" in code
        assert ".min(" in code
        assert ".max(" in code
        assert "as i64" in code

    def test_max_window_sum(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import MaxWindowSumSpec

        spec = MaxWindowSumSpec(k=3, invalid_k_default=0)
        code = render_simple_algorithms(spec)
        assert "window_sum" in code
        assert "max_sum" in code
        assert "max_sum.max(window_sum)" in code

    def test_preprocess_filter(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            MostFrequentSpec,
            TieBreakMode,
        )

        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
            pre_filter=PredicateGt(value=0),
        )
        code = render_simple_algorithms(spec)
        assert ".filter(" in code
        assert "_filtered" in code

    def test_preprocess_transform(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            MostFrequentSpec,
            TieBreakMode,
        )

        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
            pre_transform=TransformAbs(),
        )
        code = render_simple_algorithms(spec)
        assert ".map(" in code
        assert "_mapped" in code

    def test_preprocess_respects_custom_var(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            MostFrequentSpec,
            TieBreakMode,
        )

        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
            pre_filter=PredicateGt(value=0),
            pre_transform=TransformAbs(),
        )
        code = render_simple_algorithms(spec, var="vals")
        assert "fn f(vals: &[i64]) -> i64" in code
        assert "let vals = _filtered.as_slice();" in code
        assert "let vals = _mapped.as_slice();" in code
        assert "for &x in vals {" in code

    def test_edge_defaults_rendered(self) -> None:
        from genfxn.langs.rust.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            MostFrequentSpec,
            TieBreakMode,
        )

        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=-1,
            tie_default=99,
        )
        code = render_simple_algorithms(spec)
        assert "return -1;" in code
        assert "return 99;" in code
        assert "candidates.len() > 1" in code


# ── Integration Tests ──────────────────────────────────────────────────


def _execute_python_code(python_code: str) -> Any:
    """Execute Python code and return the function f."""
    namespace = execute_code_restricted(
        python_code,
        _ALLOWED_BUILTINS,
        trust_untrusted_code=True,
    )
    return namespace["f"]


def _parse_query_input_by_family(family: str, input_value: Any) -> Any:
    """Parse query input based on task family."""
    if family == "piecewise":
        return int(input_value)
    elif family in ("stateful", "fsm", "simple_algorithms", "temporal_logic"):
        if isinstance(input_value, (list, tuple)):
            return list(input_value)
        return input_value
    elif family == "stringrules":
        if isinstance(input_value, str):
            return input_value
        return str(input_value)
    elif family == "bitops":
        return int(input_value)
    elif family == "sequence_dp":
        if not isinstance(input_value, dict):
            raise TypeError("sequence_dp query input must be a dict")
        a_vals = input_value.get("a")
        b_vals = input_value.get("b")
        if not isinstance(a_vals, (list, tuple)) or not isinstance(
            b_vals, (list, tuple)
        ):
            raise TypeError(
                "sequence_dp query input must contain list/tuple fields"
            )
        return (list(a_vals), list(b_vals))
    elif family == "intervals":
        if not isinstance(input_value, list):
            raise TypeError("intervals query input must be a list")
        parsed: list[tuple[int, int]] = []
        for item in input_value:
            if (
                isinstance(item, (tuple, list))
                and len(item) == 2
                and isinstance(item[0], int)
                and isinstance(item[1], int)
            ):
                parsed.append((int(item[0]), int(item[1])))
            else:
                raise TypeError("intervals query input must contain int pairs")
        return parsed
    elif family == "graph_queries":
        if not isinstance(input_value, dict):
            raise TypeError("graph_queries query input must be a dict")
        src = input_value.get("src")
        dst = input_value.get("dst")
        if not isinstance(src, int) or not isinstance(dst, int):
            raise TypeError(
                "graph_queries query input must contain integer src/dst"
            )
        return (src, dst)
    elif family == "stack_bytecode":
        if isinstance(input_value, (list, tuple)):
            return list(input_value)
        return input_value
    else:
        return input_value


def _run_rust_code(
    rustc: str,
    code: str,
    family: str,
    query_input: Any,
) -> Any:
    """Execute Rust code and return the result."""
    payload = _family_payload(family, query_input)
    main_src = _build_rust_main_source(code, family, payload)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src_path = tmp / "main.rs"
        out = tmp / "main_bin"
        src_path.write_text(main_src, encoding="utf-8")
        run_checked_subprocess(
            [rustc, "--edition=2021", str(src_path), "-O", "-o", str(out)],
            cwd=tmp,
        )
        proc = run_checked_subprocess(
            [str(out)],
            cwd=tmp,
        )
        output = proc.stdout.strip()

        if family == "stack_bytecode":
            parts = output.split()
            if len(parts) != 2:
                raise ValueError(f"Expected 2 outputs, got: {output}")
            return (int(parts[0]), int(parts[1]))
        elif family == "stringrules":
            return output
        else:
            return int(output)


def _run_java_code(
    javac: str,
    java: str,
    code: str,
    family: str,
    query_input: Any,
) -> Any:
    """Execute Java code and return the result."""
    payload = _family_payload(family, query_input)
    main_src = _build_java_main_source(code, family, payload)

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        src_path = tmp / "Main.java"
        src_path.write_text(main_src, encoding="utf-8")
        run_checked_subprocess(
            [javac, str(src_path)],
            cwd=tmp,
        )
        proc = run_checked_subprocess(
            [java, "-cp", str(tmp), "Main"],
            cwd=tmp,
        )
        output = proc.stdout.strip()

        if family == "stringrules":
            return output
        else:
            return int(output)


def _sequence_payload(query_input: Any) -> dict[str, Any]:
    xs = list(query_input) if isinstance(query_input, list) else [query_input]
    return {"xs": xs}


def _family_payload(family: str, query_input: Any) -> dict[str, Any]:
    shared_sequence_families = {
        "stateful",
        "fsm",
        "simple_algorithms",
        "temporal_logic",
        "stack_bytecode",
    }
    if family in {"piecewise", "bitops"}:
        return {"x": int(query_input)}
    if family in shared_sequence_families:
        return _sequence_payload(query_input)
    if family == "stringrules":
        return {"s": str(query_input)}
    if family == "sequence_dp":
        a_vals, b_vals = query_input
        return {"a_vals": a_vals, "b_vals": b_vals}
    if family == "intervals":
        return {"intervals": query_input}
    if family == "graph_queries":
        src, dst = query_input
        return {"src": src, "dst": dst}
    raise ValueError(f"Unknown family: {family}")


def _build_rust_main_source(
    code: str, family: str, payload: dict[str, Any]
) -> str:
    xs_lit = ", ".join(f"{x}i64" for x in payload.get("xs", []))
    a_lit = ", ".join(f"{x}i64" for x in payload.get("a_vals", []))
    b_lit = ", ".join(f"{x}i64" for x in payload.get("b_vals", []))
    intervals_lit = ", ".join(
        f"({a}i64, {b}i64)" for a, b in payload.get("intervals", [])
    )
    builders = {
        "piecewise": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let x: i64 = {payload['x']}i64;\n"
            '    println!("{}", f(x));\n'
            "}\n"
        ),
        "stateful": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let xs: Vec<i64> = vec![{xs_lit}];\n"
            '    println!("{}", f(&xs));\n'
            "}\n"
        ),
        "fsm": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let xs: Vec<i64> = vec![{xs_lit}];\n"
            '    println!("{}", f(&xs));\n'
            "}\n"
        ),
        "simple_algorithms": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let xs: Vec<i64> = vec![{xs_lit}];\n"
            '    println!("{}", f(&xs));\n'
            "}\n"
        ),
        "temporal_logic": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let xs: Vec<i64> = vec![{xs_lit}];\n"
            '    println!("{}", f(&xs));\n'
            "}\n"
        ),
        "stringrules": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let s = {rust_string_literal(payload['s'])};\n"
            '    print!("{}", f(s));\n'
            "}\n"
        ),
        "bitops": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let x: i64 = {payload['x']}i64;\n"
            '    println!("{}", f(x));\n'
            "}\n"
        ),
        "sequence_dp": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let a: Vec<i64> = vec![{a_lit}];\n"
            f"    let b: Vec<i64> = vec![{b_lit}];\n"
            '    println!("{}", f(&a, &b));\n'
            "}\n"
        ),
        "intervals": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let intervals: Vec<(i64, i64)> = vec![{intervals_lit}];\n"
            '    println!("{}", f(&intervals));\n'
            "}\n"
        ),
        "graph_queries": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f'    println!("{{}}", f({payload["src"]}, {payload["dst"]}));\n'
            "}\n"
        ),
        "stack_bytecode": lambda: (
            f"{code}\n"
            "fn main() {\n"
            f"    let xs: Vec<i64> = vec![{xs_lit}];\n"
            "    let (status, value) = f(&xs);\n"
            '    println!("{} {}", status, value);\n'
            "}\n"
        ),
    }
    if family not in builders:
        raise ValueError(f"Unknown family: {family}")
    return builders[family]()


def _java_string_literal(value: str) -> str:
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
        .replace("\b", "\\b")
        .replace("\f", "\\f")
    )
    return f'"{escaped}"'


def _build_java_main_source(
    code: str, family: str, payload: dict[str, Any]
) -> str:
    xs_lit_int = ", ".join(str(x) for x in payload.get("xs", []))
    xs_lit_long = ", ".join(f"{x}L" for x in payload.get("xs", []))
    a_lit = ", ".join(f"{x}L" for x in payload.get("a_vals", []))
    b_lit = ", ".join(f"{x}L" for x in payload.get("b_vals", []))
    interval_rows = ", ".join(
        "{" + f"{a}L, {b}L" + "}" for a, b in payload.get("intervals", [])
    )
    builders = {
        "piecewise": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    long x = {payload['x']}L;\n"
            "    System.out.print(f(x));\n"
            "  }\n"
            "}\n"
        ),
        "stateful": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    long[] xs = new long[]{{{xs_lit_long}}};\n"
            "    System.out.print(f(xs));\n"
            "  }\n"
            "}\n"
        ),
        "fsm": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    int[] xs = new int[]{{{xs_lit_int}}};\n"
            "    System.out.print(f(xs));\n"
            "  }\n"
            "}\n"
        ),
        "simple_algorithms": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    long[] xs = new long[]{{{xs_lit_long}}};\n"
            "    System.out.print(f(xs));\n"
            "  }\n"
            "}\n"
        ),
        "temporal_logic": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    long[] xs = new long[]{{{xs_lit_long}}};\n"
            "    System.out.print(f(xs));\n"
            "  }\n"
            "}\n"
        ),
        "stringrules": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    String s = {_java_string_literal(payload['s'])};\n"
            "    System.out.print(f(s));\n"
            "  }\n"
            "}\n"
        ),
        "bitops": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    long x = {payload['x']}L;\n"
            "    System.out.print(f(x));\n"
            "  }\n"
            "}\n"
        ),
        "sequence_dp": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    long[] a = new long[]{{{a_lit}}};\n"
            f"    long[] b = new long[]{{{b_lit}}};\n"
            "    System.out.print(f(a, b));\n"
            "  }\n"
            "}\n"
        ),
        "intervals": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    long[][] intervals = new long[][]{{{interval_rows}}};\n"
            "    System.out.print(f(intervals));\n"
            "  }\n"
            "}\n"
        ),
        "graph_queries": lambda: (
            "public class Main {\n"
            f"{code}\n"
            "  public static void main(String[] args) {\n"
            f"    System.out.print(f({payload['src']}, {payload['dst']}));\n"
            "  }\n"
            "}\n"
        ),
    }
    if family not in builders:
        raise ValueError(f"Unknown family: {family}")
    return builders[family]()


def _expected_python_output(
    python_f: Any, family: str, query_input: Any
) -> Any:
    if family in ("sequence_dp", "graph_queries") and isinstance(
        query_input, tuple
    ):
        return python_f(*query_input)
    return python_f(query_input)


def _assert_rust_parity(task: Task, code: dict[str, str]) -> None:
    rustc = require_rust_runtime()
    python_f = _execute_python_code(code["python"])

    for query in task.queries:
        query_input = _parse_query_input_by_family(task.family, query.input)
        expected = _expected_python_output(python_f, task.family, query_input)
        actual = _run_rust_code(rustc, code["rust"], task.family, query_input)
        assert actual == expected, (
            f"Query input {query.input}: expected {expected}, got {actual}"
        )


class TestMultiLanguageRustGeneration:
    """Test that task generation with Rust produces valid output."""

    def test_piecewise_generates_rust(self) -> None:
        task = generate_piecewise_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(x: i64) -> i64" in code["rust"]

        _assert_rust_parity(task, code)

    def test_stateful_generates_rust(self) -> None:
        task = generate_stateful_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(xs: &[i64]) -> i64" in code["rust"]

        _assert_rust_parity(task, code)

    def test_stringrules_generates_rust(self) -> None:
        task = generate_stringrules_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(s: &str) -> String" in code["rust"]

        _assert_rust_parity(task, code)

    def test_simple_algorithms_generates_rust(self) -> None:
        task = generate_simple_algorithms_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(xs: &[i64]) -> i64" in code["rust"]

        _assert_rust_parity(task, code)

    def test_fsm_generates_rust(self) -> None:
        task = generate_fsm_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(xs: &[i64]) -> i64" in code["rust"]

        _assert_rust_parity(task, code)

    def test_bitops_generates_rust(self) -> None:
        task = generate_bitops_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(x: i64) -> i64" in code["rust"]

        _assert_rust_parity(task, code)

    def test_sequence_dp_generates_rust(self) -> None:
        task = generate_sequence_dp_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(a: &[i64], b: &[i64]) -> i64" in code["rust"]

        _assert_rust_parity(task, code)

    def test_intervals_generates_rust(self) -> None:
        task = generate_intervals_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(intervals: &[(i64, i64)]) -> i64" in code["rust"]

        _assert_rust_parity(task, code)

    def test_graph_queries_generates_rust(self) -> None:
        task = generate_graph_queries_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(" in code["rust"]

        _assert_rust_parity(task, code)

    def test_temporal_logic_generates_rust(self) -> None:
        task = generate_temporal_logic_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(xs: &[i64]) -> i64" in code["rust"]

        _assert_rust_parity(task, code)

    def test_stack_bytecode_generates_rust_when_available(self) -> None:
        if not _supports_stack_bytecode_rust():
            pytest.skip("stack_bytecode Rust rendering is not available")
        from genfxn.stack_bytecode.task import generate_stack_bytecode_task

        task = generate_stack_bytecode_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert "python" in code
        assert "rust" in code
        assert "def f(" in code["python"]
        assert "fn f(xs: &[i64]) -> (i64, i64)" in code["rust"]
        assert "return (" in code["rust"]

        _assert_rust_parity(task, code)

    def test_rust_only(self) -> None:
        task = generate_piecewise_task(
            rng=seeded_rng(42),
            languages=[Language.RUST],
        )
        assert "rust" in task.code
        assert "python" not in task.code

    def test_all_three_languages(self) -> None:
        task = generate_piecewise_task(
            rng=seeded_rng(42),
            languages=[Language.PYTHON, Language.JAVA, Language.RUST],
        )
        assert "python" in task.code
        assert "java" in task.code
        assert "rust" in task.code

        # Execute and compare outputs across all languages
        code = _code_map(task)
        rustc = require_rust_runtime()
        javac, java = require_java_runtime()
        python_f = _execute_python_code(code["python"])

        for query in task.queries:
            query_input = _parse_query_input_by_family(task.family, query.input)
            expected = python_f(query_input)
            rust_result = _run_rust_code(
                rustc, code["rust"], task.family, query_input
            )
            java_result = _run_java_code(
                javac, java, code["java"], task.family, query_input
            )
            assert rust_result == expected, (
                f"Rust: Query input {query.input}: "
                f"expected {expected}, got {rust_result}"
            )
            assert java_result == expected, (
                f"Java: Query input {query.input}: "
                f"expected {expected}, got {java_result}"
            )

    @pytest.mark.parametrize("seed", range(10))
    def test_piecewise_rust_renders_non_empty(self, seed: int) -> None:
        task = generate_piecewise_task(
            rng=seeded_rng(seed),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert len(code["rust"]) > 20

        _assert_rust_parity(task, code)

    @pytest.mark.parametrize("seed", range(10))
    def test_stateful_rust_renders_non_empty(self, seed: int) -> None:
        task = generate_stateful_task(
            rng=seeded_rng(seed),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert len(code["rust"]) > 20

        _assert_rust_parity(task, code)

    @pytest.mark.parametrize("seed", range(10))
    def test_stringrules_rust_renders_non_empty(self, seed: int) -> None:
        task = generate_stringrules_task(
            rng=seeded_rng(seed),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert len(code["rust"]) > 20

        _assert_rust_parity(task, code)

    @pytest.mark.parametrize("seed", range(10))
    def test_simple_algorithms_rust_renders_non_empty(self, seed: int) -> None:
        task = generate_simple_algorithms_task(
            rng=seeded_rng(seed),
            languages=[Language.PYTHON, Language.RUST],
        )
        code = _code_map(task)
        assert len(code["rust"]) > 20

        _assert_rust_parity(task, code)


# ── Registry Tests ─────────────────────────────────────────────────────


class TestRustRegistry:
    def test_language_enum_has_rust(self) -> None:
        assert Language.RUST.value == "rust"

    def test_registry_rust_all_families(self) -> None:
        from genfxn.langs.registry import get_render_fn

        families = [
            "bitops",
            "graph_queries",
            "intervals",
            "sequence_dp",
            "temporal_logic",
            "piecewise",
            "stateful",
            "simple_algorithms",
            "stringrules",
        ]
        if _supports_stack_bytecode_rust():
            families.append("stack_bytecode")
        families.append("fsm")
        for family in families:
            fn = get_render_fn(Language.RUST, family)
            assert callable(fn)

    def test_registry_graph_queries(self) -> None:
        from genfxn.langs.registry import get_render_fn

        assert callable(get_render_fn(Language.PYTHON, "graph_queries"))
        assert callable(get_render_fn(Language.JAVA, "graph_queries"))
        assert callable(get_render_fn(Language.RUST, "graph_queries"))

    def test_registry_temporal_logic(self) -> None:
        from genfxn.langs.registry import get_render_fn

        assert callable(get_render_fn(Language.PYTHON, "temporal_logic"))
        assert callable(get_render_fn(Language.JAVA, "temporal_logic"))
        assert callable(get_render_fn(Language.RUST, "temporal_logic"))

    def test_available_languages_includes_rust(self) -> None:
        from genfxn.langs.render import _available_languages

        available = _available_languages()
        assert Language.RUST in available

    def test_render_all_languages_includes_rust(self) -> None:
        from genfxn.langs.render import render_all_languages
        from genfxn.piecewise.models import Branch, PiecewiseSpec

        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateGt(value=0),
                    expr=ExprAffine(a=1, b=0),
                )
            ],
            default_expr=ExprAffine(a=0, b=0),
        )
        result = render_all_languages("piecewise", spec)
        assert "python" in result
        assert "java" in result
        assert "rust" in result
        assert "fn f(" in result["rust"]

    def test_render_all_languages_custom_selection_and_func_name(self) -> None:
        from genfxn.langs.render import render_all_languages
        from genfxn.piecewise.models import Branch, PiecewiseSpec

        spec = PiecewiseSpec(
            branches=[
                Branch(
                    condition=PredicateGt(value=0),
                    expr=ExprAffine(a=1, b=0),
                )
            ],
            default_expr=ExprAffine(a=0, b=0),
        )
        result = render_all_languages(
            "piecewise",
            spec,
            languages=[Language.RUST],
            func_name="g",
        )
        assert list(result.keys()) == ["rust"]
        assert "fn g(x: i64) -> i64" in result["rust"]

    def test_render_all_languages_stack_bytecode_when_available(self) -> None:
        if not _supports_stack_bytecode_rust():
            pytest.skip("stack_bytecode Rust rendering is not available")
        from genfxn.langs.render import render_all_languages
        from genfxn.stack_bytecode.models import (
            Instruction,
            InstructionOp,
            StackBytecodeSpec,
        )

        spec = StackBytecodeSpec(
            program=[
                Instruction(op=InstructionOp.PUSH_CONST, value=1),
                Instruction(op=InstructionOp.HALT),
            ]
        )
        result = render_all_languages(
            "stack_bytecode",
            spec,
            languages=[Language.PYTHON, Language.RUST],
        )
        assert "python" in result
        assert "rust" in result
