# Bitops Family Implementation Plan

Date: 2026-02-09
Owner: Codex + Danielle
Status: In progress (M1-M3 complete, M4 pending)

## Goal

Add a new `bitops` family with deterministic task generation, validation, and
multi-language rendering support, following existing `genfxn` family patterns.

## Target Contract (v1)

- Family name: `bitops`
- Primary signature: `f(x: int) -> int`
- Behavior: apply a configured pipeline of bit operations to `x` and return the
  final integer.

## Scope Decisions (Phase 1)

1. Keep v1 single-input:
   - only `f(x: int) -> int` (no second operand input arg in v1)
2. Canonical width semantics:
   - fixed-width arithmetic with explicit mask after each operation
   - v1 default width: 8/16/32 (axis-controlled)
3. Deterministic operation set:
   - `and_mask`, `or_mask`, `xor_mask`, `shl`, `shr_logical`, `rotl`, `rotr`,
     `not`, `popcount`, `parity`
4. Signedness policy:
   - operate on unsigned bit patterns; return canonical unsigned integer value
5. Output mode:
   - int only in v1 (no bool/list modes)

## File Plan

Create:
- `src/genfxn/bitops/models.py`
- `src/genfxn/bitops/sampler.py`
- `src/genfxn/bitops/eval.py`
- `src/genfxn/bitops/queries.py`
- `src/genfxn/bitops/render.py`
- `src/genfxn/bitops/ast_safety.py`
- `src/genfxn/bitops/validate.py`
- `src/genfxn/bitops/task.py`
- `src/genfxn/bitops/__init__.py`
- `tests/test_bitops.py`
- `tests/test_validate_bitops.py`

Update:
- `src/genfxn/cli.py`
- `src/genfxn/core/difficulty.py`
- `src/genfxn/core/describe.py`
- `src/genfxn/core/presets.py`
- `src/genfxn/langs/registry.py`
- `src/genfxn/langs/java/bitops.py`
- `src/genfxn/langs/rust/bitops.py`
- `README.md`
- `AXES.md`
- relevant CLI/render/preset tests

## Milestones

## M1: Models + Evaluator + Task Wiring

Deliverables:
- Pydantic models for bitops spec and axes.
- Canonical evaluator (`eval_bitops`) with explicit width-masking semantics.
- Task generator (`generate_bitops_task`) using sampler + renderer + queries.

Acceptance:
- Unit tests for evaluator cover each op and edge inputs:
  - `0`, `1`, `-1`, max-width value, overflow boundaries
  - rotate/shift amounts near and above width

## M2: Sampler + Difficulty + Query Quality

Deliverables:
- Sampler that respects `target_difficulty`.
- Query generator with `BOUNDARY`, `COVERAGE`, `TYPICAL`, `ADVERSARIAL`.
- Difficulty scoring added to `core/difficulty.py`.

Acceptance:
- Difficulty monotonicity tests (means increase with target).
- Query outputs exactly match evaluator for sampled specs.

## M3: Renderer + Validator + AST Safety

Deliverables:
- Python renderer (canonical behavior).
- Java + Rust renderers.
- Validator (spec/task/code/query/semantic checks).
- AST whitelist aligned with renderer output.

Acceptance:
- Generated tasks validate with zero errors across many seeds.
- Cross-language parity tests pass for fixed sampled specs.

## M4: CLI + Docs + Suite Integration

Deliverables:
- CLI generation support for `bitops` (including difficulty path).
- Family listed in README and AXES docs.
- Optional suites integration (`suites/features.py`, `suites/quotas.py`,
  `suites/generate.py`) if we include in balanced suites now.

Acceptance:
- CLI tests for family/language/difficulty variants.
- End-to-end generate/validate smoke test.
- Balanced sampling check for 50 samples across targets.

## Open Design Questions

1. Should `popcount`/`parity` be terminal-only ops in v1?
   - Recommendation: allow anywhere; output remains masked int.
2. Should shift counts wrap (`k % width`) or clamp?
   - Recommendation: wrap for deterministic cross-language parity.
3. Do we include arithmetic right shift in v1?
   - Recommendation: no; keep only logical right shift to avoid signedness
     ambiguity.
4. Should v1 include two-input variant (`f(x, y)`)?
   - Recommendation: defer to v2.

## Testing Strategy

- Deterministic seed tests for reproducibility.
- Differential tests:
  - renderer output vs canonical evaluator
  - Python vs Java vs Rust behavior parity
- Validator fuzz-style sampling sweep:
  - `execute_untrusted_code=False` large sweep
  - `execute_untrusted_code=True` smaller sweep
- CLI integration tests for `--family bitops` and language switching.
- Suite-balancing checks to confirm target quotas are reachable.

## Resume Checklist

Use this after memory compaction:

1. Read `docs/bitops_plan.md`.
2. Confirm branch and clean state: `git status`.
3. Implement milestones in order (`M1` -> `M4`).
4. After each milestone, run focused tests before continuing.
5. Keep this checklist updated by checking boxes below.

## Execution Checklist

- [x] M1 complete
- [x] M2 complete
- [x] M3 complete
- [ ] M4 complete
- [ ] Suite integration follow-up complete
- [ ] Full `ruff` and full `pytest` pass
- [ ] PR updated with behavior notes + test evidence

## Notes Log

- 2026-02-09: Plan drafted. `fsm` completed and merged; `bitops` selected as
  next family.
- 2026-02-09: M1 implemented. Added `src/genfxn/bitops/*` core package files
  (models/eval/sampler/queries/render/task plus validator + AST safety),
  Python renderer registry wiring in `src/genfxn/langs/registry.py`, and
  initial tests in `tests/test_bitops.py`. Added bitops description support in
  `src/genfxn/core/describe.py`.
  Focused verification passed:
  `uv run ruff check src/genfxn/bitops src/genfxn/langs/registry.py src/genfxn/core/describe.py tests/test_bitops.py`
  and `uv run pytest tests/test_bitops.py -v` (7 passed).
- 2026-02-09: M2 implemented. Added `bitops` difficulty scoring in
  `src/genfxn/core/difficulty.py` and wired `compute_difficulty("bitops", ...)`.
  Strengthened tests in `tests/test_bitops.py` for
  target-difficulty monotonicity and full query-tag coverage, and added bitops
  family coverage in `tests/test_difficulty.py`.
  Focused verification passed:
  `uv run ruff check src/genfxn/core/difficulty.py tests/test_bitops.py tests/test_difficulty.py`
  and `uv run pytest tests/test_bitops.py tests/test_difficulty.py -v`
  (82 passed).
- 2026-02-09: M3 implemented. Added language renderers for
  `bitops` in `src/genfxn/langs/java/bitops.py` and
  `src/genfxn/langs/rust/bitops.py` and wired language registry support.
  Hardened validator/AST safety in `src/genfxn/bitops/validate.py` and
  `src/genfxn/bitops/ast_safety.py`, then added validator tests in
  `tests/test_validate_bitops.py` and renderer coverage updates in
  `tests/test_java_render.py` and `tests/test_rust_render.py`.
  Focused verification passed:
  `uv run ruff check src/genfxn/bitops/ast_safety.py src/genfxn/bitops/validate.py src/genfxn/langs/java/bitops.py src/genfxn/langs/rust/bitops.py src/genfxn/langs/registry.py tests/test_validate_bitops.py tests/test_java_render.py tests/test_rust_render.py`
  and
  `uv run pytest tests/test_validate_bitops.py tests/test_java_render.py tests/test_rust_render.py tests/test_bitops.py -q`
  (305 passed).
