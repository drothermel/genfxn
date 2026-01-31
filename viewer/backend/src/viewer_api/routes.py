from fastapi import APIRouter, HTTPException
from genfxn.core.models import Task

from viewer_api.loader import TaskStore

router = APIRouter(prefix="/api")


def create_routes(store: TaskStore) -> APIRouter:
    """Create API routes with access to the task store."""

    @router.get("/tasks")
    def list_tasks(family: str | None = None) -> list[Task]:
        """List all tasks, optionally filtered by family."""
        return store.list_tasks(family)

    @router.get("/tasks/{task_id}")
    def get_task(task_id: str) -> Task:
        """Get a single task by ID."""
        task = store.get_task(task_id)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return task

    @router.get("/families")
    def list_families() -> list[str]:
        """List available task families."""
        return store.get_families()

    return router
