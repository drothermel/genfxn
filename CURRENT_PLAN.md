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
- In progress:
  - Converting review findings into repeatable cross-family tests.
- Pending:
  - CI and policy tightening so `full` verification is routinely enforced.

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
- Current status: CLI is optimized for streaming memory behavior; output set may
  differ from library shuffle+slice semantics for identical seed/ratio.

Exit criterion:
- No ambiguous expectations between CLI split and `splits.py` outputs.

### 5) Verification Policy
- enforce `uv run pytest tests/ -v --verification-level=full` in CI for merge
  gates (or at minimum changed-family + nightly global full).
- keep `standard` for local fast loop, but document that it is non-exhaustive.

Exit criterion:
- Full-mode-only failures are rare and quickly detected pre-merge.

## Immediate Next Actions
1. Build a shared validator contract checklist and apply it to all newer
   families.
2. Land suite-generation quota-trap regression + retry diversification.
3. Tighten merge-gate policy so full verification is run routinely.
