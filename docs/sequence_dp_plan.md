# Sequence DP Family Implementation Plan

Date: 2026-02-09
Owner: Codex + Danielle
Status: In progress (M0-M2 complete)

## Goal

Add a new `sequence_dp` family with deterministic dynamic-programming behavior,
validator + AST safety checks, Python/Java/Rust rendering, and balanced-suite
integration at the same robustness level as `fsm` and `bitops`.

## Target Contract (v1)

- Family name: `sequence_dp`
- Primary signature: `f(a: list[int], b: list[int]) -> int`
- Behavior: evaluate a configured DP recurrence over two sequences and return
  an integer derived from score and/or traceback according to `output_mode`.

## Scope Decisions (Phase 1)

1. Keep v1 strictly two-sequence:
   - no single-sequence DP templates in v1
2. Templates in v1:
   - `global` (Needleman-Wunsch style)
   - `local` (Smith-Waterman style)
3. Match predicates:
   - `eq`
   - `abs_diff_le`
   - `mod_eq` (D4/D5-capable complexity)
4. Scoring:
   - integer `match_score`, `mismatch_score`, `gap_score`
   - local template clamps negative cells to `0`
5. Deterministic tie rules:
   - `step_tie_break`: total order over `diag`, `up`, `left`
   - local endpoint ties resolved by fixed row-major earliest index
6. Output mode (int only in v1):
   - `score`
   - `alignment_len`
   - `gap_count`
7. Explicit non-goals in v1:
   - affine-gap penalties
   - returning alignment/path arrays
   - single-sequence DP variants

## Core Semantics Lock

Before parallel implementation starts, freeze and document exact semantics:

- DP table size: `(len(a) + 1) x (len(b) + 1)`
- Global base cases:
  - `dp[i][0] = i * gap_score`
  - `dp[0][j] = j * gap_score`
- Local base cases:
  - first row/col are `0`
- Transition candidates:
  - `diag = dp[i-1][j-1] + score(a[i-1], b[j-1])`
  - `up = dp[i-1][j] + gap_score`
  - `left = dp[i][j-1] + gap_score`
- Local recurrence includes `0` candidate before max-selection.
- Traceback parent pointers are chosen by `step_tie_break`.
- `alignment_len` and `gap_count` must come from traceback path, not from
  aggregate heuristics.

This lock is the cross-language parity contract for Python/Java/Rust.

## Axes and Sampling Guidelines

Planned `SequenceDpAxes` knobs:

- `target_difficulty: int | None` in `[1, 5]`
- `templates: list[TemplateType]`
- `output_modes: list[OutputMode]`
- `predicate_types: list[PredicateType]`
- `len_a_range: tuple[int, int]`
- `len_b_range: tuple[int, int]`
- `value_range: tuple[int, int]`
- `score_ranges`:
  - `match_score_range`
  - `mismatch_score_range`
  - `gap_score_range`
- `tie_break_orders: list[TieBreakOrder]`

Difficulty targeting guidelines:

- D1: short inputs, `global`, `eq`, `score`, diag-first tie-break
- D2: slightly longer, add `abs_diff_le`, still mostly score-only
- D3: introduce `local`, mixed score signs, occasional traceback outputs
- D4: enforce traceback-heavy outputs (`alignment_len`/`gap_count`) and
  tie-prone scoring
- D5: highest cell budgets + tie-heavy recurrences + modular predicates

Query sampling guidelines:

- `BOUNDARY`: empty/one-empty/singleton/no-match/all-match
- `COVERAGE`: force diagonal, up, and left path selections
- `TYPICAL`: random in-distribution pairs
- `ADVERSARIAL`: tie-heavy and repeated-value cases stressing tie-break logic

## Difficulty Model Design

Add `sequence_dp` branch to `compute_difficulty` with transparent components:

- `size_score`: based on DP cell budget (`len(a) * len(b)`)
- `template_score`: `global < local`
- `predicate_score`: `eq < abs_diff_le < mod_eq`
- `traceback_score`: `score < alignment_len < gap_count`
- `tie_score`: lower for strict-scoring setups, higher for tie-heavy setups

Design goal:

- all D1..D5 reachable
- monotonic trend for `target_difficulty`
- no dead zones where a target cannot be sampled at useful rates

