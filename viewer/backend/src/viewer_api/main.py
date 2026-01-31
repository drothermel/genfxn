import os
from pathlib import Path

import typer
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from viewer_api.loader import TaskStore
from viewer_api.routes import create_routes

cli = typer.Typer()


def create_app(jsonl_path: Path) -> FastAPI:
    """Create FastAPI app with loaded task store."""
    app = FastAPI(title="genfxn Trace Viewer API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:5174",
            "http://127.0.0.1:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = TaskStore()
    count = store.load_jsonl(jsonl_path)
    print(f"Loaded {count} tasks from {jsonl_path}")

    router = create_routes(store)
    app.include_router(router)

    return app


@cli.command()
def serve(
    jsonl_path: Path = typer.Argument(..., help="Path to JSONL file"),
    host: str = typer.Option("127.0.0.1", help="Host to bind to"),
    port: int = typer.Option(8000, help="Port to bind to"),
) -> None:
    """Start the trace viewer API server."""
    if not jsonl_path.exists():
        raise typer.BadParameter(f"File not found: {jsonl_path}")

    app = create_app(jsonl_path)
    uvicorn.run(app, host=host, port=port)


# For programmatic use: uvicorn viewer_api.main:app (app = FastAPI instance)
# Default path from GENFXN_VIEWER_JSONL env var, or "tasks.jsonl" in cwd.
_default_jsonl = Path(os.environ.get("GENFXN_VIEWER_JSONL", "tasks.jsonl"))
app = create_app(_default_jsonl)

if __name__ == "__main__":
    cli()
