# Temporal Logic Over Streams Family Implementation Plan

Date: 2026-02-10
Owner: Codex + Danielle
Status: In progress (M0-M1 complete; M2-M5 pending)

## Goal

Add a new `temporal_logic` family with deterministic finite-trace temporal
semantics, robust validation + AST safety checks, Python/Java/Rust rendering,
and balanced-suite integration at the same robustness standard as
`stack_bytecode`, `fsm`, `bitops`, `sequence_dp`, `intervals`, and
`graph_queries`.

## Target Contract (v1)

- Family name: `temporal_logic`
- Primary signature: `f(xs: list[int]) -> int`
- Behavior: evaluate a spec-defined temporal formula over `xs` and return an
  integer output according to a configured output mode.

## Scope Decisions (Phase 1)

1. Keep v1 integer-output only:
   - `sat_at_start`: `1` if formula holds at index `0`, else `0`
   - `sat_count`: number of indices where formula holds
   - `first_sat_index`: first satisfying index or `-1`
2. Temporal domain is finite traces:
   - indices are `0..n-1`
   - no infinite-trace semantics in v1
3. Operator set in v1:
   - boolean: `NOT`, `AND`, `OR`
   - temporal future: `NEXT`, `EVENTUALLY`, `ALWAYS`, `UNTIL`
   - temporal past: `SINCE` (included for higher difficulties)
4. Predicate layer stays integer and explicit:
   - atomic predicates compare current value to constants
   - no cross-index arithmetic inside atomic predicates
5. Determinism constraints:
   - deterministic formula AST in spec
   - deterministic evaluator with no randomness
6. Explicit non-goals in v1:
   - probabilistic temporal operators
   - user-defined predicate code
   - infinite-trace/LTL model-checking semantics

## Core Semantics Lock

Freeze these semantics before parallel implementation:

1. Atomic predicates at index `i` evaluate on `xs[i]` only.
2. Valid evaluation indices are `0 <= i < n`:
   - if `n == 0`, no index-level evaluation occurs
3. `NEXT(phi)`:
   - true at `i` iff `i + 1 < n` and `phi(i + 1)` is true
4. `EVENTUALLY(phi)`:
   - true at `i` iff exists `j` in `[i, n-1]` with `phi(j)` true
5. `ALWAYS(phi)`:
   - true at `i` iff for all `j` in `[i, n-1]`, `phi(j)` true
6. `phi UNTIL psi`:
   - true at `i` iff exists `j` in `[i, n-1]` where `psi(j)` true and
     `phi(k)` is true for all `k` in `[i, j)`
7. `phi SINCE psi`:
   - true at `i` iff exists `j` in `[0, i]` where `psi(j)` true and
     `phi(k)` is true for all `k` in `(j, i]`
8. Empty-sequence output semantics (`n == 0`):
   - `sat_at_start = 0`
   - `sat_count = 0`
   - `first_sat_index = -1`

This lock is the parity contract for Python/Java/Rust implementations.

## Axes and Sampling Guidelines

Planned `TemporalLogicAxes` knobs:

- `target_difficulty: int | None` in `[1, 5]`
- `output_modes: list[TemporalOutputMode]`
- `formula_depth_range: tuple[int, int]`
- `operator_mix: list[TemporalOperator]`
- `include_since_choices: list[bool]`
- `sequence_length_range: tuple[int, int]`
- `value_range: tuple[int, int]`
- `predicate_constant_range: tuple[int, int]`
- `predicate_kinds: list[PredicateKind]`
- `bounded_window_prob_range: tuple[float, float]`
- `bounded_window_size_range: tuple[int, int]`

Difficulty targeting guidelines:

- D1: shallow formulas, mostly `EVENTUALLY`/`ALWAYS`, short sequences,
  `sat_at_start`
- D2: mixed boolean + temporal operators, moderate sequence lengths
- D3: deeper trees, more `UNTIL`, branch-heavy formulas
- D4: frequent `SINCE`, bounded windows, long traces
- D5: nested temporal operators with competing branches and edge-bound windows

Query sampling guidelines:

