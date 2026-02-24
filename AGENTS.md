# genfxn Agent Instructions

All existing guidance in `CLAUDE.md` applies. This file adds explicit execution
requirements for coding tasks in this repository.
For test/check categories and copy-paste commands, see `TESTING.md`.

## Mandatory Verification Workflow

Unless the user explicitly says to skip checks for the current task, agents
must run this exact sequence after making code changes:

1. Run `uv run ruff format` on all Python files in the repository.
2. Run `uv run ruff check --fix src/ tests/ scripts/`.
3. Manually fix any remaining lint issues in `src/` only.
4. Run `uv run ty check src` and fix all type issues in `src/`.
5. Run all tests: `uv run pytest tests/ -v --verification-level=full`.
6. Fix obvious failures. If any remaining failures require a design decision,
   surface them clearly with options and tradeoffs.

Agents should not claim checks were skipped "per instructions" unless the
current user message explicitly requested skipping them.
