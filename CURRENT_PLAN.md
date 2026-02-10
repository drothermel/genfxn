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

New intake extension (2026-02-10, safe_exec startup-timeout flake):
- [x] Separate persistent-worker startup timeout from function execution timeout
      in `src/genfxn/core/safe_exec.py` (floor-based init timeout).
- [x] Keep runtime timeout semantics unchanged for function execution calls.
- [x] Add focused startup-timeout regression coverage in
      `tests/test_safe_exec.py`.
- [x] Run requested targeted `pytest`/`ruff`/`ty` validations and record
      results.

Progress update (2026-02-10, safe_exec startup-timeout flake):
- Added `_PERSISTENT_STARTUP_TIMEOUT_FLOOR_SEC` and
  `_persistent_startup_timeout_sec(...)` in `src/genfxn/core/safe_exec.py`.
- `_PersistentWorker` startup now waits on init handshake using the startup
  timeout floor instead of reusing tiny execution timeouts.
- Function execution timeout semantics remain unchanged in
  `_IsolatedFunction.__call__` -> `_PersistentWorker.call(..., timeout_sec)`.
- Added regression `test_persistent_worker_startup_timeout_uses_floor` in
  `tests/test_safe_exec.py`.
- Validation evidence:
  - `uv run pytest tests/test_safe_exec.py::test_timeout_terminates_descendant_processes -v`
    -> 1 passed
  - `uv run pytest tests/test_safe_exec.py -k "startup or timeout" -v`
    -> 2 passed
  - `uv run ruff check src/genfxn/core/safe_exec.py tests/test_safe_exec.py`
    -> passed
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
1. [x] Build a shared validator contract checklist and apply it to remaining
   families where coverage shape still differs.
2. [x] Decide and document policy for Python evaluator semantics vs Java/Rust
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
- [x] Define and codify query-input uniqueness contract (global input
      uniqueness vs per-tag uniqueness) for families like `intervals` and
      `graph_queries`.

Progress update (2026-02-10, policy/docs follow-up):
- Codified query-input uniqueness contract:
  - default contract is global input uniqueness (`dedupe_queries`) for
    `piecewise`, `stateful`, `simple_algorithms`, `stringrules`, `stack_bytecode`,
    `fsm`, and `bitops`.
  - explicit exception contract is per-tag input uniqueness for relation-like
    families where tag coverage is primary:
    `intervals`, `graph_queries`, `sequence_dp`, and `temporal_logic`.
- Codified overflow-semantics policy for `stack_bytecode` and `sequence_dp`:
  Python evaluator remains the canonical semantic source; overflow-adjacent
  Java/Rust parity assertions compare against evaluator output normalized to
  signed `i64`/Java `long` representation.
- Added concise contract notes to `README.md`; no logic changes were required.

New intake extension (2026-02-10, intervals/graph_queries uniqueness codification):
- [x] Add a shared helper that makes per-tag query-input uniqueness explicit.
- [x] Switch `intervals` and `graph_queries` query generators to that helper
      while preserving current behavior (per-tag uniqueness, cross-tag allowed).
- [x] Add focused tests that lock the contract:
      duplicate inputs allowed across tags, rejected/deduped within a tag.
- [x] Update any contract docs touched by this behavior and record validation
      evidence for requested targeted commands.

Progress update (2026-02-10, intervals/graph_queries uniqueness codification):
- Added shared per-tag helper `dedupe_queries_per_tag_input(...)` in
  `src/genfxn/core/models.py` and reused shared freeze/equality internals so
  keying/conflict behavior is consistent with `dedupe_queries(...)`.
- Updated generators:
  - `src/genfxn/intervals/queries.py`
  - `src/genfxn/graph_queries/queries.py`
  to enforce explicit per-tag uniqueness contract through the shared helper.
- Added validator enforcement for the same contract (duplicate inputs blocked
  within the same tag, cross-tag duplicates allowed) in:
  - `src/genfxn/intervals/validate.py`
  - `src/genfxn/graph_queries/validate.py`
- Added focused tests in:
  - `tests/test_core_models.py`
  - `tests/test_intervals.py`
  - `tests/test_graph_queries.py`
  - `tests/test_validate_intervals.py`
  - `tests/test_validate_graph_queries.py`
- Updated contract docs in `README.md` and architecture note in
  `ARCHITECTURE.md`.
- Validation evidence:
  - `uv run pytest tests/test_intervals.py tests/test_graph_queries.py tests/test_core_models.py -v --verification-level=standard`
    -> 73 passed.
  - `uv run pytest tests/test_validator_contract_matrix.py -k "intervals or graph_queries" -v --verification-level=standard`
    -> 8 passed.
  - `uv run ruff check src/genfxn/core/models.py src/genfxn/intervals/queries.py src/genfxn/graph_queries/queries.py src/genfxn/intervals/validate.py src/genfxn/graph_queries/validate.py tests/test_core_models.py tests/test_intervals.py tests/test_graph_queries.py tests/test_validate_intervals.py tests/test_validate_graph_queries.py`
    -> All checks passed.
  - `uv run ty check` -> All checks passed.

### 10) Python Renderer Int32 Semantics Parity (Current Batch)
Current execution batch (2026-02-10):
- [x] Add optional int32-aware render modes in:
      `src/genfxn/core/predicates.py` and
      `src/genfxn/core/transforms.py`
      with default behavior unchanged.
- [x] Update family renderers to use int32-aware rendering and wrapped
      accumulation/window logic in:
      `src/genfxn/piecewise/render.py`,
      `src/genfxn/stateful/render.py`, and
      `src/genfxn/simple_algorithms/render.py`.
