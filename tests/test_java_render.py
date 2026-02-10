"""Tests for Java rendering modules."""

import importlib.util
import random
from typing import Literal

import pytest

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
from genfxn.graph_queries.task import generate_graph_queries_task
from genfxn.intervals.task import generate_intervals_task
from genfxn.langs.java._helpers import (
    _regex_char_class_escape,
    java_string_literal,
)
from genfxn.langs.java.expressions import render_expression_java
from genfxn.langs.java.predicates import render_predicate_java
from genfxn.langs.java.string_predicates import render_string_predicate_java
from genfxn.langs.java.string_transforms import render_string_transform_java
from genfxn.langs.java.transforms import render_transform_java
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


def _supports_stack_bytecode_java() -> bool:
    return (
        importlib.util.find_spec("genfxn.stack_bytecode.task") is not None
        and importlib.util.find_spec("genfxn.langs.java.stack_bytecode")
        is not None
    )


# ── Helpers ────────────────────────────────────────────────────────────


class TestJavaStringLiteral:
    def test_simple(self) -> None:
        assert java_string_literal("hello") == '"hello"'

    def test_escapes_backslash(self) -> None:
        assert java_string_literal("a\\b") == '"a\\\\b"'

    def test_escapes_quote(self) -> None:
        assert java_string_literal('say "hi"') == '"say \\"hi\\""'

    def test_escapes_newline(self) -> None:
        assert java_string_literal("a\nb") == '"a\\nb"'

    def test_escapes_carriage_return(self) -> None:
        assert java_string_literal("a\rb") == '"a\\rb"'

    def test_escapes_tab(self) -> None:
        assert java_string_literal("a\tb") == '"a\\tb"'


class TestRegexCharClassEscape:
    def test_no_specials(self) -> None:
        assert _regex_char_class_escape("abc") == "abc"

    def test_bracket(self) -> None:
        assert _regex_char_class_escape("]") == "\\]"

    def test_backslash(self) -> None:
        assert _regex_char_class_escape("\\") == "\\\\"

    def test_caret_and_dash(self) -> None:
        assert _regex_char_class_escape("^-") == "\\^\\-"


# ── Predicates ─────────────────────────────────────────────────────────


class TestPredicateJava:
    def test_even(self) -> None:
        assert render_predicate_java(PredicateEven()) == "x % 2 == 0"

    def test_odd(self) -> None:
        # Java modulo fix: != 0 instead of == 1
        assert render_predicate_java(PredicateOdd()) == "x % 2 != 0"

    def test_lt(self) -> None:
        assert render_predicate_java(PredicateLt(value=5)) == "x < 5"

    def test_le(self) -> None:
        assert render_predicate_java(PredicateLe(value=10)) == "x <= 10"

    def test_gt(self) -> None:
        assert render_predicate_java(PredicateGt(value=-3)) == "x > -3"

    def test_ge(self) -> None:
        assert render_predicate_java(PredicateGe(value=0)) == "x >= 0"

    def test_mod_eq_uses_floor_mod(self) -> None:
        result = render_predicate_java(PredicateModEq(divisor=3, remainder=1))
        assert result == "Math.floorMod(x, 3) == 1"

    def test_in_set(self) -> None:
        result = render_predicate_java(
            PredicateInSet(values=frozenset({3, 1, 2}))
        )
        assert result == "(x == 1 || x == 2 || x == 3)"

    def test_not(self) -> None:
        result = render_predicate_java(PredicateNot(operand=PredicateEven()))
        assert result == "!(x % 2 == 0)"

    def test_and(self) -> None:
        result = render_predicate_java(
            PredicateAnd(operands=[PredicateGt(value=0), PredicateLt(value=10)])
        )
        assert result == "(x > 0 && x < 10)"

    def test_or(self) -> None:
        result = render_predicate_java(
            PredicateOr(operands=[PredicateEven(), PredicateGt(value=5)])
        )
        assert result == "(x % 2 == 0 || x > 5)"

    def test_custom_var(self) -> None:
        assert render_predicate_java(PredicateEven(), var="n") == "n % 2 == 0"


