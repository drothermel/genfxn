# genfxn

Synthetic function dataset generator for code reasoning research. Generates executable Python functions with structured test cases.

## Installation

```bash
uv sync
```

## CLI

```bash
# Generate tasks
genfxn generate -o tasks.jsonl -f all -n 100 -s 42

# Show info
genfxn info tasks.jsonl

# Split with axis holdouts
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis template --holdout-value longest_run
```

## Viewer

Web UI for browsing generated tasks.

```bash
# 1. Generate tasks
uv run genfxn generate -o tasks.jsonl -n 50

# 2. Start backend (from repo root)
cd viewer/backend && uv run viewer-api serve ../../tasks.jsonl --port 8000

# 3. Start frontend (separate terminal)
cd viewer/frontend && bun dev
```

Open http://localhost:5173 to browse tasks.

## Function Families

### Piecewise (`int -> int`)

Conditional functions with predicate-guarded branches:

```python
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.piecewise.models import PiecewiseAxes, ExprType

axes = PiecewiseAxes(n_branches=2, expr_types=[ExprType.AFFINE])
task = generate_piecewise_task(axes)

print(task.code)      # Generated Python function
print(task.queries)   # Test cases with coverage tags
```

### Stateful (`list[int] -> int`)

Iteration functions with accumulator state:

```python
from genfxn.stateful.task import generate_stateful_task
from genfxn.stateful.models import StatefulAxes, TemplateType

axes = StatefulAxes(templates=[TemplateType.CONDITIONAL_LINEAR_SUM])
task = generate_stateful_task(axes)

print(task.code)      # Generated Python function
print(task.queries)   # Test cases with coverage tags
```

Three templates available:
- **ConditionalLinearSum**: Accumulates with predicate-based transforms
- **ResettingBestPrefixSum**: Tracks best sum with reset conditions
- **LongestRun**: Counts longest consecutive run matching predicate

## Splits

Split datasets using axis holdouts for generalization studies. Tasks matching the holdout go to test; all others go to train.

```bash
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis template --holdout-value longest_run
```

Holdout types:
- `exact`: Value equals holdout (default)
- `range`: Value in range, e.g. `--holdout-value "3,5"` for values 3-5
- `contains`: Value contains substring

### Available Axes

Axes use dot-path notation to access nested spec fields (e.g., `predicate.type`). List indices are supported (e.g., `branches.0.expr.kind`).

#### Stateful

| Axis | Values | Effect |
|------|--------|--------|
| `template` | `conditional_linear_sum`, `resetting_best_prefix_sum`, `longest_run` | **Difficulty**: `longest_run` < `conditional_linear_sum` < `resetting_best_prefix_sum` (tracking best requires more state) |
| `predicate.type` | `even`, `odd`, `lt`, `le`, `gt`, `ge`, `mod_eq` | Distribution shift (structurally similar) |
| `true_transform.type`, `false_transform.type` | `identity`, `abs`, `shift`, `negate`, `scale` | Distribution shift; `identity` is simplest |

#### Piecewise

| Axis | Values | Effect |
|------|--------|--------|
| `default_expr.kind` | `affine`, `quadratic`, `abs`, `mod` | **Difficulty**: `affine` < `abs` < `mod` < `quadratic` |
| `branches.N.expr.kind` | Same as above | Expression type in branch N |
| `branches.N.condition.type` | `even`, `odd`, `lt`, `le`, `gt`, `ge`, `mod_eq`, `in_set` | Distribution shift |

Note: `n_branches` (number of branches) increases difficulty but isn't directly splittable—it's a generation-time parameter in `PiecewiseAxes`.

### Python API

```python
from genfxn.splits import AxisHoldout, HoldoutType, split_tasks

holdouts = [AxisHoldout(
    axis_path="template",
    holdout_type=HoldoutType.EXACT,
    holdout_value="longest_run",
)]
result = split_tasks(tasks, holdouts)
# result.train: tasks not matching holdout
# result.test: tasks matching holdout
```

## Demos

```bash
uv run python scripts/demo_phase1_dsl.py       # Core DSL building blocks
uv run python scripts/demo_phase2_piecewise.py # Piecewise function generation
uv run python scripts/demo_phase3_stateful.py  # Stateful function generation
uv run python scripts/demo_phase4_splits.py    # Axis-heldout splits
uv run python scripts/demo_phase5_cli.py       # CLI usage
```

## Tests

```bash
uv run pytest tests/ -v
```
