# Testing and Code Quality

This guide is the source of truth for running local quality gates and matching
CI behavior.

## Setup

Run from repo root:

```bash
uv sync
```

If you run generated Java formatting checks locally, install
`google-java-format` once:

```bash
mkdir -p "$HOME/.local/bin" "$HOME/.local/share"
curl -sSL \
  -o "$HOME/.local/share/google-java-format-1.34.1-all-deps.jar" \
  "https://github.com/google/google-java-format/releases/download/v1.34.1/google-java-format-1.34.1-all-deps.jar"
cat > "$HOME/.local/bin/google-java-format" <<'SH'
#!/usr/bin/env bash
exec java -jar "$HOME/.local/share/google-java-format-1.34.1-all-deps.jar" "$@"
SH
chmod +x "$HOME/.local/bin/google-java-format"
export PATH="$HOME/.local/bin:$PATH"
```

## One-Command Full Gate

```bash
# Local (auto-fixes format/lint where configured)
uv run python scripts/run_all_checks.py

# CI mode (no write-back; fails if fixes would be needed)
uv run python scripts/run_all_checks.py --ci
```

## Verification Tiers

```bash
# Fast: skips slow + full
uv run pytest tests/ -v --verification-level=fast -n auto --dist=worksteal

# Standard: skips full
uv run pytest tests/ -v --verification-level=standard -n auto --dist=worksteal

# Full: runs everything
uv run pytest tests/ -v --verification-level=full -n auto --dist=worksteal
```

Notes:
- Runtime parity suites are marked `@pytest.mark.full`, so they require
  `--verification-level=full`.
- Pytest default parallelization comes from `pyproject.toml` (`-n auto`).
  Use `-n 0` for single-process debugging.

## Core Quality Commands

```bash
# Format all Python files
uv run ruff format .

# Lint with AGENTS scope
uv run ruff check --fix src/ tests/ scripts/

# Blocking lint scope after autofix
uv run ruff check src/

# Type check (AGENTS blocking scope)
uv run ty check src

# Generated Java/Rust quality checks
uv run python scripts/check_generated_code_quality.py \
  --families all --seed 42 --count-per-family 2 --pool-size 24

# Full verification tests
uv run pytest tests/ -v --verification-level=full -n auto --dist=worksteal
```

## Recommended Local Flows

```bash
# Quick local confidence
uv run ruff check .
uv run ty check
uv run pytest tests/ -v --verification-level=fast -n auto --dist=worksteal
```

```bash
# Pre-PR confidence
uv run ruff check .
uv run ty check
uv run python scripts/check_generated_code_quality.py --families all --seed 42 --count-per-family 2 --pool-size 24
uv run pytest tests/ -v --verification-level=standard -n auto --dist=worksteal
```

```bash
# Full CI-equivalent run
uv run python scripts/run_all_checks.py --ci
```

## Family-Scoped Full Markers

```bash
# Example: piecewise-only full tests
uv run pytest tests/ -v --verification-level=full -m "full_piecewise"
```

Available families have matching markers like `full_stateful`,
`full_sequence_dp`, `full_graph_queries`, etc.

## CI Mapping

Current CI jobs (`.github/workflows/ci.yml`) map directly to:

- `all-checks`: `uv run python scripts/run_all_checks.py --ci`