# ── Transforms ─────────────────────────────────────────────────────────


class TestTransformJava:
    def test_identity(self) -> None:
        assert render_transform_java(TransformIdentity()) == "x"

    def test_abs(self) -> None:
        assert render_transform_java(TransformAbs()) == "Math.abs(x)"

    def test_shift_positive(self) -> None:
        assert render_transform_java(TransformShift(offset=3)) == "x + 3"

    def test_shift_negative(self) -> None:
        assert render_transform_java(TransformShift(offset=-5)) == "x - 5"

    def test_clip(self) -> None:
        result = render_transform_java(TransformClip(low=-10, high=10))
        assert result == "Math.max(-10, Math.min(10, x))"

    def test_negate(self) -> None:
        assert render_transform_java(TransformNegate()) == "-x"

    def test_scale(self) -> None:
        assert render_transform_java(TransformScale(factor=2)) == "x * 2"

    def test_pipeline(self) -> None:
        pipe = TransformPipeline(
            steps=[TransformAbs(), TransformShift(offset=1)]
        )
        result = render_transform_java(pipe)
        assert result == "(Math.abs(x)) + 1"


# ── Expressions ────────────────────────────────────────────────────────


class TestExpressionJava:
    def test_affine_simple(self) -> None:
        assert render_expression_java(ExprAffine(a=2, b=3)) == "2 * x + 3"

    def test_affine_identity(self) -> None:
        assert render_expression_java(ExprAffine(a=1, b=0)) == "x"

    def test_affine_constant(self) -> None:
        assert render_expression_java(ExprAffine(a=0, b=7)) == "7"

    def test_affine_negative_b(self) -> None:
        assert render_expression_java(ExprAffine(a=1, b=-5)) == "x - 5"

    def test_quadratic(self) -> None:
        result = render_expression_java(ExprQuadratic(a=1, b=-2, c=1))
        assert result == "x * x - 2 * x + 1"

    def test_abs_uses_math(self) -> None:
        result = render_expression_java(ExprAbs(a=1, b=0))
        assert result == "Math.abs(x)"

    def test_mod_uses_floor_mod(self) -> None:
        result = render_expression_java(ExprMod(divisor=3, a=1, b=0))
        assert result == "Math.floorMod(x, 3)"

    def test_mod_with_coeff(self) -> None:
        result = render_expression_java(ExprMod(divisor=5, a=2, b=1))
        assert result == "2 * Math.floorMod(x, 5) + 1"


# ── String Predicates ──────────────────────────────────────────────────


class TestStringPredicateJava:
    def test_starts_with(self) -> None:
        result = render_string_predicate_java(
            StringPredicateStartsWith(prefix="hello")
        )
        assert result == 's.startsWith("hello")'

    def test_ends_with(self) -> None:
        result = render_string_predicate_java(
            StringPredicateEndsWith(suffix="world")
        )
        assert result == 's.endsWith("world")'

    def test_contains(self) -> None:
        result = render_string_predicate_java(
            StringPredicateContains(substring="foo")
        )
        assert result == 's.contains("foo")'

    def test_is_alpha(self) -> None:
        result = render_string_predicate_java(StringPredicateIsAlpha())
        assert result == (
            "!s.isEmpty() && s.chars().allMatch(Character::isLetter)"
        )

    def test_is_digit(self) -> None:
        result = render_string_predicate_java(StringPredicateIsDigit())
        assert result == (
            "!s.isEmpty() && s.chars().allMatch(Character::isDigit)"
        )

    def test_is_upper(self) -> None:
        result = render_string_predicate_java(StringPredicateIsUpper())
        assert result == (
            "!s.isEmpty() && s.chars().anyMatch(Character::isLetter) && "
            "s.equals(s.toUpperCase(java.util.Locale.ROOT))"
        )

    def test_is_lower(self) -> None:
        result = render_string_predicate_java(StringPredicateIsLower())
        assert result == (
            "!s.isEmpty() && s.chars().anyMatch(Character::isLetter) && "
            "s.equals(s.toLowerCase(java.util.Locale.ROOT))"
        )

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
        result = render_string_predicate_java(
            StringPredicateLengthCmp(op=op, value=5)
        )
        assert result == f"s.length() {expected_op} 5"

    def test_not(self) -> None:
        result = render_string_predicate_java(
            StringPredicateNot(operand=StringPredicateIsAlpha())
        )
        assert "!(" in result

    def test_and(self) -> None:
        result = render_string_predicate_java(
            StringPredicateAnd(
                operands=[
                    StringPredicateIsAlpha(),
                    StringPredicateLengthCmp(op="gt", value=3),
                ]
            )
        )
        assert "&&" in result

    def test_or(self) -> None:
        result = render_string_predicate_java(
            StringPredicateOr(
                operands=[
                    StringPredicateStartsWith(prefix="a"),
                    StringPredicateEndsWith(suffix="z"),
                ]
            )
        )
        assert "||" in result


