from fastapi import APIRouter, HTTPException, Query
from genfxn.core.models import Task
from pydantic import BaseModel

from viewer_api.loader import TaskStore


class TaskSummary(BaseModel):
    """Lightweight task payload for list views."""

    task_id: str
    family: str
    difficulty: int | None = None
    description: str


class TaskListResponse(BaseModel):
    """Paginated task summary response."""

    items: list[TaskSummary]
    total: int
    offset: int
    limit: int


def create_routes(store: TaskStore) -> APIRouter:
    """Create API routes with access to the task store."""
    router = APIRouter(prefix="/api")

    @router.get("/tasks")
    def list_tasks(
        family: str | None = None,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=500),
    ) -> TaskListResponse:
        """List task summaries with optional family filter and pagination."""
        tasks = store.list_tasks(family)
        page = tasks[offset : offset + limit]
        items = [
            TaskSummary(
                task_id=t.task_id,
                family=t.family,
                difficulty=t.difficulty,
                description=t.description,
            )
            for t in page
        ]
        return TaskListResponse(
            items=items,
            total=len(tasks),
            offset=offset,
            limit=limit,
        )

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
