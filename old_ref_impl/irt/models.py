from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


class RequestedControls(BaseModel):
    temperature: float | None = None
    top_p: float | None = None
    reasoning_effort: str | None = None


class EffectiveControls(BaseModel):
    temperature: float | None = None
    top_p: float | None = None
    reasoning_effort: str | None = None


class ItemRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    task_id: str
    family: str
    spec_id: str
    sem_hash: str
    stratum_cell: str
    stratum_fields: dict[str, str]
    spec: dict[str, Any]
    description: str
    created_at: str = Field(default_factory=utc_now_iso)


class EvalCaseInputRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    case_id: str
    input: Any


class EvalCaseExpectedRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    case_id: str
    expected_output: Any


class ResponseRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item_id: str
    family: str
    task_id: str
    respondent_id: str
    provider: str
    model: str
    repeat_index: int = Field(ge=1)
    n_cases_total: int = Field(ge=0)
    n_cases_correct: int = Field(ge=0)
    correct: bool
    requested_controls: RequestedControls | dict[str, Any] = Field(
        default_factory=RequestedControls
    )
    effective_controls: EffectiveControls | dict[str, Any] = Field(
        default_factory=EffectiveControls
    )
    parse_error: bool = False
    runtime_error: bool = False
    timeout: bool = False
    raw_response_ref: str | None = None
    run_id: str
    timestamp_utc: str = Field(default_factory=utc_now_iso)


class ItemParameterRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    model_type: str
    family: str
    item_id: str
    b: float
    b_se: float | None = None
    a: float | None = None
    a_se: float | None = None


class RespondentParameterRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    model_type: str
    family: str
    respondent_id: str
    theta: float
    theta_se: float | None = None
    base_respondent_id: str


class DifficultyBinRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    scope: str
    family: str | None = None
    item_id: str
    b: float
    bin: int = Field(ge=1, le=5)
    quantile_edges: list[float]


class AnchorItemParameter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    family: str
    item_id: str
    a: float
    b: float


class AnchorsFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    schema_version: str
    model_type: str
    created_at: str = Field(default_factory=utc_now_iso)
    items: list[AnchorItemParameter]


class ThetaScoreRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    family: str
    respondent_id: str
    base_respondent_id: str
    theta: float
    theta_se: float | None = None
    n_items: int = Field(ge=0)


class ThetaModelSummaryRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fit_id: str
    family: str
    base_respondent_id: str
    theta_mean: float
    theta_std: float
    n_repeats: int = Field(ge=0)
