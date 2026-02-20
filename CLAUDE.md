# genfxn Project Instructions

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
  language rendering, split tooling, and suite generation.

## Core Modules

- `src/genfxn/core/difficulty.py` - Difficulty scoring (1-5) per family
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

- `graph_queries.shortest_path_cost` is defined as the minimum wrapped-i64
  cost over simple paths (`<= n_nodes - 1` edges), not first-hit frontier
  behavior.
- `task_id_from_spec(...)` hashing must preserve container value types
  (`list`, `tuple`, `set`, `frozenset`) to avoid cross-type collisions.
- Cross-language numeric parity guarantees apply to generated specs/tasks
  under validated axes constraints; hand-authored specs outside those
  constraints are not contract-covered.

## TODO (Next PR)

- Add generated-code style/lint checks for Java and Rust:
  materialize generated snippets to temp sources, then run formatter/linter
  checks in CI (`google-java-format --dry-run --set-exit-if-changed`,
  `checkstyle` or equivalent, `cargo fmt --check`, `cargo clippy -- -D warnings`).
