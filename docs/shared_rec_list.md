# Shared Recommendation List (Top 7)

Agreed top‑7 families (with a tie at #6).
Date: 2026-02-09

## Status

- Completed: `Stack/Bytecode Interpreter` (implemented as `stack_bytecode`)
- Completed: `Finite-State Transducer (FSM/Mealy/Moore)`
- Completed: `Bit Manipulation Pipelines` (implemented as `bitops`)
- Completed: `Sequence DP With Custom Scoring` (implemented as `sequence_dp`)
- Completed: `Interval Operations` (implemented as `intervals`)
- In progress: `Graph Query Functions` (implemented as `graph_queries`, M0)
- Implementation plans:
  `docs/fsm_plan.md`, `docs/bitops_plan.md`, `docs/sequence_dp_plan.md`,
  `docs/intervals_plan.md`, `docs/graph_queries_plan.md`

1. Stack/Bytecode Interpreter
Signature: `f(xs: list[int]) -> int` (program baked into spec; optional `f(program, xs)` variant)
Axes: instruction set size, program length, control‑flow depth, stack depth, input mode, output mode, max_step_count, jump_target_mode (error/clamp/wrap)
Difficulty scaling: longer programs, add conditional jumps/loops, mixed arithmetic/compare ops, higher max_step_count
Hard parts: halting/step limit, out‑of‑bounds jumps, stack underflow, operand order, division/modulo semantics
Testing/description: reference interpreter; cover every opcode + both jump branches

2. Finite‑State Transducer (FSM/Mealy/Moore)
Signature: `f(xs: list[int]) -> list[int]` or `-> int`
Axes: machine_type (Mealy vs Moore), number of states, input predicate complexity, output mode, default transition policy (sink/stay/error)
Difficulty scaling: more states, composed predicates, outputs per transition, default/implicit transitions
Hard parts: output length alignment (Mealy vs Moore), undefined transitions, ambiguous predicates
Testing/description: sequences that hit every transition; full transition + output mapping

3. Bit Manipulation Pipelines
Signature: `f(x: int) -> int` (optional `f(x: int, y: int) -> int` variant)
Axes: op types (and/or/xor/shift/rotate/popcount), bit width, bit numbering (LSB=0 vs MSB=0), signedness, mask source, combine mode (chain/parallel/conditional)
Difficulty scaling: longer pipelines, conditional branches, mixed widths, two‑operand ops
Hard parts: width/overflow semantics, rotation direction, bit indexing convention, signed vs unsigned
Testing/description: edge values (`0`, `-1`, max‑width); must state width and indexing

4. Sequence DP With Custom Scoring
Signature: `f(a: list[int], b: list[int]) -> int` or `-> list[int]` (plus single‑sequence variant `f(xs: list[int]) -> int`, as separate templates)
Axes: template (single‑seq vs two‑seq), recurrence type, scoring params, base cases, tie‑breaks, optimization direction (min/max), output mode (score vs alignment/path)
Difficulty scaling: negative scores, explicit tie‑break rules, return alignment/path rather than score
Hard parts: base case semantics, tie‑break ordering, path reconstruction
Testing/description: reference DP with tie‑forcing cases; specify recurrence + base + tie‑break

5. Interval Operations
Signature: `f(intervals: list[tuple[int,int]]) -> list[tuple[int,int]]` or `-> int`
Axes: boundary mode (open/closed), operation type, merge_touching flag, output format, degenerate interval policy
Difficulty scaling: mixed boundary modes, unsorted input, degenerate intervals, operation composition, optional weights
Hard parts: touching vs overlapping, degenerate interval handling, empty input behavior, ordering conventions
Testing/description: boundary‑heavy tests; must state endpoint semantics clearly

6. Graph Query Functions (tie)
Signature: `f(u: int, v: int) -> int|bool` or `f(qs: list[tuple[int,int]]) -> list[int|bool]` (graph baked into spec by default)
Axes: graph size (nodes/edges, with max_nodes cap), directed/undirected, weighted/unweighted, negative weights allowed, query type, path constraints
Difficulty scaling: edge predicates, max‑hop constraints, weighted paths, multiple queries
Hard parts: constraint semantics, negative weights (algorithm choice), path tie‑breaking, disconnected graphs, code size vs description length
Testing/description: BFS/DFS/Dijkstra reference; specify constraints and tie‑breaks

6. Temporal Logic Over Streams (tie)
Signature: `f(xs: list[int]) -> bool` or `-> int`
Axes: formula depth, operator mix (eventually/always/until/since/next), predicate layer (value predicates vs raw values), windows, output mode
Difficulty scaling: nested tree formulas, bounded windows, return indices/counts
Hard parts: empty sequence semantics, "next" at last element, window boundaries, past‑looking "since"
Testing/description: brute‑force evaluator; include empty/single‑element cases; build and validate the evaluator before sampler complexity

Next outside the top 7: Grid/Cellular Operations.
