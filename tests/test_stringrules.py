import random

import pytest

from genfxn.core.models import QueryTag
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
    StringPredicateType,
    eval_string_predicate,
    render_string_predicate,
)
from genfxn.core.string_transforms import (
    StringTransformAppend,
    StringTransformCapitalize,
    StringTransformLowercase,
    StringTransformPipeline,
    StringTransformPrepend,
    StringTransformReplace,
    StringTransformReverse,
    StringTransformStrip,
    StringTransformType,
    StringTransformUppercase,
    eval_string_transform,
    render_string_transform,
)
from genfxn.stringrules.eval import eval_stringrules
from genfxn.stringrules.models import (
    OverlapLevel,
    StringRule,
    StringRulesAxes,
    StringRulesSpec,
)
from genfxn.stringrules.queries import generate_stringrules_queries
from genfxn.stringrules.render import render_stringrules
from genfxn.stringrules.sampler import sample_stringrules_spec
from genfxn.stringrules.task import generate_stringrules_task
from genfxn.stringrules.utils import _get_charset, _random_string


class TestStringPredicates:
    def test_starts_with(self) -> None:
        pred = StringPredicateStartsWith(prefix="hello")
        assert eval_string_predicate(pred, "hello world") is True
        assert eval_string_predicate(pred, "world hello") is False
        assert eval_string_predicate(pred, "hello") is True
        assert eval_string_predicate(pred, "hel") is False

    def test_ends_with(self) -> None:
        pred = StringPredicateEndsWith(suffix="world")
        assert eval_string_predicate(pred, "hello world") is True
        assert eval_string_predicate(pred, "world hello") is False

    def test_contains(self) -> None:
        pred = StringPredicateContains(substring="ell")
        assert eval_string_predicate(pred, "hello") is True
        assert eval_string_predicate(pred, "world") is False

    def test_is_alpha(self) -> None:
        pred = StringPredicateIsAlpha()
        assert eval_string_predicate(pred, "hello") is True
        assert eval_string_predicate(pred, "hello123") is False
        assert eval_string_predicate(pred, "") is False

    def test_is_digit(self) -> None:
        pred = StringPredicateIsDigit()
        assert eval_string_predicate(pred, "123") is True
        assert eval_string_predicate(pred, "12a") is False
        assert eval_string_predicate(pred, "") is False

    def test_length_cmp(self) -> None:
        pred_lt = StringPredicateLengthCmp(op="lt", value=5)
        assert eval_string_predicate(pred_lt, "abc") is True
        assert eval_string_predicate(pred_lt, "abcde") is False

        pred_ge = StringPredicateLengthCmp(op="ge", value=3)
        assert eval_string_predicate(pred_ge, "abc") is True
        assert eval_string_predicate(pred_ge, "ab") is False


class TestStringPredicatesRender:
    def test_starts_with_render(self) -> None:
        pred = StringPredicateStartsWith(prefix="test")
        assert render_string_predicate(pred, "s") == "s.startswith('test')"

    def test_contains_render(self) -> None:
        pred = StringPredicateContains(substring="sub")
        assert render_string_predicate(pred, "s") == "'sub' in s"

    def test_length_cmp_render(self) -> None:
        pred = StringPredicateLengthCmp(op="gt", value=10)
        assert render_string_predicate(pred, "s") == "len(s) > 10"


class TestStringTransforms:
    def test_lowercase(self) -> None:
        t = StringTransformLowercase()
        assert eval_string_transform(t, "HELLO") == "hello"

    def test_uppercase(self) -> None:
        t = StringTransformUppercase()
        assert eval_string_transform(t, "hello") == "HELLO"

    def test_capitalize(self) -> None:
        t = StringTransformCapitalize()
        assert eval_string_transform(t, "hello world") == "Hello world"

    def test_reverse(self) -> None:
        t = StringTransformReverse()
        assert eval_string_transform(t, "hello") == "olleh"

    def test_replace(self) -> None:
        t = StringTransformReplace(old="a", new="X")
        assert eval_string_transform(t, "banana") == "bXnXnX"

    def test_strip(self) -> None:
        t = StringTransformStrip(chars=None)
        assert eval_string_transform(t, "  hello  ") == "hello"

        t2 = StringTransformStrip(chars="_")
        assert eval_string_transform(t2, "__hello__") == "hello"

    def test_prepend(self) -> None:
        t = StringTransformPrepend(prefix="PRE_")
        assert eval_string_transform(t, "hello") == "PRE_hello"

    def test_append(self) -> None:
        t = StringTransformAppend(suffix="_SUF")
        assert eval_string_transform(t, "hello") == "hello_SUF"


