# Working Memory

## Mission
Keep `genfxn` reliable as a deterministic research primitive with explicit
contracts, strong validation, and cross-language parity.

## Current Invariants
- Python evaluator semantics are authoritative for expected outputs.
- Runtime parity is enforced against Java and Rust implementations.
- Query dedupe contract:
  - default: global input uniqueness via `dedupe_queries`
  - exception families: per-tag input uniqueness via
    `dedupe_queries_per_tag_input` (`intervals`, `graph_queries`,
    `sequence_dp`, `temporal_logic`)
- Split semantics are contract-critical and must stay aligned between library
  and CLI.
- Full verification is required before merge for behavior-affecting changes.

## Known Risk Areas
- Overflow-adjacent arithmetic and i64 normalization paths.
- Unicode predicate semantics across Python/Java/Rust.
- Validator strictness drift from emitted renderer structure.
- Suite quota and pool-selection regressions when retuning suite logic.

## Operating Rules
- Use `uv run ...` for Python tooling.
- Prefer targeted regression tests for discovered failures before broad
  refactors.
- Keep docs synchronized with actual CLI/runtime behavior.

## Open Questions
- None currently. Add only unresolved, decision-relevant questions here.

## Last Updated
- 2026-02-20
