# genfxn

Synthetic function dataset generator for code reasoning research. Generates
executable function tasks with structured test cases across ten function
families. CLI output is single-language (Python by default, or Java/Rust via
`--language`).

## Installation

```bash
uv sync
```

## Function Families

| Family | Signature | Description |
|--------|-----------|-------------|
| **piecewise** | `f(x: int) -> int` | Conditional functions with predicate-guarded branches |
| **stateful** | `f(xs: list[int]) -> int` | Iteration with accumulator state (sums, runs, resets) |
| **simple_algorithms** | `f(xs: list[int]) -> int` | Algorithms with subtle edge cases (frequency, pairs, windows) |
| **stringrules** | `f(s: str) -> str` | Ordered pattern matching with first-match-wins precedence |
| **stack_bytecode** | `f(xs: list[int]) -> int` | Small stack-machine programs with controlled runtime semantics |
| **fsm** | `f(xs: list[int]) -> int` | Finite-state machine execution over integer sequences |
| **bitops** | `f(x: int) -> int` | Fixed-width bit-operation pipelines over integer inputs |
| **sequence_dp** | `f(a: list[int], b: list[int]) -> int` | Sequence dynamic-programming alignment variants with custom scoring |
| **intervals** | `f(intervals: list[tuple[int, int]]) -> int` | Interval normalization/merging statistics under configurable boundary modes |
| **graph_queries** | `f(src: int, dst: int) -> int` | Deterministic graph-query evaluation (`reachable`, `min_hops`, `shortest_path_cost`) |

### Family Roadmap

New family implementation is being done in the prioritized order documented in
`docs/shared_rec_list.md`.

### Piecewise

Branching functions that apply different expressions based on input conditions.

```python
def f(x: int) -> int:
    if x % 2 == 0:
        return 2 * x + 1
    elif x < 10:
        return abs(x - 5)
    else:
        return x * x
```

**Templates**: Affine (`a*x + b`), quadratic, absolute value, modulo expressions.

### Stateful

Functions that iterate over lists maintaining state.

```python
def f(xs: list[int]) -> int:
    acc = 0
    for x in xs:
        if x > 0:
            acc = acc + x
        else:
            acc = acc - 1
    return acc
```

**Templates**: `conditional_linear_sum`, `resetting_best_prefix_sum`, `longest_run`

### Simple Algorithms

Classic algorithms with semantic distinctions that test edge case handling.

```python
def f(xs: list[int]) -> int:
    # Find most frequent element (tie-break: smallest)
    counts = {}
    for x in xs:
        counts[x] = counts.get(x, 0) + 1
    max_count = max(counts.values())
    candidates = [v for v, c in counts.items() if c == max_count]
    return min(candidates)
```

**Templates**: `most_frequent` (tie-break modes), `count_pairs_sum` (counting modes), `max_window_sum`

### String Rules

Ordered if/elif chains matching string predicates and applying transforms.

```python
def f(s: str) -> str:
    if s.startswith("hello"):
        return s.upper()
    elif s.isdigit():
        return s[::-1]
    else:
        return s.lower()
```

**Key axis**: `overlap_level` controls how much rules can shadow each other.

### Stack Bytecode

Programs are sampled as instruction sequences for a tiny stack VM with bounded
execution and explicit runtime status codes.

### FSM

Finite-state machines process each integer input step-by-step using ordered
transitions and configurable behavior when no transition matches.

### Bitops

Fixed-width pipelines over integer inputs using bitwise and shift/rotate
operations, with output masked to the configured width.

### Sequence DP

Alignment-style dynamic programming over two integer sequences with
configurable matching predicates, scoring profile, tie-break order, and output
mode (`score`, `alignment_len`, or `gap_count`).

### Intervals

Interval operations over integer endpoints with explicit boundary handling
(`closed_closed`, `closed_open`, `open_closed`, `open_open`), touching-merge
control, endpoint clipping/quantization (`endpoint_clip_abs`,
`endpoint_quantize_step`), and configurable output operation
(`total_coverage`, `merged_count`, `max_overlap_count`, `gap_count`).

### Graph Queries

Graph query tasks over a fixed spec graph where each query asks for
`reachable`, `min_hops`, or `shortest_path_cost` between two nodes under
deterministic normalization and path semantics.

## Generation

Generate tasks to JSONL files.

```bash
genfxn generate -o OUTPUT -f FAMILY -n COUNT [-s SEED] [OPTIONS]
```

### Required Options