- [x] Add high-magnitude regression tests in:
      `tests/test_piecewise.py`, `tests/test_stateful.py`, and
      `tests/test_simple_algorithms.py` (including `2_000_000_000` and
      quadratic `x=50_000` style cases).
- [x] Run validation commands:
      `uv run pytest tests/test_piecewise.py tests/test_stateful.py tests/test_simple_algorithms.py -v`,
      `uv run ruff check <touched files>`, and `uv run ty check`.

Progress update (2026-02-10, Python renderer int32 semantics complete):
- Added optional `int32_wrap` rendering mode in:
  - `src/genfxn/core/predicates.py`
  - `src/genfxn/core/transforms.py`
  while preserving default render output for non-int32 families.
- Updated Python family renderers to emit int32-semantics code with helper
  ops and wrapped control/accumulator/window arithmetic:
  - `src/genfxn/piecewise/render.py`
  - `src/genfxn/stateful/render.py`
  - `src/genfxn/simple_algorithms/render.py`
- Added regression coverage for high-magnitude int32 behavior:
  - `tests/test_piecewise.py`:
    `test_render_roundtrip_int32_large_values`
  - `tests/test_stateful.py`:
    `test_render_roundtrip_int32_large_values`
  - `tests/test_simple_algorithms.py`:
    `test_count_pairs_roundtrip_int32_wrapped_sum_comparison`,
    `test_max_window_roundtrip_int32_large_values`
- Validation evidence:
  - `uv run pytest tests/test_piecewise.py tests/test_stateful.py tests/test_simple_algorithms.py -v`
    -> 157 passed.
  - `uv run ruff check src/genfxn/core/predicates.py src/genfxn/core/transforms.py src/genfxn/piecewise/render.py src/genfxn/stateful/render.py src/genfxn/simple_algorithms/render.py tests/test_piecewise.py tests/test_stateful.py tests/test_simple_algorithms.py`
    -> All checks passed.
  - `uv run ty check` -> All checks passed.

Exit criterion:
- Rendered Python output for the three int32 families matches evaluator results
  on overflow-adjacent deterministic inputs, with regression coverage.

### 11) Java FSM Predicate Semantic Drift (Current Batch)
Current execution batch (2026-02-10):
- [x] Add explicit `int32_wrap` mode in
      `src/genfxn/langs/java/predicates.py` so wrapped/unwrapped semantics are
      selectable.
- [x] Update Java family renderers to pass predicate mode explicitly:
      FSM unwrapped; piecewise/stateful/simple_algorithms wrapped.
- [x] Ensure unwrapped mode renders out-of-int32 constants as compilable
      non-narrowing comparisons/in-set checks to preserve Python eval intent.
- [x] Add focused regressions in:
      `tests/test_java_render.py` and `tests/test_fsm_runtime_parity.py`
      for `lt(2147483648)` mismatch behavior.
- [x] Run targeted validation:
      `uv run pytest tests/test_java_render.py tests/test_fsm_runtime_parity.py -v --verification-level=full`,
      `uv run ruff check <touched files>`,
      `uv run ty check`.

Progress update (2026-02-10, Java FSM predicate drift complete):
- Added `int32_wrap` mode in `src/genfxn/langs/java/predicates.py` and
  propagated mode through recursive predicate rendering.
- Unwrapped mode now preserves int-input predicate intent for out-of-int32
  constants without uncompilable literals by:
  - constant-folding comparison predicates outside int32 bounds
  - ignoring unreachable out-of-int32 values for unwrapped `in_set`.
- Updated Java family renderers to set predicate mode explicitly:
  - `fsm`: `int32_wrap=False`
  - `piecewise`, `stateful`, `simple_algorithms`: `int32_wrap=True`
- Added regressions:
  - `tests/test_java_render.py` for wrapped vs unwrapped `lt(2147483648)` and
    unwrapped `in_set` out-of-int32 filtering.
  - `tests/test_fsm_runtime_parity.py` parity case covering
    `lt(2147483648)` threshold behavior.
- Validation evidence:
  - `uv run pytest tests/test_java_render.py tests/test_fsm_runtime_parity.py -v --verification-level=full`
    -> 178 passed.
  - `uv run ruff check src/genfxn/langs/java/predicates.py src/genfxn/langs/java/fsm.py src/genfxn/langs/java/stateful.py src/genfxn/langs/java/simple_algorithms.py src/genfxn/langs/java/piecewise.py tests/test_java_render.py tests/test_fsm_runtime_parity.py`
    -> All checks passed.
  - `uv run ty check` -> All checks passed.

Exit criterion:
- FSM Java predicate behavior matches Python evaluator semantics for out-of-int32
  comparison constants, while int32 families retain explicit wrapped behavior.

### 12) Boundary Query Synthesis Semantics (Current Batch)
Current execution batch (2026-02-10):
- [x] Fix `stateful` mod_eq matching-value synthesis in
      `src/genfxn/stateful/queries.py` so generated matches honor
      `eval_predicate(..., int32_wrap=True)` semantics for large/out-of-range
      value ranges.
- [x] Fix `piecewise` boundary query threshold handling in
      `src/genfxn/piecewise/queries.py` to use wrapped int32 threshold
      semantics.
- [x] Add focused regressions in:
      `tests/test_stateful.py` and `tests/test_piecewise.py`.
- [x] Run targeted validation commands:
      `uv run pytest tests/test_stateful.py tests/test_piecewise.py -v`,
      `uv run ruff check <touched files>`,
      `uv run ty check`.

Exit criterion:
- Boundary/query synthesis for int32 families uses wrapped predicate semantics
  for mod-equality matching and threshold boundaries, with regression coverage
  and requested command evidence.

