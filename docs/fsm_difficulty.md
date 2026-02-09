# FSM Difficulty Model

This note documents how `compute_difficulty("fsm", spec)` is intended to work,
including the rationale for an explicit, reachable D5 band.

## Design Goal

FSM difficulty should increase when machines get harder along independent axes:

1. State-space size
2. Transition density
3. Predicate complexity
4. Mode complexity (machine/output/policy semantics)

Any axis can contribute meaningful complexity, but D5 should represent
specifications that are jointly hard across several axes, not an arbitrary cap.

## Current Scoring

The model combines four components with weights:

- `states`: `0.30`
- `transitions`: `0.25`
- `predicate`: `0.20`
- `mode`: `0.25`

Then rounds and clamps to `[1, 5]`.

### Component mappings

- State count:
  - `<=2 -> 1`, `3 -> 2`, `4 -> 3`, `5 -> 4`, `>=6 -> 5`
- Transition density:
  - derived from `max(avg_transitions_per_state, max_transitions_in_any_state)`
  - bucketed to scores `1..5`
- Predicate complexity:
  - `even/odd -> 1`
  - comparisons (`lt/le/gt/ge`) -> `2`
  - `mod_eq -> 5`
- Mode complexity:
  - start at `1`
  - `+1` if `machine_type == mealy`
  - `+1` for `accept_bool`, `+2` for `transition_count`
  - `+1` for `sink`, `+2` for `error`
  - clamped to `1..5`

## D5 Rationale

D5 is reserved for high-complexity FSMs that combine:

- larger state spaces (typically `>=6` states),
- high transition density,
- strong predicate complexity (`mod_eq` in the mix),
- and higher-complexity mode semantics (`mealy + transition_count + error`).

This is intentional and avoids two failure modes:

1. **Artificial D5**: assigning D5 without genuinely harder behavior.
2. **Unreachable D5**: model/quotas requiring D5 but scoring never producing it.

## Operational Guidance

- If future sampler changes reduce observed D5 rates, treat that as calibration
  drift and update either sampler presets or scoring thresholds.
- If new predicate language features are added (e.g. composed predicates),
  update FSM predicate scoring so D-level semantics stay stable.