class TestStringTransformsRender:
    def test_lowercase_render(self) -> None:
        t = StringTransformLowercase()
        assert render_string_transform(t, "s") == "s.lower()"

    def test_reverse_render(self) -> None:
        t = StringTransformReverse()
        assert render_string_transform(t, "s") == "s[::-1]"

    def test_prepend_render(self) -> None:
        t = StringTransformPrepend(prefix="pre")
        assert render_string_transform(t, "s") == "'pre' + s"


class TestComposedStringPredicates:
    def test_not_eval(self) -> None:
        p = StringPredicateNot(operand=StringPredicateIsAlpha())
        assert eval_string_predicate(p, "123") is True
        assert eval_string_predicate(p, "abc") is False

    def test_not_render(self) -> None:
        p = StringPredicateNot(operand=StringPredicateIsAlpha())
        assert render_string_predicate(p) == "not (s.isalpha())"

    def test_and_eval(self) -> None:
        p = StringPredicateAnd(
            operands=[
                StringPredicateIsAlpha(),
                StringPredicateStartsWith(prefix="a"),
            ]
        )
        assert eval_string_predicate(p, "abc") is True
        assert eval_string_predicate(p, "xyz") is False
        assert eval_string_predicate(p, "a123") is False

    def test_and_render(self) -> None:
        p = StringPredicateAnd(
            operands=[
                StringPredicateIsAlpha(),
                StringPredicateLengthCmp(op="gt", value=3),
            ]
        )
        assert render_string_predicate(p) == "(s.isalpha() and len(s) > 3)"

    def test_or_eval(self) -> None:
        p = StringPredicateOr(
            operands=[
                StringPredicateIsDigit(),
                StringPredicateStartsWith(prefix="x"),
            ]
        )
        assert eval_string_predicate(p, "123") is True
        assert eval_string_predicate(p, "xyz") is True
        assert eval_string_predicate(p, "abc") is False

    def test_or_render(self) -> None:
        p = StringPredicateOr(
            operands=[
                StringPredicateIsDigit(),
                StringPredicateIsAlpha(),
            ]
        )
        assert render_string_predicate(p) == "(s.isdigit() or s.isalpha())"


class TestStringTransformPipeline:
    def test_pipeline_eval(self) -> None:
        p = StringTransformPipeline(
            steps=[StringTransformUppercase(), StringTransformReverse()]
        )
        assert eval_string_transform(p, "hello") == "OLLEH"

    def test_pipeline_render(self) -> None:
        p = StringTransformPipeline(
            steps=[StringTransformUppercase(), StringTransformReverse()]
        )
        assert render_string_transform(p) == "(s.upper())[::-1]"

    def test_three_step_pipeline(self) -> None:
        p = StringTransformPipeline(
            steps=[
                StringTransformStrip(chars="_"),
                StringTransformLowercase(),
                StringTransformAppend(suffix="!"),
            ]
        )
        assert eval_string_transform(p, "__Hello__") == "hello!"

    def test_pipeline_render_three_steps(self) -> None:
        p = StringTransformPipeline(
            steps=[
                StringTransformStrip(chars="_"),
                StringTransformLowercase(),
                StringTransformAppend(suffix="!"),
            ]
        )
        assert render_string_transform(p) == "((s.strip('_')).lower()) + '!'"


class TestStringRulesEval:
    def test_first_match_wins(self) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="a"),
                    transform=StringTransformUppercase(),
                ),
                StringRule(
                    predicate=StringPredicateIsAlpha(),
                    transform=StringTransformLowercase(),
                ),
            ],
            default_transform=StringTransformReverse(),
        )
        # "abc" matches both rules, first should win
        assert eval_stringrules(spec, "abc") == "ABC"
        # "xyz" only matches second rule
        assert (
            eval_stringrules(spec, "xyz") == "xyz"
        )  # isalpha -> lowercase (no change)
        # "123" matches no rules, default applies
        assert eval_stringrules(spec, "123") == "321"

    def test_default_when_no_match(self) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="x"),
                    transform=StringTransformUppercase(),
                ),
            ],
            default_transform=StringTransformReverse(),
        )
        assert eval_stringrules(spec, "hello") == "olleh"