# ── String Transforms ──────────────────────────────────────────────────


class TestStringTransformJava:
    def test_identity(self) -> None:
        assert render_string_transform_java(StringTransformIdentity()) == "s"

    def test_lowercase(self) -> None:
        assert (
            render_string_transform_java(StringTransformLowercase())
            == "s.toLowerCase(java.util.Locale.ROOT)"
        )

    def test_uppercase(self) -> None:
        assert (
            render_string_transform_java(StringTransformUppercase())
            == "s.toUpperCase(java.util.Locale.ROOT)"
        )

    def test_capitalize(self) -> None:
        result = render_string_transform_java(StringTransformCapitalize())
        assert "substring(0, 1).toUpperCase(java.util.Locale.ROOT)" in result
        assert "isEmpty()" in result

    def test_swapcase(self) -> None:
        result = render_string_transform_java(StringTransformSwapcase())
        assert "codePoints()" in result
        assert "Character.isUpperCase" in result

    def test_reverse(self) -> None:
        result = render_string_transform_java(StringTransformReverse())
        assert result == "new StringBuilder(s).reverse().toString()"

    def test_replace(self) -> None:
        result = render_string_transform_java(
            StringTransformReplace(old="a", new="b")
        )
        assert result == 's.replace("a", "b")'

    def test_strip_none(self) -> None:
        result = render_string_transform_java(StringTransformStrip(chars=None))
        assert result == "s.strip()"

    def test_strip_empty_chars(self) -> None:
        result = render_string_transform_java(StringTransformStrip(chars=""))
        assert result == "s"

    def test_strip_chars(self) -> None:
        result = render_string_transform_java(StringTransformStrip(chars="xy"))
        assert "replaceAll" in result
        assert "xy" in result

    def test_strip_chars_escapes_java_string_literal(self) -> None:
        chars = '"]'
        escaped = _regex_char_class_escape(chars)
        pattern = f"^[{escaped}]+|[{escaped}]+$"
        result = render_string_transform_java(StringTransformStrip(chars=chars))
        assert result == f's.replaceAll({java_string_literal(pattern)}, "")'

    def test_prepend(self) -> None:
        result = render_string_transform_java(
            StringTransformPrepend(prefix="hi_")
        )
        assert result == '"hi_" + s'

    def test_append(self) -> None:
        result = render_string_transform_java(
            StringTransformAppend(suffix="_end")
        )
        assert result == 's + "_end"'

    def test_pipeline(self) -> None:
        pipe = StringTransformPipeline(
            steps=[
                StringTransformLowercase(),
                StringTransformReverse(),
            ]
        )
        result = render_string_transform_java(pipe)
        assert "toLowerCase(java.util.Locale.ROOT)" in result
        assert "StringBuilder" in result


# ── Family Renderers ───────────────────────────────────────────────────


