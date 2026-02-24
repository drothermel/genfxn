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
# Lint
uv run ruff check .

# Type check
uv run ty check

# Generated Java/Rust quality checks
uv run python scripts/check_generated_code_quality.py \
  --families all --seed 42 --count-per-family 2 --pool-size 24
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
uv run ruff check .
uv run ty check
uv run python scripts/check_generated_code_quality.py --families all --seed 42 --count-per-family 2 --pool-size 24
uv run pytest tests/ -v --verification-level=full -n auto --dist=worksteal
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

- `lint`: `uv run ruff check .`
- `typecheck`: `uv run ty check`
- `generated-code-quality`: `uv run python scripts/check_generated_code_quality.py --families all --seed 42 --count-per-family 2 --pool-size 24`
- `test-full`: `uv run pytest tests/ -v --verification-level=full -n auto --dist=worksteal`
