# Graph Queries Family Implementation Plan

Date: 2026-02-10
Owner: Codex + Danielle
Status: Complete (M0-M5 complete with suite + calibration integration)

## Goal

Add a new `graph_queries` family with deterministic graph-query semantics,
validator + AST safety checks, Python/Java/Rust rendering, and balanced-suite
integration at the same robustness standard as `stack_bytecode`, `fsm`,
`bitops`, `sequence_dp`, and `intervals`.

## Target Contract (v1)

- Family name: `graph_queries`
- Primary signature: `f(src: int, dst: int) -> int`
- Behavior: answer a graph query baked into the task spec for one source/target
  pair and return a deterministic integer result.

## Scope Decisions (Phase 1)

1. Keep v1 int-output only:
   - no list/batch query outputs in v1
2. Graph storage in spec:
   - node ids are `0..n_nodes-1`
   - edges are explicit in spec (`u`, `v`, optional `w`)
3. Query types in v1:
   - `reachable` (`0` or `1`)
   - `min_hops` (unweighted shortest-path edge count; `-1` if unreachable)
   - `shortest_path_cost` (weighted non-negative; `-1` if unreachable)
4. Directedness is explicit:
   - `directed: bool` determines adjacency interpretation
5. Weights:
   - integer weights only
   - non-negative in v1
6. Explicit non-goals in v1:
   - negative weights
   - all-pairs outputs
   - path reconstruction output
   - dynamic graph mutations

## Core Semantics Lock

Freeze and document exact semantics before parallel implementation:

1. Node domain:
   - valid nodes are integers in `[0, n_nodes-1]`
2. Edge normalization:
   - discard self-invalid edges outside node domain in sampling
   - for duplicate directed edges `(u, v)`, keep minimum weight
   - if `directed == false`, materialize symmetric adjacency
3. Query behavior:
   - `reachable`: return `1` iff any path exists else `0`
   - `min_hops`: BFS hop count; return `-1` if no path
   - `shortest_path_cost`: Dijkstra over normalized non-negative weights;
     return `-1` if no path
4. Same-node queries:
   - `reachable(src, src) = 1`
   - `min_hops(src, src) = 0`
   - `shortest_path_cost(src, src) = 0`
5. Determinism:
   - stable adjacency ordering
   - no randomness in evaluator

This lock is the parity contract for Python/Java/Rust implementations.

## Axes and Sampling Guidelines

Planned `GraphQueriesAxes` knobs:

- `target_difficulty: int | None` in `[1, 5]`
- `query_types: list[QueryType]`
- `directed_choices: list[bool]`
- `weighted_choices: list[bool]`
- `n_nodes_range: tuple[int, int]`
- `edge_count_range: tuple[int, int]`
- `weight_range: tuple[int, int]` (used when weighted)
- `disconnected_prob_range: tuple[float, float]`
- `multi_edge_prob_range: tuple[float, float]`
- `hub_bias_prob_range: tuple[float, float]`

Difficulty targeting guidelines:

- D1: small sparse graphs, mostly `reachable`
- D2: small-medium graphs with clear paths, `min_hops`
- D3: medium graphs, mixed directedness, more ambiguity
- D4: weighted + directed combinations, denser alternatives
- D5: larger graphs, high branching, tie-prone shortest-path cases

Query sampling guidelines:

- `BOUNDARY`: same-node, isolated-node, empty-neighborhood cases
- `COVERAGE`: direct edge, two-hop path, unreachable pair
- `TYPICAL`: in-distribution random pairs
- `ADVERSARIAL`: dense/hub-heavy and tie-prone weighted alternatives

## Difficulty Model Design

Add `graph_queries` branch to `compute_difficulty` with transparent components:

- `size_score`: from `n_nodes` and `n_edges`
- `density_score`: from edge density bucket
- `query_type_score`: `reachable < min_hops < shortest_path_cost`
- `directed_score`: directed generally harder than undirected
- `weight_score`: weighted generally harder than unweighted
- `structure_score`: disconnectedness, hubs, and multi-edge normalization

Design goals:

- all D1..D5 reachable at useful rates
- monotonic trend for `target_difficulty`
- no dead zones where suite quotas cannot be filled