class TestPiecewiseJava:
    def test_renders_method_signature(self) -> None:
        from genfxn.langs.java.piecewise import render_piecewise
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
        assert "public static int f(int x)" in code
        assert "if (x > 0)" in code
        assert "return 2 * x;" in code
        assert "return -1;" in code

    def test_no_branches(self) -> None:
        from genfxn.langs.java.piecewise import render_piecewise
        from genfxn.piecewise.models import PiecewiseSpec

        spec = PiecewiseSpec(branches=[], default_expr=ExprAffine(a=1, b=0))
        code = render_piecewise(spec)
        assert "return x;" in code
        assert "if" not in code

    def test_multi_branch(self) -> None:
        from genfxn.langs.java.piecewise import render_piecewise
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
        assert "if (x < -5)" in code
        assert "} else if (x > 5)" in code
        assert "} else {" in code

    def test_in_set_condition_uses_or_comparisons(self) -> None:
        from genfxn.langs.java.piecewise import render_piecewise
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
        assert "(x == 1 || x == 2)" in code


class TestBitopsJava:
    def test_renders_fixed_width_operations(self) -> None:
        from genfxn.langs.java.bitops import render_bitops

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
        assert "public static long f(long x)" in code
        assert "long mask = widthBits == 64 ? -1L" in code
        assert "Math.floorMod(arg, (long) widthBits)" in code
        assert ">>> amt" in code
        assert "Long.bitCount" in code
        assert "& 1" in code

    def test_custom_signature(self) -> None:
        from genfxn.langs.java.bitops import render_bitops

        spec = BitopsSpec(
            width_bits=16,
            operations=[BitInstruction(op=BitOp.NOT)],
        )
        code = render_bitops(spec, func_name="g", var="n")
        assert "public static long g(long n)" in code
        assert "value = (~value) & mask;" in code


class TestStatefulJava:
    def test_conditional_linear_sum(self) -> None:
        from genfxn.langs.java.stateful import render_stateful
        from genfxn.stateful.models import ConditionalLinearSumSpec

        spec = ConditionalLinearSumSpec(
            predicate=PredicateEven(),
            true_transform=TransformIdentity(),
            false_transform=TransformNegate(),
            init_value=0,
        )
        code = render_stateful(spec)
        assert "public static int f(int[] xs)" in code
        assert "for (int x : xs)" in code
        assert "x % 2 == 0" in code
        assert "-x" in code

    def test_longest_run(self) -> None:
        from genfxn.langs.java.stateful import render_stateful
        from genfxn.stateful.models import LongestRunSpec

        spec = LongestRunSpec(match_predicate=PredicateGt(value=0))
        code = render_stateful(spec)
        assert "longest_run" in code
        assert "current_run" in code
        assert "Math.max" in code

    def test_toggle_sum(self) -> None:
        from genfxn.langs.java.stateful import render_stateful
        from genfxn.stateful.models import ToggleSumSpec

        spec = ToggleSumSpec(
            toggle_predicate=PredicateOdd(),
            on_transform=TransformIdentity(),
            off_transform=TransformAbs(),
            init_value=0,
        )
        code = render_stateful(spec)
        assert "boolean on = false" in code
        assert "on = !on" in code

    def test_resetting_best_prefix(self) -> None:
        from genfxn.langs.java.stateful import render_stateful
        from genfxn.stateful.models import ResettingBestPrefixSumSpec

        spec = ResettingBestPrefixSumSpec(
            reset_predicate=PredicateLt(value=0),
            value_transform=None,
            init_value=0,
        )
        code = render_stateful(spec)
        assert "best_sum" in code
        assert "current_sum" in code


class TestStringrulesJava:
    def test_basic_if_else(self) -> None:
        from genfxn.langs.java.stringrules import render_stringrules
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
        assert "public static String f(String s)" in code
        assert 's.startsWith("a")' in code
        assert "s.toUpperCase(java.util.Locale.ROOT)" in code
        assert "} else {" in code

    def test_no_rules(self) -> None:
        from genfxn.langs.java.stringrules import render_stringrules
        from genfxn.stringrules.models import StringRulesSpec

        spec = StringRulesSpec(
            rules=[],
            default_transform=StringTransformLowercase(),
        )
        code = render_stringrules(spec)
        assert "return s.toLowerCase(java.util.Locale.ROOT);" in code
        assert "if" not in code