Progress update (2026-02-10, boundary query synthesis semantics complete):
- `src/genfxn/stateful/queries.py`:
  - rewrote mod-equality matching synthesis to solve congruence across int32
    wrap segments (`k * 2^32`) instead of raw modulo on unbounded `x`.
  - generated candidates now align with
    `eval_predicate(..., int32_wrap=True)` for overflow-adjacent ranges.
- `src/genfxn/piecewise/queries.py`:
  - `_get_branch_threshold(...)` now wraps extracted threshold values with
    `wrap_i32(...)` before boundary/coverage query synthesis.
- Added focused regressions:
  - `tests/test_stateful.py`:
    `test_mod_eq_boundary_uses_wrapped_predicate_truth`
  - `tests/test_piecewise.py`:
    `test_boundary_queries_use_wrapped_thresholds`
- Validation evidence:
  - `uv run pytest tests/test_stateful.py tests/test_piecewise.py -v`
    -> 82 passed, 4 failed (existing unrelated render-string assertions in
       `tests/test_stateful.py`).
  - `uv run ruff check src/genfxn/stateful/queries.py
    src/genfxn/piecewise/queries.py tests/test_stateful.py
    tests/test_piecewise.py` -> passed.
  - `uv run ty check` -> passed.

### 13) Default Test Parallelism + CI Fan-out (Current Batch)
Current execution batch (2026-02-10):
- [x] Make pytest parallel by default via repository configuration so plain
      `uv run pytest ...` runs with xdist workers.
- [x] Update CI workflow to keep full verification gate while maximizing
      parallel execution (job fan-out + parallel pytest workers).
- [x] Align `scripts/run_tests.py` defaults with machine-maximized workers and
      keep explicit worker override behavior.
- [x] Update test/docs coverage for runner/default parallel behavior changes.
- [x] Run focused validation:
      `uv run pytest tests/test_run_tests_script.py tests/test_verification_levels.py -v --verification-level=standard`,
      `uv run ruff check scripts/run_tests.py tests/test_run_tests_script.py`,
      `uv run ty check scripts/run_tests.py tests/test_run_tests_script.py`.

Exit criterion:
- Default local pytest and CI full gate execute with xdist worker parallelism,
  CI quality gates fan out safely, and docs/tests reflect the new default.

Progress update (2026-02-10, default parallelism + CI fan-out complete):
- Set pytest xdist as the repository default in `pyproject.toml`:
  `addopts = "-n auto --dist=worksteal"`.
- Updated CI workflow in `.github/workflows/ci.yml` to run three parallel jobs:
  `lint`, `typecheck`, and `test-full`; full test job now runs:
  `uv run pytest tests/ -v --verification-level=full -n auto --dist=worksteal`.
- Updated `scripts/run_tests.py` defaults to machine-max workers (`auto` for
  all tiers), retained explicit `--workers <int>` override behavior, and kept
  `--workers 0` as explicit single-process mode (`-n 0`).
- Expanded runner tests in `tests/test_run_tests_script.py`:
  - default `auto` workers when xdist is present
  - explicit `--workers 0` forces single-process execution (`-n 0`)
- Updated docs in `README.md` and `ARCHITECTURE.md` to state default pytest
  parallelism and CI gate/job behavior.
- Validation evidence:
  - `uv run pytest tests/test_run_tests_script.py
    tests/test_verification_levels.py -v --verification-level=standard`
    -> 8 passed.
  - `uv run pytest tests/test_run_tests_script.py -v
    --verification-level=standard -n 0` -> 5 passed.
  - `uv run ruff check scripts/run_tests.py tests/test_run_tests_script.py`
    -> passed.
  - `uv run ty check scripts/run_tests.py tests/test_run_tests_script.py`
    -> passed.
  - `uv run python` workflow guard script on `.github/workflows/ci.yml`
    basic structure -> passed.

### 14) AST Compatibility for Int32 Helper Prelude (Current Batch)
Current execution batch (2026-02-10):
- [x] Extend AST whitelists for `piecewise`, `stateful`, and
      `simple_algorithms` to allow renderer-owned int32 helper prelude
      patterns (helper names/calls, helper locals, bitwise wrap, raise).
- [x] Keep security assertions intact: imports/dunder/open still rejected.
- [x] Add minimal regression tests that codify helper prelude acceptance.
- [x] Run requested targeted validation:
      `uv run pytest tests/test_validate_piecewise.py tests/test_validate_stateful.py tests/test_validate_simple_algorithms.py tests/test_validation_exec_optin.py tests/test_validator_contract_matrix.py -v --verification-level=standard`,
      `uv run ruff check <touched files>`,
      `uv run ty check`.

Exit criterion:
- Generated Python code from current int32 renderers validates cleanly under
  AST whitelist for the three families while preserving strict/lenient query
  type behavior, exec lifecycle close behavior, and core security rejection
  checks.

Progress update (2026-02-10, AST int32 helper prelude compatibility complete):
- Expanded AST safety contracts in:
  - `src/genfxn/piecewise/ast_safety.py`
  - `src/genfxn/stateful/ast_safety.py`
  - `src/genfxn/simple_algorithms/ast_safety.py`
  to explicitly allow renderer-owned int32 helper patterns:
  helper names/calls, helper locals, helper call arities, `Raise` and
  bitwise-and wrap expressions.
- Updated piecewise AST validator arity/name handling in
  `src/genfxn/piecewise/validate.py` to use explicit arity+name contracts
  (matching stateful/simple style) instead of fixed single-arg calls.
- Added safe-exec runtime compatibility mappings for helper symbols in:
  - `src/genfxn/piecewise/validate.py`
  - `src/genfxn/stateful/validate.py`
  - `src/genfxn/simple_algorithms/validate.py`
  by wiring `__i32_*` and `ValueError` into family `_ALLOWED_BUILTINS`.
