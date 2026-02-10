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

    def test_continues_after_generator_exceptions(self) -> None:
        attempts = 0

        def gen() -> int:
            nonlocal attempts
            attempts += 1
            if attempts <= 2:
                raise ValueError("transient")
            return attempts

        result = find_satisfying(gen, lambda x: x == 3, max_attempts=5)
        assert result == 3
        assert attempts == 3

    def test_continues_after_predicate_value_errors(self) -> None:
        attempts = 0

        def gen() -> int:
            nonlocal attempts
            attempts += 1
            return attempts

        def pred(value: int) -> bool:
            if value <= 2:
                raise ValueError("bad eval")
            return value == 3

        result = find_satisfying(gen, pred, max_attempts=5)
        assert result == 3

    def test_generator_runtime_errors_fail_soft(self) -> None:
        attempts = 0

        def gen() -> int:
            nonlocal attempts
            attempts += 1
            if attempts <= 2:
                raise RuntimeError("unexpected generator error")
            return attempts

        result = find_satisfying(gen, lambda x: x == 3, max_attempts=5)
        assert result == 3

    def test_predicate_runtime_errors_fail_soft(self) -> None:
        attempts = 0

        def pred(value: int) -> bool:
            nonlocal attempts
            attempts += 1
            if attempts <= 2:
                raise RuntimeError("unexpected predicate error")
            return value == 3

        result = find_satisfying(lambda: 3, pred, max_attempts=5)
        assert result == 3
