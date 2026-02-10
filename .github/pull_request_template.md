## What Changed
- [ ] Describe the functional change.
- [ ] Describe key implementation choices.

## Why
- [ ] Link issue/context and explain rationale.

## Risk Assessment
- [ ] Low
- [ ] Medium
- [ ] High

Notes on risk and rollout:

## Testing Evidence
- [ ] `uv run ruff check .`
- [ ] `uv run pytest tests/ -v --verification-level=standard` (or targeted subset)
- [ ] `uv run pytest tests/ -v --verification-level=full` (for changes that may affect `@pytest.mark.full` coverage)
- [ ] Additional manual verification (if applicable)

Commands and outcomes:

## Reviewer Focus Areas
Point reviewers to the highest-risk logic paths and edge cases:
- 

## Checklist
- [ ] New behavior is covered by tests.
- [ ] Error paths are handled and tested where relevant.
- [ ] Security-sensitive inputs/flows were considered.
- [ ] Performance impact was considered for hot paths.
- [ ] Docs/comments were updated for changed behavior.

## Review Severity Labels
Use these labels in review comments:
- `[blocking]` Must fix before merge
- `[important]` Should fix; discuss tradeoffs if needed
- `[nit]` Non-blocking suggestion
- `[suggestion]` Optional alternative
- `[learning]` Educational context
- `[praise]` Positive feedback