- Added focused helper-contract regressions in:
  - `tests/test_validate_piecewise.py`
  - `tests/test_validate_stateful.py`
  - `tests/test_validate_simple_algorithms.py`
  including generated int32 helper prelude acceptance and explicit `open`
  rejection coverage for simple_algorithms helper-level AST checks.
- Validation evidence:
  - `uv run pytest tests/test_validate_piecewise.py
    tests/test_validate_stateful.py
    tests/test_validate_simple_algorithms.py
    tests/test_validation_exec_optin.py
    tests/test_validator_contract_matrix.py -v
    --verification-level=standard`
    -> 205 passed, 8 skipped.
  - `uv run ruff check` on touched validator/ast_safety/test files
    -> passed.
  - `uv run ty check` -> passed.

### 15) Intervals Quantize Difficulty Calibration (Current Batch)
Current execution batch (2026-02-10):
- [x] Reproduce preset calibration failures for intervals and preserve evidence.
- [x] Calibrate intervals quantize-step contribution in
      `src/genfxn/core/difficulty.py` while keeping quantize-step represented.
- [x] Preserve targeted intervals quantize effect semantics and bool coercion
      consistency checks in `tests/test_difficulty.py`.
- [x] Update/extend `tests/test_presets.py` only if calibration coverage needs
      explicit guardrails.
- [x] Run requested validation:
      `uv run pytest tests/test_presets.py -k "intervals_preset_accuracy" -v --verification-level=standard`,
      `uv run pytest tests/test_difficulty.py -k "intervals" -v --verification-level=standard`,
      `uv run ruff check <touched files>`,
      `uv run ty check`.

Exit criterion:
- Intervals preset accuracy passes for difficulties 1-5 with quantize-step
  still included in difficulty scoring, and targeted intervals difficulty tests
  remain green.

Progress update (2026-02-10, intervals quantize calibration complete):
- Root cause confirmed: the previous quantize bonus schedule in
  `_intervals_quantize_bonus(...)` over-shifted preset distributions upward for
  difficulties 1/2/4 due round-threshold crossings.
- Calibrated quantize contribution in `src/genfxn/core/difficulty.py` to:
  - `step <= 1`: `0.0`
  - `step <= 2`: `0.1`
  - `step <= 4`: `0.15`
  - `step > 4`: `0.4`
- Preserved targeted quantize-effect semantics in
  `tests/test_difficulty.py` by keeping the `easy < harder` assertion and
  using a stable baseline spec where quantize-step is the only changed field.
- Validation evidence:
  - `uv run pytest tests/test_presets.py -k "intervals_preset_accuracy" -v --verification-level=standard`
    -> 5 passed.
  - `uv run pytest tests/test_difficulty.py -k "intervals" -v --verification-level=standard`
    -> 5 passed.
  - `uv run ruff check src/genfxn/core/difficulty.py tests/test_difficulty.py`
    -> passed.
  - `uv run ty check` -> passed.

### 16) Intervals D2 Local-Optimum Recovery Hardening (Current Batch)
Current execution batch (2026-02-10):
- [x] Reproduce and root-cause `intervals` D2 local-optimum recovery failure (`46/50` restart-0+repair) with deterministic evidence.
- [x] Harden suite selection in `src/genfxn/suites/generate.py` with deterministic size repair, bounded backtracking/repair improvement, and intra-attempt seed-diversified pool augmentation while preserving determinism.
- [x] Add/adjust regression coverage in `tests/test_suites.py` for the repaired deterministic behavior.
- [x] Run requested validation:
      `uv run pytest tests/test_suites.py::TestIntegration::test_intervals_d2_local_optimum_recovery_when_available -v --verification-level=full`,
      `uv run pytest tests/test_suites.py -k "Determinism or intervals" -v --verification-level=standard`,
      `uv run ruff check <touched files>`,
      `uv run ty check`.

Exit criterion:
- Intervals D2 local-optimum recovery path is deterministic and robust for the known seed/pathology, requested test slices pass, and lint/type gates stay green.

Progress update (2026-02-10, intervals D2 local-optimum recovery complete):
- Updated `src/genfxn/suites/generate.py` with deterministic hardening:
  - selection-size repair in `_repair_selection_with_swaps(...)` now
    deterministically backfills to `quota.total` before swap optimization
  - added bounded deterministic
    `_repair_selection_with_backtracking(...)` for stubborn near-miss deficits
  - added intra-attempt deterministic pool diversification when initial pool
    has bucket-supply shortfall, merging unique candidates via stable task-id
    order.
- Existing integration regression in `tests/test_suites.py` now passes as-is:
  restart-0+repair deterministically reaches full quota size and
  `generate_suite(..., max_retries=0)` recovers to a quota-satisfying suite.
- Validation evidence:
  - `uv run pytest tests/test_suites.py::TestIntegration::test_intervals_d2_local_optimum_recovery_when_available -v --verification-level=full`
    -> 1 passed.
  - `uv run pytest tests/test_suites.py -k "Determinism or intervals" -v --verification-level=standard`
    -> 25 passed, 3 skipped.
  - `uv run ruff check src/genfxn/suites/generate.py`
    -> passed.
  - `uv run ty check`
    -> passed.

### 17) Family-Scoped Full Markers (Current Batch)
Current execution batch (2026-02-10):
- [x] Add dynamic family-scoped markers for full tests in `tests/conftest.py`
      (for example `full_piecewise`, `full_stateful`) based on test file
      ownership, while preserving existing verification-level behavior.
- [x] Register family-scoped markers in `pyproject.toml` for discoverability.
- [x] Add regression coverage in `tests/test_verification_levels.py` proving
      `-m "full_<family>"` selection works for family-owned full tests.