## Suite Proportions and Reachability Script

Add explicit suite integration for `sequence_dp`:

- `src/genfxn/suites/features.py`: `sequence_dp_features(spec)`
- `src/genfxn/suites/quotas.py`: `D1..D5` quota specs
- `src/genfxn/suites/generate.py`:
  - `_pool_axes_sequence_dp_d1` .. `_pool_axes_sequence_dp_d5`
  - family dispatch in `_POOL_AXES_FNS`, `_FEATURE_FNS`, sampling, rendering

Add script:

- `scripts/calibrate_sequence_dp.py`

Script responsibilities:

1. Difficulty reachability scan:
   - sample N specs per target difficulty
   - report exact-hit rates, mean/variance, histogram over achieved difficulty
2. Monotonicity checks:
   - assert mean difficulty rises with target (`D1 < ... < D5`)
3. Suite quota checks:
   - run `generate_suite("sequence_dp", d, ...)` for `d=1..5`
   - run `quota_report(...)` and assert no `UNDER` buckets in strict mode
4. Output a machine-readable report:
   - `artifacts/sequence_dp_calibration.json`

Minimum acceptance thresholds for strict mode:

- Each target `d` has exact-hit rate >= 0.50 on targeted sampling.
- Each target `d` has >= 0.90 samples within `d +/- 1`.
- `generate_suite(..., pool_size=3000)` succeeds for all `d=1..5`.
- `quota_report` has zero `UNDER` rows for all `d=1..5`.

## File Plan

Create:

- `src/genfxn/sequence_dp/models.py`
- `src/genfxn/sequence_dp/sampler.py`
- `src/genfxn/sequence_dp/eval.py`
- `src/genfxn/sequence_dp/queries.py`
- `src/genfxn/sequence_dp/render.py`
- `src/genfxn/sequence_dp/ast_safety.py`
- `src/genfxn/sequence_dp/validate.py`
- `src/genfxn/sequence_dp/task.py`
- `src/genfxn/sequence_dp/__init__.py`
- `src/genfxn/langs/java/sequence_dp.py`
- `src/genfxn/langs/rust/sequence_dp.py`
- `tests/test_sequence_dp.py`
- `tests/test_validate_sequence_dp.py`
- `tests/test_sequence_dp_runtime_parity.py`
- `scripts/calibrate_sequence_dp.py`

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

Orchestrator responsibilities:

- Own this plan + semantics lock.
- Keep interface contracts stable.
- Merge/reconcile shared integration files.
- Run final full verification and update notes.

Parallel workstreams:

1. `Agent A` (Core family contract)
   - `sequence_dp/models.py`, `eval.py`, `render.py`, `task.py`, `__init__.py`
   - base `tests/test_sequence_dp.py` evaluator semantics
2. `Agent B` (Sampling + difficulty + query quality)
   - `sampler.py`, `queries.py`, `core/difficulty.py`, `core/describe.py`
   - monotonicity and query-tag coverage tests
3. `Agent C` (Validation + AST safety)
   - `ast_safety.py`, `validate.py`, `tests/test_validate_sequence_dp.py`
4. `Agent D` (Java/Rust + runtime parity)
   - `langs/java/sequence_dp.py`, `langs/rust/sequence_dp.py`,
     `tests/test_sequence_dp_runtime_parity.py`,
     updates to `tests/test_java_render.py`, `tests/test_rust_render.py`
5. `Agent E` (CLI/presets/suites + calibration script)
   - `cli.py`, `core/presets.py`, `suites/*`, `scripts/calibrate_sequence_dp.py`,
     `scripts/generate_balanced_suites.py`, integration tests
6. `Agent F` (Docs + release notes)
   - `README.md`, `AXES.md`, plan notes/checklist maintenance

Dependency order:

- A first (contract freeze), then B/C/D in parallel.
- E starts once B finalizes feature keys and difficulty knobs.
- F can run in parallel after contract freeze; finalize after E.

## Milestones

## M0: Contract Freeze + Skeleton

Deliverables:

- freeze v1 semantics in models/evaluator contract
- package skeleton + basic task wiring

Acceptance:

- evaluator unit tests for base/global/local edge semantics pass
- deterministic sampling smoke test exists

## M1: Models + Evaluator + Task Wiring

