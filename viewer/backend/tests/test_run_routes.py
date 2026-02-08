import json
import sys
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from viewer_api.run_loader import RunStore
from viewer_api.run_routes import create_run_routes


def _make_app(base: Path) -> TestClient:
    app = FastAPI()
    app.include_router(create_run_routes(RunStore(base)))
    return TestClient(app)


def _write_good_run(base: Path, tag: str, model: str, run_id: str) -> Path:
    run_dir = base / tag / model / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "model": model,
                "tag": tag,
                "task": {"task_id": "t1", "family": "piecewise"},
            }
        )
    )
    return run_dir


def test_path_traversal_rejected(tmp_path: Path) -> None:
    client = _make_app(tmp_path)

    _write_good_run(tmp_path, "goodtag", "goodmodel", "run-1")
    outside = tmp_path.parent / "run_meta.json"
    outside.write_text('{"run_id":"x"}')

    assert client.get("/api/runs/tags/%2E%2E/models").status_code == 400
    assert client.get("/api/runs/%2E%2E/goodmodel").status_code == 400
    assert client.get("/api/runs/goodtag/%2E%2E/run-1").status_code == 400


def test_malformed_summary_files_are_skipped(tmp_path: Path) -> None:
    _write_good_run(tmp_path, "tag", "model", "run-good")
    bad_dir = tmp_path / "tag" / "model" / "run-bad"
    bad_dir.mkdir(parents=True)
    (bad_dir / "run_meta.json").write_text("not-json")

    client = _make_app(tmp_path)
    response = client.get("/api/runs/tag/model")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["run_id"] == "run-good"


def test_malformed_run_detail_returns_422(tmp_path: Path) -> None:
    run_dir = _write_good_run(tmp_path, "tag", "model", "run-1")
    (run_dir / "validation_decoder.json").write_text("{bad json")

    client = _make_app(tmp_path)
    response = client.get("/api/runs/tag/model/run-1")

    assert response.status_code == 422


def test_non_utf8_decoder_output_is_tolerated(tmp_path: Path) -> None:
    run_dir = _write_good_run(tmp_path, "tag", "model", "run-1")
    (run_dir / "output_decoder.txt").write_bytes(b"ok\xffbad")

    client = _make_app(tmp_path)
    response = client.get("/api/runs/tag/model/run-1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["decoder_outputs"]["decoder"] == "ok\ufffdbad"


def test_runs_summary_cache_invalidates_on_meta_change(tmp_path: Path) -> None:
    run_dir = _write_good_run(tmp_path, "tag", "model", "run-1")
    client = _make_app(tmp_path)

    first = client.get("/api/runs/tag/model")
    assert first.status_code == 200
    assert first.json()[0]["task_id"] == "t1"

    time.sleep(0.001)
    (run_dir / "run_meta.json").write_text(
        json.dumps(
            {
                "run_id": "run-1",
                "model": "model",
                "tag": "tag",
                "task": {"task_id": "t2", "family": "piecewise"},
            }
        )
    )
    second = client.get("/api/runs/tag/model")
    assert second.status_code == 200
    assert second.json()[0]["task_id"] == "t2"
