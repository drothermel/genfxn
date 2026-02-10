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
  - split contract drift between CLI and library random split remains an open
    policy/testing decision

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

## Completed This Chunk (2026-02-10)
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
