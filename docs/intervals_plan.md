# Intervals Family Implementation Plan

Date: 2026-02-09
Owner: Codex + Danielle
Status: In progress (M0-M2 complete; M3-M5 remaining)

## Goal

Add a new `intervals` family with deterministic interval semantics, strong
validator + AST safety checks, Python/Java/Rust rendering, and balanced-suite
integration at the same robustness standard as `fsm`, `bitops`, and
`sequence_dp`.

## Target Contract (v1)

- Family name: `intervals`
- Primary signature: `f(intervals: list[tuple[int, int]]) -> int`
- Behavior: compute an interval-derived integer statistic according to a
  configured interval operation policy.

## Scope Decisions (Phase 1)

1. Keep v1 int-output only:
   - no list-of-interval outputs in v1
2. Boundary semantics are explicit:
   - `closed_closed`, `closed_open`, `open_closed`, `open_open`
3. Endpoint domain is integer lattice:
   - all operations are defined over covered integer points
4. Reversed endpoints are deterministic:
   - input interval `(hi, lo)` is normalized to `(lo, hi)` (no runtime error)
5. Merge/adjacency behavior is explicit:
   - `merge_touching: bool` controls whether adjacent runs are merged
6. Output operations in v1:
   - `total_coverage`
   - `merged_count`
   - `max_overlap_count`
   - `gap_count`
7. Explicit non-goals in v1:
   - weighted intervals
   - interval list outputs (`merge`, `find_gaps`, `split_at` payloads)
   - floating-point endpoints

## Core Semantics Lock

Freeze these semantics before parallel implementation:

1. Normalize each raw interval:
   - `lo = min(a, b)`, `hi = max(a, b)`
2. Apply boundary mode to convert to discrete inclusive integer span:
   - `closed_closed`: `[lo, hi]`
   - `closed_open`: `[lo, hi - 1]`
   - `open_closed`: `[lo + 1, hi]`
   - `open_open`: `[lo + 1, hi - 1]`
3. Empty adjusted intervals (`start > end`) are ignored.
4. `merge_touching` for discrete spans:
   - when true: `[a, b]` and `[c, d]` merge if `c <= b + 1`
   - when false: merge only if `c <= b`
5. Operation definitions:
   - `total_coverage`: count of covered integer points
   - `merged_count`: number of merged runs after union
   - `max_overlap_count`: max active interval multiplicity at any integer point
   - `gap_count`: number of uncovered integer gaps between merged runs
6. Empty-input behavior:
   - all operations return `0`

This lock is the parity contract for Python/Java/Rust implementations.

## Axes and Sampling Guidelines

Planned `IntervalsAxes` knobs:

- `target_difficulty: int | None` in `[1, 5]`
- `operation_types: list[OperationType]`
- `boundary_modes: list[BoundaryMode]`
- `merge_touching_choices: list[bool]`
- `n_intervals_range: tuple[int, int]`
- `endpoint_range: tuple[int, int]`
- `max_span_range: tuple[int, int]`
- `allow_reversed_interval_prob_range: tuple[float, float]`
- `degenerate_interval_prob_range: tuple[float, float]`
- `nested_interval_prob_range: tuple[float, float]`

Difficulty targeting guidelines:

- D1: short lists, `closed_closed`, simple operations (`total_coverage`)
- D2: add `merged_count`, occasional touching/disjoint ambiguity
- D3: add mixed boundary modes and `max_overlap_count`
- D4: frequent degenerate/reversed/nested intervals, `gap_count` emphasis
- D5: larger interval sets, heavy overlap + mixed boundary/adjacency semantics

Query sampling guidelines:

- `BOUNDARY`: empty list, single interval, fully empty-after-boundary case
- `COVERAGE`: touching vs overlapping vs disjoint vs nested
- `TYPICAL`: random in-distribution sets
- `ADVERSARIAL`: tie-heavy overlap, many degenerate/reversed intervals

## Difficulty Model Design

Add `intervals` branch to `compute_difficulty` with transparent components:

- `size_score`: from `n_intervals` and effective endpoint span
- `operation_score`: `total_coverage < merged_count < max_overlap_count < gap_count`
- `boundary_score`: `closed_closed < mixed open/closed`
- `adjacency_score`: higher when `merge_touching` and borderline cases coexist
- `structure_score`: higher with nested/reversed/degenerate prevalence

Design goals:

- all D1..D5 reachable at useful rates
- monotonic trend for `target_difficulty`
- no dead zones where suite quotas cannot be filled

## Suite Proportions and Reachability Script

Add explicit suite integration for `intervals`:

