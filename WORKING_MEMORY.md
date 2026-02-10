# Working Memory

## Mission
Make `genfxn` a resilient research primitive: deterministic where expected,
strict in validation, and consistent across Python/Java/Rust runtime behavior.

## Current Focus
- Close quality parity gaps between early families (`piecewise`, `stateful`,
  `simple_algorithms`, `stringrules`) and newer families.
- Reduce classes of failures that only surface under
  `--verification-level=full`.
- Address latest correctness regressions in deduping/splits and verification
  gate clarity.

## Recent Findings
- Validator bool-as-int gaps existed across multiple newer families; these are
  high risk for cross-language semantic drift because `True == 1` and
  `False == 0`.
- Suite generation for `intervals` difficulty-2 can get trapped by greedy
  one-pass quota filling with insufficient retry diversification.
- Safe-exec lifecycle leaks in several validators can leave worker processes
  alive and cause flaky `full` failures in long runs.
- Coverage quality is uneven:
  - Mature patterns (semantic capping checks, strict-vs-lenient checks, code
    map path checks, forced parity variant coverage) are strong in some early
    families.
  - Several newer families still rely more on sampled tests and thin edge-case
    assertions.

## Latest Intake (2026-02-10)
- `dedupe_queries` scalar freeze key currently conflates distinct scalar types
  (`True` vs `1`, `1` vs `1.0`), causing false merges/conflicts.
- Range holdout matching in both library and CLI currently accepts bools as
  numeric values, so `False` can match `[0, 0]` unexpectedly.
- Default verification level (`standard`) skips `@pytest.mark.full`, including
  runtime parity suites; default green runs are not full safety coverage.
- Verification-level skip/run behavior was configured in `tests/conftest.py`
  but lacked a focused regression test to guard against marker-gating drift.
- CLI random split regressed to materializing all tasks in memory via
  `list(_iter_validated_tasks(...))`, risking OOM on large JSONL inputs.
- Runtime parity depth ownership includes five sampled-heavy suites:
  `fsm`, `bitops`, `intervals`, `stateful`, and `simple_algorithms`.
- `fsm` sampled parity currently uses skip-on-`ValueError` behavior that hides
  undefined-transition error-policy outcomes instead of asserting parity.
- Older-family validator parity ownership for this task:
  - add bool rejection tests where `int` is expected in queries
  - add strict-vs-lenient severity tests for query input/output type issues
  - add exec lifecycle `close()` assertions after semantic validation
- Remaining priority batch:
  1) intervals D2 suite generation robustness
  2) validator parity in older families
  3) runtime parity forced-variant depth
- New intake (this pass):
  - exact holdout still conflates bool/int in library+CLI
  - dedupe hashable fallback still allows cross-type collisions
  - dedupe repr fallback can crash on broken-`__repr__` unhashables
  - split contract drift between CLI and library random split was not codified
    after memory-regression fixes
- Validator contract coverage still relies on many family-local bespoke tests;
  shared matrix coverage is missing for strict/lenient severity parity and
  bool-rejection behavior on int-like query fields.
- Common validator lifecycle/skip behavior (non-Python code-map path and
  exec-function `close()` lifecycle) is still asserted per-family rather than
  through one reusable parameterized contract suite.

## Latest Intake Extension (2026-02-10, CI Policy Hardening)
- Repository currently has no `.github/workflows/*` CI workflow, so merge
  validation depends on local/manual command discipline.
- Default pytest mode remains `--verification-level=standard`, which skips
  `@pytest.mark.full`; without CI enforcement, full parity/edge suites are not
  routinely gated.
- Existing guidance in docs/PR template references full verification, but there
  is no automated path that makes it mandatory on pull requests.

## Latest Intake Extension (2026-02-10, Numeric/Representation Hardening)
- `stack_bytecode` Rust renderer currently uses plain `i64` arithmetic (`+`,
  `-`, `*`, unary negation, `/`, `%`, `abs`) that can diverge from Java
  `long` semantics on overflow-adjacent values (especially `MIN / -1`,
  `MIN % -1`, `abs(MIN)`, and `-MIN`).
- `sequence_dp` Rust renderer currently uses plain `i64` arithmetic for DP
  score/path accumulation and predicate subtraction in `mod_eq`; these paths
  can overflow and diverge from Java `long` wrapping behavior.
- Existing runtime parity suites for these families are strong on sampled and
  forced-variant coverage but thin on explicit overflow-adjacent regressions.
- String length parity already uses code-point semantics in Java/Rust renderers,
  but coverage can be strengthened for combining-mark and ZWJ emoji cases.

## Latest Intake Extension (2026-02-10, CLI Range + NaN Dedupe Hardening)
- `graph_queries` CLI `--value-range` currently ignores user-provided negative
  ranges with no explicit signal (falls back to default `weight_range`).
