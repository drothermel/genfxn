# Current Plan: Robustness and Test-Parity Hardening

## Goal
Raise all families to a consistent quality bar so failures are caught early and
behavior remains stable across languages and verification levels.

## Status Snapshot
- Completed:
  - Identified and triaged suite-generation, validator type-safety, and
    lifecycle leak issues from recent reviews.
  - Mapped major test-parity gaps between early and newer families.
  - Added verification-level guard coverage in
    `tests/test_verification_levels.py` and documented parity-tier behavior in
    `README.md`.
  - Added GitHub Actions CI merge gating in `.github/workflows/ci.yml` to run
    `uv sync`, `ruff`, `ty`, and full verification pytest on push/PR.
- In progress:
  - Converting review findings into repeatable cross-family tests.
- Pending:
  - Cross-family validator contract matrix standardization.

## Workstreams

### 0) Current Batch: Correctness Regressions (2026-02-10)
- [x] Fix scalar-type collision in `src/genfxn/core/models.py` dedupe keying.
- [x] Add `tests/test_core_models.py` cases for `True` vs `1`, `1` vs `1.0`,
      and conflict handling across type-distinct inputs.
- [x] Harden range holdout matching in both `src/genfxn/splits.py` and
      `src/genfxn/cli.py` to reject bool as numeric.
- [x] Add range holdout tests in `tests/test_splits.py` and `tests/test_cli.py`
      asserting bool non-matches for numeric ranges.
- [x] Add verification-level guard test/doc assertion so runtime parity skip
      behavior in `standard` remains explicit and intentional.

Exit criterion:
- All three reported findings are fixed with regression tests, and full/standard
  behavior is unambiguous in docs/tests.

New intake extension (2026-02-10):
- [x] Make EXACT holdout type-sensitive in both `splits.py` and CLI matching.
- [x] Fix `dedupe_queries` hashable fallback type-collision risk.
- [x] Harden `dedupe_queries` repr fallback for broken-`__repr__` unhashables.

New intake extension (2026-02-10, CLI range + NaN dedupe):
- [x] Make graph_queries `--value-range` behavior explicit when provided ranges
      do not overlap valid non-negative weights.
- [x] Reject non-finite values (`nan`/`inf`/`-inf`) in `_parse_numeric_range`
      with clear CLI errors and tests in `tests/test_cli.py`.
- [x] Make `dedupe_queries` NaN keying deterministic and add regression tests in
      `tests/test_core_models.py`.

New intake extension (2026-02-10, CLI exact/contains non-finite holdouts):
- [x] Audit `split` holdout parsing for `exact`/`contains` to reject
      non-finite holdout tokens with clear `BadParameter`.
- [x] Add fail-closed matcher guards for non-finite `EXACT`/`CONTAINS`
      holdout values in `src/genfxn/splits.py`.
- [x] Add focused regressions in `tests/test_cli.py` and `tests/test_splits.py`
      while preserving normal JSON-type holdout behavior.

Progress update (2026-02-10, CLI exact/contains non-finite holdouts):
- Added `_parse_non_range_holdout_value(...)` in `src/genfxn/cli.py` so
  `split` now rejects non-finite exact/contains holdout values from both
  JSON constants (`NaN`, `Infinity`, `-Infinity`) and raw token fallbacks
  (`nan`, `inf`, `-inf`) with explicit `BadParameter`.
- Added fail-closed non-finite guard handling for `EXACT` and `CONTAINS` in
  `src/genfxn/splits.py` to keep direct matcher behavior deterministic.
- Added focused regression coverage:
  - `tests/test_cli.py`:
    `test_split_exact_contains_reject_non_finite_holdout_values`,
    `test_split_exact_allows_json_string_nan_literal`
  - `tests/test_splits.py`:
    `test_exact_holdout_rejects_non_finite_holdout_values`,
    `test_contains_holdout_rejects_non_finite_holdout_values`
- Validation evidence:
  - `uv run pytest tests/test_cli.py tests/test_splits.py -v
    --verification-level=standard` -> 166 passed
  - `uv run ruff check src/genfxn/cli.py src/genfxn/splits.py
    tests/test_cli.py tests/test_splits.py` -> passed
  - `uv run ty check src/genfxn/cli.py src/genfxn/splits.py
    tests/test_cli.py tests/test_splits.py` -> passed

New intake extension (2026-02-10, dedupe NaN output equality):
- [x] Fix `dedupe_queries` conflict detection so duplicate outputs that are both
      NaN are treated as equal (no false conflict).