## Suite Proportions and Reachability Script

Add explicit suite integration for `graph_queries`:

- `src/genfxn/suites/features.py`: `graph_queries_features(spec)`
- `src/genfxn/suites/quotas.py`: `D1..D5` quota specs
- `src/genfxn/suites/generate.py`:
  - `_pool_axes_graph_queries_d1` .. `_pool_axes_graph_queries_d5`
  - family dispatch in `_POOL_AXES_FNS`, `_FEATURE_FNS`, sampling, rendering

Add script:

- `scripts/calibrate_graph_queries.py`

Script responsibilities:

1. Difficulty reachability scan:
   - sample `N` specs per target difficulty
   - report exact-hit, within-one, mean, variance, histogram
2. Monotonicity checks:
   - assert means increase with target (`D1 < ... < D5`)
3. Suite quota checks:
   - run `generate_suite("graph_queries", d, ...)` for `d=1..5`
   - run `quota_report(...)` and assert zero `UNDER` in strict mode
4. Output machine-readable report:
   - `artifacts/graph_queries_calibration.json`

Minimum strict thresholds:

- exact-hit rate per `d`: `>= 0.50`
- within-one rate per `d`: `>= 0.90`
- `generate_suite(..., pool_size=3000)` succeeds for all `d=1..5`
- zero `UNDER` rows in strict `quota_report`

## Required Parity Gate

This family is not merge-ready until the executable runtime parity harness
passes for Python vs Java vs Rust:

- `tests/test_graph_queries_runtime_parity.py`

Renderer-only string tests are insufficient.

## File Plan

Create:

- `src/genfxn/graph_queries/models.py`
- `src/genfxn/graph_queries/sampler.py`
- `src/genfxn/graph_queries/eval.py`
- `src/genfxn/graph_queries/queries.py`
- `src/genfxn/graph_queries/render.py`
- `src/genfxn/graph_queries/ast_safety.py`
- `src/genfxn/graph_queries/validate.py`
- `src/genfxn/graph_queries/task.py`
- `src/genfxn/graph_queries/__init__.py`
- `src/genfxn/langs/java/graph_queries.py`
- `src/genfxn/langs/rust/graph_queries.py`
- `tests/test_graph_queries.py`
- `tests/test_validate_graph_queries.py`
- `tests/test_graph_queries_runtime_parity.py`
- `scripts/calibrate_graph_queries.py`

Update:

- `src/genfxn/cli.py`
- `src/genfxn/core/difficulty.py`
- `src/genfxn/core/describe.py`
- `src/genfxn/core/presets.py`
- `src/genfxn/langs/registry.py`
- `src/genfxn/suites/features.py`
- `src/genfxn/suites/quotas.py`
- `src/genfxn/suites/generate.py`
- `scripts/generate_balanced_suites.py`
- `README.md`
- `AXES.md`
- `tests/test_cli.py`
- `tests/test_difficulty.py`
- `tests/test_presets.py`
- `tests/test_suites.py`
- `tests/test_java_render.py`
- `tests/test_rust_render.py`
- `tests/test_generate_balanced_suites_script.py`

## Parallel Subagent Execution Topology

Orchestrator responsibilities (high-level context only):

- own semantics lock and contracts
- keep cross-stream interfaces stable
- prioritize gates and unblock agents quickly
- reconcile shared integration files
- run final validation and release notes

Parallel workstreams:

1. `Agent A` (Contract + canonical evaluator)
   - `graph_queries/models.py`, `eval.py`, `render.py`, `task.py`, `__init__.py`
   - core evaluator tests in `tests/test_graph_queries.py`
2. `Agent B` (Sampling + difficulty + query quality)
   - `sampler.py`, `queries.py`, `core/difficulty.py`, `core/describe.py`
   - target-difficulty monotonicity + `QueryTag` coverage tests
3. `Agent C` (Validation + AST safety)
   - `ast_safety.py`, `validate.py`, `tests/test_validate_graph_queries.py`
4. `Agent D` (Java/Rust + runtime parity)
   - `langs/java/graph_queries.py`, `langs/rust/graph_queries.py`
   - `tests/test_graph_queries_runtime_parity.py`
   - updates in `tests/test_java_render.py`, `tests/test_rust_render.py`