- `src/genfxn/suites/features.py`: `intervals_features(spec)`
- `src/genfxn/suites/quotas.py`: `D1..D5` quota specs
- `src/genfxn/suites/generate.py`:
  - `_pool_axes_intervals_d1` .. `_pool_axes_intervals_d5`
  - family dispatch in `_POOL_AXES_FNS`, `_FEATURE_FNS`, sampling, rendering

Add script:

- `scripts/calibrate_intervals.py`

Script responsibilities:

1. Difficulty reachability scan:
   - sample `N` specs per target difficulty
   - report exact-hit, within-one, mean, variance, histogram
2. Monotonicity checks:
   - assert means increase with target (`D1 < ... < D5`)
3. Suite quota checks:
   - run `generate_suite("intervals", d, ...)` for `d=1..5`
   - run `quota_report(...)` and assert zero `UNDER` in strict mode
4. Output a machine-readable report:
   - `artifacts/intervals_calibration.json`

Minimum strict thresholds:

- exact-hit rate per `d`: `>= 0.50`
- within-one rate per `d`: `>= 0.90`
- `generate_suite(..., pool_size=3000)` succeeds for all `d=1..5`
- zero `UNDER` rows in strict `quota_report`

## File Plan

Create:

- `src/genfxn/intervals/models.py`
- `src/genfxn/intervals/sampler.py`
- `src/genfxn/intervals/eval.py`
- `src/genfxn/intervals/queries.py`
- `src/genfxn/intervals/render.py`
- `src/genfxn/intervals/ast_safety.py`
- `src/genfxn/intervals/validate.py`
- `src/genfxn/intervals/task.py`
- `src/genfxn/intervals/__init__.py`
- `src/genfxn/langs/java/intervals.py`
- `src/genfxn/langs/rust/intervals.py`
- `tests/test_intervals.py`
- `tests/test_validate_intervals.py`
- `tests/test_intervals_runtime_parity.py`
- `scripts/calibrate_intervals.py`

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

Orchestrator responsibilities (keep high-level context only):

- Own semantics lock and interface contracts.
- Keep `models`/`eval` semantics stable across streams.
- Reconcile shared integration files (`cli`, `difficulty`, `suites`, docs).
- Run final validation gates and update checklist/notes.

Parallel workstreams:

1. `Agent A` (Core contract + canonical evaluator)
   - `intervals/models.py`, `intervals/eval.py`, `intervals/render.py`,
     `intervals/task.py`, `intervals/__init__.py`
   - base evaluator tests in `tests/test_intervals.py`
2. `Agent B` (Sampling + difficulty + query quality)
   - `intervals/sampler.py`, `intervals/queries.py`,
     `core/difficulty.py`, `core/describe.py`
   - monotonic-target tests + query-tag coverage tests
3. `Agent C` (Validation + AST safety)
   - `intervals/ast_safety.py`, `intervals/validate.py`,
     `tests/test_validate_intervals.py`
4. `Agent D` (Java/Rust + runtime parity)
   - `langs/java/intervals.py`, `langs/rust/intervals.py`,
     `tests/test_intervals_runtime_parity.py`,
     updates in `tests/test_java_render.py`, `tests/test_rust_render.py`
5. `Agent E` (CLI/presets/suites + calibration)
   - `cli.py`, `core/presets.py`, `suites/*`,
     `scripts/calibrate_intervals.py`,
     `scripts/generate_balanced_suites.py`, integration tests
6. `Agent F` (Docs + release notes)
   - `README.md`, `AXES.md`, plan checklist/notes maintenance

Dependency order:

- A first (semantic freeze), then B/C/D in parallel.
- E starts after B finalizes difficulty/feature keys.
- F can run in parallel after A freeze; finalize after E.

## Milestones

## M0: Contract Freeze + Skeleton

Deliverables:

- frozen interval semantics in models/evaluator contract
- package skeleton + task wiring scaffold

Acceptance:

- evaluator tests for boundary and normalization semantics pass
- deterministic sampling smoke test exists

## M1: Models + Evaluator + Task Wiring

Deliverables:

- full pydantic models for spec + axes
- canonical evaluator and Python renderer
- initial queries + task generation

Acceptance:

- tests cover empty, degenerate, reversed, touching, nested cases
- renderer output matches evaluator on sampled tasks

## M2: Sampler + Difficulty + Query Quality

Deliverables:

- difficulty-aware sampler with `target_difficulty`
- `compute_difficulty("intervals", ...)`
- complete `QueryTag` coverage

Acceptance:

- monotonicity checks pass for targeted sampling
- query outputs match evaluator exactly
- each task/query set includes all required tags