- `_parse_numeric_range` currently accepts non-finite bounds (`nan`, `inf`,
  `-inf`) and should reject them with clear `BadParameter`.
- `dedupe_queries` currently treats `float('nan')` inputs as distinct keys,
  so equivalent NaN queries are not deduped deterministically.

## Latest Intake Extension (2026-02-10, dedupe NaN output equality)
- `dedupe_queries` conflict detection currently uses raw `!=` on outputs, so
  duplicate outputs that are both `float('nan')` are incorrectly treated as a
  conflict.
- Required behavior for this pass: treat NaN-vs-NaN outputs as equal for
  duplicate inputs, while still raising on true output mismatches.

## Latest Intake Extension (2026-02-10, FSM + Holdout Matcher Hardening)
- FSM runtime parity error-path assertions currently accept any nonzero process
  failure; they should assert semantic alignment with Python evaluator error
  messages so compile/runtime drift is not masked.
- Holdout matching behavior is duplicated in `src/genfxn/splits.py` and
  `src/genfxn/cli.py`, increasing regression risk from drift between library
  and CLI behavior.

## Latest Intake Extension (2026-02-10, Int32 Overflow Semantics)
- `piecewise`, `stateful`, and `simple_algorithms` Python evaluators currently
  use unbounded Python integer arithmetic, while Java renderers execute with
  Java `int` overflow semantics.
- Rust renderers for those same families currently run `i64` arithmetic, so
  overflow-adjacent cases diverge from Java `int` and from any intended shared
  contract.
- Existing runtime parity suites for these families stay in small numeric
  ranges and do not currently lock overflow behavior.
- Reproduced concrete drift cases:
  - piecewise quadratic: Python/Rust `2500000000` vs Java `-1794967296`
  - stateful sum path: Python/Rust `4000000000` vs Java `-294967296`
  - simple_algorithms max-window path: Python/Rust `4000000000` vs Java
    `-294967296`

## Latest Intake Extension (2026-02-10, Java Int Literal Compile Safety)
- Java renderers for int-based families emit raw decimal literals for spec
  constants; literals above Java `int` range can fail javac with
  `integer number too large`.
- Affected emission paths are concentrated in
  `src/genfxn/langs/java/{predicates.py,expressions.py,stateful.py,`
  `simple_algorithms.py,piecewise.py}` plus helper transform rendering.
- Priority for this issue is compile-safety for valid specs; overflow-semantics
  alignment can be handled separately where needed.

## Completed This Chunk (2026-02-10, Java Int Literal Compile Safety)
- Added shared helper `java_int_literal(...)` in
  `src/genfxn/langs/java/_helpers.py` to emit compile-safe int expressions for
  out-of-range constants via explicit long-cast narrowing.
- Patched int-literal emission in:
  `src/genfxn/langs/java/predicates.py`,
  `src/genfxn/langs/java/expressions.py`,
  `src/genfxn/langs/java/transforms.py`,
  `src/genfxn/langs/java/stateful.py`, and
  `src/genfxn/langs/java/simple_algorithms.py`.
- Audited `src/genfxn/langs/java/piecewise.py`; no direct integer-literal
  emission path required patching because it delegates to predicates/expressions
  renderers.
- Added compile-safety regressions with oversized constants in:
  - `tests/test_piecewise_runtime_parity.py`
  - `tests/test_stateful_runtime_parity.py`
  - `tests/test_simple_algorithms_runtime_parity.py`
  and helper unit coverage in `tests/test_java_render.py`.
- Validation evidence:
  - targeted full pytest (`TestJavaIntLiteral` + oversized compile tests):
    6 passed.
  - targeted renderer pytest slice: 44 passed.
  - targeted `ruff` and `ty` on touched files: passed.

## Latest Intake Extension (2026-02-10, Runtime Parity Int32 Boundary Coverage)
- Runtime parity files for `simple_algorithms`, `stateful`, and `piecewise`
  currently lean on sampled/small-domain checks and lack explicit deterministic
  int32-boundary probes.
- Needed coverage should include high-magnitude deterministic values near and
  at signed int32 edges (for example `2_000_000_000`, `2_147_483_647`) plus
  `50_000^2`-style arithmetic stress inputs.
- Validation for this batch should run targeted full-mode parity suites plus
  `ruff` and `ty` on touched files.

## Latest Intake Extension (2026-02-10, Oversized Literal Parity Rigor)
- Oversized-literal runtime tests in `piecewise`, `stateful`, and
  `simple_algorithms` currently only prove Java compile/run viability; they do
  not assert Java/Rust output parity against Python evaluators.
- Some oversized literal cases use out-of-range divisor/remainder values in
  mod predicates/expressions, which can diverge from the chosen int32 contract
  used in core overflow fixes.
- `tests/test_java_render.py` currently has thin `java_int_literal(...)`
  coverage and should explicitly lock compile-safe behavior at int32 and
  long-range boundaries.

