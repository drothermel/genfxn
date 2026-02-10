# genfxn Project Instructions

## Task Families

- `piecewise` - Piecewise functions with branches
- `stateful` - Stateful list processing (longest_run, conditional_linear_sum, resetting_best_prefix_sum)
- `simple_algorithms` - Simple algorithms (most_frequent, count_pairs_sum, max_window_sum)
- `stringrules` - String transformation rules with predicates

## Family Roadmap

We are implementing new families in the order tracked by
`docs/shared_rec_list.md`. Treat that file as the source-of-truth ordering
unless a newer planning doc explicitly supersedes it.

## Core Modules

- `src/genfxn/core/difficulty.py` - Difficulty scoring (1-5) per family
- `src/genfxn/core/describe.py` - Natural language task descriptions
- `src/genfxn/{family}/task.py` - Task generation entry points

## Family Quality Gate

No new family should be added or marked complete without an executable
cross-language runtime parity test harness.

Required:
- Runtime parity tests must execute code (not only inspect rendered strings).
- Tests must compare Python, Java, and Rust outputs on the same specs/inputs.
- Parity harness coverage must be part of the family's test evidence in PRs.