## M3: Validator + AST Safety

Deliverables:

- AST safety policy for rendered Python
- task validator with spec/code/query/semantic checks

Acceptance:

- large sweep validate pass (`execute_untrusted_code=False`)
- smaller execute-enabled sweep pass

## M4: Java/Rust + Runtime Parity Harness

Deliverables:

- Java and Rust renderers wired in registry
- executable parity harness (Python vs Java vs Rust)

Acceptance:

- parity tests pass across fixed seeds + sampled specs
- parity harness meets required gate for new families

## M5: CLI + Presets + Suites + Calibration + Docs

Deliverables:

- CLI support, presets, suite integration, calibration script, docs updates
- script tests for calibration and balanced-suite generation hooks

Acceptance:

- CLI tests for family/language/difficulty pass
- strict calibration script passes
- suites for D1..D5 fill quotas with zero `UNDER`

## Required Completion Gate

This family is not complete until all are true:

1. Full `uv run ruff check .` passes.
2. Full `uv run pytest tests/ -v --verification-level=full` passes.
3. Runtime parity harness (`tests/test_intervals_runtime_parity.py`) passes.
4. `scripts/calibrate_intervals.py --strict` passes with report artifact.
5. PR includes behavior notes and concrete test evidence commands/results.

## Testing Strategy

- Deterministic seed checks for reproducibility.
- Property-style evaluator tests over randomized interval sets.
- Differential checks:
  - renderer output vs canonical evaluator
  - Python vs Java vs Rust parity
- Validator sweeps:
  - large `execute_untrusted_code=False`
  - smaller `execute_untrusted_code=True`
- Suite balancing checks:
  - `generate_suite("intervals", d)` + `quota_report(...)` for `d=1..5`

## Resume Checklist

1. Read `docs/intervals_plan.md`.
2. Confirm branch and clean state: `git status`.
3. Freeze semantics before parallel implementation.
4. Run milestones in order (`M0` -> `M5`) with focused tests at each gate.
5. Update checklist + notes log after each merged stream.

## Execution Checklist

- [x] M0 complete
- [x] M1 complete
- [x] M2 complete
- [ ] M3 complete
- [ ] M4 complete
- [ ] M5 complete
- [ ] Full `ruff` and full `pytest` pass
- [ ] Calibration script strict mode pass
- [ ] PR updated with behavior notes + test evidence

## Notes Log

- 2026-02-09: Plan drafted. `intervals` selected as next family from
  `docs/shared_rec_list.md` after completed `sequence_dp`.
- 2026-02-09: M0 completed with parallel subagents. Added package skeleton and
  core contract files in `src/genfxn/intervals/`:
  `models.py`, `eval.py`, `sampler.py`, `queries.py`, `render.py`, `task.py`,
  and `__init__.py`; added focused M0 tests in `tests/test_intervals.py`.
  Contract freeze semantics implemented for boundary modes, reversed endpoint
  normalization, merge-touching behavior, and int-output operations
  (`total_coverage`, `merged_count`, `max_overlap_count`, `gap_count`).
  Focused verification passed:
  `uv run ruff check src/genfxn/intervals tests/test_intervals.py`
  `uv run pytest tests/test_intervals.py -q` (6 passed).
- 2026-02-09: M1 completed. Hardened model and renderer/evaluator parity
  coverage in `tests/test_intervals.py`, including model roundtrip validation,
  invalid-axes rejection checks, and rendered Python equivalence against
  canonical evaluator outputs for sampled interval inputs.
  Focused verification passed:
  `uv run ruff check src/genfxn/intervals tests/test_intervals.py`
  `uv run pytest tests/test_intervals.py -q` (10 passed).
- 2026-02-09: M2 completed. Added `intervals` difficulty scoring in
  `src/genfxn/core/difficulty.py` and targeted-difficulty sampling preferences
  in `src/genfxn/intervals/sampler.py`. Updated task difficulty wiring in
  `src/genfxn/intervals/task.py` to use `compute_difficulty("intervals", ...)`
  directly. Expanded tests in `tests/test_intervals.py` for target-difficulty
  monotonicity and cross-seed query quality, and in `tests/test_difficulty.py`
  for intervals family coverage, monotonic examples, and clamped extremes.
  Focused verification passed:
  `uv run ruff check src/genfxn/core/difficulty.py src/genfxn/intervals/sampler.py src/genfxn/intervals/task.py tests/test_intervals.py tests/test_difficulty.py`
  `uv run pytest tests/test_intervals.py tests/test_difficulty.py -q` (92 passed).