class TestStringRulesRender:
    def test_single_rule(self) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="test"),
                    transform=StringTransformUppercase(),
                ),
            ],
            default_transform=StringTransformLowercase(),
        )
        code = render_stringrules(spec)
        assert "def f(s: str) -> str:" in code
        assert "if s.startswith('test'):" in code
        assert "s.upper()" in code
        assert "else:" in code
        assert "s.lower()" in code

    def test_multiple_rules(self) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="a"),
                    transform=StringTransformUppercase(),
                ),
                StringRule(
                    predicate=StringPredicateEndsWith(suffix="z"),
                    transform=StringTransformReverse(),
                ),
            ],
            default_transform=StringTransformLowercase(),
        )
        code = render_stringrules(spec)
        assert "if s.startswith('a'):" in code
        assert "elif s.endswith('z'):" in code
        assert "else:" in code


class TestRenderRoundtrip:
    def test_single_rule_roundtrip(self) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateIsAlpha(),
                    transform=StringTransformUppercase(),
                ),
            ],
            default_transform=StringTransformReverse(),
        )
        code = render_stringrules(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = ["hello", "123", "abc123", ""]
        for s in test_inputs:
            assert f(s) == eval_stringrules(spec, s), f"s={s!r}"

    def test_multiple_rules_roundtrip(self) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="a"),
                    transform=StringTransformUppercase(),
                ),
                StringRule(
                    predicate=StringPredicateLengthCmp(op="lt", value=3),
                    transform=StringTransformReverse(),
                ),
            ],
            default_transform=StringTransformLowercase(),
        )
        code = render_stringrules(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        test_inputs = ["abc", "ab", "ABC", "xy", "hello"]
        for s in test_inputs:
            assert f(s) == eval_stringrules(spec, s), f"s={s!r}"


class TestSampler:
    def test_reproducible(self) -> None:
        axes = StringRulesAxes(n_rules=2)
        spec1 = sample_stringrules_spec(axes, random.Random(42))
        spec2 = sample_stringrules_spec(axes, random.Random(42))
        assert spec1 == spec2

    def test_respects_n_rules(self) -> None:
        for n in [1, 3, 5]:
            axes = StringRulesAxes(n_rules=n)
            spec = sample_stringrules_spec(axes, random.Random(42))
            assert len(spec.rules) == n


class TestQueryGeneration:
    def test_generates_queries(self) -> None:
        axes = StringRulesAxes(n_rules=2)
        spec = sample_stringrules_spec(axes, random.Random(42))
        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        assert len(queries) > 0

    def test_all_queries_valid(self) -> None:
        axes = StringRulesAxes(n_rules=2)
        spec = sample_stringrules_spec(axes, random.Random(42))
        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        for q in queries:
            assert q.output == eval_stringrules(spec, q.input)

    def test_queries_respect_string_length_range(self) -> None:
        axes = StringRulesAxes(n_rules=3, string_length_range=(0, 4))
        spec = sample_stringrules_spec(axes, random.Random(42))
        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        lo, hi = axes.string_length_range
        assert queries
        assert all(lo <= len(q.input) <= hi for q in queries)

    def test_coverage_queries_trigger_their_target_rule(self) -> None:
        axes = StringRulesAxes(n_rules=3, overlap_level=OverlapLevel.NONE)
        spec = sample_stringrules_spec(axes, random.Random(42))
        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        coverage = [q for q in queries if q.tag == QueryTag.COVERAGE]
        assert len(coverage) >= len(spec.rules)

        for i, rule in enumerate(spec.rules):
            assert any(
                eval_string_predicate(rule.predicate, q.input)
                and not any(
                    eval_string_predicate(prev.predicate, q.input)
                    for prev in spec.rules[:i]
                )
                for q in coverage
            )

    def test_queries_respect_charset_constraints(self) -> None:
        axes = StringRulesAxes(
            n_rules=2,
            charset="digits",
            string_length_range=(1, 8),
        )
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="12"),
                    transform=StringTransformUppercase(),
                ),
                StringRule(
                    predicate=StringPredicateContains(substring="34"),
                    transform=StringTransformLowercase(),
                ),
            ],
            default_transform=StringTransformReverse(),
        )
        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        charset = set(_get_charset(axes.charset))
        assert queries
        assert all(set(q.input).issubset(charset) for q in queries)

    def test_is_upper_non_matching_queries_are_truly_non_matching(self) -> None:
        axes = StringRulesAxes(
            n_rules=1,
            string_length_range=(1, 6),
            charset="ascii_letters_digits",
        )
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateIsUpper(),
                    transform=StringTransformUppercase(),
                )
            ],
            default_transform=StringTransformLowercase(),
        )
        queries = generate_stringrules_queries(spec, axes, random.Random(101))
        non_matching = [
            q
            for q in queries
            if not eval_string_predicate(spec.rules[0].predicate, q.input)
        ]
        assert non_matching
        for query in non_matching:
            assert query.output == eval_stringrules(spec, query.input)

    def test_is_lower_non_matching_queries_are_truly_non_matching(self) -> None:
        axes = StringRulesAxes(
            n_rules=1,
            string_length_range=(1, 6),
            charset="ascii_letters_digits",
        )
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateIsLower(),
                    transform=StringTransformLowercase(),
                )
            ],
            default_transform=StringTransformUppercase(),
        )
        queries = generate_stringrules_queries(spec, axes, random.Random(102))
        non_matching = [
            q
            for q in queries
            if not eval_string_predicate(spec.rules[0].predicate, q.input)
        ]
        assert non_matching
        for query in non_matching:
            assert query.output == eval_stringrules(spec, query.input)