- [x] Add focused `tests/test_core_models.py` coverage for:
      duplicate NaN outputs (no conflict) and NaN-vs-non-NaN outputs (conflict).

Progress update (2026-02-10, dedupe NaN output equality):
- `src/genfxn/core/models.py` now uses NaN-aware output equality for duplicate
  query conflict detection, so `nan` vs `nan` no longer raises a false conflict.
- Added focused regressions in `tests/test_core_models.py` for:
  - duplicate NaN outputs on identical input (dedupes, no conflict)
  - NaN-vs-non-NaN outputs on identical input (raises conflict)
- Validation evidence:
  - `uv run pytest tests/test_core_models.py -v --verification-level=standard`
    -> 16 passed.
  - `uv run ruff check src/genfxn/core/models.py tests/test_core_models.py`
    -> passed.
  - `uv run ty check src/genfxn/core/models.py tests/test_core_models.py`
    -> passed.

New intake extension (2026-02-10, Java int literal compile safety):
- [x] Audit Java int-family renderers for raw literal emission paths that can
      trigger `integer number too large`.
- [x] Add a shared Java int-literal helper and patch the minimal render surface
      (`predicates`, `expressions`, `stateful`, `simple_algorithms`,
      `piecewise`, and dependent helpers) so code compiles with large constants.
- [x] Add focused Java compile-safety regressions that fail on oversized
      literals and validate with targeted `pytest`/`ruff`/`ty`.

Progress update (2026-02-10, Java int literal compile safety):
- Added `java_int_literal(...)` in `src/genfxn/langs/java/_helpers.py` to emit
  int-typed expressions that stay compilable for out-of-range literals via
  `((int) <value>L)`.
- Patched integer-constant rendering paths in:
  - `src/genfxn/langs/java/predicates.py`
  - `src/genfxn/langs/java/expressions.py`
  - `src/genfxn/langs/java/transforms.py`
  - `src/genfxn/langs/java/stateful.py`
  - `src/genfxn/langs/java/simple_algorithms.py`
  and audited `src/genfxn/langs/java/piecewise.py` (delegates constant emission
  to predicate/expression renderers; no direct literal interpolation needed).
- Added focused regressions:
  - `TestJavaIntLiteral` in `tests/test_java_render.py`
  - `test_piecewise_java_compiles_with_oversized_int_literals` in
    `tests/test_piecewise_runtime_parity.py`
  - `test_stateful_java_compiles_with_oversized_int_literals` in
    `tests/test_stateful_runtime_parity.py`
  - `test_simple_algorithms_java_compiles_with_oversized_int_literals` in
    `tests/test_simple_algorithms_runtime_parity.py`
- Validation evidence:
  - `uv run pytest tests/test_java_render.py
    tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full -k "TestJavaIntLiteral or oversized_int_literals"`
    -> 6 passed.
  - `uv run pytest tests/test_java_render.py -v
    --verification-level=standard -k
    "TestPredicateJava or TestTransformJava or TestExpressionJava or
    TestPiecewiseJava or TestStatefulJava or TestSimpleAlgorithmsJava"`
    -> 44 passed.
  - `uv run ruff check` on touched Java renderer/test files -> passed.
  - `uv run ty check` on touched Java renderer/test files -> passed.

Progress update (2026-02-10, CLI range + NaN dedupe):
- `graph_queries` CLI now raises clear `BadParameter` for negative-only
  `--value-range` input instead of silently falling back to defaults.
- `_parse_numeric_range` now rejects non-finite bounds (`nan`, `inf`, `-inf`)
  with explicit CLI error text.
- `dedupe_queries` now canonicalizes float NaN scalar keys so NaN inputs dedupe
  deterministically and still raise conflict errors on output mismatch.
- Validation evidence:
  - `uv run pytest tests/test_cli.py tests/test_core_models.py -v
    --verification-level=standard` -> 109 passed
  - `uv run ruff check src/genfxn/cli.py src/genfxn/core/models.py
    tests/test_cli.py tests/test_core_models.py` -> passed
  - `uv run ty check src/genfxn/cli.py src/genfxn/core/models.py
    tests/test_cli.py tests/test_core_models.py` -> passed

New intake extension (2026-02-10, CLI numeric range precision):
- [x] Fix `_parse_numeric_range` integer-bound parsing in `src/genfxn/cli.py`
      to avoid float round-trip precision loss for integer-looking values.
- [x] Preserve float/scientific notation support and non-finite rejection
      behavior in `_parse_numeric_range`.