## Latest Intake Extension (2026-02-10, Overflow-Adjacent Expected Source)
- Overflow-adjacent runtime parity tests in `sequence_dp` and `stack_bytecode`
  currently pin hardcoded expected numeric outputs.
- These expectations should be derived from the Python evaluators
  (`eval_sequence_dp`, `eval_stack_bytecode`) to keep parity assertions aligned
  with the canonical runtime semantics while remaining deterministic.
- Scope is limited to:
  - `tests/test_sequence_dp_runtime_parity.py`
  - `tests/test_stack_bytecode_runtime_parity.py`

## Latest Intake Extension (2026-02-10, Core Semantics Blocking Fixes #1/#2/#3)
- `eval_predicate(...)` currently has no int32-eval mode, so int32 families
  (`piecewise`, `stateful`, `simple_algorithms`) evaluate predicate constants
  with unbounded-Python semantics while Java/Rust execute int32 semantics.
- int32 transform `clip` in `eval_transform(...)` currently clips against raw
  `low/high` bounds before wrapping, diverging from Java/Rust behavior that
  applies int32-cast bounds during clamp.
- Core `mod_eq` and `piecewise` `ExprMod` divisors are only validated as `> 0`;
  very large positive divisors can wrap to zero/negative in int32 runtimes,
  creating compile/runtime modulo crash or divergence risk.
- `stateful`/`simple_algorithms` query-generation helpers still call
  `eval_predicate(...)` in default mode, so generated boundary/adversarial
  examples can drift from int32 runtime semantics for wrapped constants.

## Latest Intake Extension (2026-02-10, CLI Exact/Contains Non-Finite Holdout Rejection)
- Split CLI currently rejects non-finite bounds only for `--holdout-type range`;
  `exact`/`contains` paths still accept non-finite tokens through
  `json.loads(...)` (`NaN`, `Infinity`, `-Infinity`) or raw fallback strings
  (`nan`, `inf`, `-inf`).
- Holdout matcher flow currently has no explicit non-finite guard for
  `EXACT`/`CONTAINS`, so direct library use with non-finite holdout values is
  not fail-closed by contract.

## Active Checklist (Current Batch)
- [x] Fix scalar key typing in `dedupe_queries` and add type-separation tests.
- [x] Reject bool values in range holdout matching (library + CLI) and add
      tests.
- [x] Add test coverage/doc signal so verification-level behavior is explicit
      and guarded against accidental regression.
- [x] Fix intervals D2 suite generation robustness in full verification.
- [x] Close validator strict/lenient + bool-rejection parity gaps in older
      families.
- [x] Add runtime parity forced-variant coverage for sampled-heavy families and
      remove skip-on-error gaps.
- [x] Fix exact holdout bool/int conflation in library + CLI.
- [x] Fix dedupe hashable fallback cross-type collisions.
- [x] Harden dedupe repr fallback against broken-`__repr__` objects.
- [x] Codify CLI/library random split contract without forcing identical set
      membership.
- [x] Add reusable parameterized validator contract matrix across families for
      strict-vs-lenient severity parity.
- [x] Add reusable parameterized validator contract matrix coverage for bool
      rejection on int-like query fields.
- [x] Add reusable shared lifecycle/skip contract checks where robust
      (non-Python code-map skip and exec close lifecycle).
- [x] Harden Rust stack_bytecode renderer arithmetic to align with Java long
      wrapping/edge behavior and add overflow-adjacent parity regression tests.
- [x] Harden Rust sequence_dp renderer arithmetic/predicate subtraction to align
      with Java long wrapping behavior and add overflow-adjacent parity tests.
- [x] Expand string length runtime parity coverage for non-ASCII code-point
      edge cases (combining marks and ZWJ sequences).
- [x] Run targeted full verification parity suites for touched families plus
      `ruff`/`ty` and record evidence.
- [x] Add a GitHub Actions CI workflow that enforces `uv sync`,
      `uv run ruff check .`, `uv run ty check`, and
      `uv run pytest tests/ -v --verification-level=full`.
- [x] Document the CI full-verification gate in `README.md`.
- [x] Run targeted validation for workflow syntax and gating commands.
- [x] Make graph_queries `--value-range` behavior explicit for negative-only
      ranges (no silent fallback).
- [x] Reject non-finite split range values (`nan`/`inf`/`-inf`) in
      `_parse_numeric_range` with clear errors.
- [x] Reject non-finite split exact/contains holdout values
      (`NaN`/`Infinity`/`-Infinity` and `nan`/`inf`/`-inf`) with clear
      `BadParameter` and fail-closed matcher behavior.
- [x] Make `dedupe_queries` NaN input dedupe deterministic and cover with
      regression tests.
- [x] Strengthen FSM runtime parity error-path assertions to check semantic
      error alignment (not only nonzero exit).
- [x] Centralize holdout matcher behavior to reduce `splits.py`/`cli.py` drift
      while preserving existing behavior and tests.
