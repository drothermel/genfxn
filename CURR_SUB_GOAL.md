I want to make the function generation code in this repo bulletproof.  In pursuit of this I want to introduce Family Contract Validators.

## Imagined Design

Given a `Task` object validate:

- ID Correctness: `task.task_id == task_id_from_spec(task.family, task.spec`
- Code Compiles: ast to compile `task.code`
- Eval Matches Exec: exhastive across `value_range`
- Stored Queries are Self-Consistent
	- `eval_piecewise(spec, q.input) == q.output`
	- inputs and outputs have expected types: `int -> int`

If there's an issue, produce a structured issue, `Issue(code, severity, message, location)`.
- code: the code itself
- severity: set by validation type
- location: something like `spec.branches[2].condition`, `queries[7]` or `code.compile`

## Prompt

Implement a **piecewise task validator** that enforces:

* task_id correctness (`task_id_from_spec` vs stored task_id),
* code compiles,
* stored queries are correct for the spec,
* semantic parity: executing the stored code matches `eval_piecewise` across a strong test set (ideally exhaustive across the default value_range).

Add tests that create intentionally corrupted tasks (wrong task_id, wrong query output, non-compiling code) and assert the validator reports the correct issue types.
  Keep it piecewise-only for now.

(Anchors: `genfxn/core/codegen.py`, `genfxn/core/models.py`, `genfxn/piecewise/eval.py`, `genfxn/piecewise/render.py`, `genfxn/piecewise/task.py`.)
