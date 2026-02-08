# Code Review Standards

This repository uses code review to catch defects, improve maintainability,
and share implementation context.

## Review Scope

Each review should explicitly check:
- Correctness and edge cases
- Security implications and input validation
- Performance impact
- Error handling behavior
- Test coverage quality
- Readability and maintainability

Formatting and import ordering are enforced by tooling (`ruff`) and should not
block unless tooling is missing or misconfigured.

## Severity Labels

Use one of these labels on review comments:
- `[blocking]`: must be fixed before merge
- `[important]`: should be fixed; discuss if tradeoffs exist
- `[nit]`: non-blocking quality suggestion
- `[suggestion]`: optional alternative design
- `[learning]`: explanatory context, no action required
- `[praise]`: highlight good practice worth repeating

## Review Process

1. Context pass (2-3 min)
- Read PR description and linked issue/context.
- Check scope and size; if very large, ask for splitting.
- Confirm tests/lint status and understand intended behavior.

2. High-level pass (5-10 min)
- Validate architecture and consistency with existing patterns.
- Check file organization and decomposition.
- Confirm a clear and sufficient testing strategy.

3. Detailed pass (10-20 min)
- Verify logic, edge cases, and failure paths.
- Evaluate security and data handling risks.
- Inspect runtime complexity and hotspots.
- Confirm naming, abstraction boundaries, and readability.

4. Decision pass (2-3 min)
- Summarize findings by severity.
- Decide: approve, comment, or request changes.
- Offer pairing if unresolved complexity remains.

## Reviewer Checklist

- [ ] Behavior matches the problem statement
- [ ] Edge and error cases are covered
- [ ] Security-sensitive paths are validated
- [ ] No obvious performance regression introduced
- [ ] Tests are deterministic and meaningful
- [ ] Public behavior/API changes are documented

## Author Checklist (Before Requesting Review)

- [ ] PR description explains what changed and why
- [ ] Scope is focused and reasonably sized
- [ ] `uv run ruff check .` passes
- [ ] Relevant `pytest` tests pass
- [ ] New behavior includes tests
- [ ] Known follow-ups are listed explicitly

## Suggested Review Comment Template

```markdown
## Summary
[What was reviewed and overall assessment]

## Required Changes
- [blocking] ...

## Important Improvements
- [important] ...

## Non-Blocking Suggestions
- [nit] ...
- [suggestion] ...

## Verdict
- Approve / Comment / Request changes
```