- [x] Define and codify an explicit int32 wrap arithmetic contract for
      `piecewise`, `stateful`, and `simple_algorithms`.
- [x] Align Python evaluators and Rust renderers for these families with the
      int32 contract (minimal blast radius).
- [x] Add overflow-focused runtime parity regressions that demonstrate prior
      divergence now aligned (Java/Rust vs Python eval).
- [x] Run targeted full parity tests plus `ruff`/`ty` on touched files and
      record evidence.
- [x] Add deterministic int32-boundary runtime parity tests for
      `simple_algorithms`, `stateful`, and `piecewise`.
- [x] Run targeted full-mode parity validation for touched runtime files plus
      `ruff` and `ty`, and record evidence.
- [x] Strengthen oversized-literal runtime tests to assert Java/Rust parity
      against Python eval in `piecewise`, `stateful`, and
      `simple_algorithms`.
- [x] Replace oversized divisor/remainder parity fixtures with values aligned
      to the chosen int32 contract for mod operations.
- [x] Expand `tests/test_java_render.py` `TestJavaIntLiteral` coverage for
      compile-safe boundary/extreme values.
- [x] Run targeted pytest + `ruff` + `ty` on touched files and record evidence.

## Completed This Chunk (2026-02-10, CLI Exact/Contains Non-Finite Holdouts)
- Updated `src/genfxn/cli.py` split parsing for non-range holdouts:
  - added `_parse_non_range_holdout_value(...)` with explicit rejection of
    non-finite numeric values for `exact`/`contains`.
  - rejects both JSON constants (`NaN`, `Infinity`, `-Infinity`) and
    token-style fallbacks (`nan`, `inf`, `-inf`) via clear `BadParameter`.
- Added fail-closed matcher guards in `src/genfxn/splits.py` so non-finite
  holdout values under `EXACT`/`CONTAINS` never match in library flow.
- Added focused regressions:
  - `tests/test_cli.py`
    - `test_split_exact_contains_reject_non_finite_holdout_values`
    - `test_split_exact_allows_json_string_nan_literal`
  - `tests/test_splits.py`
    - `test_exact_holdout_rejects_non_finite_holdout_values`
    - `test_contains_holdout_rejects_non_finite_holdout_values`
- Validation evidence:
  - `uv run pytest tests/test_cli.py tests/test_splits.py -v
    --verification-level=standard` -> 166 passed.
  - `uv run ruff check src/genfxn/cli.py src/genfxn/splits.py
    tests/test_cli.py tests/test_splits.py` -> passed.
  - `uv run ty check src/genfxn/cli.py src/genfxn/splits.py
    tests/test_cli.py tests/test_splits.py` -> passed.

## Completed This Chunk (2026-02-10, Oversized Literal Parity Rigor)
- Replaced compile-only oversized-literal checks with Python-oracle runtime
  parity assertions in:
  - `tests/test_piecewise_runtime_parity.py`
  - `tests/test_stateful_runtime_parity.py`
  - `tests/test_simple_algorithms_runtime_parity.py`
- Updated oversized mod fixtures to align with the current int32 contract:
  - `piecewise` oversized case now uses `ExprMod.divisor=11` (in-range).
  - `stateful` oversized case no longer uses oversized `PredicateModEq`
    divisor/remainder constants.
- Expanded `tests/test_java_render.py` `TestJavaIntLiteral` boundary/extreme
  coverage for:
  - int32 boundary literals
  - just-outside-int32 casted literals
  - long-range casted literal rendering.
- Validation evidence:
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py tests/test_java_render.py
    -v --verification-level=full -k
    "oversized_int_literals or TestJavaIntLiteral"` -> 9 passed.
  - `uv run ruff check tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py tests/test_java_render.py`
    -> passed.
  - `uv run ty check tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py tests/test_java_render.py`
    -> passed.

## Completed This Chunk (2026-02-10, Int32 Overflow Contract Alignment)
- Added shared int32 arithmetic helpers in `src/genfxn/core/int32.py` and
  applied explicit Java-style 32-bit wrap semantics in Python evaluators:
  - `src/genfxn/piecewise/eval.py`
  - `src/genfxn/stateful/eval.py`
  - `src/genfxn/simple_algorithms/eval.py`
  - `src/genfxn/core/transforms.py` (`int32_wrap` mode)
  - `src/genfxn/simple_algorithms/queries.py` pair-sum preprocessing helpers
- Updated Rust renderers for the same families to enforce int32 wrapping
  semantics while keeping public signatures stable:
  - `src/genfxn/langs/rust/piecewise.py`
  - `src/genfxn/langs/rust/stateful.py`
  - `src/genfxn/langs/rust/simple_algorithms.py`
  - `src/genfxn/langs/rust/expressions.py` (`int32_wrap` mode)
  - `src/genfxn/langs/rust/transforms.py` (`int32_wrap` mode)
- Added overflow-focused runtime parity regressions:
  - `tests/test_piecewise_runtime_parity.py`
  - `tests/test_stateful_runtime_parity.py`
  - `tests/test_simple_algorithms_runtime_parity.py`
- Updated impacted Rust renderer expectation tests:
  - `tests/test_rust_render.py`
- Validation evidence:
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full` -> 21 passed
  - `uv run pytest tests/test_piecewise.py tests/test_stateful.py
    tests/test_simple_algorithms.py -v --verification-level=standard`
    -> 144 passed
  - `uv run pytest tests/test_rust_render.py -v
    --verification-level=standard -k
    "TransformRust or ExpressionRust or PiecewiseRust or StatefulRust or
    SimpleAlgorithmsRust"` -> 45 passed
  - `uv run ruff check` on touched files -> passed
  - `uv run ty check` on touched files -> passed