class TestAxesValidation:
    def test_invalid_string_length_range(self) -> None:
        with pytest.raises(ValueError, match="string_length_range"):
            StringRulesAxes(string_length_range=(20, 5))

    def test_n_rules_too_low(self) -> None:
        with pytest.raises(ValueError):
            StringRulesAxes(n_rules=0)

    def test_n_rules_too_high(self) -> None:
        with pytest.raises(ValueError):
            StringRulesAxes(n_rules=11)

    def test_empty_predicate_types(self) -> None:
        with pytest.raises(
            ValueError, match="predicate_types must not be empty"
        ):
            StringRulesAxes(predicate_types=[])

    def test_non_ascii_charset_rejected_for_parity(self) -> None:
        with pytest.raises(ValueError, match="ASCII-only"):
            StringRulesAxes(charset="abcé")


class TestTaskGeneration:
    def test_full_pipeline(self) -> None:
        axes = StringRulesAxes(n_rules=2)
        task = generate_stringrules_task(axes, random.Random(42))
        assert task.family == "stringrules"
        assert task.task_id.startswith("stringrules_")
        assert len(task.queries) > 0

        assert isinstance(task.code, str)
        namespace: dict = {}
        exec(task.code, namespace)  # noqa: S102
        f = namespace["f"]
        for q in task.queries:
            assert f(q.input) == q.output

    def test_different_overlap_levels(self) -> None:
        for overlap in OverlapLevel:
            axes = StringRulesAxes(n_rules=3, overlap_level=overlap)
            task = generate_stringrules_task(axes, random.Random(42))
            assert len(task.spec["rules"]) == 3

            assert isinstance(task.code, str)
            namespace: dict = {}
            exec(task.code, namespace)  # noqa: S102
            f = namespace["f"]
            for q in task.queries:
                assert f(q.input) == q.output, f"Overlap {overlap}: mismatch"


class TestRandomStringUtils:
    """Tests for _random_string edge cases (empty charset / exclude)."""

    def test_empty_charset_length_zero_returns_empty_string(self) -> None:
        rng = random.Random(42)
        assert _random_string(0, "", rng) == ""

    def test_empty_charset_length_positive_raises(self) -> None:
        rng = random.Random(42)
        with pytest.raises(
            ValueError,
            match=(
                "charset \\(after exclude\\) must contain "
                "at least one character"
            ),
        ):
            _random_string(3, "", rng)

    def test_normal_case_returns_string_of_requested_length(self) -> None:
        rng = random.Random(42)
        s = _random_string(5, "abc", rng)
        assert len(s) == 5
        assert all(c in "abc" for c in s)