Deliverables:

- full pydantic models for spec + axes
- canonical evaluator and Python renderer
- initial query generator + task generation

Acceptance:

- tests cover empty/one-empty/tie-heavy inputs
- render output matches evaluator on sampled tasks

## M2: Sampler + Difficulty + Query Quality

Deliverables:

- difficulty-aware sampler with `target_difficulty`
- `compute_difficulty("sequence_dp", ...)`
- query set with all `QueryTag` categories

Acceptance:

- monotonic average difficulty across targets 1..5
- exact query output/evaluator parity for many seeds

## M3: Validator + AST Safety + Language Renderers

Deliverables:

- validator + AST whitelist
- Java and Rust renderers
- registry wiring

Acceptance:

- generated tasks validate cleanly across seed sweeps
- executable runtime parity tests (Python vs Java vs Rust) pass

## M4: CLI + Presets + Docs

Deliverables:

- CLI family integration
- difficulty presets for D1..D5
- README/AXES documentation

Acceptance:

- CLI family/language/difficulty tests pass
- preset tests pass and reach all targets

## M5: Balanced Suite Integration + Calibration Script

Deliverables:

- suite features + quotas + pool axes
- `scripts/calibrate_sequence_dp.py`
- suite and script tests

Acceptance:

- quota checks pass for D1..D5 with expected proportions
- strict calibration script passes end-to-end

## Robustness and Test Gates

Focused verification (per milestone) plus final gates:

- `uv run ruff check .`
- `uv run pytest tests/test_sequence_dp.py tests/test_validate_sequence_dp.py -v`
- `uv run pytest tests/test_sequence_dp_runtime_parity.py -q --verification-level=full`
- `uv run pytest tests/test_cli.py tests/test_presets.py tests/test_suites.py -q --verification-level=full`
- `uv run python scripts/calibrate_sequence_dp.py --strict --seed 42`
- `uv run pytest tests/ -v`

Required completion gate for this family:

- executable cross-language runtime parity harness is green and checked in

## Open Design Questions

1. Do we keep only `global` + `local` in v1, or add `semi_global` now?
   - Recommendation: keep `global` + `local` in v1.
2. Should `mod_eq` predicate be available at all difficulties?
   - Recommendation: bias to D4/D5 pool axes to preserve separation.
3. Should traceback-only output modes be mandatory for D5?
   - Recommendation: yes, enforce for better semantic stress.
4. Should script strict mode be CI-gated or release-gated?
   - Recommendation: release-gated first, then CI after stabilization.

## Resume Checklist

1. Read `docs/sequence_dp_plan.md`.
2. Confirm branch and clean state: `git status`.
3. Freeze spec semantics before parallel implementation.
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

- 2026-02-09: Plan drafted; `sequence_dp` chosen as next family.
- 2026-02-09: M0 implemented with parallel subagents. Added
  `src/genfxn/sequence_dp/{models,eval,sampler,queries,render,task,__init__}.py`
  and baseline coverage in `tests/test_sequence_dp.py`.
  Focused verification passed:
  `uv run ruff check src/genfxn/sequence_dp tests/test_sequence_dp.py`
  and `uv run pytest tests/test_sequence_dp.py -q` (8 passed).
- 2026-02-09: M1 accepted. Added rendered-code parity coverage in
  `tests/test_sequence_dp.py` and re-ran focused checks:
  `uv run ruff check src/genfxn/sequence_dp tests/test_sequence_dp.py`
  and `uv run pytest tests/test_sequence_dp.py -q` (9 passed).
- 2026-02-09: M2 completed via parallel subagents + orchestration. Added
  `sequence_dp` difficulty scoring in `src/genfxn/core/difficulty.py`,
  connected task difficulty assignment in `src/genfxn/sequence_dp/task.py`,
  and expanded coverage in `tests/test_difficulty.py` and
  `tests/test_sequence_dp.py` for target-difficulty monotonicity and query
  quality across sampled seeds/tasks.
  Focused verification passed:
  `uv run ruff check src/genfxn/core/difficulty.py src/genfxn/sequence_dp tests/test_difficulty.py tests/test_sequence_dp.py`
  and `uv run pytest tests/test_difficulty.py tests/test_sequence_dp.py -q`
  (88 passed).
