# genfxn Project Instructions

For test/check categories and copy-paste commands, see `TESTING.md`.

## Task Families

- `piecewise` - Piecewise functions with branches
- `stateful` - Stateful list processing (longest_run, conditional_linear_sum, resetting_best_prefix_sum)
- `simple_algorithms` - Simple algorithms (most_frequent, count_pairs_sum, max_window_sum)
- `stringrules` - String transformation rules with predicates
- `stack_bytecode` - Stack-machine bytecode programs over integer lists
- `fsm` - Finite-state machine execution over integer sequences
- `bitops` - Fixed-width bit operation pipelines
- `sequence_dp` - Sequence dynamic-programming alignment variants
- `intervals` - Interval normalization and coverage/overlap statistics
- `graph_queries` - Graph reachability/hops/cost queries
- `temporal_logic` - Finite-trace temporal-logic evaluation

## Project State

- All listed families are implemented and integrated in generation, validation,
  language rendering, and suite generation.

## Core Modules

- `src/genfxn/core/describe.py` - Natural language task descriptions
- `src/genfxn/{family}/task.py` - Task generation entry points

## Family Quality Gate

No new family should be added or marked complete without an executable
cross-language runtime parity test harness.

Required:
- Runtime parity tests must execute code (not only inspect rendered strings).
- Tests must compare Python, Java, and Rust outputs on the same specs/inputs.
- Parity harness coverage must be part of the family's test evidence in PRs.

## Semantic Invariants

- `graph_queries.shortest_path_cost` is defined as the minimum saturating-i64
  cost over simple paths (`<= n_nodes - 1` edges), not first-hit frontier
  behavior.
- `task_id_from_spec(...)` hashing must preserve container value types
  (`list`, `tuple`, `set`, `frozenset`) to avoid cross-type collisions.
- Cross-language numeric parity guarantees apply to generated specs/tasks
  under validated axes constraints; hand-authored specs outside those
  constraints are not contract-covered.

## Generated Code Quality Gate

- Generated Java/Rust code quality checks are now part of the workflow:
  `google-java-format --dry-run --set-exit-if-changed`,
  `javac -Xlint:all -Werror`, `cargo fmt -- --check`,
  `cargo clippy -- -D warnings`, and `cargo check`.
- CI runs deterministic smoke coverage via
  `scripts/check_generated_code_quality.py`.
- Historical note: older single-file Rust checks used
  `rustc --edition=2021 -D warnings` for snippet compatibility and therefore
  missed broader Clippy lint coverage. The current check materializes snippets
  as temporary Cargo projects so Clippy is enforced.

## Mandatory Verification Workflow

Unless the user explicitly says to skip checks for the current task, agents
must run this exact sequence after making code changes:

1. Run `uv run ruff format` on all Python files in the repository.
2. Run `uv run ruff check --fix src/ tests/ scripts/`.
3. Manually fix any remaining lint issues in `src/` only.
4. Run `uv run ty check src` and fix all type issues in `src/`.
5. Run all tests: `uv run pytest tests/ -v --verification-level=full`.
6. Fix obvious failures. If any remaining failures require a design decision,
   surface them clearly with options and tradeoffs.

Agents should not claim checks were skipped "per instructions" unless the
current user message explicitly requested skipping them.
