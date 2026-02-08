import pytest
from pydantic import ValidationError

from genfxn.core.models import Task
from genfxn.core.validate import Issue, Severity


class TestSeverity:
    def test_enum_values(self) -> None:
        assert Severity.ERROR.value == "error"
        assert Severity.WARNING.value == "warning"

    def test_string_comparison(self) -> None:
        assert Severity.ERROR == "error"
        assert Severity.WARNING == "warning"


class TestIssue:
    def test_serialization_roundtrip(self) -> None:
        issue = Issue(
            code="TEST_CODE",
            severity=Severity.ERROR,
            message="Test message",
            location="test.location",
            task_id="piecewise_abc123",
        )
        data = issue.model_dump()
        restored = Issue.model_validate(data)
        assert restored == issue

    def test_serialization_without_task_id(self) -> None:
        issue = Issue(
            code="TEST_CODE",
            severity=Severity.WARNING,
            message="Test message",
            location="queries[0]",
        )
        data = issue.model_dump()
        assert data["task_id"] is None
        restored = Issue.model_validate(data)
        assert restored.task_id is None

    def test_json_roundtrip(self) -> None:
        issue = Issue(
            code="SEMANTIC_MISMATCH",
            severity=Severity.ERROR,
            message="f(5) = 10, expected 12",
            location="code",
            task_id="piecewise_deadbeef",
        )
        json_str = issue.model_dump_json()
        restored = Issue.model_validate_json(json_str)
        assert restored == issue


def _minimal_task_payload(**overrides: object) -> dict:
    """Minimal Task payload for validation tests."""
    return {
        "task_id": "test_abc123",
        "family": "piecewise",
        "spec": {},
        "code": "def f(): pass",
        "queries": [{"input": 0, "output": 0, "tag": "typical"}],
        "description": "test task",
        **overrides,
    }


class TestTaskDifficultyValidation:
    """Task.difficulty must be None or an int in 1..5."""

    def test_difficulty_none_accepted(self) -> None:
        payload = _minimal_task_payload()
        payload["difficulty"] = None
        task = Task.model_validate(payload)
        assert task.difficulty is None

    def test_difficulty_omitted_defaults_to_none(self) -> None:
        payload = _minimal_task_payload()
        assert "difficulty" not in payload
        task = Task.model_validate(payload)
        assert task.difficulty is None

    def test_difficulty_1_through_5_accepted(self) -> None:
        for d in (1, 2, 3, 4, 5):
            payload = _minimal_task_payload(difficulty=d)
            task = Task.model_validate(payload)
            assert task.difficulty == d

    def test_difficulty_zero_raises(self) -> None:
        payload = _minimal_task_payload(difficulty=0)
        with pytest.raises(ValidationError) as exc_info:
            Task.model_validate(payload)
        err = exc_info.value
        assert "difficulty" in str(err).lower() or any(
            "difficulty" in e.get("loc", ()) for e in err.errors()
        )
        # Message should indicate valid range (1-5)
        msg = str(err).lower()
        assert "1" in msg or "greater" in msg or "least" in msg

    def test_difficulty_six_raises(self) -> None:
        payload = _minimal_task_payload(difficulty=6)
        with pytest.raises(ValidationError) as exc_info:
            Task.model_validate(payload)
        err = exc_info.value
        msg = str(err).lower()
        assert "5" in msg or "less" in msg or "most" in msg

    def test_difficulty_negative_raises(self) -> None:
        payload = _minimal_task_payload(difficulty=-1)
        with pytest.raises(ValidationError) as exc_info:
            Task.model_validate(payload)
        err = exc_info.value
        msg = str(err).lower()
        assert "1" in msg or "greater" in msg or "least" in msg