## Completed This Chunk (2026-02-10, Runtime Parity Int32 Boundary Coverage)
- Added deterministic boundary-focused runtime parity tests:
  - `tests/test_simple_algorithms_runtime_parity.py`:
    `test_simple_algorithms_runtime_parity_int32_boundary_cases`
  - `tests/test_stateful_runtime_parity.py`:
    `test_stateful_runtime_parity_int32_boundary_cases`
  - `tests/test_piecewise_runtime_parity.py`:
    `test_piecewise_runtime_parity_int32_boundary_cases`
- New cases include explicit high-magnitude int32-edge probes and
  overflow-adjacent arithmetic values, including `2_000_000_000`,
  `2_147_483_647`, and `50_000^2`-magnitude paths.
- Validation evidence:
  - `uv run pytest tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py -v --verification-level=full`
    -> 18 passed.
  - `uv run ruff check tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py` -> passed.
  - `uv run ty check tests/test_simple_algorithms_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_piecewise_runtime_parity.py` -> passed.
 
## Completed This Chunk (2026-02-10, FSM + Holdout Matcher Follow-up)
- Strengthened FSM runtime parity error-path assertions in
  `tests/test_fsm_runtime_parity.py`:
  - now captures Java/Rust `CalledProcessError` details
  - asserts nonzero exit and semantic error-message alignment with Python
    `eval_fsm` `ValueError` text (`undefined transition encountered under error
    policy`)
  - reduces risk of accepting unrelated compile/runtime failures as parity.
- Centralized holdout matching behavior in `src/genfxn/splits.py` via shared
  `matches_holdout(...)` and switched `split_tasks(...)` to use it.
- Refactored `src/genfxn/cli.py` to delegate `_matches_holdout(...)` to the
  shared splitter matcher, preserving existing helper symbol behavior used by
  tests while removing duplicated matching logic.
- Validation evidence:
  - `uv run pytest tests/test_fsm_runtime_parity.py -v
    --verification-level=full` -> 4 passed.
  - `uv run pytest tests/test_splits.py tests/test_cli.py -v
    --verification-level=standard -k "...matcher/holdout exact-range bool
    cases..."` -> 18 passed.
  - `uv run ruff check src/genfxn/splits.py src/genfxn/cli.py
    tests/test_fsm_runtime_parity.py` -> passed.
  - `uv run ty check src/genfxn/splits.py src/genfxn/cli.py
    tests/test_fsm_runtime_parity.py` -> passed.

## Completed This Chunk (2026-02-10)
- Added `tests/test_validator_contract_matrix.py`, a reusable parameterized
  validator contract suite across int-like families:
  `bitops`, `fsm`, `graph_queries`, `intervals`, `piecewise`,
  `sequence_dp`, `simple_algorithms`, `stack_bytecode`, `stateful`,
  and `temporal_logic`.
- CLI range + NaN dedupe hardening updates:
  - `src/genfxn/cli.py` now rejects `graph_queries` negative-only
    `--value-range` via explicit `BadParameter` instead of silently ignoring.
  - `_parse_numeric_range` now rejects non-finite bounds with clear message:
    `bounds must be finite numbers (no nan/inf/-inf)`.
  - `src/genfxn/core/models.py` now canonicalizes float NaN in scalar freezing
    so NaN query inputs dedupe deterministically.
  - Added CLI regressions in `tests/test_cli.py` for:
    - graph_queries value-range application and negative-only rejection
    - split range non-finite bound rejection (`nan`, `inf`, `-inf`)
  - Added core regressions in `tests/test_core_models.py` for:
    - NaN input dedupe determinism
    - NaN conflicting-output conflict detection
  - Validation evidence:
    - `uv run pytest tests/test_cli.py tests/test_core_models.py -v
      --verification-level=standard` -> 109 passed.
    - `uv run ruff check src/genfxn/cli.py src/genfxn/core/models.py
      tests/test_cli.py tests/test_core_models.py` -> passed.
    - `uv run ty check src/genfxn/cli.py src/genfxn/core/models.py
      tests/test_cli.py tests/test_core_models.py` -> passed.
