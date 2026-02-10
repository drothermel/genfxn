from decimal import Decimal
from fractions import Fraction

from genfxn.core.models import (
    Query,
    QueryTag,
    dedupe_queries,
    dedupe_queries_per_tag_input,
)


class _UnhashableInput:
    def __init__(self, value: int) -> None:
        self.value = value

    __hash__ = None


class _BadReprKey:
    def __repr__(self) -> str:
        return 1  # type: ignore[return-value]


class _BrokenReprNoDict:
    __slots__ = ()
    __hash__ = None

    def __repr__(self) -> str:
        raise RuntimeError("broken repr")


def test_dedupe_queries_rejects_conflicting_outputs() -> None:
    queries = [
        Query(input=1, output=10, tag=QueryTag.TYPICAL),
        Query(input=1, output=99, tag=QueryTag.BOUNDARY),
        Query(input=2, output=20, tag=QueryTag.COVERAGE),
    ]

    try:
        dedupe_queries(queries)
    except ValueError as exc:
        assert "conflicting outputs" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for conflicting outputs")


def test_dedupe_queries_bool_and_int_inputs_remain_distinct() -> None:
    queries = [
        Query(input=True, output=10, tag=QueryTag.TYPICAL),
        Query(input=1, output=10, tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 2
    assert [q.input for q in deduped] == [True, 1]


def test_dedupe_queries_int_and_float_inputs_remain_distinct() -> None:
    queries = [
        Query(input=1, output=10, tag=QueryTag.TYPICAL),
        Query(input=1.0, output=10, tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 2
    assert [q.input for q in deduped] == [1, 1.0]


def test_dedupe_queries_float_nan_inputs_dedupe_deterministically() -> None:
    queries = [
        Query(input=float("nan"), output=10, tag=QueryTag.TYPICAL),
        Query(input=float("nan"), output=10, tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 1
    assert deduped[0].output == 10
    assert deduped[0].tag == QueryTag.BOUNDARY
    assert isinstance(deduped[0].input, float)
    assert deduped[0].input != deduped[0].input


def test_dedupe_queries_float_nan_conflicting_outputs_raise() -> None:
    queries = [
        Query(input=float("nan"), output=10, tag=QueryTag.TYPICAL),
        Query(input=float("nan"), output=99, tag=QueryTag.BOUNDARY),
    ]

    try:
        dedupe_queries(queries)
    except ValueError as exc:
        assert "conflicting outputs" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for conflicting outputs")


def test_dedupe_queries_float_nan_outputs_do_not_conflict() -> None:
    queries = [
        Query(input=1, output=float("nan"), tag=QueryTag.TYPICAL),
        Query(input=1, output=float("nan"), tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 1
    assert deduped[0].tag == QueryTag.BOUNDARY
    assert isinstance(deduped[0].output, float)
    assert deduped[0].output != deduped[0].output


def test_dedupe_queries_nested_nan_outputs_do_not_conflict() -> None:
    queries = [
        Query(
            input=1,
            output=[float("nan"), {"k": float("nan")}],
            tag=QueryTag.TYPICAL,
        ),
        Query(
            input=1,
            output=[float("nan"), {"k": float("nan")}],
            tag=QueryTag.BOUNDARY,
        ),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 1
    assert deduped[0].tag == QueryTag.BOUNDARY
    nested = deduped[0].output
    assert isinstance(nested, list)
    assert nested[0] != nested[0]
    assert nested[1]["k"] != nested[1]["k"]


def test_dedupe_queries_float_nan_vs_non_nan_outputs_raise() -> None:
    queries = [
        Query(input=1, output=float("nan"), tag=QueryTag.TYPICAL),
        Query(input=1, output=10, tag=QueryTag.BOUNDARY),
    ]

    try:
        dedupe_queries(queries)
    except ValueError as exc:
        assert "conflicting outputs" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for conflicting outputs")


def test_dedupe_queries_nested_nan_vs_non_nan_outputs_raise() -> None:
    queries = [
        Query(input=1, output=[float("nan")], tag=QueryTag.TYPICAL),
        Query(input=1, output=[0.0], tag=QueryTag.BOUNDARY),
    ]

    try:
        dedupe_queries(queries)
    except ValueError as exc:
        assert "conflicting outputs" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for conflicting outputs")


def test_dedupe_queries_type_distinct_inputs_do_not_conflict() -> None:
    queries = [
        Query(input=True, output=10, tag=QueryTag.TYPICAL),
        Query(input=1, output=99, tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 2
    assert [q.output for q in deduped] == [10, 99]


def test_dedupe_queries_decimal_and_fraction_do_not_conflict() -> None:
    queries = [
        Query(input=Decimal("1"), output=10, tag=QueryTag.TYPICAL),
        Query(input=Fraction(1, 1), output=99, tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 2
    assert [q.output for q in deduped] == [10, 99]


def test_dedupe_queries_list_input_hashing() -> None:
    queries = [
        Query(input=[1, 2], output=10, tag=QueryTag.TYPICAL),
        Query(input=[1, 2], output=10, tag=QueryTag.BOUNDARY),
        Query(input=[2, 1], output=20, tag=QueryTag.COVERAGE),
    ]

    deduped = dedupe_queries(queries)

    assert [q.input for q in deduped] == [[1, 2], [2, 1]]
    assert [q.output for q in deduped] == [10, 20]
    assert deduped[0].tag == QueryTag.BOUNDARY


def test_dedupe_queries_stable_order_for_unique_values() -> None:
    queries = [
        Query(input="a", output=1, tag=QueryTag.TYPICAL),
        Query(input="b", output=2, tag=QueryTag.BOUNDARY),
        Query(input="c", output=3, tag=QueryTag.COVERAGE),
    ]

    deduped = dedupe_queries(queries)

    assert [q.input for q in deduped] == ["a", "b", "c"]


def test_dedupe_queries_nested_unhashable_inputs_first_wins() -> None:
    queries = [
        Query(
            input={"a": [1, {"k": {2, 3}}], "b": (4, 5)},
            output=10,
            tag=QueryTag.TYPICAL,
        ),
        Query(
            input={"b": (4, 5), "a": [1, {"k": {3, 2}}]},
            output=10,
            tag=QueryTag.BOUNDARY,
        ),
        Query(
            input={"a": [1, {"k": {2, 4}}], "b": (4, 5)},
            output=20,
            tag=QueryTag.COVERAGE,
        ),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 2
    assert deduped[0].output == 10
    assert deduped[0].tag == QueryTag.BOUNDARY
    assert deduped[1].output == 20


def test_dedupe_queries_mixed_key_type_dict_does_not_crash() -> None:
    queries = [
        Query(
            input={1: "one", "2": "two"},
            output=1,
            tag=QueryTag.TYPICAL,
        ),
        Query(
            input={"2": "two", 1: "one"},
            output=1,
            tag=QueryTag.BOUNDARY,
        ),
        Query(
            input={1: "one", "2": "TWO"},
            output=3,
            tag=QueryTag.COVERAGE,
        ),
    ]

    deduped = dedupe_queries(queries)
    assert len(deduped) == 2
    assert deduped[0].output == 1
    assert deduped[0].tag == QueryTag.BOUNDARY
    assert deduped[1].output == 3


def test_dedupe_queries_unhashable_custom_input_does_not_crash() -> None:
    queries = [
        Query(input=_UnhashableInput(7), output=1, tag=QueryTag.TYPICAL),
        Query(input=_UnhashableInput(7), output=1, tag=QueryTag.BOUNDARY),
        Query(input=_UnhashableInput(8), output=3, tag=QueryTag.COVERAGE),
    ]

    deduped = dedupe_queries(queries)
    assert [q.output for q in deduped] == [1, 3]
    assert deduped[0].tag == QueryTag.BOUNDARY


def test_dedupe_queries_bad_repr_key_does_not_crash() -> None:
    bad_key = _BadReprKey()
    queries = [
        Query(
            input={bad_key: "x", 1: "one"},
            output=1,
            tag=QueryTag.TYPICAL,
        ),
        Query(
            input={1: "one", bad_key: "x"},
            output=1,
            tag=QueryTag.BOUNDARY,
        ),
    ]

    deduped = dedupe_queries(queries)
    assert len(deduped) == 1
    assert deduped[0].output == 1
    assert deduped[0].tag == QueryTag.BOUNDARY


def test_dedupe_queries_broken_repr_no_dict_does_not_crash() -> None:
    queries = [
        Query(input=_BrokenReprNoDict(), output=1, tag=QueryTag.TYPICAL),
        Query(input=_BrokenReprNoDict(), output=1, tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries(queries)

    assert len(deduped) == 1
    assert deduped[0].output == 1
    assert deduped[0].tag == QueryTag.BOUNDARY


def test_dedupe_queries_per_tag_input_allows_cross_tag_duplicates() -> None:
    queries = [
        Query(input={"src": 0, "dst": 0}, output=1, tag=QueryTag.COVERAGE),
        Query(input={"src": 0, "dst": 0}, output=1, tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries_per_tag_input(queries)

    assert len(deduped) == 2
    assert [query.tag for query in deduped] == [
        QueryTag.COVERAGE,
        QueryTag.BOUNDARY,
    ]


def test_dedupe_queries_per_tag_input_dedupes_within_tag() -> None:
    queries = [
        Query(input=[(0, 0)], output=1, tag=QueryTag.TYPICAL),
        Query(input=[(0, 0)], output=1, tag=QueryTag.TYPICAL),
        Query(input=[(0, 0)], output=1, tag=QueryTag.BOUNDARY),
    ]

    deduped = dedupe_queries_per_tag_input(queries)

    assert len(deduped) == 2
    assert [query.tag for query in deduped] == [
        QueryTag.TYPICAL,
        QueryTag.BOUNDARY,
    ]


def test_dedupe_queries_per_tag_input_rejects_conflicting_outputs() -> None:
    queries = [
        Query(input=[(0, 0)], output=1, tag=QueryTag.TYPICAL),
        Query(input=[(0, 0)], output=2, tag=QueryTag.TYPICAL),
    ]

    try:
        dedupe_queries_per_tag_input(queries)
    except ValueError as exc:
        assert "conflicting outputs" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected ValueError for conflicting outputs")
