# Current Plan: Robustness and Test-Parity Hardening

## Goal
Maintain consistent, deterministic behavior across all families and runtimes
while keeping generation, validation, splitting, and suites stable.

## Status Snapshot
- Baseline hardening work is complete for current shipped families.
- There is no active hardening batch in progress.
- New plan items should be added only for net-new issues or regressions.

## Current State
- All shipped families are integrated in generation, validation, and suites.
- Runtime parity coverage exists for Python/Java/Rust.
- CI enforces full verification gates (`ruff`, `ty`, full pytest).
- Validator contract matrix coverage is in place.

## Active Risks
- Cross-language semantic drift after renderer or evaluator changes.
- Contract drift between CLI and library behavior (especially split/holdout
  parsing and matching).
- Full-suite performance and flake risk as coverage grows.

## Next Actions
1. For any semantic change, add focused evaluator-renderer-runtime parity tests
   in the same change.
2. Keep CLI docs and help output aligned when options/defaults change.
3. Treat split/holdout behavior as contract-critical and add regressions for any
   parser/matcher edits.
4. Run strict calibration and quota checks when suite/difficulty logic changes.

## Exit Criteria
- No unresolved correctness regressions for shipped families.
- Full verification remains green in CI.
- Documentation reflects current behavior without historical execution logs.