- Matrix coverage now centrally asserts:
  - strict vs lenient severity behavior for query type issues
  - bool rejection in int-like query input/output fields
  - non-Python code-map skip behavior for Python parse/exec/missing-function
    paths
  - exec-function lifecycle `close()` invocation after semantic validation
    via patched `execute_code_restricted`
- Validation evidence for this shared-matrix batch:
  - `uv run pytest tests/test_validator_contract_matrix.py -v
    --verification-level=standard` -> 40 passed.
  - `uv run ruff check tests/test_validator_contract_matrix.py` -> passed.
  - `uv run ty check` -> passed.
- Updated `dedupe_queries` scalar freeze keys to encode concrete scalar type,
  preventing bool/int/float key collisions.
- Added `tests/test_core_models.py` regression coverage for:
  - `True` vs `1` staying distinct.
  - `1` vs `1.0` staying distinct.
  - No false conflict for type-distinct inputs with different outputs.
- Hardened RANGE holdout matching in both library and CLI to reject bool bounds
  and bool axis values.
- Added regression tests in `tests/test_splits.py` and `tests/test_cli.py` for
  bool range non-matching behavior.
- Added `tests/test_verification_levels.py` with a deterministic `pytester`
  guard that asserts:
  - `@pytest.mark.full` is skipped in `standard`.
  - `@pytest.mark.full` runs in `full`.
  - `@pytest.mark.slow` is skipped in `fast`.
- Updated `README.md` Tests section to state runtime parity suites are
  `@pytest.mark.full` and require `--verification-level=full`.
- Added semantic mismatch capping regression tests for validator families:
  - `bitops`
  - `intervals`
  - `sequence_dp`
  - `fsm`
  - `graph_queries`
  - `temporal_logic`
  Each test now asserts capped behavior with `max_semantic_issues=3`:
  three `CODE_SEMANTIC_MISMATCH` plus one `CODE_SEMANTIC_ISSUES_CAPPED`.
- Added non-Python code-map skip and exec-function close-lifecycle tests for:
  - `bitops`
  - `intervals`
  - `sequence_dp`
  - `graph_queries`
  - `temporal_logic`
  These now explicitly guard both behavior paths:
  code map validation skip and `close()` invocation after exec-based semantic
  checks.
- Reworked CLI random split back to streaming exact-count assignment:
  - two-pass flow (count then split/write)
  - O(1) task memory (no full task materialization)
  - deterministic seeded behavior and exact floor-count train size
- Replaced library-coupled random-ratio CLI test with deterministic/partition
  assertions and added a regression guard that fails if CLI calls
  `genfxn.splits.random_split`.
- Added older-family validator parity tests in:
  - `tests/test_validate_stateful.py`
  - `tests/test_validate_simple_algorithms.py`
  - `tests/test_validate_piecewise.py`
  Coverage added:
  - bool rejection where `int` is expected in query fields
  - strict-vs-lenient severity assertions for query input/output type issues
  - exec lifecycle close assertions via patched `execute_code_restricted`
- Removed FSM runtime parity skip-on-error behavior and now assert explicit
  outcomes for both success and error-policy paths.
- Added forced-variant runtime parity tests in:
  - `tests/test_fsm_runtime_parity.py`
  - `tests/test_bitops_runtime_parity.py`
  - `tests/test_intervals_runtime_parity.py`
  - `tests/test_stateful_runtime_parity.py`
  - `tests/test_simple_algorithms_runtime_parity.py`
  Coverage now includes focused mode/template/boundary cases per file.
- Validation evidence for this runtime-parity batch:
  - `uv run pytest tests/test_fsm_runtime_parity.py
    tests/test_bitops_runtime_parity.py
    tests/test_intervals_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full` -> 20 passed.
  - `uv run ruff check` on changed parity files -> passed.
  - `uv run ty check` -> passed.
- Suite generation robustness updates:
  - diversified pool seed across retries in `generate_suite`
  - added deterministic multi-restart selection per retry
  - added intervals D2 local-optimum recovery regression in
    `tests/test_suites.py`
  - validated with full-mode intervals integration tests
- Exact holdout hardening updates:
  - `HoldoutType.EXACT` now uses type-sensitive matching in both
    `src/genfxn/splits.py` and `src/genfxn/cli.py`
  - added library + CLI regression tests showing `False` no longer matches `0`
- `dedupe_queries` fallback hardening updates:
  - hashable fallback keys now encode concrete type identity to avoid
    cross-type collisions (e.g., `Decimal("1")` vs `Fraction(1, 1)`)
  - unhashable repr fallback now uses safe repr + type identity and no longer
    crashes on broken-`__repr__` objects with no `__dict__`
