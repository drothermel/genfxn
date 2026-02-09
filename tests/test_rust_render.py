"""Tests for Rust rendering modules."""

import importlib.util
import random

import pytest

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
from genfxn.langs.rust._helpers import rust_string_literal
from genfxn.langs.rust.expressions import render_expression_rust
from genfxn.langs.rust.predicates import render_predicate_rust
from genfxn.langs.rust.string_predicates import render_string_predicate_rust
from genfxn.langs.rust.string_transforms import render_string_transform_rust
from genfxn.langs.rust.transforms import render_transform_rust
from genfxn.langs.types import Language
from genfxn.piecewise.models import ExprAbs, ExprAffine, ExprMod, ExprQuadratic
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.simple_algorithms.task import generate_simple_algorithms_task
from genfxn.stateful.task import generate_stateful_task
from genfxn.stringrules.task import generate_stringrules_task


def _code_map(task: Task) -> dict[str, str]:
    assert isinstance(task.code, dict)
    return task.code


def seeded_rng(seed: int) -> random.Random:  # noqa: S311
    return random.Random(seed)


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
            "!s.is_empty() && s.chars().all(|c| c.is_numeric())"
        )

    def test_is_digit_uses_unicode_aware_numeric_check(self) -> None:
        result = render_string_predicate_rust(StringPredicateIsDigit())
        assert "is_numeric()" in result

    def test_is_upper(self) -> None:
        result = render_string_predicate_rust(StringPredicateIsUpper())
        assert result == (
            "!s.is_empty() && s.chars().any(|c| c.is_alphabetic()) && "
            "s.to_uppercase() == s"
        )

    def test_is_lower(self) -> None:
        result = render_string_predicate_rust(StringPredicateIsLower())
        assert result == (
            "!s.is_empty() && s.chars().any(|c| c.is_alphabetic()) && "
            "s.to_lowercase() == s"
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
    def test_length_cmp(self, op: str, expected_op: str) -> None:
        result = render_string_predicate_rust(
            StringPredicateLengthCmp(op=op, value=5)
        )
        assert result == f"s.len() {expected_op} 5"

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
        assert "} else {" in code

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
        assert "xs[i] + xs[j] == 10" in code
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
        assert code["python"].startswith("def f(")
        assert "fn f(x: i64) -> i64" in code["rust"]

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
        assert "fn " in code["rust"]

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

    @pytest.mark.parametrize("seed", range(10))
    def test_piecewise_rust_renders_non_empty(self, seed: int) -> None:
        task = generate_piecewise_task(
            rng=seeded_rng(seed),
            languages=[Language.RUST],
        )
        code = _code_map(task)
        assert len(code["rust"]) > 20

    @pytest.mark.parametrize("seed", range(10))
    def test_stateful_rust_renders_non_empty(self, seed: int) -> None:
        task = generate_stateful_task(
            rng=seeded_rng(seed),
            languages=[Language.RUST],
        )
        code = _code_map(task)
        assert len(code["rust"]) > 20

    @pytest.mark.parametrize("seed", range(10))
    def test_stringrules_rust_renders_non_empty(self, seed: int) -> None:
        task = generate_stringrules_task(
            rng=seeded_rng(seed),
            languages=[Language.RUST],
        )
        code = _code_map(task)
        assert len(code["rust"]) > 20

    @pytest.mark.parametrize("seed", range(10))
    def test_simple_algorithms_rust_renders_non_empty(self, seed: int) -> None:
        task = generate_simple_algorithms_task(
            rng=seeded_rng(seed),
            languages=[Language.RUST],
        )
        code = _code_map(task)
        assert len(code["rust"]) > 20


# ── Registry Tests ─────────────────────────────────────────────────────


class TestRustRegistry:
    def test_language_enum_has_rust(self) -> None:
        assert Language.RUST.value == "rust"

    def test_registry_rust_all_families(self) -> None:
        from genfxn.langs.registry import get_render_fn

        families = [
            "piecewise",
            "stateful",
            "simple_algorithms",
            "stringrules",
        ]
        if _supports_stack_bytecode_rust():
            families.append("stack_bytecode")
        for family in families:
            fn = get_render_fn(Language.RUST, family)
            assert callable(fn)

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
