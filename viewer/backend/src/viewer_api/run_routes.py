"""API routes for nl_latents runs."""

from fastapi import APIRouter, HTTPException

from viewer_api.run_loader import RunData, RunStore, RunSummary


def create_run_routes(store: RunStore) -> APIRouter:
    """Create API routes for runs."""
    router = APIRouter(prefix="/api/runs")

    @router.get("/tags")
    def list_tags() -> list[str]:
        """List all available tags."""
        return store.get_tags()

    @router.get("/tags/{tag}/models")
    def list_models(tag: str) -> list[str]:
        """List all models for a tag."""
        models = store.get_models(tag)
        if not models:
            raise HTTPException(status_code=404, detail=f"Tag not found: {tag}")
        return models

    @router.get("/{tag}/{model}")
    def list_runs(tag: str, model: str) -> list[RunSummary]:
        """List all runs for a tag/model combination."""
        runs = store.get_runs(tag, model)
        if not runs:
            raise HTTPException(
                status_code=404, detail=f"No runs found for {tag}/{model}"
            )
        return runs

    @router.get("/{tag}/{model}/{run_id}")
    def get_run(tag: str, model: str, run_id: str) -> RunData:
        """Get full run data."""
        run = store.get_run(tag, model, run_id)
        if run is None:
            raise HTTPException(
                status_code=404, detail=f"Run not found: {tag}/{model}/{run_id}"
            )
        return run

    return router