| Option | Description |
|--------|-------------|
| `-o, --output PATH` | Output JSONL file |
| `-f, --family` | `piecewise`, `stateful`, `simple_algorithms`, `stringrules`, `stack_bytecode`, `fsm`, `bitops`, `sequence_dp`, `intervals`, `graph_queries`, or `all` |
| `-n, --count INT` | Number of tasks to generate |

### General Options

| Option | Description |
|--------|-------------|
| `-s, --seed INT` | Random seed for reproducibility |
| `-l, --language` | Single language output: `python`, `java`, or `rust` |

### Piecewise Options

| Option | Values | Description |
|--------|--------|-------------|
| `--n-branches INT` | 1-5 | Number of conditional branches |
| `--expr-types` | `affine`, `quadratic`, `abs`, `mod` | Expression types (comma-separated) |
| `--coeff-range LO,HI` | e.g., `-5,5` | Coefficient range for expressions |

### Stateful Options

| Option | Values | Description |
|--------|--------|-------------|
| `--templates` | `conditional_linear_sum`, `resetting_best_prefix_sum`, `longest_run` | Template types (comma-separated) |
| `--predicate-types` | `even`, `odd`, `lt`, `le`, `gt`, `ge`, `mod_eq` | Predicate types (comma-separated) |
| `--transform-types` | `identity`, `abs`, `shift`, `negate`, `scale` | Transform types (comma-separated) |
| `--list-length-range LO,HI` | e.g., `5,20` | Range for test list lengths |
| `--shift-range LO,HI` | e.g., `-10,10` | Range for shift transform values |
| `--scale-range LO,HI` | e.g., `-5,5` | Range for scale transform factors |

### Simple Algorithms Options

| Option | Values | Description |
|--------|--------|-------------|
| `--algorithm-types` | `most_frequent`, `count_pairs_sum`, `max_window_sum` | Algorithm templates (comma-separated) |
| `--tie-break-modes` | `smallest`, `first_seen` | Tie-break semantics for most_frequent |
| `--counting-modes` | `all_indices`, `unique_values` | Counting mode for count_pairs_sum |
| `--window-size-range LO,HI` | e.g., `1,10` | Window size range for max_window_sum |
| `--target-range LO,HI` | e.g., `-50,50` | Target sum range for count_pairs_sum |

### String Rules Options

| Option | Values | Description |
|--------|--------|-------------|
| `--n-rules INT` | 1-8 | Number of rules in the if/elif chain |
| `--string-predicate-types` | `starts_with`, `ends_with`, `contains`, `is_alpha`, `is_digit`, `is_upper`, `is_lower`, `length_cmp` | Predicate types (comma-separated) |
| `--string-transform-types` | `identity`, `lowercase`, `uppercase`, `capitalize`, `swapcase`, `reverse`, `replace`, `strip`, `prepend`, `append` | Transform types (comma-separated) |
| `--overlap-level` | `none`, `low`, `high` | How much rules can shadow each other |
| `--string-length-range LO,HI` | e.g., `1,20` | Range for input string lengths |

### Shared Range Options

These apply to multiple families:

| Option | Families | Default | Description |
|--------|----------|---------|-------------|
| `--value-range LO,HI` | all | family-specific | Range for input/element values (`-100,100` for piecewise/stateful/simple_algorithms/stringrules, `-50,50` for stack_bytecode, `-20,20` for fsm/sequence_dp, `-20,20` for intervals endpoints, `0,20` effective for graph_queries weights, `-1024,1024` for bitops) |
| `--threshold-range LO,HI` | piecewise, stateful, fsm | family-specific | Range for predicate thresholds (`-50,50` for piecewise/stateful, `-10,10` for fsm) |
| `--divisor-range LO,HI` | piecewise, stateful, fsm, sequence_dp | family-specific | Range for mod divisors (`2,10` for piecewise/stateful/fsm, `1,10` for sequence_dp) |
| `--list-length-range LO,HI` | stateful, simple_algorithms, stack_bytecode, sequence_dp, intervals, graph_queries | family-specific | Range for test list lengths (`5,20` for stateful/simple_algorithms, `0,8` for stack_bytecode, `2,10` for sequence_dp, `0,10` for intervals query interval-counts, mapped to `n_nodes_range` for graph_queries) |

### Examples

