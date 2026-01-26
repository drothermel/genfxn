# genfxn

Synthetic function dataset generator for code reasoning research. Generates executable Python functions with structured test cases.

## Installation

```bash
uv sync
```

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

## Demos

```bash
uv run python scripts/demo_phase1_dsl.py       # Core DSL building blocks
uv run python scripts/demo_phase2_piecewise.py # Piecewise function generation
uv run python scripts/demo_phase3_stateful.py  # Stateful function generation
```

## Tests

```bash
uv run pytest tests/ -v
```