5. `Agent E` (CLI/presets/suites + calibration)
   - `cli.py`, `core/presets.py`, `suites/*`,
     `scripts/calibrate_graph_queries.py`,
     `scripts/generate_balanced_suites.py`, integration tests
6. `Agent F` (Docs + tracking)
   - `README.md`, `AXES.md`, plan checklist/notes maintenance

Dependency order:

- A first (semantics freeze), then B/C/D in parallel
- E starts after B finalizes feature keys + difficulty knobs
- F can run in parallel after A freeze and finalizes after E

## Milestones

## M0: Contract Freeze + Skeleton

Deliverables:

- frozen graph-query semantics lock
- package skeleton + task wiring scaffold

Acceptance:

- semantics doc complete and explicit
- deterministic sampling smoke test exists

## M1: Models + Evaluator + Task Wiring

Deliverables:

- full pydantic models for spec + axes
- canonical evaluator and Python renderer
- initial query generation + task generation

Acceptance:

- tests cover reachable/unreachable/same-node/boundary behavior
- rendered Python matches evaluator on sampled tasks

## M2: Sampler + Difficulty + Query Quality

Deliverables:

- difficulty-aware sampler with `target_difficulty`
- `compute_difficulty("graph_queries", ...)`
- full `QueryTag` coverage with evaluator-consistent outputs

Acceptance:

- monotonic target-difficulty trend
- exact-hit/within-one rates meet baseline thresholds in calibration sampling

## M3: Validation + AST Safety

Deliverables:

- AST safety policy aligned with renderer output
- robust task validator with spec/task_id/code/query/semantic checks

Acceptance:

- generated tasks validate with zero errors across many seeds
- unsafe code patterns are rejected with clear diagnostics

## M4: Java/Rust + Runtime Parity

Deliverables:

- Java + Rust renderers for graph queries
- executable parity harness (Python vs Java vs Rust)

Acceptance:

- runtime parity tests pass across fixed + sampled specs
- parity harness is included in test evidence

## M5: CLI + Presets + Suites + Docs + Calibration

Deliverables:

- CLI family wiring and difficulty path
- presets + suite pool/feature/quota integration
- docs updates (`README.md`, `AXES.md`)
- calibration script with strict mode

Acceptance:

- `generate_suite("graph_queries", d)` succeeds for `d=1..5`
- strict calibration passes with zero `UNDER` rows
- full repo verification passes

## Execution Checklist

- [x] M0 complete
- [x] M1 complete
- [x] M2 complete
- [x] M3 complete
- [x] M4 complete
- [x] M5 complete
- [x] Full `ruff` and full `pytest` pass
- [x] PR notes/test evidence finalized

## Notes Log

- 2026-02-10: Plan drafted from `docs/shared_rec_list.md` next-family order
  after `intervals` completion.
- 2026-02-10: M0 completed with package skeleton under
  `src/genfxn/graph_queries/` and deterministic smoke tests in
  `tests/test_graph_queries.py`.
- 2026-02-10: M1 completed with hardened spec/evaluator checks, task
  description integration via `src/genfxn/core/describe.py`, and expanded
  evaluator/render parity tests.
- 2026-02-10: M2 completed with difficulty-aware sampler tuning, new
  `compute_difficulty("graph_queries", ...)` model integration, task
  difficulty wiring, and expanded query-quality/multi-seed monotonicity tests.
- 2026-02-10: M3 completed with renderer-safe code generation for restricted
  exec, new AST whitelist policy, `validate_graph_queries_task`, and dedicated
  validation tests (`tests/test_validate_graph_queries.py`).
- 2026-02-10: M4 completed with Java/Rust graph query renderers, language
  registry/task wiring, and executable runtime parity tests in
  `tests/test_graph_queries_runtime_parity.py`.
- 2026-02-10: M5 completed with CLI/preset/suite/quota integration, graph
  calibration script (`scripts/calibrate_graph_queries.py`), docs updates
  (`README.md`, `AXES.md`), and end-to-end verification (`uv run ruff check .`,
  `uv run ty check`, `uv run pytest tests/ -v`, plus strict graph calibration).