class TestSimpleAlgorithmsJava:
    def test_most_frequent_smallest(self) -> None:
        from genfxn.langs.java.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            MostFrequentSpec,
            TieBreakMode,
        )

        spec = MostFrequentSpec(
            tie_break=TieBreakMode.SMALLEST,
            empty_default=0,
        )
        code = render_simple_algorithms(spec)
        assert "public static int f(int[] xs)" in code
        assert "HashMap<Integer, Integer>" in code
        assert "getOrDefault" in code
        assert "Collections.min" in code

    def test_most_frequent_first_seen(self) -> None:
        from genfxn.langs.java.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            MostFrequentSpec,
            TieBreakMode,
        )

        spec = MostFrequentSpec(
            tie_break=TieBreakMode.FIRST_SEEN,
            empty_default=0,
        )
        code = render_simple_algorithms(spec)
        assert "HashSet<Integer>" in code
        assert "candidates.contains(x)" in code

    def test_count_pairs_all_indices(self) -> None:
        from genfxn.langs.java.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import (
            CountingMode,
            CountPairsSumSpec,
        )

        spec = CountPairsSumSpec(
            target=10,
            counting_mode=CountingMode.ALL_INDICES,
        )
        code = render_simple_algorithms(spec)
        assert "xs[i] + xs[j] == 10" in code
        assert "count += 1" in code

    def test_count_pairs_unique(self) -> None:
        from genfxn.langs.java.simple_algorithms import render_simple_algorithms
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
        assert "Math.min" in code
        assert "Math.max" in code

    def test_max_window_sum(self) -> None:
        from genfxn.langs.java.simple_algorithms import render_simple_algorithms
        from genfxn.simple_algorithms.models import MaxWindowSumSpec

        spec = MaxWindowSumSpec(k=3, invalid_k_default=0)
        code = render_simple_algorithms(spec)
        assert "window_sum" in code
        assert "max_sum" in code
        assert "Math.max" in code

    def test_preprocess_filter(self) -> None:
        from genfxn.langs.java.simple_algorithms import render_simple_algorithms
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
        assert "Arrays.stream" in code
        assert "filter" in code

    def test_preprocess_transform(self) -> None:
        from genfxn.langs.java.simple_algorithms import render_simple_algorithms
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
        assert "Arrays.stream" in code
        assert "map" in code

    def test_edge_defaults_rendered(self) -> None:
        from genfxn.langs.java.simple_algorithms import render_simple_algorithms
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
        assert "candidates.size() > 1" in code


# ── Integration Tests ──────────────────────────────────────────────────


