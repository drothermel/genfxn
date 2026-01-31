# genfxn

Synthetic function dataset generator for code reasoning research. Generates executable Python functions with structured test cases.

## Installation

```bash
uv sync
```

## CLI

### Generate Command

```bash
genfxn generate -o OUTPUT -f FAMILY -n COUNT [-s SEED] [OPTIONS]
```

**Required:**
- `-o, --output PATH` - Output JSONL file
- `-f, --family` - `piecewise`, `stateful`, or `all`
- `-n, --count` - Number of tasks to generate

**Optional:**
- `-s, --seed` - Random seed for reproducibility

**Type Filters (constrain what gets generated):**

| Option | Family | Values | Description |
|--------|--------|--------|-------------|
| `--templates` | stateful | `conditional_linear_sum`, `resetting_best_prefix_sum`, `longest_run` | Template types to include |
| `--predicate-types` | stateful | `even`, `odd`, `lt`, `le`, `gt`, `ge`, `mod_eq` | Predicate types to include |
| `--transform-types` | stateful | `identity`, `abs`, `shift`, `negate`, `scale` | Transform types to include |
| `--n-branches` | piecewise | 1-5 | Number of conditional branches |
| `--expr-types` | piecewise | `affine`, `quadratic`, `abs`, `mod` | Expression types to include |

**Range Options (control numeric bounds):**

| Option | Family | Default | Description |
|--------|--------|---------|-------------|
| `--value-range` | both | -100,100 | Range for input/element values |
| `--threshold-range` | both | -50,50 | Range for predicate thresholds |
| `--divisor-range` | both | 2,10 | Range for mod divisors |
| `--coeff-range` | piecewise | -5,5 | Range for expression coefficients |
| `--list-length-range` | stateful | 5,20 | Range for test list lengths |
| `--shift-range` | stateful | -10,10 | Range for shift transform values |
| `--scale-range` | stateful | -5,5 | Range for scale transform factors |

**Examples:**
```bash
# Basic generation
genfxn generate -o tasks.jsonl -f all -n 100 -s 42

# Only longest_run templates with small lists
genfxn generate -o tasks.jsonl -f stateful -n 50 \
    --templates longest_run --list-length-range 3,10

# Only affine piecewise with single branch
genfxn generate -o tasks.jsonl -f piecewise -n 50 \
    --expr-types affine --n-branches 1 --coeff-range -2,2

# Multiple predicate types
genfxn generate -o tasks.jsonl -f stateful -n 100 \
    --predicate-types even,odd,lt,gt
```

### Info Command

```bash
genfxn info tasks.jsonl
```

### Split Command

```bash
genfxn split INPUT --train TRAIN --test TEST [OPTIONS]
```

**Required:**
- `INPUT` - Input JSONL file
- `--train PATH` - Train output JSONL
- `--test PATH` - Test output JSONL

**Split Mode (choose one):**

*Random split:*
- `--random-ratio FLOAT` - Train ratio (0-1), e.g., 0.8 for 80/20 split
- `--seed INT` - Random seed for reproducibility

*Axis holdout:*
- `--holdout-axis PATH` - Dot-path to spec field (e.g., `template`, `predicate.type`)
- `--holdout-value VALUE` - Value to hold out for test set
- `--holdout-type TYPE` - `exact` (default), `range`, or `contains`

**Examples:**
```bash
# Random 80/20 split
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --random-ratio 0.8 --seed 42

# Hold out longest_run for test
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis template --holdout-value longest_run

# Hold out range of branch counts
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis n_branches --holdout-value "3,5" --holdout-type range
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
