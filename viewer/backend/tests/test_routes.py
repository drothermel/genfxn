import sys
from pathlib import Path

import srsly
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from viewer_api.main import create_app


def _write_tasks(path: Path) -> None:
    srsly.write_jsonl(
        path,
        [
            {
                "task_id": "t1",
                "family": "piecewise",
                "spec": {"a": 1},
                "code": "def f(x): return x",
                "queries": [{"input": 1, "output": 1, "tag": "typical"}],
                "description": "task one",
                "difficulty": 1,
            },
            {
                "task_id": "t2",
                "family": "stateful",
                "spec": {"b": 2},
                "code": "def f(x): return x + 1",
                "queries": [{"input": 2, "output": 3, "tag": "boundary"}],
                "description": "task two",
                "difficulty": 2,
            },
            {
                "task_id": "t3",
                "family": "piecewise",
                "spec": {"c": 3},
                "code": "def f(x): return x - 1",
                "queries": [{"input": 3, "output": 2, "tag": "coverage"}],
                "description": "task three",
                "difficulty": 3,
            },
        ],
    )


def test_tasks_list_returns_paginated_summaries(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "tasks.jsonl"
    _write_tasks(jsonl_path)
    client = TestClient(create_app(jsonl_path=jsonl_path))

    response = client.get("/api/tasks?offset=1&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["offset"] == 1
    assert payload["limit"] == 1
    assert len(payload["items"]) == 1
    assert payload["items"][0] == {
        "task_id": "t2",
        "family": "stateful",
        "difficulty": 2,
        "description": "task two",
    }


def test_tasks_filter_and_detail_payload(tmp_path: Path) -> None:
    jsonl_path = tmp_path / "tasks.jsonl"
    _write_tasks(jsonl_path)
    client = TestClient(create_app(jsonl_path=jsonl_path))

    list_response = client.get("/api/tasks?family=piecewise")
    assert list_response.status_code == 200
    list_payload = list_response.json()
    assert list_payload["total"] == 2
    assert [item["task_id"] for item in list_payload["items"]] == ["t1", "t3"]
    assert "spec" not in list_payload["items"][0]
    assert "queries" not in list_payload["items"][0]
    assert "code" not in list_payload["items"][0]

    detail_response = client.get("/api/tasks/t1")
    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["task_id"] == "t1"
    assert detail_payload["spec"] == {"a": 1}
    assert detail_payload["queries"] == [
        {"input": 1, "output": 1, "tag": "typical"}
    ]
    assert detail_payload["code"] == "def f(x): return x"
