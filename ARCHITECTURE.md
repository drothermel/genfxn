# Architecture Overview

`genfxn` generates algorithmic task specs, renders runnable implementations in
multiple languages, validates tasks, and builds dataset splits/suites.

```mermaid
flowchart TD
    A[Family Generators\nsrc/genfxn/<family>/task.py] --> B[Task Model\nsrc/genfxn/core/models.py]
    B --> C[Validation\nsrc/genfxn/<family>/validate.py]
    B --> D[Difficulty/Description\nsrc/genfxn/core/difficulty.py + describe.py]
    B --> E[Language Renderers\nsrc/genfxn/langs/python|java|rust]
    E --> F[Runtime Parity Tests\ntests/test_*_runtime_parity.py]
    B --> G[Suite Generation\nsrc/genfxn/suites/generate.py]
    B --> H[Dataset Splitters\nsrc/genfxn/splits.py + CLI]
    I[CLI\nsrc/genfxn/cli.py] --> A
    I --> G
    I --> H
```

## Package Layout
- `src/genfxn/core/`: shared schemas, validation helpers, tracing, safe exec.
- `src/genfxn/<family>/`: family-specific models, generators, validators.
- `src/genfxn/langs/`: language renderers and runtime integration points.
- `src/genfxn/suites/`: cross-family suite composition and quota logic.
- `src/genfxn/splits.py`: dataset split strategies.
- `tests/`: validator tests, integration/suite tests, runtime parity tests.

## Test Layers
- Unit and schema validation: `tests/test_validate_*.py`
- Family integration generation checks: `tests/test_<family>.py`
- Cross-language runtime parity: `tests/test_*_runtime_parity.py`
- Suite composition/regression: `tests/test_suites.py`
- Split/CLI behavior: `tests/test_splits.py`, `tests/test_cli.py`

## Verification Modes
- `standard`: default for quick iteration, skips `@pytest.mark.full`.
- `full`: required to catch deep fuzz/lifecycle/parity edge failures.

## Related Docs
- `WORKING_MEMORY.md` for current findings and assumptions.
- `CURRENT_PLAN.md` for active hardening execution steps.