```bash
# Generate 100 tasks from all families
genfxn generate -o tasks.jsonl -f all -n 100

# Generate with seed for reproducibility
genfxn generate -o tasks.jsonl -f stateful -n 50 -s 42

# Generate Java output
genfxn generate -o tasks_java.jsonl -f piecewise -n 25 --language java

# Only longest_run with small lists
genfxn generate -o tasks.jsonl -f stateful -n 50 \
    --templates longest_run --list-length-range 3,10

# Only affine piecewise with single branch
genfxn generate -o tasks.jsonl -f piecewise -n 50 \
    --expr-types affine --n-branches 1 --coeff-range -2,2

# Most frequent with first_seen tie-break only
genfxn generate -o tasks.jsonl -f simple_algorithms -n 50 \
    --algorithm-types most_frequent --tie-break-modes first_seen

# String rules with high overlap (tests rule precedence)
genfxn generate -o tasks.jsonl -f stringrules -n 50 \
    --n-rules 4 --overlap-level high

# Bitops tasks at target difficulty 4
genfxn generate -o tasks.jsonl -f bitops -n 50 --difficulty 4

# Sequence DP tasks at target difficulty 5
genfxn generate -o tasks.jsonl -f sequence_dp -n 50 --difficulty 5

# Intervals tasks at target difficulty 4
genfxn generate -o tasks.jsonl -f intervals -n 50 --difficulty 4

# Graph query tasks at target difficulty 4
genfxn generate -o tasks.jsonl -f graph_queries -n 50 --difficulty 4
```

See [AXES.md](AXES.md) for complete axis documentation.

### Task Structure

Each generated task contains:

```python
{
    "task_id": "sha256-hash",
    "family": "stateful",
    "spec": { ... },           # Structured specification
    "code": "def f(xs): ...",  # Executable code for selected language
    "queries": [               # Test cases
        {"input": [1, 2, 3], "output": 6, "tag": "COVERAGE"},
        {"input": [], "output": 0, "tag": "BOUNDARY"},
    ]
}
```

### Python API

```python
from genfxn.stateful.task import generate_stateful_task
from genfxn.stateful.models import StatefulAxes, TemplateType

axes = StatefulAxes(
    templates=[TemplateType.LONGEST_RUN],
    list_length_range=(3, 10),
)
task = generate_stateful_task(axes)

print(task.code)
print(task.queries)
```

You can also request multiple languages from the Python API:

```python
from genfxn.langs.types import Language
from genfxn.piecewise.task import generate_piecewise_task

task = generate_piecewise_task(languages=[Language.PYTHON, Language.JAVA])
print(task.code["python"])
print(task.code["java"])
```

## Splitting

Split datasets for train/test with random or axis-based holdouts.

```bash
# Random 80/20 split
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --random-ratio 0.8 --seed 42

# Hold out specific axis value for test
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis template --holdout-value longest_run

# Hold out numeric range
genfxn split tasks.jsonl --train train.jsonl --test test.jsonl \
    --holdout-axis k --holdout-value "5,10" --holdout-type range
```

**Holdout types**: `exact` (default), `range`, `contains`

Axis paths use dot notation for nested fields: `predicate.kind`, `rules.0.transform.kind`

See [AXES.md](AXES.md) for all spec field paths.

### Python API

```python
from genfxn.splits import AxisHoldout, HoldoutType, split_tasks

holdouts = [AxisHoldout(
    axis_path="template",
    holdout_type=HoldoutType.EXACT,
    holdout_value="longest_run",
)]
result = split_tasks(tasks, holdouts)
# result.train, result.test
```

## CLI Reference

```bash
genfxn generate -o OUTPUT -f FAMILY -n COUNT [-s SEED] [OPTIONS]
genfxn split INPUT --train TRAIN --test TEST [--random-ratio R | --holdout-axis A --holdout-value V]
genfxn info FILE
```

## Tests

```bash
# Fast feedback (skips slow + full)
uv run pytest tests/ -v --verification-level=fast

# Standard CI/dev confidence (skips full)
uv run pytest tests/ -v --verification-level=standard

# Full verification (runs everything)
uv run pytest tests/ -v --verification-level=full
```

### Local Performance Budgets

Use the helper runner to apply tuned xdist worker counts and optional
runtime budget checks.

```bash
# Standard tier with tuned workers and duration report
uv run python scripts/run_tests.py --tier standard

# Enforce runtime budget for the selected tier
uv run python scripts/run_tests.py --tier fast --enforce-budget

# Override workers or pass through extra pytest args
uv run python scripts/run_tests.py --tier full --workers 2 -- -k validate
```