- [x] Add focused regression coverage in `tests/test_cli.py` for large integer
      range bounds (for example `9223372036854775807`) and validate requested
      `pytest`/`ruff`/`ty` commands.

Progress update (2026-02-10, CLI numeric range precision):
- Updated `src/genfxn/cli.py` `_parse_numeric_range(...)` so integer-looking
  bounds are parsed as exact `int` before float fallback, preventing precision
  loss on large integers while preserving float/scientific parsing.
- Preserved non-finite bound rejection (`nan`/`inf`/`-inf`) with the existing
  `BadParameter` finite-bounds message path.
- Added focused tests in `tests/test_cli.py`:
  - `test_split_range_parses_large_integer_bounds_exactly`
  - `test_parse_numeric_range_scientific_notation_uses_float`
- Validation evidence:
  - `uv run pytest tests/test_cli.py -v` -> 111 passed
  - `uv run ruff check src/genfxn/cli.py tests/test_cli.py` -> passed
  - `uv run ty check` -> passed

### 1) Validator Contract Parity (Cross-Family)
Add/standardize tests in each `tests/test_validate_<family>.py` for:
- bool-rejection where numeric ints are expected.
- strict vs lenient (`strict=False`) behavior.
- semantic mismatch capping (including unlimited mode behavior).
- non-Python code-map execution path behavior.
- exec lifecycle closure assertions for families using safe-exec workers.

Progress update (2026-02-10):
- Completed semantic mismatch capping tests for:
  `bitops`, `intervals`, `sequence_dp`, `fsm`, `graph_queries`,
  and `temporal_logic`.
- Completed explicit non-Python code-map skip tests for:
  `bitops`, `intervals`, `sequence_dp`, `fsm`, `graph_queries`,
  and `temporal_logic`.
- Completed explicit exec lifecycle-close tests for:
  `bitops`, `intervals`, `sequence_dp`, `graph_queries`,
  and `temporal_logic`.
- Completed older-family strict-vs-lenient and bool-rejection parity tests for:
  `stateful`, `simple_algorithms`, and `piecewise`.
- Completed older-family exec lifecycle-close assertions for:
  `stateful`, `simple_algorithms`, and `piecewise`.
- Next in this workstream:
  audit remaining families for any residual indirect-only lifecycle coverage
  and add explicit close assertions where still useful.
Current execution batch:
- [x] Add missing strict-vs-lenient and bool-rejection tests in:
      `test_validate_stateful.py`, `test_validate_simple_algorithms.py`,
      `test_validate_piecewise.py`.
- [x] Add missing exec lifecycle-close tests in:
      `test_validate_stateful.py`, `test_validate_simple_algorithms.py`,
      `test_validate_piecewise.py`.
- [x] Add shared parameterized validator contract matrix tests covering
      strict-vs-lenient severity for query input/output type issues across
      int-like families.
- [x] Add shared parameterized validator contract matrix tests covering bool
      rejection for int-like query fields across families.
- [x] Add shared parameterized lifecycle/skip matrix checks where stable:
      non-Python code-map skip behavior and exec function `close()` lifecycle.

Progress update (2026-02-10, shared matrix pass):
- Added `tests/test_validator_contract_matrix.py` to centralize reusable
  validator contract checks across int-like families.
- Matrix suite now covers strict/lenient severity, bool rejection,
  non-Python code-map skip behavior, and exec close lifecycle contracts.
- Validation evidence:
  - `uv run pytest tests/test_validator_contract_matrix.py -v
    --verification-level=standard` -> 40 passed
  - `uv run ruff check tests/test_validator_contract_matrix.py` -> passed
  - `uv run ty check` -> passed

Exit criterion:
- Every family has equivalent validator contract coverage shape.

### 2) Runtime Parity Depth
For parity suites that are currently mostly sampled:
- add forced variant matrices for mode/status/output-type dimensions.
- remove silent skip patterns (for example skip-on-`ValueError`) and assert
  explicit expected outcomes.
- include boundary arithmetic/size cases where language overflow/representation
  may diverge.
Current execution batch:
- [x] Remove skip-on-error in FSM runtime parity sampled loop.
- [x] Add forced-variant parity coverage for sampled-heavy families.
- [x] Add forced-variant runtime parity tests in:
      `tests/test_fsm_runtime_parity.py`,
      `tests/test_bitops_runtime_parity.py`,
      `tests/test_intervals_runtime_parity.py`,
      `tests/test_stateful_runtime_parity.py`,
      `tests/test_simple_algorithms_runtime_parity.py`.

