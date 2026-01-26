# genfxn

Synthetic function dataset generator for code reasoning research. Generates executable Python functions with structured test cases and axis-heldout train/test splits.

## Installation

```bash
uv sync
```

## Quick Start

```python
from genfxn.piecewise.task import generate_piecewise_task
from genfxn.piecewise.models import PiecewiseAxes, ExprType

axes = PiecewiseAxes(n_branches=2, expr_types=[ExprType.AFFINE])
task = generate_piecewise_task(axes)

print(task.code)      # Generated Python function
print(task.queries)   # Test cases with coverage tags
```

## Demos

```bash
uv run python scripts/demo_phase1_dsl.py       # Core building blocks
uv run python scripts/demo_phase2_piecewise.py # Piecewise function generation
```

## Tests

```bash
uv run pytest tests/ -v
```
