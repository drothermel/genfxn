# genfxn Project Instructions

## Viewer API Paths

Backend runs on `http://127.0.0.1:8000`

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/tasks` | GET | List all tasks. Optional `?family=` filter |
| `/api/tasks/{task_id}` | GET | Get single task by ID |
| `/api/families` | GET | List available task families |

## Running the Viewer

```bash
# Generate test data
uv run genfxn generate -f all -n 20 -o /tmp/viewer.jsonl

# Start backend (from viewer/backend)
cd viewer/backend && uv run viewer-api /tmp/viewer.jsonl

# Start frontend (from viewer/frontend)
cd viewer/frontend && bun dev
```

Frontend runs on `http://localhost:5173` (or next available port).

## Task Families

- `piecewise` - Piecewise functions with branches
- `stateful` - Stateful list processing (longest_run, conditional_linear_sum, resetting_best_prefix_sum)
- `simple_algorithms` - Simple algorithms (most_frequent, count_pairs_sum, max_window_sum)
- `stringrules` - String transformation rules with predicates

## Core Modules

- `src/genfxn/core/difficulty.py` - Difficulty scoring (1-5) per family
- `src/genfxn/core/describe.py` - Natural language task descriptions
- `src/genfxn/{family}/task.py` - Task generation entry points
