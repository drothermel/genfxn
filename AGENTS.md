# Repository Guidelines

## Project Structure & Module Organization
Core Python package code lives in `src/genfxn/`. Family-specific generators are in:
- `src/genfxn/piecewise/`
- `src/genfxn/stateful/`
- `src/genfxn/simple_algorithms/`
- `src/genfxn/stringrules/`

Shared logic (models, validation, difficulty, tracing, presets) is in `src/genfxn/core/` and dataset splitting in `src/genfxn/splits.py`. Tests are in `tests/` with one module per feature area (for example `tests/test_stateful.py`, `tests/test_cli.py`). Utility and demo scripts are in `scripts/`. The viewer is split into `viewer/backend/` (FastAPI) and `viewer/frontend/` (SvelteKit).

## Build, Test, and Development Commands
- `uv sync`: install Python dependencies (root project).
- `uv run pytest tests/ -v`: run the full Python test suite.
- `uv run ruff check .`: run lint checks.
- `uv run genfxn generate -f all -n 20 -o /tmp/tasks.jsonl`: generate sample tasks.
- `uv run genfxn split /tmp/tasks.jsonl --train /tmp/train.jsonl --test /tmp/test.jsonl --random-ratio 0.8 --seed 42`: split dataset.
- `cd viewer/backend && uv run viewer-api /tmp/tasks.jsonl`: start backend API.
- `cd viewer/frontend && bun dev`: run frontend locally.

## Coding Style & Naming Conventions
Target Python is 3.12 with `ruff` enforcing style (`line-length = 80`, import sorting via `I`). Use 4-space indentation, type hints, and `snake_case` for functions/modules. Keep models and enums explicit (see `models.py` patterns in each family). For Svelte/TypeScript in `viewer/frontend/`, use existing component naming conventions like `*-card.svelte` and route-based files under `src/routes/`.

## Testing Guidelines
Use `pytest`; add tests under `tests/` as `test_<feature>.py`. Prefer focused unit tests near touched behavior and include CLI coverage when changing `src/genfxn/cli.py`. For generators/validators, test both valid and invalid cases plus deterministic behavior with fixed seeds.

## Commit & Pull Request Guidelines
Recent commits use short, imperative summaries (for example: `fix hashing to ensure reproducibility`, `balanced sampling script`). Keep subject lines concise and specific; optionally include PR references like `(#11)`. PRs should include:
- What changed and why.
- Linked issue/context.
- Test evidence (commands run and outcomes).
- Screenshots/GIFs for viewer UI changes.
