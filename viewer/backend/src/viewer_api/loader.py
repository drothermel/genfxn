from pathlib import Path

import srsly
from genfxn.core.models import Task


class TaskStore:
    """In-memory store for tasks loaded from JSONL."""

    def __init__(self) -> None:
        self._tasks: dict[str, Task] = {}

    def load_jsonl(self, path: Path) -> int:
        """Load tasks from JSONL file. Returns count of lines processed."""
        total_loaded = 0
        for line in srsly.read_jsonl(path):
            task = Task.model_validate(line)
            self._tasks[task.task_id] = task
            total_loaded += 1
        return total_loaded

    def list_tasks(self, family: str | None = None) -> list[Task]:
        """List all tasks, optionally filtered by family."""
        tasks = list(self._tasks.values())
        if family:
            tasks = [t for t in tasks if t.family == family]
        return tasks

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def get_families(self) -> list[str]:
        """Get list of unique families."""
        return sorted({t.family for t in self._tasks.values()})

    @property
    def count(self) -> int:
        return len(self._tasks)