- `BOUNDARY`: empty sequence, single element, `NEXT` at last index
- `COVERAGE`: all-true/all-false/alternating traces
- `TYPICAL`: in-distribution random traces
- `ADVERSARIAL`: formulas designed to trigger boundary-window off-by-one errors

## Difficulty Model Design

Add `temporal_logic` branch to `compute_difficulty` with transparent
components:

- `length_score`: from `len(xs)` bucket
- `formula_depth_score`: AST depth + node count
- `operator_score`: higher for `UNTIL`/`SINCE` than `EVENTUALLY`/`ALWAYS`
- `window_score`: higher for bounded windows and tight boundaries
- `predicate_score`: higher for mixed predicate kinds/constants
- `output_mode_score`: `sat_at_start < sat_count < first_sat_index`

Design goals:

- all D1..D5 reachable at useful rates
- monotonic trend for `target_difficulty`
- no dead zones where suite quotas cannot be filled

## Suite Proportions and Reachability Script

Add explicit suite integration for `temporal_logic`:

- `src/genfxn/suites/features.py`: `temporal_logic_features(spec)`
- `src/genfxn/suites/quotas.py`: `D1..D5` quota specs
- `src/genfxn/suites/generate.py`:
  - `_pool_axes_temporal_logic_d1` .. `_pool_axes_temporal_logic_d5`
  - family dispatch in `_POOL_AXES_FNS`, `_FEATURE_FNS`, sampling, rendering

Add script:

- `scripts/calibrate_temporal_logic.py`

Script responsibilities:

1. Difficulty reachability scan:
   - sample `N` specs per target difficulty
   - report exact-hit, within-one, mean, variance, histogram
2. Monotonicity checks:
   - assert means increase with target (`D1 < ... < D5`)
3. Suite quota checks:
   - run `generate_suite("temporal_logic", d, ...)` for `d=1..5`
   - run `quota_report(...)` and assert zero `UNDER` in strict mode
4. Output a machine-readable report:
   - `artifacts/temporal_logic_calibration.json`

Minimum strict thresholds:

- exact-hit rate per `d`: `>= 0.50`
- within-one rate per `d`: `>= 0.90`
- `generate_suite(..., pool_size=3000)` succeeds for all `d=1..5`
- zero `UNDER` rows in strict `quota_report`

## Required Parity Gate

This family is not merge-ready until the executable runtime parity harness
passes for Python vs Java vs Rust:

- `tests/test_temporal_logic_runtime_parity.py`

Renderer-only string tests are insufficient.

## File Plan

Create:

- `src/genfxn/temporal_logic/models.py`
- `src/genfxn/temporal_logic/sampler.py`
- `src/genfxn/temporal_logic/eval.py`
- `src/genfxn/temporal_logic/queries.py`
- `src/genfxn/temporal_logic/render.py`
- `src/genfxn/temporal_logic/ast_safety.py`
- `src/genfxn/temporal_logic/validate.py`
- `src/genfxn/temporal_logic/task.py`
- `src/genfxn/temporal_logic/__init__.py`
- `src/genfxn/langs/java/temporal_logic.py`
- `src/genfxn/langs/rust/temporal_logic.py`
- `tests/test_temporal_logic.py`
- `tests/test_validate_temporal_logic.py`
- `tests/test_temporal_logic_runtime_parity.py`
- `scripts/calibrate_temporal_logic.py`

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

- own semantics lock and interface contracts
- keep cross-stream interfaces stable
- reconcile shared integration files (`cli`, `difficulty`, `suites`, docs)
- run final validation gates and update checklist/notes

Parallel workstreams:

1. `Agent A` (Contract + canonical evaluator)
   - `temporal_logic/models.py`, `eval.py`, `render.py`, `task.py`,
     `__init__.py`
   - evaluator semantics tests in `tests/test_temporal_logic.py`
2. `Agent B` (Sampling + difficulty + query quality)
   - `sampler.py`, `queries.py`, `core/difficulty.py`, `core/describe.py`
   - monotonic targeting tests + `QueryTag` coverage tests
3. `Agent C` (Validation + AST safety)
   - `ast_safety.py`, `validate.py`, `tests/test_validate_temporal_logic.py`