- [x] Document family-scoped full test selection in `README.md`.
- [x] Run focused validation:
      `uv run pytest tests/test_verification_levels.py -v --verification-level=standard`,
      `uv run ruff check tests/conftest.py tests/test_verification_levels.py`,
      `uv run ty check tests/conftest.py tests/test_verification_levels.py`.

Exit criterion:
- Users can select full tests by family marker (`full_<family>`) without
  regressing existing fast/standard/full marker gating semantics.

Progress update (2026-02-10, family-scoped full markers complete):
- Added dynamic family marker assignment in `tests/conftest.py`:
  - full tests in `test_<family>_runtime_parity.py` and
    `test_validate_<family>.py` now receive marker `full_<family>` during
    collection (for supported families).
  - existing verification-level skip logic remains unchanged.
- Registered family-scoped full markers in `pyproject.toml` for all supported
  families (`full_piecewise`, `full_stateful`, `full_simple_algorithms`, etc.).
- Expanded `tests/test_verification_levels.py` with pytester regressions:
  - family marker selects only matching family full tests in full mode
  - family marker still respects standard-mode full-test skip behavior.
- Updated `README.md` Tests section with an example command:
  `uv run pytest tests/ -v --verification-level=full -m "full_piecewise"`.
- Validation evidence:
  - `uv run pytest tests/test_verification_levels.py -v --verification-level=standard`
    -> 5 passed.
  - `uv run ruff check tests/conftest.py tests/test_verification_levels.py`
    -> passed.
  - `uv run ty check tests/conftest.py tests/test_verification_levels.py`
    -> passed.
  - `uv run pytest tests/ --verification-level=full -m "full_piecewise" --collect-only -q`
    -> 12/1910 tests collected (1898 deselected).

### 18) stack_bytecode + sequence_dp Overflow Contract Alignment (Current Batch)
Current execution batch (2026-02-10):
- [x] Audit evaluator vs Java/Rust runtime overflow behavior for
      `stack_bytecode` and `sequence_dp` and confirm concrete divergence points.
- [x] Implement one explicit shared contract with minimal breakage (chosen:
      evaluator-level signed i64 wrap semantics aligned to Java `long`).
- [x] Update runtime parity tests so Python evaluator outputs are asserted
      directly for overflow-adjacent cases, with deterministic edge-value
      coverage.
- [x] Add focused evaluator regression tests in family suites where needed so
      overflow behavior is explicitly locked outside runtime harnesses.
- [x] Run requested validation commands:
      `uv run pytest tests/test_stack_bytecode_runtime_parity.py tests/test_sequence_dp_runtime_parity.py -v --verification-level=full`,
      `uv run pytest tests/test_stack_bytecode.py tests/test_sequence_dp.py -v --verification-level=standard`,
      `uv run ruff check <touched files>`,
      `uv run ty check`.

Exit criterion:
- `stack_bytecode` and `sequence_dp` evaluators, Java renderers, Rust
  renderers, and runtime parity tests share one explicit signed i64 overflow
  contract with no silent divergence on covered edge cases.

Progress update (2026-02-10, stack_bytecode + sequence_dp overflow alignment complete):
- Codified evaluator-level signed i64 semantics to match Java/Rust runtime
  behavior:
  - `src/genfxn/stack_bytecode/eval.py` now applies i64 wrap semantics for
    arithmetic ops (`add/sub/mul/neg/abs`) and Java-consistent `div/mod`
    `Long.MIN_VALUE` edge behavior.
  - `src/genfxn/sequence_dp/eval.py` now applies i64 wrap semantics for DP
    accumulation and wrapped predicate arithmetic for `abs_diff_le` and
    `mod_eq`.
- Updated runtime parity suites to treat Python evaluator output as the
  expected source directly for overflow-adjacent cases (no test-local wrap
  adapters in assertions):
  - `tests/test_stack_bytecode_runtime_parity.py`
  - `tests/test_sequence_dp_runtime_parity.py`
- Added focused evaluator contract tests:
  - `tests/test_stack_bytecode.py`
  - `tests/test_sequence_dp.py`
- Validation evidence:
  - `uv run pytest tests/test_stack_bytecode_runtime_parity.py tests/test_sequence_dp_runtime_parity.py -v --verification-level=full`
    -> 11 passed.
  - `uv run pytest tests/test_stack_bytecode.py tests/test_sequence_dp.py -v --verification-level=standard`
    -> 77 passed.
  - `uv run ruff check src/genfxn/stack_bytecode/eval.py
    src/genfxn/sequence_dp/eval.py tests/test_stack_bytecode_runtime_parity.py
    tests/test_sequence_dp_runtime_parity.py tests/test_stack_bytecode.py
    tests/test_sequence_dp.py`
    -> passed.
  - `uv run ty check`
    -> passed.

### 19) Review Comment Sweep (Current Batch)
Current execution batch (2026-02-10):
- [x] Fix xdist import-mismatch collisions in
      `tests/test_verification_levels.py` by using unique pytester probe module
      names that cannot shadow repo test modules.
- [x] Add CLI split guard in `src/genfxn/cli.py` rejecting identical
      `--train`/`--test` destination paths and add regression tests in
      `tests/test_cli.py`.
- [x] Fix `graph_queries` Java renderer overflow in shortest-path accumulation
      (`src/genfxn/langs/java/graph_queries.py`) and add runtime parity
      regression coverage.
- [x] Align Python renderers to evaluator i64 semantics for:
      `src/genfxn/stack_bytecode/render.py` and
      `src/genfxn/sequence_dp/render.py`, with regression tests in
      `tests/test_stack_bytecode.py` and `tests/test_sequence_dp.py`.
