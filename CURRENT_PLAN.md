# Current Plan

## Goal
Maintain correctness and parity guarantees while minimizing regression risk in
CLI parsing/splitting, evaluator/renderer semantics, and validator contracts.

## Current Status (2026-02-10)
- Active batch: strict surfacing + remaining type-coercion hardening.
- Prior hardening batches are complete and validated.
- Current baseline is green in standard verification, Ruff, and ty.

## Active Checklist
- [x] Harden query output dedupe equality to be type-sensitive (including
      nested/dict-key cases) and add focused regression tests.
- [x] Reject bool bounds for `StringRulesAxes` int-range fields and add tests.
- [x] Make `find_satisfying(...)` strict-surfacing (propagate unexpected
      generator/predicate exceptions) and update tests to assert propagation.
- [x] Run targeted validation (`pytest` slices + `ruff` + `ty`) and record
      outcomes in `WORKING_MEMORY.md`.

## Default Execution Template (use for next batch)
1. Reproduce and isolate issue with minimal failing case.
2. Patch with smallest safe blast radius.
3. Add focused regression tests near changed behavior.
4. Run targeted validation (`pytest` slices + `ruff` + `ty`).
5. Run broader confidence check as needed.
6. Record outcomes in `WORKING_MEMORY.md`.

## Validation Baseline Snapshot
- `uv run pytest tests/ -q --verification-level=standard`
  - 1922 passed, 101 skipped
- `uv run ruff check .`
  - passed
- `uv run ty check`
  - passed

## Deferred Watch Items
- Ensure parity/toolchain checks remain mandatory in CI environments.
- Continue preferring end-to-end CLI tests for split parser/matcher wiring,
  not only helper-level matcher tests.
