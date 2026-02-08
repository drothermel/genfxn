"""Tests for query generation quality and edge cases."""

import random

from genfxn.core.models import QueryTag
from genfxn.core.predicates import (
    PredicateAnd,
    PredicateGt,
    PredicateModEq,
)
from genfxn.core.string_predicates import (
    StringPredicateContains,
    StringPredicateIsAlpha,
    StringPredicateIsUpper,
    StringPredicateStartsWith,
    StringPredicateType,
    eval_string_predicate,
)
from genfxn.core.string_transforms import (
    StringTransformIdentity,
    StringTransformLowercase,
    StringTransformType,
    StringTransformUppercase,
)
from genfxn.core.transforms import TransformIdentity, TransformShift
from genfxn.simple_algorithms.eval import eval_count_pairs_sum
from genfxn.simple_algorithms.models import (
    CountingMode,
    CountPairsSumSpec,
    SimpleAlgorithmsAxes,
)
from genfxn.simple_algorithms.queries import generate_simple_algorithms_queries
from genfxn.stateful.eval import eval_stateful
from genfxn.stateful.models import ConditionalLinearSumSpec, StatefulAxes
from genfxn.stateful.queries import generate_stateful_queries
from genfxn.stringrules.eval import eval_stringrules
from genfxn.stringrules.models import (
    OverlapLevel,
    StringRule,
    StringRulesAxes,
    StringRulesSpec,
)
from genfxn.stringrules.queries import generate_stringrules_queries


class TestComposedPredicateBoundaryQueries:
    def test_unsatisfiable_composed_predicate_produces_valid_queries(
        self,
    ) -> None:
        """AND(mod_eq(97,0), gt(50)) with value_range=(-10,10) is unsatisfiable.

        Boundary queries should either be absent or have outputs matching eval.
        """
        pred = PredicateAnd(
            operands=[
                PredicateModEq(divisor=97, remainder=0),
                PredicateGt(value=50),
            ]
        )
        spec = ConditionalLinearSumSpec(
            predicate=pred,
            true_transform=TransformShift(offset=1),
            false_transform=TransformIdentity(),
        )
        axes = StatefulAxes(value_range=(-10, 10), list_length_range=(3, 8))
        rng = random.Random(42)

        queries = generate_stateful_queries(spec, axes, rng)

        for q in queries:
            expected = eval_stateful(spec, q.input)
            assert q.output == expected, (
                f"Query output {q.output} doesn't match eval {expected} "
                f"for input {q.input}"
            )


class TestContainsLongSubstring:
    def test_contains_long_substring_no_crash(self) -> None:
        """Longer-than-range substring in `contains` should not crash."""
        long_sub = "abcdefghijklmnopqrstuvwxyz"
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateContains(substring=long_sub),
                    transform=StringTransformUppercase(),
                )
            ],
            default_transform=StringTransformIdentity(),
        )
        axes = StringRulesAxes(
            n_rules=1,
            predicate_types=[StringPredicateType.CONTAINS],
            transform_types=[
                StringTransformType.IDENTITY,
                StringTransformType.UPPERCASE,
            ],
            string_length_range=(1, 10),
            substring_length_range=(1, 3),
        )
        rng = random.Random(42)

        queries = generate_stringrules_queries(spec, axes, rng)
        assert len(queries) > 0

        for q in queries:
            expected = eval_stringrules(spec, q.input)
            assert q.output == expected

    def test_contains_exact_length_substring(self) -> None:
        """Contains predicate where substring length == max string length."""
        sub = "hello"
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateContains(substring=sub),
                    transform=StringTransformLowercase(),
                )
            ],
            default_transform=StringTransformIdentity(),
        )
        axes = StringRulesAxes(
            n_rules=1,
            predicate_types=[StringPredicateType.CONTAINS],
            transform_types=[
                StringTransformType.IDENTITY,
                StringTransformType.LOWERCASE,
            ],
            string_length_range=(1, 5),
            substring_length_range=(1, 3),
        )
        rng = random.Random(42)

        queries = generate_stringrules_queries(spec, axes, rng)

        for q in queries:
            expected = eval_stringrules(spec, q.input)
            assert q.output == expected


