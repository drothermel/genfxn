import os
from pathlib import Path

import typer
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from viewer_api.loader import TaskStore
from viewer_api.routes import create_routes
from viewer_api.run_loader import RunStore
from viewer_api.run_routes import create_run_routes

cli = typer.Typer()


def create_app(
    jsonl_path: Path | None = None,
    runs_dir: Path | None = None,
) -> FastAPI:
    """Create FastAPI app with loaded task store and/or run store."""
    app = FastAPI(title="genfxn Trace Viewer API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
            "http://100.111.204.70:5173",
            "http://100.111.204.70:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if jsonl_path is not None:
        store = TaskStore()
        count = store.load_jsonl(jsonl_path)
        print(f"Loaded {count} tasks from {jsonl_path}")
        router = create_routes(store)
        app.include_router(router)

    if runs_dir is not None:
        run_store = RunStore(runs_dir)
        tags = run_store.get_tags()
        print(f"Found {len(tags)} tags in {runs_dir}")
        run_router = create_run_routes(run_store)
        app.include_router(run_router)

    return app


@cli.command()
def serve(
    jsonl_path: Path | None = typer.Argument(
        None, help="Path to JSONL file (optional if --runs-dir provided)"
    ),
    runs_dir: Path | None = typer.Option(
        None, "--runs-dir", help="Path to nl_latents runs directory"
    ),
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
) -> None:
    """Start the trace viewer API server."""
    if jsonl_path is None and runs_dir is None:
        raise typer.BadParameter("Must provide either JSONL_PATH or --runs-dir")

    if jsonl_path is not None and not jsonl_path.exists():
        raise typer.BadParameter(f"File not found: {jsonl_path}")

    if runs_dir is not None and not runs_dir.exists():
        raise typer.BadParameter(f"Directory not found: {runs_dir}")

    app = create_app(jsonl_path, runs_dir)
    uvicorn.run(app, host=host, port=port)


# Lazy app for uvicorn: viewer_api.main:app (no file loading at import time).
_default_jsonl = Path(os.environ.get("GENFXN_VIEWER_JSONL", "tasks.jsonl"))
_default_runs_dir = os.environ.get("GENFXN_VIEWER_RUNS_DIR")
_cached_app: FastAPI | None = None


def get_app() -> FastAPI:
    """Return the FastAPI app, creating it from env vars on first use."""
    global _cached_app
    if _cached_app is None:
        jsonl_path = _default_jsonl if _default_jsonl.exists() else None
        runs_dir = Path(_default_runs_dir) if _default_runs_dir else None
        _cached_app = create_app(jsonl_path, runs_dir)
    return _cached_app


class _LazyASGI:
    """ASGI callable that delegates to get_app() on first request."""

    async def __call__(self, scope, receive, send):
        await get_app()(scope, receive, send)


app = _LazyASGI()

if __name__ == "__main__":
    cli()