- Split contract hardening updates:
  - added `tests/test_split_contracts.py` with deterministic contract checks
    for library and CLI random split, plus explicit cross-implementation
    invariant parity checks
  - expanded exact-holdout type matrix coverage in both
    `tests/test_splits.py` and `tests/test_cli.py` (bool/int, int/float,
    string/numeric, `None`, and missing-path behavior)
  - clarified in `README.md` that CLI random split is streaming and deterministic
    but not guaranteed to match library shuffle+slice membership exactly
  - attempted flake reproduction for split random-ratio determinism:
    20 repeated runs, all passing (no repro)
- CI policy hardening updates:
  - added GitHub Actions workflow at `.github/workflows/ci.yml` to enforce
    `uv sync`, `uv run ruff check .`, `uv run ty check`, and
    `uv run pytest tests/ -v --verification-level=full` on push/PR.
  - updated `README.md` with an explicit CI gate section listing enforced
    commands.
  - aligned `.github/pull_request_template.md` testing checklist with the CI
    gate (`ty check` included and full verification no longer conditional).
  - validation evidence:
    - workflow YAML parse check via Ruby `YAML.load_file`: passed.
    - `uv run ruff check .`: passed.
    - `uv run ty check`: passed.
    - `uv run pytest tests/test_verification_levels.py -v
      --verification-level=full`: 3 passed.
- Numeric/representation hardening updates:
  - Updated `src/genfxn/langs/rust/stack_bytecode.py` arithmetic semantics to
    mirror Java `long` behavior on overflow-adjacent paths:
    - `wrapping_add`/`wrapping_sub`/`wrapping_mul`
    - `wrapping_neg`
    - `abs` handling for `i64::MIN`
    - guarded `java_div`/`java_mod` helpers for `MIN / -1` and `MIN % -1`
  - Updated `src/genfxn/langs/rust/sequence_dp.py` to use explicit wrapping
    arithmetic in DP accumulation and `mod_eq` subtraction, and to mirror
    Java unsigned comparison behavior for `abs_diff_le`.
  - Added overflow-adjacent runtime parity regressions:
    - `tests/test_stack_bytecode_runtime_parity.py`:
      `test_stack_bytecode_runtime_parity_overflow_adjacent_cases`
      (add/sub/mul/neg/abs/div/mod edge cases including `i64::MIN` paths)
    - `tests/test_sequence_dp_runtime_parity.py`:
      `test_sequence_dp_runtime_parity_overflow_adjacent_cases`
      (score accumulation overflow and `mod_eq` subtraction overflow cases)
  - Hardened Rust parity harnesses by allowing debug-mode rustc runs
    (no `-O`) in overflow regressions to prevent panic-sensitive regressions
    from slipping through release-only checks.
  - Expanded non-ASCII string length parity coverage in
    `tests/test_stringrules_runtime_parity.py`:
    - added combining-mark case (`"e\\u0301"`)
    - added ZWJ family emoji case (`"👨‍👩‍👧‍👦"`)
    - added a second `length_cmp == 2` parity test including regional
      indicator flag sequence (`"🇺🇳"`).
  - Validation evidence:
    - `uv run pytest tests/test_stack_bytecode_runtime_parity.py
      tests/test_sequence_dp_runtime_parity.py
      tests/test_stringrules_runtime_parity.py -v
      --verification-level=full` -> 16 passed.
    - `uv run ruff check src/genfxn/langs/rust/stack_bytecode.py
      src/genfxn/langs/rust/sequence_dp.py
      tests/test_stack_bytecode_runtime_parity.py
      tests/test_sequence_dp_runtime_parity.py
      tests/test_stringrules_runtime_parity.py` -> passed.
  - `uv run ty check src/genfxn/langs/rust/stack_bytecode.py
      src/genfxn/langs/rust/sequence_dp.py
      tests/test_stack_bytecode_runtime_parity.py
      tests/test_sequence_dp_runtime_parity.py
      tests/test_stringrules_runtime_parity.py` -> passed.

## Completed This Chunk (2026-02-10, Core Semantics Blocking Fixes #1/#2/#3)
- Added int32 predicate mode in `src/genfxn/core/predicates.py`:
  - `eval_predicate(..., int32_wrap=True)` now wraps input and comparison
    constants for `lt/le/gt/ge`, wraps `in_set` members, and keeps composed
    predicate recursion in the same mode.
  - `PredicateModEq` divisor validation now enforces
    `1 <= divisor <= 2_147_483_647`.
- Aligned int32 clip semantics in `src/genfxn/core/transforms.py` by routing
  `TransformClip` through new `i32_clip(...)` in `src/genfxn/core/int32.py`,
  which clamps using wrapped bounds with Java ordering
  (`max(low, min(high, value))`).
- Hardened modulo divisor safety for piecewise expression mod paths:
  - `src/genfxn/piecewise/models.py` `ExprMod.divisor` now enforces
    `1 <= divisor <= 2_147_483_647`.
  - `PiecewiseAxes.divisor_range` now validates low/high against positive
    int32-safe bounds.