class TestCoverageQueriesCoverAllRules:
    @staticmethod
    def _first_matching_rule_index(spec: StringRulesSpec, s: str) -> int | None:
        for i, rule in enumerate(spec.rules):
            if eval_string_predicate(rule.predicate, s):
                return i
        return None

    def test_coverage_queries_exercise_each_rule(self) -> None:
        """Coverage queries include at least one input for each rule."""
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="abc"),
                    transform=StringTransformUppercase(),
                ),
                StringRule(
                    predicate=StringPredicateIsAlpha(),
                    transform=StringTransformLowercase(),
                ),
                StringRule(
                    predicate=StringPredicateContains(substring="xyz"),
                    transform=StringTransformIdentity(),
                ),
            ],
            default_transform=StringTransformIdentity(),
        )
        axes = StringRulesAxes(
            n_rules=3,
            predicate_types=[
                StringPredicateType.STARTS_WITH,
                StringPredicateType.IS_ALPHA,
                StringPredicateType.CONTAINS,
            ],
            transform_types=[
                StringTransformType.IDENTITY,
                StringTransformType.UPPERCASE,
                StringTransformType.LOWERCASE,
            ],
            overlap_level=OverlapLevel.NONE,
            string_length_range=(1, 20),
        )
        rng = random.Random(42)

        queries = generate_stringrules_queries(spec, axes, rng)
        coverage_queries = [q for q in queries if q.tag == QueryTag.COVERAGE]

        # Should have at least one coverage query per rule
        assert len(coverage_queries) >= len(spec.rules)

        # Each coverage query output must match eval
        for q in coverage_queries:
            expected = eval_stringrules(spec, q.input)
            assert q.output == expected

    def test_coverage_query_triggers_intended_rule(self) -> None:
        """First coverage query should trigger rule 0, not a later rule."""
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="test"),
                    transform=StringTransformUppercase(),
                ),
                StringRule(
                    predicate=StringPredicateIsAlpha(),
                    transform=StringTransformLowercase(),
                ),
            ],
            default_transform=StringTransformIdentity(),
        )
        axes = StringRulesAxes(
            n_rules=2,
            predicate_types=[
                StringPredicateType.STARTS_WITH,
                StringPredicateType.IS_ALPHA,
            ],
            transform_types=[
                StringTransformType.IDENTITY,
                StringTransformType.UPPERCASE,
                StringTransformType.LOWERCASE,
            ],
            overlap_level=OverlapLevel.NONE,
            string_length_range=(1, 20),
        )
        rng = random.Random(42)

        queries = generate_stringrules_queries(spec, axes, rng)
        coverage_queries = [q for q in queries if q.tag == QueryTag.COVERAGE]

        if len(coverage_queries) >= 1:
            # First coverage query should trigger rule 0 (starts_with "test")
            first_input = coverage_queries[0].input
            assert eval_string_predicate(
                spec.rules[0].predicate, first_input
            ), (
                "First coverage query input "
                f"'{first_input}' doesn't match rule 0 predicate"
            )

    def test_coverage_queries_do_not_include_shadowed_rule_fallbacks(
        self,
    ) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="a"),
                    transform=StringTransformUppercase(),
                ),
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="a"),
                    transform=StringTransformLowercase(),
                ),
                StringRule(
                    predicate=StringPredicateStartsWith(prefix="b"),
                    transform=StringTransformIdentity(),
                ),
            ],
            default_transform=StringTransformIdentity(),
        )
        axes = StringRulesAxes(
            n_rules=3,
            predicate_types=[StringPredicateType.STARTS_WITH],
            transform_types=[
                StringTransformType.IDENTITY,
                StringTransformType.UPPERCASE,
                StringTransformType.LOWERCASE,
            ],
            overlap_level=OverlapLevel.NONE,
            string_length_range=(1, 8),
        )
        rng = random.Random(42)

        queries = generate_stringrules_queries(spec, axes, rng)
        coverage_queries = [q for q in queries if q.tag == QueryTag.COVERAGE]
        first_match_indices = [
            self._first_matching_rule_index(spec, q.input)
            for q in coverage_queries
        ]

        assert first_match_indices
        assert all(i is not None for i in first_match_indices)
        assert sorted(set(first_match_indices)) == [0, 2]
        assert len(first_match_indices) == len(set(first_match_indices))


class TestCharsetAwareStringQueries:
    def test_alpha_queries_respect_digit_charset(self) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateIsAlpha(),
                    transform=StringTransformUppercase(),
                )
            ],
            default_transform=StringTransformIdentity(),
        )
        axes = StringRulesAxes(
            n_rules=1,
            predicate_types=[StringPredicateType.IS_ALPHA],
            transform_types=[
                StringTransformType.IDENTITY,
                StringTransformType.UPPERCASE,
            ],
            string_length_range=(1, 8),
            charset="digits",
        )

        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        assert queries
        assert all(all(ch.isdigit() for ch in q.input) for q in queries)

    def test_upper_queries_respect_lowercase_charset(self) -> None:
        spec = StringRulesSpec(
            rules=[
                StringRule(
                    predicate=StringPredicateIsUpper(),
                    transform=StringTransformUppercase(),
                )
            ],
            default_transform=StringTransformIdentity(),
        )
        axes = StringRulesAxes(
            n_rules=1,
            predicate_types=[StringPredicateType.IS_UPPER],
            transform_types=[
                StringTransformType.IDENTITY,
                StringTransformType.UPPERCASE,
            ],
            string_length_range=(1, 8),
            charset="ascii_lowercase",
        )

        queries = generate_stringrules_queries(spec, axes, random.Random(42))
        assert queries
        assert all(all(ch.islower() for ch in q.input) for q in queries)


class TestCountPairsNoPairsInvariant:
    def test_no_pairs_fixture_has_zero_pairs(self) -> None:
        spec = CountPairsSumSpec(
            target=7,
            counting_mode=CountingMode.ALL_INDICES,
        )
        axes = SimpleAlgorithmsAxes(
            value_range=(0, 12),
            list_length_range=(2, 5),
            window_size_range=(1, 5),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )

        no_pair_candidates = [
            q
            for q in queries
            if q.tag == QueryTag.TYPICAL
            and eval_count_pairs_sum(spec, q.input) == 0
        ]
        assert no_pair_candidates
        for q in no_pair_candidates:
            assert all(
                q.input[i] + q.input[j] != spec.target
                for i in range(len(q.input))
                for j in range(i + 1, len(q.input))
            )

    def test_queries_respect_tight_length_bounds(self) -> None:
        spec = CountPairsSumSpec(
            target=7,
            counting_mode=CountingMode.ALL_INDICES,
        )
        axes = SimpleAlgorithmsAxes(
            value_range=(0, 12),
            list_length_range=(1, 2),
            window_size_range=(1, 2),
        )
        queries = generate_simple_algorithms_queries(
            spec, axes, random.Random(42)
        )
        assert queries
        assert all(1 <= len(q.input) <= 2 for q in queries if q.input != [])
