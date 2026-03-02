# genfxn

`genfxn` generates synthetic function tasks for code-reasoning research.
It produces executable tasks with structured queries across 11 families,
rendered in a single target language per task file (`python`, `java`, or `rust`).

Additional docs:
- [AXES.md](AXES.md): full family axes reference
- [TESTING.md](TESTING.md): test and quality command guide

## Quickstart

```bash
uv sync

# Generate 50 Python tasks from all families
uv run genfxn generate -o tasks.jsonl -f all -n 50 -s 42

# Inspect family counts
uv run genfxn info tasks.jsonl
```

## Function Families

| Family | Logical signature | Description |
|---|---|---|
| `piecewise` | `f(x: int) -> int` | Predicate-guarded branch expressions |
| `stateful` | `f(xs: list[int]) -> int` | Iterative accumulator/update patterns |
| `simple_algorithms` | `f(xs: list[int]) -> int` | Frequency/pair/window algorithms with tie/edge semantics |
| `stringrules` | `f(s: str) -> str` | Ordered string predicate/transform rules |
| `stack_bytecode` | `f(xs: list[int]) -> int` | Tiny stack-VM program execution |
| `fsm` | `f(xs: list[int]) -> int` | Finite-state-machine execution |
| `bitops` | `f(x: int) -> int` | Fixed-width bit-operation pipelines |
| `sequence_dp` | `f(a: list[int], b: list[int]) -> int` | Sequence DP alignment variants |
| `intervals` | `f(intervals: list[tuple[int, int]]) -> int` | Interval normalization/coverage/overlap stats |
| `graph_queries` | `f(src: int, dst: int) -> int` | Reachability/hops/cost queries over sampled graph specs |
| `temporal_logic` | `f(xs: list[int]) -> int` | Finite-trace temporal-logic evaluation |

All families are integrated across generation, validation, rendering, and
verification workflows.

## Generation CLI

```bash
uv run genfxn generate -o OUTPUT -f FAMILY -n COUNT [-s SEED] [OPTIONS]
```

### Core options

- `-o, --output PATH`: output JSONL
- `-f, --family`: one of the 11 families or `all` (default `all`)
- `-n, --count`: task count (default `100`)
- `-s, --seed`: random seed
- `-l, --language`: `python`, `java`, or `rust` (default `python`)
- `--skip-generated-style-checks`: skip Java/Rust generated-code quality checks

### Family-specific option groups

- Piecewise: `--n-branches`, `--expr-types`, `--coeff-range`
- Stateful: `--templates`, `--predicate-types`, `--transform-types`,
  `--shift-range`, `--scale-range`
- Simple algorithms: `--algorithm-types`, `--tie-break-modes`,
  `--counting-modes`, `--window-size-range`, `--target-range`
- String rules: `--n-rules`, `--string-predicate-types`,
  `--string-transform-types`, `--overlap-level`, `--string-length-range`

### Shared range options

- `--value-range LO,HI`
- `--threshold-range LO,HI`
- `--divisor-range LO,HI`
- `--list-length-range LO,HI`

Important mappings:
- `sequence_dp --list-length-range` maps to both `len_a_range` and `len_b_range`.
- `intervals --value-range` maps to endpoint range.
- `intervals --list-length-range` maps to interval-count range.
- `graph_queries --value-range` maps to edge weight range and is clamped to
  non-negative values; negative-only ranges are rejected.
- `graph_queries --list-length-range` maps to node-count range.
- `temporal_logic --value-range` sets sequence value range and predicate constant
  range.
- `temporal_logic --list-length-range` maps to sequence length range.

Use [AXES.md](AXES.md) for full default values and complete per-family details.

### Examples

```bash
# Generate from all families
uv run genfxn generate -o tasks.jsonl -f all -n 100

# Java output for one family
uv run genfxn generate -o tasks_java.jsonl -f piecewise -n 25 --language java

# Stateful subset
uv run genfxn generate -o tasks.jsonl -f stateful -n 50 \
  --templates longest_run --list-length-range 3,10

# Sequence DP shorter lengths
uv run genfxn generate -o tasks.jsonl -f sequence_dp -n 50 \
  --list-length-range 2,6

# Graph queries smaller graphs
uv run genfxn generate -o tasks.jsonl -f graph_queries -n 50 \
  --list-length-range 3,6
```