- [x] Treat structurally equivalent nested NaN outputs as equal in
      `dedupe_queries` conflict checks (`src/genfxn/core/models.py`) and add
      focused tests in `tests/test_core_models.py`.
- [x] Make `render_tests(...)` emit valid Python for non-finite values in
      `src/genfxn/core/codegen.py` and add regressions in
      `tests/test_core_dsl.py`.
- [x] Improve runtime parity reliability:
      add subprocess timeout wrapper(s) in `tests/helpers.py`, apply them in
      all `tests/test_*_runtime_parity.py` suites, and fail-closed on missing
      Java/Rust toolchains.
- [x] Update `.github/workflows/ci.yml` to explicitly install Java and Rust
      before full verification.

Exit criterion:
- All eight reported review comments are resolved with regression coverage,
  standard/full verification behavior remains deterministic, and CI parity
  gates are fail-closed for missing toolchains.

Progress update (2026-02-10, review comment sweep complete):
- Fixed xdist import-mismatch regression in `tests/test_verification_levels.py`
  by writing family-marker probe files under a dedicated subdirectory rather
  than shadowing repository module basenames.
- Added CLI split destination guard in `src/genfxn/cli.py`:
  `--train` and `--test` now reject the same resolved path, with coverage in
  `tests/test_cli.py::test_split_rejects_same_train_and_test_path`.
- Fixed graph_queries Java overflow path in
  `src/genfxn/langs/java/graph_queries.py` by moving shortest-path cost
  bookkeeping/return to `long` while keeping node indices as `int`.
- Added large-weight parity regression in
  `tests/test_graph_queries_runtime_parity.py` that now asserts
  `4_000_000_000` round-trips across Python/Java/Rust.
- Aligned Python renderers with evaluator i64 semantics:
  - `src/genfxn/stack_bytecode/render.py` now emits explicit `wrap_i64`
    helpers and edge-safe div/mod handling (`MIN / -1`, `MIN % -1`).
  - `src/genfxn/sequence_dp/render.py` now emits i64 wrap helpers for DP
    score/len/gap arithmetic and wrapped predicate subtraction paths.
  - Added regressions in `tests/test_stack_bytecode.py` and
    `tests/test_sequence_dp.py`.
- Hardened dedupe output equality for nested NaN structures in
  `src/genfxn/core/models.py` and added focused coverage in
  `tests/test_core_models.py`.
- Updated `render_tests(...)` in `src/genfxn/core/codegen.py` to emit valid
  Python literals for non-finite floats (`float("nan")`, `float("inf")`,
  `float("-inf")`) recursively through container outputs, with regressions in
  `tests/test_core_dsl.py`.
- Added shared runtime subprocess helper in `tests/helpers.py`:
  `run_checked_subprocess(...)` with explicit timeout, and switched all runtime
  parity suites to use it.
- Changed `require_java_runtime()` / `require_rust_runtime()` to fail-closed
  via `pytest.fail(...)` instead of skip in runtime parity contexts.
- Updated `.github/workflows/ci.yml` `test-full` job to explicitly install:
  - Java via `actions/setup-java@v4` (`temurin`, `21`)
  - Rust via `dtolnay/rust-toolchain@stable`

Validation evidence:
- `uv run ruff check <touched Python files>` -> passed.
- `uv run ty check <touched files>` -> passed.
- `uv run pytest tests/test_cli.py::TestGenerate::test_generate_sequence_dp
  tests/test_cli.py::TestGenerate::test_generate_stack_bytecode_when_available
  -v --verification-level=standard` -> 2 passed.
- `uv run pytest tests/test_verification_levels.py tests/test_cli.py
  tests/test_core_models.py tests/test_core_dsl.py tests/test_stack_bytecode.py
  tests/test_sequence_dp.py -v --verification-level=standard`
  -> 282 passed.
- `uv run pytest tests/test_*_runtime_parity.py -v --verification-level=full
  -k "java_runtime_parity or rust_runtime_parity or
  large_weight_cost_accumulation"` -> 23 passed.
- `uv run pytest tests/ -q --verification-level=standard`
  -> 1831 passed, 101 skipped.

### 20) FSM `machine_type` Deprecation Signaling (Current Batch)
Current execution batch (2026-02-10):
- [x] Add explicit compatibility/deprecation comments around FSM
      `machine_type` in model, evaluator, and renderer code to signal that the
      axis is intentionally non-semantic.
- [x] Keep behavior unchanged (no schema removal, no task-id-affecting edits).
- [x] Run targeted lint/type/tests for touched FSM files.

Exit criterion:
- Codebase clearly communicates `machine_type` is retained for compatibility
  and intentionally does not affect runtime semantics.

Progress update (2026-02-10, FSM machine_type deprecation signaling complete):
- Added explicit deprecation/compatibility signaling in:
  - `src/genfxn/fsm/models.py`
    - `MachineType` enum docstring
    - `FsmSpec.machine_type` field description
    - `FsmAxes.machine_types` field description
  - `src/genfxn/fsm/eval.py`
    - evaluator comment stating `machine_type` is intentionally non-semantic
  - `src/genfxn/fsm/render.py`
    - renderer comment stating `machine_type` is intentionally non-semantic
- No behavior or schema contract changes were introduced.
- Validation evidence:
  - `uv run ruff check src/genfxn/fsm/models.py src/genfxn/fsm/eval.py src/genfxn/fsm/render.py`
    -> passed.
  - `uv run ty check src/genfxn/fsm/models.py src/genfxn/fsm/eval.py src/genfxn/fsm/render.py`
    -> passed.
  - `uv run pytest tests/test_fsm.py -v --verification-level=standard`
    -> 26 passed.