Progress update (2026-02-10):
- FSM sampled parity now asserts explicit success/error outcomes instead of
  skipping on `ValueError`.
- Added focused forced-variant parity tests for all five targeted files.
- Validation evidence:
  - targeted full parity run: 20 passed
  - `ruff` on changed parity files: passed
  - `ty check`: passed

Current execution batch (2026-02-10 follow-up):
- [x] Strengthen FSM runtime parity error-path assertions to require semantic
      alignment with Python evaluator errors (not just nonzero exit).

Progress update (2026-02-10 follow-up):
- Updated `tests/test_fsm_runtime_parity.py` error-path checks to assert
  semantic alignment (nonzero exit + expected undefined-transition message)
  from Java/Rust runtime failures, tied to Python `eval_fsm` error text.
- Validation evidence:
  - `uv run pytest tests/test_fsm_runtime_parity.py -v
    --verification-level=full` -> 4 passed

Current execution batch (2026-02-10, issue #3 int32-boundary parity coverage):
- [x] Add deterministic boundary-focused runtime parity tests in:
      `tests/test_simple_algorithms_runtime_parity.py`,
      `tests/test_stateful_runtime_parity.py`,
      `tests/test_piecewise_runtime_parity.py`.
- [x] Include explicit high-magnitude int32-edge probe values
      (`2_000_000_000`, `2_147_483_647`, and `50_000^2`-style inputs).
- [x] Run targeted full parity suites for touched files and run
      `uv run ruff check` + `uv run ty check` on touched files.

Current execution batch (2026-02-10, review item #6 expected-source cleanup):
- [x] Replace hardcoded expected values in overflow-adjacent parity tests with
      evaluator-derived expected outputs in:
      `tests/test_sequence_dp_runtime_parity.py` and
      `tests/test_stack_bytecode_runtime_parity.py`.
- [x] Preserve deterministic inputs/cases and explicit Java/Rust parity
      assertions against evaluator-derived expected outputs.
- [x] Run targeted validation:
      `uv run pytest ... --verification-level=full` for both touched files,
      plus `uv run ruff check` and `uv run ty check` on touched files.

Progress update (2026-02-10, review item #6 expected-source cleanup):
- Replaced hardcoded expected values in overflow-adjacent parity tests with
  evaluator-derived expected outputs in:
  - `tests/test_sequence_dp_runtime_parity.py`
  - `tests/test_stack_bytecode_runtime_parity.py`
- Added runtime-output normalization helpers where needed to compare evaluator
  outputs against Java/Rust `i64` runtime representations.
- Kept deterministic case coverage and Java/Rust parity assertions intact while
  using evaluator-derived expected values.
- Validation evidence:
  - `uv run pytest tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py -v
    --verification-level=full` -> 11 passed
  - `uv run ruff check tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py` -> passed
  - `uv run ty check tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py` -> passed

Progress update (2026-02-10, issue #3 int32-boundary parity coverage):
- Added deterministic int32-boundary parity regressions:
  - `test_simple_algorithms_runtime_parity_int32_boundary_cases`
  - `test_stateful_runtime_parity_int32_boundary_cases`
  - `test_piecewise_runtime_parity_int32_boundary_cases`
- New cases cover explicit boundary values and overflow-adjacent arithmetic
  probes including `2_000_000_000`, `2_147_483_647`, and `50_000^2`-magnitude
  paths.
- Validation evidence:
  - `uv run pytest tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py -v --verification-level=full`
    -> 18 passed
  - `uv run ruff check tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py` -> passed
  - `uv run ty check tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py` -> passed

Current execution batch (2026-02-10, review item #5 oversized-literal parity):
- [x] Update oversized-literal tests in:
      `tests/test_piecewise_runtime_parity.py`,
      `tests/test_stateful_runtime_parity.py`,
      `tests/test_simple_algorithms_runtime_parity.py`
      so Java/Rust outputs are asserted against Python evaluator outputs.
- [x] Replace oversized divisor/remainder fixtures in parity tests with values
      that remain valid under the current int32 contract.
- [x] Expand `tests/test_java_render.py` `TestJavaIntLiteral` assertions to
      cover compile-safe boundary/extreme integer rendering.
- [x] Run targeted verification commands:
      `uv run pytest ... --verification-level=full`,
      `uv run ruff check ...`,
      `uv run ty check ...`.

Progress update (2026-02-10, review item #5 oversized-literal parity):
- Replaced compile-only oversized-literal checks with runtime parity assertions
  against Python eval in:
  - `test_piecewise_runtime_parity_with_oversized_int_literals`
  - `test_stateful_runtime_parity_with_oversized_int_literals`
  - `test_simple_algorithms_runtime_parity_with_oversized_int_literals`
- Updated oversized mod fixtures to valid-contract values (for example,
  `piecewise` now uses `ExprMod.divisor=11`, and the `stateful` oversized case
  no longer uses oversized `PredicateModEq` divisor/remainder constants).
- Expanded `TestJavaIntLiteral` coverage in `tests/test_java_render.py` for:
  - int32 boundary literals
  - just-outside-int32 casted literals
  - long-range boundary values rendered via casted `L` literals.
- Validation evidence:
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py
    tests/test_java_render.py -v --verification-level=full -k
    "oversized_int_literals or TestJavaIntLiteral"` -> 9 passed.
  - `uv run ruff check tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py tests/test_java_render.py`
    -> passed.
  - `uv run ty check tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py tests/test_java_render.py`
    -> passed.

Current execution batch (2026-02-10, core semantics blocking fixes #1/#2/#3):
- [x] Add int32 predicate evaluation mode in `src/genfxn/core/predicates.py`
      and wire int32-family eval/query call sites (`piecewise`, `stateful`,
      `simple_algorithms`) to use it.
- [x] Align int32 `TransformClip` evaluation semantics in
      `src/genfxn/core/transforms.py` with Java/Rust wrapped-bound behavior.
- [x] Harden modulo divisor safety at model layer:
      `src/genfxn/core/predicates.py` (`PredicateModEq`) and
      `src/genfxn/piecewise/models.py` (`ExprMod`) with int32-safe divisor
      bounds to prevent zero/negative-after-wrap divergence.
- [x] Update Rust predicate rendering and affected family renderers as needed to
      preserve int32 parity with new core predicate semantics.
- [x] Add/adjust regression and parity tests for int32 predicate semantics,
      clip alignment, and modulo-divisor safety.
- [x] Run targeted validation for touched files:
      `uv run pytest ... --verification-level=full`,
      `uv run ruff check ...`, and `uv run ty check ...`.

Progress update (2026-02-10, core semantics blocking fixes #1/#2/#3):
- Added int32 predicate evaluation mode in `src/genfxn/core/predicates.py` and
  switched int32-family eval/query call sites in:
  `src/genfxn/piecewise/eval.py`,
  `src/genfxn/stateful/eval.py`,
  `src/genfxn/stateful/queries.py`,
  `src/genfxn/simple_algorithms/eval.py`, and
  `src/genfxn/simple_algorithms/queries.py`.
- Aligned int32 clip semantics via new helpers in `src/genfxn/core/int32.py`
  and `src/genfxn/core/transforms.py`, and synchronized Rust helper ordering in
  `src/genfxn/langs/rust/stateful.py` and
  `src/genfxn/langs/rust/simple_algorithms.py`.
- Hardened divisor bounds for int32 parity safety in:
  `src/genfxn/core/predicates.py` (`PredicateModEq`) and
  `src/genfxn/piecewise/models.py` (`ExprMod` + `PiecewiseAxes.divisor_range`).
- Updated Rust predicate rendering for int32 mode in
  `src/genfxn/langs/rust/predicates.py` and applied it in
  `src/genfxn/langs/rust/piecewise.py`,
  `src/genfxn/langs/rust/stateful.py`, and
  `src/genfxn/langs/rust/simple_algorithms.py`.
- Added targeted regressions in:
  `tests/test_core_dsl.py`,
  `tests/test_piecewise.py`,
  `tests/test_piecewise_runtime_parity.py`,
  `tests/test_stateful_runtime_parity.py`,
  `tests/test_simple_algorithms_runtime_parity.py`,
  and `tests/test_rust_render.py`.
- Validation evidence:
  - `uv run pytest tests/test_core_dsl.py tests/test_piecewise.py
    tests/test_rust_render.py -v --verification-level=standard`
    -> 232 passed.
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full` -> 25 passed.
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.

Exit criterion:
- Each family parity file contains both sampled and forced-variant sections.

### 3) Suite Generation Robustness
- harden greedy quota selection with local repair/backtracking or diversified
  retry seeds.
- validate invalid inputs early (for example `pool_size <= 0`).
- add deterministic regression tests for previously failing quota traps.
Current execution batch:
- [x] Diversify pool seed across retries in `generate_suite`.
- [x] Add deterministic multi-restart selection per retry to escape local
      optima.
- [x] Add/extend intervals D2 regression coverage in `tests/test_suites.py`.

Progress update (2026-02-10):
- Added deterministic pool-seed diversification per retry and best-of-restarts
  selection in `src/genfxn/suites/generate.py`.
- Added intervals D2 local-optimum recovery regression coverage in
  `tests/test_suites.py`.
- Validation evidence:
  - intervals all-difficulties full test: passed
  - intervals D2 local-optimum recovery full test: passed
  - `ruff` + `ty check`: passed

Exit criterion:
- `tests/test_suites.py` full-mode integration no longer fails on known traps.

### 4) Split Behavior Consistency
- decide whether CLI and library random split behavior should be identical.
- either unify implementations or document intentional divergence clearly.
- add regression tests that codify the chosen contract.

Progress update (2026-02-10):
- Fixed CLI random split memory regression by restoring streaming exact-count
  split (no task-list materialization).
- Added regression coverage ensuring CLI random split does not call
  `genfxn.splits.random_split`.
- Added `tests/test_split_contracts.py`:
  - deterministic contract tests for library random split
  - deterministic contract tests for CLI random split
  - explicit cross-implementation contract parity tests (without enforcing
    identical membership)
- Expanded exact-holdout type matrix tests in both library and CLI split tests.
- Updated `README.md` split docs to clarify intentional CLI/library behavior
  differences under equal seed/ratio.

Current execution batch (2026-02-10 follow-up):
- [x] Centralize holdout matcher behavior so CLI and library share one
      implementation while preserving existing external behavior/tests.

Progress update (2026-02-10 follow-up):
- Added shared matcher `matches_holdout(...)` in `src/genfxn/splits.py` and
  updated `split_tasks(...)` to call it.
- Refactored `src/genfxn/cli.py` `_matches_holdout(...)` to delegate to
  `genfxn.splits.matches_holdout`, removing duplicate logic while preserving
  public behavior/tests.
- Validation evidence:
  - `uv run pytest tests/test_splits.py tests/test_cli.py -v
    --verification-level=standard -k "...matcher/holdout exact-range bool
    cases..."` -> 18 passed
  - `uv run ruff check src/genfxn/splits.py src/genfxn/cli.py` -> passed
  - `uv run ty check src/genfxn/splits.py src/genfxn/cli.py` -> passed

Exit criterion:
- No ambiguous expectations between CLI split and `splits.py` outputs.

### 5) Verification Policy
- enforce `uv run pytest tests/ -v --verification-level=full` in CI for merge
  gates (or at minimum changed-family + nightly global full).
- keep `standard` for local fast loop, but document that it is non-exhaustive.

Current execution batch (2026-02-10):
- [x] Add GitHub Actions workflow under `.github/workflows/` to run:
      `uv sync`, `uv run ruff check .`, `uv run ty check`, and
      `uv run pytest tests/ -v --verification-level=full` on PR/push.
- [x] Update docs to make CI full-verification enforcement explicit.
- [x] Validate workflow syntax/lint (if tool available) and run targeted local
      gate commands.

Progress update (2026-02-10):
- Added `.github/workflows/ci.yml` with enforced full gate on push/PR.
- Updated `README.md` CI/testing docs and aligned PR testing checklist.
- Validation evidence:
  - workflow YAML parse check passed.
  - `uv run ruff check .`: passed.
  - `uv run ty check`: passed.
  - `uv run pytest tests/test_verification_levels.py -v
    --verification-level=full`: 3 passed.

Exit criterion:
- Full-mode-only failures are rare and quickly detected pre-merge.

### 6) Numeric/Representation Hardening
- audit stack bytecode and sequence-dp Java vs Rust runtime arithmetic semantics
  for overflow-adjacent divergence and panic risk.
- prefer runtime-parity hardening (renderer semantics + explicit parity tests)
  over broad feature reduction.
- add/adjust non-ASCII string length parity tests to confirm code-point
  alignment.

Current execution batch (2026-02-10):
- [x] Align Rust stack bytecode arithmetic ops with Java long behavior for
      overflow-adjacent paths (`add/sub/mul/neg/abs/div/mod`).
- [x] Align Rust sequence-dp arithmetic with Java long behavior for DP
      accumulation and `mod_eq` subtraction path.
- [x] Add runtime parity regressions for overflow-adjacent cases in
      `tests/test_stack_bytecode_runtime_parity.py` and
      `tests/test_sequence_dp_runtime_parity.py`.
- [x] Expand non-ASCII string length parity coverage in
      `tests/test_stringrules_runtime_parity.py`.
- [x] Run targeted full parity tests on touched runtime suites and run
      `uv run ruff check` + `uv run ty check` on touched files.

Progress update (2026-02-10):
- `src/genfxn/langs/rust/stack_bytecode.py` now emits explicit wrapping/edge
  semantics aligned with Java `long`:
  `wrapping_add/sub/mul`, `wrapping_neg`, `i64::MIN`-safe abs handling, and
  guarded div/mod helpers for `MIN / -1` and `MIN % -1`.
- `src/genfxn/langs/rust/sequence_dp.py` now uses wrapping arithmetic for DP
  accumulation and predicate subtraction, and mirrors Java unsigned comparison
  behavior in `abs_diff_le`.
- Added explicit overflow-adjacent parity tests:
  - `test_stack_bytecode_runtime_parity_overflow_adjacent_cases`
  - `test_sequence_dp_runtime_parity_overflow_adjacent_cases`
  Both suites exercise Rust in debug mode (`rustc` without `-O`) and release
  mode to guard against panic-sensitive arithmetic drift.
- Expanded string length parity tests for combining marks, ZWJ emoji sequence,
  and regional-indicator flag sequence:
  - updated `test_stringrules_runtime_parity_non_ascii_length_cmp`
  - added `test_stringrules_runtime_parity_non_ascii_length_cmp_eq_two`
- Validation evidence:
  - `uv run pytest tests/test_stack_bytecode_runtime_parity.py
    tests/test_sequence_dp_runtime_parity.py
    tests/test_stringrules_runtime_parity.py -v
    --verification-level=full` -> 16 passed.
  - `uv run ruff check` on touched renderer/parity files -> passed.
  - `uv run ty check` on touched renderer/parity files -> passed.

Exit criterion:
- Overflow-adjacent runtime behavior is explicitly parity-tested and Rust/Java
  arithmetic semantics are aligned for targeted families.

### 7) Int32 Overflow Contract Alignment (Blocking Issue #2)
- define one explicit arithmetic contract for `piecewise`, `stateful`, and
  `simple_algorithms`: Java `int`-style signed 32-bit wrapping for overflow-
  adjacent paths.
- apply the contract with minimal blast radius:
  - Python evaluators become explicit int32 semantics oracle.
  - Rust renderers for these families mirror the same int32 wrapping behavior.
  - Java renderers remain on `int` semantics (already aligned).
- add targeted overflow parity regressions that previously diverged and now
  align across Python eval, Java runtime, and Rust runtime.

Current execution batch (2026-02-10, blocking):
- [x] Add shared int32 arithmetic helpers and update Python eval paths in:
      `src/genfxn/piecewise/eval.py`,
      `src/genfxn/stateful/eval.py`,
      `src/genfxn/simple_algorithms/eval.py`
      (and supporting transform/query helpers as needed).
- [x] Update Rust family renderers to enforce int32 wrapping semantics in:
      `src/genfxn/langs/rust/piecewise.py`,
      `src/genfxn/langs/rust/stateful.py`,
      `src/genfxn/langs/rust/simple_algorithms.py`.
- [x] Add overflow-focused runtime parity regressions in:
      `tests/test_piecewise_runtime_parity.py`,
      `tests/test_stateful_runtime_parity.py`,
      `tests/test_simple_algorithms_runtime_parity.py`.
- [x] Run targeted full parity tests and touched-file `ruff`/`ty`.

Progress update (2026-02-10, blocking issue #2 complete):
- Added `src/genfxn/core/int32.py` and switched Python eval paths for
  `piecewise`, `stateful`, and `simple_algorithms` to explicit int32 wrapping.
- Extended `src/genfxn/core/transforms.py` with opt-in int32-wrapping eval and
  wired int32-aware usage into evaluator/query paths where needed.
- Updated Rust renderers for the same families to preserve public `i64`
  signatures while enforcing int32 wrapping semantics internally.
- Added overflow-focused runtime parity regressions in:
  `tests/test_piecewise_runtime_parity.py`,
  `tests/test_stateful_runtime_parity.py`,
  `tests/test_simple_algorithms_runtime_parity.py`.
- Updated impacted Rust renderer assertions in `tests/test_rust_render.py`.
- Validation evidence:
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full` -> 21 passed
  - `uv run pytest tests/test_piecewise.py tests/test_stateful.py
    tests/test_simple_algorithms.py -v --verification-level=standard`
    -> 144 passed
  - `uv run pytest tests/test_rust_render.py -v
    --verification-level=standard -k "TransformRust or ExpressionRust or
    PiecewiseRust or StatefulRust or SimpleAlgorithmsRust"` -> 45 passed
  - `uv run ruff check` on touched files -> passed
  - `uv run ty check` on touched files -> passed

Exit criterion:
- Overflow-adjacent outputs that previously diverged now align under one
  explicit int32 contract across Python eval, Java, and Rust for the three
  targeted families.

## Immediate Next Actions
1. Build a shared validator contract checklist and apply it to remaining
   families where coverage shape still differs.
2. Decide and document policy for Python evaluator semantics vs Java/Rust
   wrapping semantics in overflow-only domains for `stack_bytecode` and
   `sequence_dp` (renderer/runtime parity is now hardened for Java/Rust).

### 8) Axes Bool-As-Int Coercion Hardening (Intervals/Piecewise)
Current execution batch (2026-02-10):
- [x] Add explicit model-level int-range helpers in:
      `src/genfxn/intervals/models.py` and
      `src/genfxn/piecewise/models.py`
      so bool values are rejected for int tuple range fields.
- [x] Add focused bool-rejection tests in:
      `tests/test_intervals.py` and `tests/test_piecewise.py`.
- [x] Run requested validation commands:
      `uv run pytest tests/test_intervals.py tests/test_piecewise.py -v`,
      `uv run ruff check src/genfxn/intervals/models.py src/genfxn/piecewise/models.py tests/test_intervals.py tests/test_piecewise.py`,
      and `uv run ty check`.

Progress update (2026-02-10, axes bool-as-int hardening complete):
- Added explicit pre-validation helpers in both model modules to reject bool
  bounds for int tuple range axes fields before pydantic int coercion:
  - `src/genfxn/intervals/models.py`
  - `src/genfxn/piecewise/models.py`
- Added focused bool-rejection regressions:
  - `tests/test_intervals.py` (`TestModels.test_axes_reject_bool_in_int_range_bounds`)
  - `tests/test_piecewise.py`
    (`TestAxesValidation.test_rejects_bool_in_int_range_bounds`)
- Validation evidence:
  - `uv run pytest tests/test_intervals.py tests/test_piecewise.py -v`
    -> 55 passed.
  - `uv run ruff check src/genfxn/intervals/models.py
    src/genfxn/piecewise/models.py tests/test_intervals.py
    tests/test_piecewise.py`
    -> All checks passed.
  - `uv run ty check`
    -> failed on pre-existing unrelated diagnostics in `tests/test_cli.py`
       (`not-subscriptable` at lines 1647 and 1648).

Exit criterion:
- Bool values no longer coerce into int tuple axis ranges for intervals and
  piecewise, with regression coverage guarding behavior.

### 9) Split Parsing/Matching Consistency Hardening (Current Batch)
Intake covered:
- Blocking: CLI large-int range parsing precision loss.
- Important: library range matcher non-finite behavior drift from CLI.
- Important: bool-as-int coercion in axes/spec model ranges.
- Important (policy): query-input uniqueness contract across tags/families.

Completed in this batch:
- [x] `src/genfxn/cli.py`: `_parse_numeric_range` now parses integer-looking
      bounds directly as `int` (no float round-trip), preserving exact large
      integers while keeping float/scientific notation support.
- [x] `src/genfxn/splits.py`: range matching now rejects non-finite bounds and
      non-finite spec values; bool rejection remains intact.
- [x] `src/genfxn/intervals/models.py` and
      `src/genfxn/piecewise/models.py`: pre-validators now reject bool bounds
      for int tuple range fields before coercion.
- [x] Added focused regression tests:
      `tests/test_cli.py`, `tests/test_splits.py`,
      `tests/test_intervals.py`, `tests/test_piecewise.py`.

Consolidated validation evidence (post-merge in this branch):
- `uv run pytest tests/test_cli.py tests/test_splits.py tests/test_intervals.py tests/test_piecewise.py -v`
  -> 226 passed.
- `uv run ruff check .` -> passed.
- `uv run ty check` -> passed.

Remaining decision/pending item:
- [ ] Define and codify query-input uniqueness contract (global input uniqueness
      vs per-tag uniqueness) for families like `intervals` and
      `graph_queries`, then align generator + tests accordingly.