## Generated Code Quality Checks

By default, `uv run genfxn generate ...` runs generated Java/Rust checks after
sampling tasks:
- `google-java-format --dry-run --set-exit-if-changed`
- `javac -Xlint:all -Werror`
- `rustfmt --check`
- `rustc --edition=2021 -D warnings`

Skip flag (local fallback):
- `uv run genfxn generate ... --skip-generated-style-checks`

Deterministic smoke command used in CI:

```bash
uv run python scripts/check_generated_code_quality.py \
  --families all --seed 42 --count-per-family 2 --pool-size 24
```

## Public Verification Sidecars

Generation emits a public verification suite per dataset and fails generation
if verification mismatches are detected:

```bash
uv run genfxn generate -o tasks.jsonl -f all -n 50
```

Layer 2 verification cases are generated with Hypothesis strategies. For
deterministic regeneration, pin the Hypothesis version in `pyproject.toml`,
use fixed verification seeds, and regenerate sidecars from the same task
dataset.

Sidecars are written to (paths are relative to the working directory; for
example, when run from the repo root they default to
`data/verification_cases/`):
- `data/verification_cases/tasks.verification_cases.jsonl`
- `data/verification_cases/tasks.verification_metrics.jsonl`

The output base directory is configured by
`DEFAULT_VERIFICATION_OUTPUT_DIR` (currently `Path("data/verification_cases")`),
so changing the working directory or that value changes where sidecars are
written by commands like `uv run genfxn generate`.

You can verify an existing dataset directly:

```bash
uv run genfxn verify tasks.jsonl
```

Legacy dataset migration/backfill:

```bash
# Backfill spec_id/sem_hash/ast_id into a legacy dataset
uv run python scripts/migrate_dataset_task_ids.py data/all_tasks.jsonl

# Generate verification sidecars for the migrated dataset
uv run python scripts/backfill_verification_cases.py data/all_tasks.jsonl
```

If Layer 2 strategy logic changes, regenerate and recommit sidecars for
affected datasets:

```bash
uv run genfxn verify data/all_tasks.jsonl --regenerate-sidecars
```

## Task JSONL Format

Each line is one task object:

```python
{
    "task_id": "sha256-hash",
    "family": "stateful",
    "spec": { ... },
    "code": "def f(xs): ...",  # or a language->code map when requested via API
    "queries": [
        {"input": [1, 2, 3], "output": 6, "tag": "COVERAGE"},
        {"input": [], "output": 0, "tag": "BOUNDARY"},
    ],
}
```

## Python API

```python
from genfxn.langs.types import Language
from genfxn.piecewise.task import generate_piecewise_task

task = generate_piecewise_task(languages=[Language.PYTHON, Language.JAVA])
print(task.code["python"])
print(task.code["java"])
```

## Semantics and Invariants

- `graph_queries.shortest_path_cost`:
  minimum cost over simple paths (`<= n_nodes - 1` edges), with saturating
  signed-64-bit accumulation and `-1` for unreachable.
- Query dedupe behavior:
  most families dedupe globally by input; relation-style families preserve
  per-tag coverage via per-tag input dedupe.
- Java long-based runtime contract applies to migrated numeric families;
  generated tasks are constrained to parity-safe ranges under validated axes.
- `task_id_from_spec(...)` hashing is container-type-sensitive for
  `list`/`tuple`/`set`/`frozenset` values.

## Testing and CI

For full commands and workflows, use [TESTING.md](TESTING.md).

CI gate (`.github/workflows/ci.yml`) enforces:

```bash
uv sync
uv run python scripts/run_all_checks.py --ci
```

## CLI Reference

```bash
uv run genfxn generate -o OUTPUT -f FAMILY -n COUNT [-s SEED] [OPTIONS]
uv run genfxn info FILE
uv run genfxn verify FILE
```