### 21) Follow-up Review Fixes (Current Batch)
Current execution batch (2026-02-10):
- [x] Fix NaN assertion semantics in `src/genfxn/core/codegen.py` `render_tests`
      and add execution-semantic regressions in `tests/test_core_dsl.py`.
- [x] Add `frozenset` NaN-safe canonicalization/equality handling in
      `src/genfxn/core/models.py` and regressions in `tests/test_core_models.py`.
- [x] Fix split warning first-sample capture sentinel in `src/genfxn/cli.py`
      and add a warning-accuracy regression in `tests/test_cli.py`.
- [x] Align bool range-bound rejection across remaining int-range families:
      `stateful`, `simple_algorithms`, `bitops`, `fsm`, `sequence_dp`,
      `stack_bytecode` (plus focused tests).
- [x] Run focused `ruff`/`ty` and targeted pytest slices, then run default
      standard suite spot-check.

Exit criterion:
- All four follow-up findings are fixed with deterministic regressions, and
  no behavior regressions appear in standard verification checks.

Progress update (2026-02-10, follow-up review fixes complete):
- Fixed NaN assertion semantics in `render_tests(...)`:
  - `src/genfxn/core/codegen.py` now emits NaN-safe assertions for NaN-bearing
    outputs by delegating to `_query_outputs_equal(...)`, while preserving
    direct `==` assertions for non-NaN outputs.
  - Added execution-semantic coverage in `tests/test_core_dsl.py` that executes
    generated assertions for direct and nested NaN outputs (including
    `frozenset`).
- Added `frozenset` NaN canonicalization/equality handling in
  `src/genfxn/core/models.py`:
  - `_freeze_query_value(...)` now has explicit `frozenset` handling.
  - `_query_outputs_equal(...)` now compares `frozenset` values structurally.
  - Added focused regressions in `tests/test_core_models.py`.
- Fixed split warning first-sample sentinel in `src/genfxn/cli.py`:
  - replaced `None` sentinel with module-level `_UNSET_SAMPLE`, so true first
    value `None` is preserved in warning output.
  - Added regression in `tests/test_cli.py`:
    `test_split_warning_preserves_first_none_axis_value`.
- Standardized bool bound rejection for int-range axes in:
  - `src/genfxn/stateful/models.py`
  - `src/genfxn/simple_algorithms/models.py`
  - `src/genfxn/bitops/models.py`
  - `src/genfxn/fsm/models.py`
  - `src/genfxn/sequence_dp/models.py`
  - `src/genfxn/stack_bytecode/models.py`
  Each now rejects bool bounds in `mode="before"` validators with clear field
  error text. Added focused tests in corresponding family test modules.
- Validation evidence:
  - `uv run pytest tests/test_core_dsl.py tests/test_core_models.py
    tests/test_cli.py -v --verification-level=standard -k
    "render_tests or dedupe_queries_frozenset_nan or
    warning_preserves_first_none_axis_value"` -> 9 passed.
  - `uv run pytest tests/test_stateful.py tests/test_simple_algorithms.py
    tests/test_bitops.py tests/test_fsm.py tests/test_sequence_dp.py
    tests/test_stack_bytecode.py -v --verification-level=standard -k
    "bool_in_int_range_bounds or axes_reject_bool_in_int_range_bounds or
    rejects_bool_in_int_range_bounds"` -> 36 passed.
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - `uv run pytest tests/ -q --verification-level=standard`
    -> 1872 passed, 101 skipped.

### 22) Holdout Contains + Remaining Bool-Range Hardening (Current Batch)
Current execution batch (2026-02-10):
- [x] Make `contains` holdout matching type-sensitive so bool does not match
      numeric int/float equivalents.
- [x] Add bool range-bound rejection in `graph_queries` and `temporal_logic`
      axes models for int-range fields.
- [x] Extend non-finite holdout detection to set/frozenset containers in
      split matcher (and CLI parser helper parity where relevant).
- [x] Add focused regressions in `tests/test_splits.py`, `tests/test_cli.py`,
      `tests/test_graph_queries.py`, and `tests/test_temporal_logic.py`.
- [x] Run targeted pytest slices plus `ruff`/`ty`; finish with standard-suite
      spot-check.

Exit criterion:
- Contains holdouts respect strict type semantics, remaining family bool-bound
  coercions are closed, and non-finite holdout guards fail-closed through
  nested set/frozenset containers with regression coverage.

Progress update (2026-02-10, holdout contains + bool-range hardening complete):
- Updated `src/genfxn/splits.py`:
  - `contains` matching now uses strict type-sensitive element comparison
    (`_contains_type_sensitive(...)`) rather than raw `in`.
  - non-finite detection now traverses set/frozenset and dict keys+values.
- Updated `src/genfxn/cli.py` non-finite helper to keep parser-side behavior
  aligned for nested container traversal (including set/frozenset and dict
  keys).
- Added bool int-range bound rejection in:
  - `src/genfxn/graph_queries/models.py`
  - `src/genfxn/temporal_logic/models.py`
  using `mode="before"` validators with consistent error text.
- Added focused regressions:
  - `tests/test_splits.py`
    - `test_contains_holdout_type_matrix`
    - `test_exact_holdout_rejects_non_finite_values_in_set_like_containers`
    - `test_contains_holdout_rejects_non_finite_values_in_set_like_containers`
  - `tests/test_cli.py`
    - `test_split_contains_matcher_type_matrix`
  - `tests/test_graph_queries.py`
    - `test_axes_reject_bool_in_int_range_bounds`
  - `tests/test_temporal_logic.py`
    - `test_axes_reject_bool_in_int_range_bounds`
