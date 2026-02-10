# Repository Guidelines

## Project Structure & Module Organization
Core Python package code lives in `src/genfxn/`. Family-specific generators are in:
- `src/genfxn/piecewise/`
- `src/genfxn/stateful/`
- `src/genfxn/simple_algorithms/`
- `src/genfxn/stringrules/`

Shared logic (models, validation, difficulty, tracing, presets) is in `src/genfxn/core/` and dataset splitting in `src/genfxn/splits.py`. Tests are in `tests/` with one module per feature area (for example `tests/test_stateful.py`, `tests/test_cli.py`). Utility and demo scripts are in `scripts/`.

## Family Roadmap
New family work is sequenced using `docs/shared_rec_list.md`. When selecting
the next family to implement, follow that list in order unless explicitly
reprioritized in a newer planning document.

## Build, Test, and Development Commands
- `uv sync`: install Python dependencies (root project).
- `uv run pytest tests/ -v --verification-level=standard`: run the default suite (skips `@pytest.mark.full`).
- `uv run pytest tests/ -v --verification-level=full`: run the full Python test suite (includes `@pytest.mark.full`).
- `uv run ruff check .`: run lint checks.
- `uv run ty check`: run static type checks (expected pre-commit).
- `uv run genfxn generate -f all -n 20 -o /tmp/tasks.jsonl`: generate sample tasks.
- `uv run genfxn split /tmp/tasks.jsonl --train /tmp/train.jsonl --test /tmp/test.jsonl --random-ratio 0.8 --seed 42`: split dataset.

### Agent Tooling Rule
When running Python tooling in this repo, always use `uv run ...` rather than
invoking binaries directly. This includes `python`, `pytest`, `ruff`, `ty`, and
related Python CLI tools.

## Coding Style & Naming Conventions
Target Python is 3.12 with `ruff` enforcing style (`line-length = 80`, import sorting via `I`). Use 4-space indentation, type hints, and `snake_case` for functions/modules. Keep models and enums explicit (see `models.py` patterns in each family).

## Testing Guidelines
Use `pytest`; add tests under `tests/` as `test_<feature>.py`. Prefer focused unit tests near touched behavior and include CLI coverage when changing `src/genfxn/cli.py`. For generators/validators, test both valid and invalid cases plus deterministic behavior with fixed seeds.

### Required Gate For New Families
Any new family must include an executable cross-language runtime parity test
harness (Python vs Java vs Rust) before the family is considered complete or
merge-ready. Renderer-only string tests are not sufficient. The parity harness
must execute generated/runtime code and assert equal outputs for the same specs
and inputs across supported languages.

## Commit & Pull Request Guidelines
Recent commits use short, imperative summaries (for example: `fix hashing to ensure reproducibility`, `balanced sampling script`). Keep subject lines concise and specific; optionally include PR references like `(#11)`. PRs should include:
- What changed and why.
- Linked issue/context.
- Test evidence (commands run and outcomes).
- Screenshots/GIFs for UI changes if applicable.

<!-- CODEX-CONTEXT-SYNC: DO NOT EDIT BELOW THIS LINE -->

# CLAUDE.md

# genfxn Project Instructions

## Task Families

- `piecewise` - Piecewise functions with branches
- `stateful` - Stateful list processing (longest_run, conditional_linear_sum, resetting_best_prefix_sum)
- `simple_algorithms` - Simple algorithms (most_frequent, count_pairs_sum, max_window_sum)
- `stringrules` - String transformation rules with predicates

## Family Roadmap

We are implementing new families in the order tracked by
`docs/shared_rec_list.md`. Treat that file as the source-of-truth ordering
unless a newer planning doc explicitly supersedes it.

## Core Modules

- `src/genfxn/core/difficulty.py` - Difficulty scoring (1-5) per family
- `src/genfxn/core/describe.py` - Natural language task descriptions
- `src/genfxn/{family}/task.py` - Task generation entry points

## Family Quality Gate

No new family should be added or marked complete without an executable
cross-language runtime parity test harness.

Required:
- Runtime parity tests must execute code (not only inspect rendered strings).
- Tests must compare Python, Java, and Rust outputs on the same specs/inputs.
- Parity harness coverage must be part of the family's test evidence in PRs.
