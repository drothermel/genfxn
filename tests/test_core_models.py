from genfxn.core.models import Query, QueryTag, dedupe_queries


class _UnhashableInput:
    def __init__(self, value: int) -> None:
        self.value = value

    __hash__ = None


class _BadReprKey:
    def __repr__(self) -> str:
        return 1  # type: ignore[return-value]


def test_dedupe_queries_first_wins() -> None:
    queries = [
        Query(input=1, output=10, tag=QueryTag.TYPICAL),
        Query(input=1, output=99, tag=QueryTag.BOUNDARY),
        Query(input=2, output=20, tag=QueryTag.COVERAGE),
    ]

    deduped = dedupe_queries(queries)

    assert [q.input for q in deduped] == [1, 2]
    assert deduped[0].output == 10


def test_dedupe_queries_list_input_hashing() -> None:
    queries = [
        Query(input=[1, 2], output=10, tag=QueryTag.TYPICAL),
        Query(input=[1, 2], output=99, tag=QueryTag.BOUNDARY),
        Query(input=[2, 1], output=20, tag=QueryTag.COVERAGE),
    ]

    deduped = dedupe_queries(queries)

    assert [q.input for q in deduped] == [[1, 2], [2, 1]]
    assert [q.output for q in deduped] == [10, 20]


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
            output=99,
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
            output=2,
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
    assert deduped[1].output == 3


def test_dedupe_queries_unhashable_custom_input_does_not_crash() -> None:
    queries = [
        Query(input=_UnhashableInput(7), output=1, tag=QueryTag.TYPICAL),
        Query(input=_UnhashableInput(7), output=2, tag=QueryTag.BOUNDARY),
        Query(input=_UnhashableInput(8), output=3, tag=QueryTag.COVERAGE),
    ]

    deduped = dedupe_queries(queries)
    assert [q.output for q in deduped] == [1, 3]


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
            output=2,
            tag=QueryTag.BOUNDARY,
        ),
    ]

    deduped = dedupe_queries(queries)
    assert len(deduped) == 1
    assert deduped[0].output == 1
