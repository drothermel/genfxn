"""Loader for nl_latents run directories."""

from pathlib import Path

import srsly
from pydantic import BaseModel, ConfigDict, Field


class RunMeta(BaseModel):
    """Metadata from run_meta.json."""

    model_config = ConfigDict(extra="allow")

    run_id: str
    engine: str | None = None
    model: str
    provider: str | None = None
    tag: str
    timestamp_utc: str | None = None
    prompt_name: str | None = None
    prompt_version: int | None = None
    sampling: dict | None = None
    budgets: dict | None = None
    git: dict | None = None
    task: dict | None = None


class ValidationResult(BaseModel):
    """Validation result for a decoder run."""

    model_config = ConfigDict(extra="allow")

    decoder_name: str = Field(description="Name of the decoder (extracted from filename)")
    raw_output: str | None = None
    extracted_code: str | None = None
    has_code_fences: bool | None = None
    is_valid_python: bool | None = None
    python_error: str | None = None
    expected_function_name: str | None = None
    has_expected_function: bool | None = None
    test_pass_rate: float | None = None
    test_case_results: list[dict] | None = None


class RunData(BaseModel):
    """Complete run data including all files."""

    meta: RunMeta
    task_prompt: str | None = None
    system_prompt: str | None = None
    output: str | None = None
    eval: dict | None = Field(default=None, description="output.eval.json if present")
    validations: list[ValidationResult] = Field(
        default_factory=list, description="All validation_*.json files"
    )
    decoder_outputs: dict[str, str] = Field(
        default_factory=dict, description="output_*.txt files keyed by decoder name"
    )


class RunSummary(BaseModel):
    """Summary of a run for list views."""

    run_id: str
    tag: str
    model: str
    task_id: str | None = None
    task_family: str | None = None
    has_eval: bool = False
    has_validation: bool = False
    validation_count: int = 0
    best_pass_rate: float | None = None


class RunStore:
    """Store for loading runs from directory structure."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    def get_tags(self) -> list[str]:
        """List all tag directories."""
        if not self.base_path.exists():
            return []
        return sorted(
            d.name
            for d in self.base_path.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    def get_models(self, tag: str) -> list[str]:
        """List all model directories for a tag."""
        tag_path = self.base_path / tag
        if not tag_path.exists():
            return []
        return sorted(
            d.name for d in tag_path.iterdir() if d.is_dir() and not d.name.startswith(".")
        )

    def get_runs(self, tag: str, model: str) -> list[RunSummary]:
        """List all runs for a tag/model combination."""
        model_path = self.base_path / tag / model
        if not model_path.exists():
            return []

        summaries = []
        for run_dir in model_path.iterdir():
            if not run_dir.is_dir() or run_dir.name.startswith("."):
                continue

            meta_path = run_dir / "run_meta.json"
            if not meta_path.exists():
                continue

            meta_data = srsly.read_json(meta_path)
            task_info = meta_data.get("task", {})

            # Check for validation files
            validation_files = list(run_dir.glob("validation_*.json"))
            best_pass_rate = None
            for vf in validation_files:
                try:
                    vdata = srsly.read_json(vf)
                    rate = vdata.get("test_pass_rate")
                    if rate is not None:
                        if best_pass_rate is None or rate > best_pass_rate:
                            best_pass_rate = rate
                except Exception:
                    pass

            summaries.append(
                RunSummary(
                    run_id=run_dir.name,
                    tag=tag,
                    model=model,
                    task_id=task_info.get("task_id"),
                    task_family=task_info.get("family"),
                    has_eval=(run_dir / "output.eval.json").exists(),
                    has_validation=len(validation_files) > 0,
                    validation_count=len(validation_files),
                    best_pass_rate=best_pass_rate,
                )
            )

        return sorted(summaries, key=lambda r: r.run_id)

    def get_run(self, tag: str, model: str, run_id: str) -> RunData | None:
        """Get full run data for a specific run."""
        run_path = self.base_path / tag / model / run_id
        meta_path = run_path / "run_meta.json"

        if not meta_path.exists():
            return None

        meta = RunMeta.model_validate(srsly.read_json(meta_path))

        # Read text files
        task_prompt = self._read_text(run_path / "task_prompt.txt")
        system_prompt = self._read_text(run_path / "system_prompt.txt")
        output = self._read_text(run_path / "output.txt")

        # Read eval if present
        eval_data = None
        eval_path = run_path / "output.eval.json"
        if eval_path.exists():
            eval_data = srsly.read_json(eval_path)

        # Read all validation files
        validations = []
        for vf in sorted(run_path.glob("validation_*.json")):
            decoder_name = vf.stem.replace("validation_", "")
            vdata = srsly.read_json(vf)
            vdata["decoder_name"] = decoder_name
            validations.append(ValidationResult.model_validate(vdata))

        # Read decoder outputs (output_*.txt files)
        decoder_outputs = {}
        for of in sorted(run_path.glob("output_*.txt")):
            decoder_name = of.stem.replace("output_", "")
            decoder_outputs[decoder_name] = self._read_text(of) or ""

        return RunData(
            meta=meta,
            task_prompt=task_prompt,
            system_prompt=system_prompt,
            output=output,
            eval=eval_data,
            validations=validations,
            decoder_outputs=decoder_outputs,
        )

    def _read_text(self, path: Path) -> str | None:
        """Read text file if it exists."""
        if path.exists():
            return path.read_text()
        return None
