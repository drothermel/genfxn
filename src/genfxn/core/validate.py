from enum import Enum

from pydantic import BaseModel, Field

WRONG_FAMILY = "WRONG_FAMILY"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"


class Issue(BaseModel):
    code: str = Field(description="Issue code, e.g. TASK_ID_MISMATCH")
    severity: Severity = Field(description="Error or warning")
    message: str = Field(description="Human-readable description")
    location: str = Field(description="Path to issue, e.g. queries[7]")
    task_id: str | None = Field(
        default=None, description="Task ID for dataset-scale aggregation"
    )