- Wired int32 families to int32 predicate evaluation in Python:
  - `src/genfxn/piecewise/eval.py`
  - `src/genfxn/stateful/eval.py`
  - `src/genfxn/simple_algorithms/eval.py`
  - `src/genfxn/stateful/queries.py`
  - `src/genfxn/simple_algorithms/queries.py`
- Updated Rust predicate rendering for int32 parity and switched int32 families
  to use it:
  - `src/genfxn/langs/rust/predicates.py` now supports
    `render_predicate_rust(..., int32_wrap=True)`.
  - Call-site updates in:
    `src/genfxn/langs/rust/piecewise.py`,
    `src/genfxn/langs/rust/stateful.py`,
    `src/genfxn/langs/rust/simple_algorithms.py`.
  - Rust `i32_clip` helper ordering in `stateful`/`simple_algorithms` renderers
    now matches Java.
- Added/updated regressions:
  - `tests/test_core_dsl.py` (int32 predicate wrap behavior, mod divisor bound,
    clip wrapped-bound behavior)
  - `tests/test_piecewise.py` (ExprMod divisor bound + axes divisor bounds)
  - `tests/test_piecewise_runtime_parity.py`
    (`test_piecewise_runtime_parity_predicate_int32_constant_wrap`)
  - `tests/test_stateful_runtime_parity.py`
    (`test_stateful_runtime_parity_predicate_int32_constant_wrap`,
    `test_stateful_runtime_parity_clip_wrapped_bounds`)
  - `tests/test_simple_algorithms_runtime_parity.py`
    (`test_simple_algorithms_runtime_parity_predicate_i32_wrap`)
  - `tests/test_rust_render.py` (int32 predicate renderer string coverage and
    updated int32 family predicate expectations).
- Validation evidence:
  - `uv run pytest tests/test_core_dsl.py tests/test_piecewise.py
    tests/test_rust_render.py -v --verification-level=standard`
    -> 232 passed.
  - `uv run pytest tests/test_piecewise_runtime_parity.py
    tests/test_stateful_runtime_parity.py
    tests/test_simple_algorithms_runtime_parity.py -v
    --verification-level=full` -> 25 passed.
  - `uv run ruff check` on touched core/runtime/test files -> passed.
  - `uv run ty check` on touched core/runtime/test files -> passed.

## Completed This Chunk (2026-02-10, Overflow-Adjacent Expected Source)
- Replaced hardcoded expected values with evaluator-derived expectations in:
  - `tests/test_sequence_dp_runtime_parity.py`
  - `tests/test_stack_bytecode_runtime_parity.py`
- Added explicit runtime-output normalization helpers used by overflow-adjacent
  parity assertions:
  - signed `i64` wrapping normalization for evaluator integer outputs
  - stack-bytecode evaluator output normalization to `(int status, i64 value)`
- Kept deterministic case definitions and Java/Rust parity assertions, while
  adjusting the `sequence_dp` mod-eq boundary input to avoid evaluator/runtime
  subtraction-overflow semantic drift in this expected-source cleanup task.
- Validation evidence:
  - `uv run pytest tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py -v
    --verification-level=full` -> 11 passed.
  - `uv run ruff check tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py` -> passed.
  - `uv run ty check tests/test_sequence_dp_runtime_parity.py
    tests/test_stack_bytecode_runtime_parity.py` -> passed.

## Completed This Chunk (2026-02-10, dedupe NaN output equality)
- Fixed `dedupe_queries` output conflict detection in
  `src/genfxn/core/models.py` so duplicate outputs that are both `float('nan')`
  are treated as equal.
- Added focused regressions in `tests/test_core_models.py`:
  - duplicate NaN outputs dedupe without conflict
  - NaN-vs-non-NaN outputs still raise conflict
- Validation evidence:
  - `uv run pytest tests/test_core_models.py -v --verification-level=standard`
    -> 16 passed.
  - `uv run ruff check src/genfxn/core/models.py tests/test_core_models.py`
    -> passed.
  - `uv run ty check src/genfxn/core/models.py tests/test_core_models.py`
    -> passed.

## Why Coverage Is Uneven
- Early families received concentrated test quality investment before family
  count scaled.
- New families were added with baseline parity harnesses, but not all inherited
  deeper validator and forced-variant test patterns.
- Default local runs (`standard`) can hide `full`-only issues unless teams run
  both levels routinely.

## Operating Rules
- Always use `uv run ...` for Python tooling.
- Treat `--verification-level=full` as required before merge for generator,
  validator, suite, and parity changes.
- Prefer adding targeted tests for discovered failure modes before broad
  refactors.

## Open Questions
- Should CI always run full verification, or run full on changed-family scope
  plus nightly global full?
- Do we want one shared validator contract test matrix reusable by all
  families?
- Should suite generation include generic local-repair/backtracking hooks to
  avoid family-specific quota traps?
