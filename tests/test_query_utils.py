"""Tests for core.query_utils."""

from genfxn.core.query_utils import find_satisfying


class TestFindSatisfying:
    def test_finds_value_when_possible(self) -> None:
        counter = 0

        def gen() -> int:
            nonlocal counter
            counter += 1
            return counter

        result = find_satisfying(gen, lambda x: x == 5)
        assert result == 5
        assert counter == 5

    def test_returns_none_when_unsatisfiable(self) -> None:
        result = find_satisfying(lambda: 1, lambda x: x > 10, max_attempts=20)
        assert result is None

    def test_respects_max_attempts(self) -> None:
        counter = 0

        def gen() -> int:
            nonlocal counter
            counter += 1
            return counter

        result = find_satisfying(gen, lambda x: False, max_attempts=10)
        assert result is None
        assert counter == 10

    def test_returns_first_match(self) -> None:
        values = iter([3, 7, 5, 7])
        result = find_satisfying(lambda: next(values), lambda x: x >= 5)
        assert result == 7