class TestComposedPredicateSampling:
    def test_sample_not_predicate(self) -> None:
        axes = StringRulesAxes(
            n_rules=2,
            predicate_types=[StringPredicateType.NOT],
        )
        spec = sample_stringrules_spec(axes, random.Random(42))
        for rule in spec.rules:
            assert isinstance(rule.predicate, StringPredicateNot)

    def test_sample_and_predicate(self) -> None:
        axes = StringRulesAxes(
            n_rules=2,
            predicate_types=[StringPredicateType.AND],
        )
        spec = sample_stringrules_spec(axes, random.Random(42))
        for rule in spec.rules:
            assert isinstance(rule.predicate, StringPredicateAnd)
            assert len(rule.predicate.operands) >= 2

    def test_sample_or_predicate(self) -> None:
        axes = StringRulesAxes(
            n_rules=2,
            predicate_types=[StringPredicateType.OR],
        )
        spec = sample_stringrules_spec(axes, random.Random(42))
        for rule in spec.rules:
            assert isinstance(rule.predicate, StringPredicateOr)
            assert len(rule.predicate.operands) >= 2

    def test_composed_only_sampling_uses_multiple_atom_kinds(self) -> None:
        axes = StringRulesAxes(
            n_rules=8,
            predicate_types=[StringPredicateType.AND],
        )
        spec = sample_stringrules_spec(axes, random.Random(42))
        operand_kinds: set[str] = set()
        for rule in spec.rules:
            assert isinstance(rule.predicate, StringPredicateAnd)
            for operand in rule.predicate.operands:
                operand_kinds.add(operand.kind)
        assert len(operand_kinds) >= 2


class TestPipelineTransformSampling:
    def test_sample_pipeline_transform(self) -> None:
        axes = StringRulesAxes(
            n_rules=2,
            transform_types=[StringTransformType.PIPELINE],
        )
        spec = sample_stringrules_spec(axes, random.Random(42))
        # At least the rule transforms should be pipelines
        for rule in spec.rules:
            assert isinstance(rule.transform, StringTransformPipeline)
            assert len(rule.transform.steps) >= 2

    def test_pipeline_only_sampling_includes_parameterized_steps(self) -> None:
        axes = StringRulesAxes(
            n_rules=8,
            transform_types=[StringTransformType.PIPELINE],
        )
        spec = sample_stringrules_spec(axes, random.Random(42))
        param_kinds = {"replace", "strip", "prepend", "append"}

        pipelines = [rule.transform for rule in spec.rules]
        pipelines.append(spec.default_transform)

        for pipeline in pipelines:
            assert isinstance(pipeline, StringTransformPipeline)
            assert any(step.kind in param_kinds for step in pipeline.steps)


class TestComposedRoundtrip:
    def test_not_predicate_roundtrip(self) -> None:
        axes = StringRulesAxes(
            n_rules=2,
            predicate_types=[StringPredicateType.NOT],
        )
        rng = random.Random(42)
        spec = sample_stringrules_spec(axes, rng)
        code = render_stringrules(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        for q in queries:
            assert f(q.input) == q.output, f"s={q.input!r}"

    def test_pipeline_transform_roundtrip(self) -> None:
        axes = StringRulesAxes(
            n_rules=2,
            transform_types=[StringTransformType.PIPELINE],
        )
        rng = random.Random(42)
        spec = sample_stringrules_spec(axes, rng)
        code = render_stringrules(spec)
        namespace: dict = {}
        exec(code, namespace)  # noqa: S102
        f = namespace["f"]
        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        for q in queries:
            assert f(q.input) == q.output, f"s={q.input!r}"


class TestRandomStringExclude:
    def test_raises_when_exclude_removes_all_chars(self) -> None:
        rng = random.Random(42)
        with pytest.raises(ValueError):
            _random_string(length=3, charset="abc", rng=rng, exclude="abc")