class TestMultiLanguageGeneration:
    """Test that task generation with Java produces valid output."""

    def test_piecewise_generates_java(self) -> None:
        task = generate_piecewise_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert code["python"].startswith("def f(")
        assert "public static int f(int x)" in code["java"]

    def test_stateful_generates_java(self) -> None:
        task = generate_stateful_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static int f(int[] xs)" in code["java"]

    def test_stringrules_generates_java(self) -> None:
        task = generate_stringrules_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static String f(String s)" in code["java"]

    def test_simple_algorithms_generates_java(self) -> None:
        task = generate_simple_algorithms_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static int f(int[] xs)" in code["java"]

    def test_fsm_generates_java(self) -> None:
        task = generate_fsm_task(
            rng=random.Random(42),  # noqa: S311
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static int f(int[] xs)" in code["java"]

    def test_bitops_generates_java(self) -> None:
        task = generate_bitops_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static long f(long x)" in code["java"]

    def test_sequence_dp_generates_java(self) -> None:
        task = generate_sequence_dp_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static long f(long[] a, long[] b)" in code["java"]

    def test_intervals_generates_java(self) -> None:
        task = generate_intervals_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static long f(long[][] intervals)" in code["java"]

    def test_graph_queries_generates_java(self) -> None:
        task = generate_graph_queries_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static" in code["java"]

    def test_temporal_logic_generates_java(self) -> None:
        task = generate_temporal_logic_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static long f(long[] xs)" in code["java"]

    def test_stack_bytecode_generates_java_when_available(self) -> None:
        if not _supports_stack_bytecode_java():
            pytest.skip("stack_bytecode Java rendering is not available")
        from genfxn.stack_bytecode.task import generate_stack_bytecode_task

        task = generate_stack_bytecode_task(
            rng=random.Random(42),
            languages=[Language.PYTHON, Language.JAVA],
        )
        code = _code_map(task)
        assert "python" in code
        assert "java" in code
        assert "def f(" in code["python"]
        assert "public static int[] f(int[] xs)" in code["java"]
        assert "return new int[] {" in code["java"]

    def test_python_only(self) -> None:
        task = generate_piecewise_task(
            rng=random.Random(42),
            languages=[Language.PYTHON],
        )
        assert "python" in task.code
        assert "java" not in task.code

    def test_piecewise_rejects_empty_languages(self) -> None:
        with pytest.raises(ValueError, match="languages list is empty"):
            generate_piecewise_task(rng=random.Random(42), languages=[])

    def test_stateful_rejects_empty_languages(self) -> None:
        with pytest.raises(ValueError, match="languages list is empty"):
            generate_stateful_task(rng=random.Random(42), languages=[])

    def test_stringrules_rejects_empty_languages(self) -> None:
        with pytest.raises(ValueError, match="languages list is empty"):
            generate_stringrules_task(rng=random.Random(42), languages=[])

    def test_simple_algorithms_rejects_empty_languages(self) -> None:
        with pytest.raises(ValueError, match="languages list is empty"):
            generate_simple_algorithms_task(
                rng=random.Random(42), languages=[]
            )

    def test_sequence_dp_rejects_empty_languages(self) -> None:
        with pytest.raises(ValueError, match="languages list is empty"):
            generate_sequence_dp_task(rng=random.Random(42), languages=[])

    def test_intervals_rejects_empty_languages(self) -> None:
        with pytest.raises(ValueError, match="languages list is empty"):
            generate_intervals_task(rng=random.Random(42), languages=[])

    def test_graph_queries_rejects_empty_languages(self) -> None:
        with pytest.raises(ValueError, match="languages list is empty"):
            generate_graph_queries_task(rng=random.Random(42), languages=[])

    def test_temporal_logic_rejects_empty_languages(self) -> None:
        with pytest.raises(ValueError, match="languages list is empty"):
            generate_temporal_logic_task(rng=random.Random(42), languages=[])

    @pytest.mark.parametrize("seed", range(10))
    def test_piecewise_java_renders_non_empty(self, seed: int) -> None:
        task = generate_piecewise_task(
            rng=random.Random(seed),
            languages=[Language.JAVA],
        )
        code = _code_map(task)
        assert len(code["java"]) > 20

    @pytest.mark.parametrize("seed", range(10))
    def test_stateful_java_renders_non_empty(self, seed: int) -> None:
        task = generate_stateful_task(
            rng=random.Random(seed),
            languages=[Language.JAVA],
        )
        code = _code_map(task)
        assert len(code["java"]) > 20

    @pytest.mark.parametrize("seed", range(10))
    def test_stringrules_java_renders_non_empty(self, seed: int) -> None:
        task = generate_stringrules_task(
            rng=random.Random(seed),
            languages=[Language.JAVA],
        )
        code = _code_map(task)
        assert len(code["java"]) > 20

    @pytest.mark.parametrize("seed", range(10))
    def test_simple_algorithms_java_renders_non_empty(self, seed: int) -> None:
        task = generate_simple_algorithms_task(
            rng=random.Random(seed),
            languages=[Language.JAVA],
        )
        code = _code_map(task)
        assert len(code["java"]) > 20


# ── Registry / Render Dispatcher Tests ─────────────────────────────────


class TestLangsInfra:
    def test_language_enum(self) -> None:
        assert Language.PYTHON.value == "python"
        assert Language.JAVA.value == "java"

    def test_registry_python(self) -> None:
        from genfxn.langs.registry import get_render_fn

        fn = get_render_fn(Language.PYTHON, "piecewise")
        assert callable(fn)

    def test_registry_java(self) -> None:
        from genfxn.langs.registry import get_render_fn

        fn = get_render_fn(Language.JAVA, "piecewise")
        assert callable(fn)

    def test_registry_java_bitops(self) -> None:
        from genfxn.langs.registry import get_render_fn

        fn = get_render_fn(Language.JAVA, "bitops")
        assert callable(fn)

    def test_registry_unknown_family_raises(self) -> None:
        from genfxn.langs.registry import get_render_fn

        with pytest.raises(ValueError, match="Unsupported family"):
            get_render_fn(Language.PYTHON, "nonexistent")

    def test_registry_rust(self) -> None:
        from genfxn.langs.registry import get_render_fn

        fn = get_render_fn(Language.RUST, "piecewise")
        assert callable(fn)

    def test_registry_stack_bytecode_when_available(self) -> None:
        if not _supports_stack_bytecode_java():
            pytest.skip("stack_bytecode Java rendering is not available")
        from genfxn.langs.registry import get_render_fn

        assert callable(get_render_fn(Language.PYTHON, "stack_bytecode"))
        assert callable(get_render_fn(Language.JAVA, "stack_bytecode"))

    def test_registry_fsm(self) -> None:
        from genfxn.langs.registry import get_render_fn

        assert callable(get_render_fn(Language.PYTHON, "fsm"))
        assert callable(get_render_fn(Language.JAVA, "fsm"))

    def test_registry_sequence_dp(self) -> None:
        from genfxn.langs.registry import get_render_fn

        assert callable(get_render_fn(Language.PYTHON, "sequence_dp"))
        assert callable(get_render_fn(Language.JAVA, "sequence_dp"))
        assert callable(get_render_fn(Language.RUST, "sequence_dp"))

    def test_registry_intervals(self) -> None:
        from genfxn.langs.registry import get_render_fn

        assert callable(get_render_fn(Language.PYTHON, "intervals"))
        assert callable(get_render_fn(Language.JAVA, "intervals"))
        assert callable(get_render_fn(Language.RUST, "intervals"))

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

    def test_available_languages_includes_python_and_java(self) -> None:
        from genfxn.langs.render import _available_languages

        available = _available_languages()
        assert Language.PYTHON in available
        assert Language.JAVA in available

    def test_available_languages_ignores_value_error(self, monkeypatch) -> None:
        from genfxn.langs import render as render_module

        original_get_render_fn = render_module.get_render_fn

        def _fake_get_render_fn(language: Language, family: str):
            if language == Language.JAVA:
                raise ValueError("unsupported")
            return original_get_render_fn(language, family)

        monkeypatch.setattr(render_module, "get_render_fn", _fake_get_render_fn)

        available = render_module._available_languages()
        assert Language.PYTHON in available
        assert Language.JAVA not in available

    def test_render_all_languages_default(self) -> None:
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
        assert "def f(" in result["python"]
        assert "public static" in result["java"]

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
            languages=[Language.JAVA],
            func_name="g",
        )
        assert list(result.keys()) == ["java"]
        assert "public static int g(int x)" in result["java"]

    def test_render_all_languages_stack_bytecode_when_available(self) -> None:
        if not _supports_stack_bytecode_java():
            pytest.skip("stack_bytecode Java rendering is not available")
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
            languages=[Language.PYTHON, Language.JAVA],
        )
        assert "python" in result
        assert "java" in result
