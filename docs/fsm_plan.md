# FSM Family Implementation Plan

Date: 2026-02-09  
Owner: Codex + Danielle  
Status: Complete (M1-M4 + suite integration)

## Goal

Add a new `fsm` family with deterministic task generation, validation, and
multi-language rendering support, following existing family conventions in
`genfxn`.

## Target Contract (initial)

- Family name: `fsm`
- Primary signature: `f(xs: list[int]) -> int`
- Behavior: run a finite-state machine over `xs` and return an integer output
  according to configured output mode.

## Scope Decisions (Phase 1)

1. Include both machine styles in one spec:
   - `machine_type`: `moore` or `mealy`
2. Keep input predicate language minimal but expressive:
   - atomic predicates only: `even`, `odd`, `<k`, `<=k`, `>k`, `>=k`, `mod_eq`
3. Use deterministic transition resolution:
   - first matching transition per state (ordered list)
4. Undefined transition policy:
   - axis + spec field (`sink`, `stay`, `error`)
5. Output mode (int only for v1):
   - `final_state_id`, `accept_bool`, `transition_count`

## File Plan

Create:
- `src/genfxn/fsm/models.py`
- `src/genfxn/fsm/sampler.py`
- `src/genfxn/fsm/eval.py`
- `src/genfxn/fsm/queries.py`
- `src/genfxn/fsm/render.py`
- `src/genfxn/fsm/ast_safety.py`
- `src/genfxn/fsm/validate.py`
- `src/genfxn/fsm/task.py`
- `src/genfxn/fsm/__init__.py`
- `tests/test_fsm.py`
- `tests/test_validate_fsm.py`

Update:
- `src/genfxn/cli.py`
- `src/genfxn/core/difficulty.py`
- `src/genfxn/core/describe.py`
- `src/genfxn/core/presets.py` (if difficulty presets enabled in v1)
- `src/genfxn/langs/registry.py`
- `src/genfxn/langs/java/fsm.py`
- `src/genfxn/langs/rust/fsm.py`
- `README.md`
- `AXES.md`
- relevant CLI/render/preset tests

## Milestones

## M1: Models + Evaluator + Task Wiring

Deliverables:
- Pydantic models for FSM spec and axes.
- Canonical evaluator (`eval_fsm`) with explicit edge-case semantics.
- Task generator (`generate_fsm_task`) using sampler + renderer + queries.

Acceptance:
- Unit tests for evaluator cover:
  - both machine types
  - undefined transition policy
  - each output mode
  - empty input and single-element input

## M2: Sampler + Difficulty + Query Quality

Deliverables:
- Sampler that respects target difficulty.
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
- CLI generation support for `fsm` (including difficulty path).
- Family listed in README and AXES docs.
- Optional suites integration (`suites/features.py`, `suites/quotas.py`,
  `suites/generate.py`) if we choose to include in balanced suites now.

Acceptance:
- CLI tests for family/language/difficulty variants.
- End-to-end generate/validate smoke test.

## Open Design Questions

1. Should transition predicates remain atomic in v1, or allow composed
   predicates (`not/and/or`) now?
2. For `error` policy, do we return an error status int or raise?
   - Recommendation: status int, aligned with stack_bytecode robustness.
3. Should we include a `sink_state` explicitly in spec, or synthesize it?
   - Recommendation: synthesize for simpler specs.
4. Should v1 include multi-query batch API signature?
   - Recommendation: no, keep single-input-list function shape.

## Testing Strategy

- Deterministic seed tests for reproducibility.
- Differential tests:
  - renderer output vs canonical evaluator
  - Python vs Java vs Rust behavior parity
- Validator fuzz-style sampling sweep:
  - `execute_untrusted_code=False` large sweep
  - `execute_untrusted_code=True` smaller sweep
- CLI integration tests for `--family fsm` and language switching.

## Resume Checklist

Use this after memory compaction:

1. Read `docs/fsm_plan.md`.
2. Confirm branch and clean state: `git status`.
3. Implement milestones in order (`M1` -> `M4`).
4. After each milestone, run focused tests before continuing.
5. Keep this checklist updated by checking boxes below.

## Execution Checklist

- [x] M1 complete
- [x] M2 complete
- [x] M3 complete
- [x] M4 complete
- [x] Suite integration follow-up complete
- [x] Full `ruff` and full `pytest` pass
- [ ] PR updated with behavior notes + test evidence

## Notes Log

- 2026-02-09: Plan drafted. Stack/bytecode work finished; FSM selected as next.
- 2026-02-09: M1 implemented (`src/genfxn/fsm/*` + `tests/test_fsm.py`).
  Added `fsm` support in `core/difficulty.py` and `core/describe.py`.
  Full suite check passed locally (`1223 passed, 22 skipped`).
- 2026-02-09: M2 implemented. Added `target_difficulty` axis and
  difficulty-aware FSM sampling in `src/genfxn/fsm/sampler.py`, plus
  monotonic-target and query-quality tests in `tests/test_fsm.py`.
  Full suite check passed locally (`1225 passed, 22 skipped`).
- 2026-02-09: M3 implemented. Added FSM AST safety + task validator
  (`src/genfxn/fsm/ast_safety.py`, `src/genfxn/fsm/validate.py`) and
  wired Java/Rust renderers (`src/genfxn/langs/java/fsm.py`,
  `src/genfxn/langs/rust/fsm.py`) through `src/genfxn/langs/registry.py`.
  Added validation + renderer integration tests
  (`tests/test_validate_fsm.py`, updates in `tests/test_java_render.py`
  and `tests/test_rust_render.py`). Full suite check passed locally
  (`1241 passed, 23 skipped`).
- 2026-02-09: M4 implemented. Added CLI support for `fsm` family
  (generation, language rendering, difficulty presets) and FSM difficulty
  presets in `src/genfxn/core/presets.py`. Updated docs (`README.md`,
  `AXES.md`) and CLI/preset tests (`tests/test_cli.py`,
  `tests/test_presets.py`). Full suite check passed locally
  (`1254 passed, 23 skipped`). Suite-balancing integration for `fsm`
  is deferred to a follow-up milestone.
- 2026-02-09: Suite integration follow-up completed. Added `fsm` to
  balanced suites pipeline (`src/genfxn/suites/features.py`,
  `src/genfxn/suites/quotas.py`, `src/genfxn/suites/generate.py`) and
  updated FSM difficulty modeling in `src/genfxn/core/difficulty.py` so
  D5 is genuinely reachable. Added suite + difficulty tests
  (`tests/test_suites.py`, `tests/test_difficulty.py`).
  Full suite check passed locally (`1263 passed, 25 skipped`).