4. `Agent D` (Java/Rust + runtime parity)
   - `langs/java/temporal_logic.py`, `langs/rust/temporal_logic.py`
   - `tests/test_temporal_logic_runtime_parity.py`
   - updates in `tests/test_java_render.py`, `tests/test_rust_render.py`
5. `Agent E` (CLI/presets/suites + calibration)
   - `cli.py`, `core/presets.py`, `suites/*`,
     `scripts/calibrate_temporal_logic.py`,
     `scripts/generate_balanced_suites.py`, integration tests
6. `Agent F` (Docs + release notes)
   - `README.md`, `AXES.md`, plan checklist/notes maintenance

Dependency order:

- A first (semantic freeze), then B/C/D in parallel
- E starts after B finalizes feature keys and difficulty knobs
- F runs in parallel after A freeze and finalizes after E

## Milestones

## M0: Contract Freeze + Skeleton

Deliverables:

- frozen temporal semantics contract and formula schema
- package skeleton + task wiring scaffold

Acceptance:

- evaluator smoke tests for empty/single-element traces pass
- deterministic sampling smoke test exists

## M1: Models + Evaluator + Task Wiring

Deliverables:

- full pydantic models for spec + axes
- canonical evaluator and Python renderer
- initial query generation + task wiring

Acceptance:

- tests cover all core operators and boundary semantics
- rendered Python matches evaluator on sampled tasks

## M2: Sampler + Difficulty + Query Quality

Deliverables:

- difficulty-aware sampler with `target_difficulty`
- `compute_difficulty("temporal_logic", ...)`
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

- Java + Rust renderers for temporal logic
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

- `generate_suite("temporal_logic", d)` succeeds for `d=1..5`
- strict calibration passes with zero `UNDER` rows
- full repo verification passes

## Required Completion Gate

This family is not complete until all are true:

1. Full `uv run ruff check .` passes.
2. Full `uv run ty check` passes.
3. Full `uv run pytest tests/ -v --verification-level=full` passes.
4. Runtime parity harness (`tests/test_temporal_logic_runtime_parity.py`)
   passes.
5. `scripts/calibrate_temporal_logic.py --strict` passes with report artifact.
6. PR includes behavior notes and concrete test evidence commands/results.

## Testing Strategy

- Deterministic seed checks for reproducibility.
- Property-style evaluator tests across randomized formulas and traces.
- Differential checks:
  - evaluator vs rendered Python execution
  - Python vs Java vs Rust runtime parity
- Boundary regression set:
  - empty trace, singleton trace, `NEXT` at end, impossible windows,
    all-true/all-false traces
- Suite sampling regression checks:
  - quota reachability at each difficulty
  - strict quota report with zero `UNDER`

## Parallel Execution Strategy

1. Freeze semantics in M0 and publish a single evaluator truth source.
2. Spawn A/B/C/D in parallel immediately after M0 freeze.
3. Start E once B stabilizes difficulty/feature keys.
4. Keep orchestrator context at high-level contracts and gates only.
5. Merge streams in small batches and run targeted tests after each merge.
6. Run full verification only after M5 integration to minimize churn.

## Execution Checklist

- [x] M0 complete
- [x] M1 complete
- [ ] M2 complete
- [ ] M3 complete
- [ ] M4 complete
- [ ] M5 complete
- [ ] Full `ruff`, `ty`, and full `pytest` pass
- [ ] PR notes/test evidence finalized

## Notes Log

- 2026-02-10: Plan drafted from `docs/shared_rec_list.md` as the final
  remaining family after `graph_queries`.
- 2026-02-10: M0 completed with a `src/genfxn/temporal_logic/` package
  scaffold (models/eval/sampler/queries/render/task/validate/ast_safety) and
  deterministic smoke tests in `tests/test_temporal_logic.py`.
- 2026-02-10: M1 completed with hardened formula validation in
  `src/genfxn/temporal_logic/models.py`, canonical evaluator/render/task
  wiring updates (including `describe_task("temporal_logic", ...)` in
  `src/genfxn/temporal_logic/task.py` and `src/genfxn/core/describe.py`), and
  expanded semantics/parity tests in `tests/test_temporal_logic.py`.