- Validation evidence:
  - `uv run pytest tests/test_splits.py tests/test_cli.py -v
    --verification-level=standard -k
    "contains_holdout_type_matrix or contains_matcher_type_matrix or
    non_finite_values_in_set_like_containers"` -> 14 passed.
  - `uv run pytest tests/test_graph_queries.py tests/test_temporal_logic.py -v
    --verification-level=standard -k "reject_bool_in_int_range_bounds"`
    -> 7 passed.
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - `uv run pytest tests/ -q --verification-level=standard`
    -> 1893 passed, 101 skipped.

### 23) Nested Holdout Typing + CLI JSON-ish Parse + graph_queries bool hardening (Current Batch)
Current execution batch (2026-02-10):
- [x] Make holdout `EXACT` matching deeply type-sensitive (nested lists/tuples/
      dicts/set/frozenset) so bool/int/float conflation is eliminated at all
      levels.
- [x] Make holdout `CONTAINS` matching deeply type-sensitive for container
      elements (including nested list payloads).
- [x] Tighten CLI exact/contains holdout parsing to reject malformed JSON-like
      tokens (for example broken `[ ...`, `{ ...`, or quoted literals) instead
      of silently treating them as raw strings.
- [x] Harden `graph_queries` direct-use contracts: reject bool on int-like
      model fields (`GraphEdge` and `GraphQueriesSpec.n_nodes`) and evaluator
      inputs (`src`/`dst`).
- [x] Add focused regressions in `tests/test_splits.py`, `tests/test_cli.py`,
      and `tests/test_graph_queries.py`.
- [x] Run targeted pytest slices plus `ruff`/`ty`, then standard-suite
      spot-check.

Exit criterion:
- Nested holdout comparisons are strictly type-safe, malformed JSON-ish CLI
  holdout tokens fail with explicit errors, and graph_queries direct-use bool
  coercions are closed with deterministic regression coverage.

Progress update (2026-02-10, nested holdout + CLI parse + graph_queries bool hardening complete):
- Updated `src/genfxn/splits.py`:
  - `EXACT` and `CONTAINS` matching now use deep type-sensitive structural
    comparison via canonical freeze keys, eliminating nested bool/int/float
    conflation (`False != 0`, `1 != 1.0` at any depth).
- Updated `src/genfxn/cli.py`:
  - exact/contains parser now rejects malformed JSON-like holdout tokens
    (prefixes `[`, `{`, or `"` that fail JSON parse) with explicit
    `BadParameter` instead of silent raw-string fallback.
- Hardened graph_queries direct-use contracts:
  - `src/genfxn/graph_queries/models.py` now rejects bool on
    `GraphEdge.{u,v,w}` and `GraphQueriesSpec.n_nodes`.
  - `src/genfxn/graph_queries/eval.py` now rejects non-int `src`/`dst`
    (including bool) before range checks.
- Added focused regressions:
  - `tests/test_splits.py`:
    - `test_exact_holdout_nested_type_sensitive_match`
    - `test_contains_holdout_nested_type_sensitive_match`
  - `tests/test_cli.py`:
    - `test_split_exact_contains_reject_malformed_json_like_holdout_values`
    - `test_split_exact_matcher_nested_type_sensitive`
    - `test_split_contains_matcher_nested_type_sensitive`
  - `tests/test_graph_queries.py`:
    - `test_graph_edge_rejects_bool_int_fields`
    - `test_graph_spec_rejects_bool_n_nodes`
    - `test_eval_rejects_bool_src_dst_inputs`
- Validation evidence:
  - `uv run pytest tests/test_splits.py tests/test_cli.py
    tests/test_graph_queries.py -v --verification-level=standard -k
    "nested_type_sensitive or malformed_json_like_holdout_values or
    graph_edge_rejects_bool_int_fields or graph_spec_rejects_bool_n_nodes or
    eval_rejects_bool_src_dst_inputs or contains_holdout_type_matrix or
    contains_matcher_type_matrix"` -> 23 passed.
  - direct repro spot-check script confirms previous drifts now closed.
  - `uv run ruff check` on touched files -> passed.
  - `uv run ty check` on touched files -> passed.
  - `uv run pytest tests/ -q --verification-level=standard`
    -> 1906 passed, 101 skipped.

### 24) CLI Malformed JSON-Scalar Holdout Rejection (Current Batch)
Current execution batch (2026-02-10):
- [x] Reject malformed JSON-like scalar tokens for exact/contains holdouts
      (`tru`, `nul`, `01`, `+1`) instead of silent raw-string fallback.
- [x] Add focused CLI split regressions for exact/contains scalar-typo cases.
- [x] Run targeted `pytest` + `ruff` + `ty` and standard-suite spot-check.

Exit criterion:
- Scalar typo tokens that look like malformed JSON literals are fail-fast with
  explicit CLI errors; non-JSON plain strings continue to work.

Progress update (2026-02-10, malformed JSON-scalar holdout rejection complete):
- Updated `src/genfxn/cli.py`:
  - added `_looks_like_malformed_json_scalar(...)` and numeric-like token
    detector.
  - `_parse_non_range_holdout_value(...)` now raises `BadParameter` for
    malformed scalar-like tokens (for example `tru`, `nul`, `01`, `+1`),
    instead of treating them as raw strings.
- Added regressions in `tests/test_cli.py`:
  - `test_split_exact_contains_reject_malformed_json_scalar_holdout_values`
    (exact + contains matrix).
- Validation evidence:
  - `uv run pytest tests/test_cli.py -v --verification-level=standard -k
    "malformed_json_like_holdout_values or
    malformed_json_scalar_holdout_values"` -> 14 passed.
  - `uv run ruff check src/genfxn/cli.py tests/test_cli.py` -> passed.
  - `uv run ty check src/genfxn/cli.py tests/test_cli.py` -> passed.
  - `uv run pytest tests/ -q --verification-level=standard`
    -> 1914 passed, 101 skipped.
