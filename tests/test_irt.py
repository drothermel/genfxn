from __future__ import annotations

from pathlib import Path

from genfxn.irt.bank import BankBuildSettings
from genfxn.irt.diagnostics import DiagnosticsSettings, run_fit_diagnostics
from genfxn.irt.fit import FitSettings, fit_irt_models
from genfxn.irt.io import write_jsonl
from genfxn.irt.models import (
    EffectiveControls,
    RequestedControls,
    ResponseRow,
)
from genfxn.irt.score import AnchorScoringSettings, score_with_anchors
from genfxn.irt.stratification import (
    _BITOPS_CELL_SPACE,
    _FSM_CELL_SPACE,
    _SIMPLE_ALGORITHMS_CELL_SPACE,
    _STATEFUL_CELL_SPACE,
    get_strata_plan,
)


def test_locked_strata_plan_totals() -> None:
    stateful = get_strata_plan("stateful", 300)
    assert sum(stateful.target_counts.values()) == 300
    assert sum(stateful.core_target_counts.values()) == 300
    assert len(stateful.target_counts) == 20
    assert all(v == 15 for v in stateful.target_counts.values())

    simple = get_strata_plan("simple_algorithms", 300)
    assert sum(simple.target_counts.values()) == 300
    by_template: dict[str, int] = {}
    for cell, count in simple.target_counts.items():
        template = cell.split("|", 1)[0]
        by_template[template] = by_template.get(template, 0) + count
    assert by_template == {
        "most_frequent": 100,
        "count_pairs_sum": 100,
        "max_window_sum": 100,
    }

    fsm = get_strata_plan("fsm", 300)
    assert sum(fsm.target_counts.values()) == 300
    assert sum(1 for value in fsm.target_counts.values() if value == 12) == 3

    bitops = get_strata_plan("bitops", 300)
    assert sum(bitops.target_counts.values()) == 300
    assert sum(1 for value in bitops.target_counts.values() if value == 12) == 3


def test_locked_strata_plan_rejects_non_300_total() -> None:
    try:
        get_strata_plan("stateful", 120)
    except ValueError as exc:
        assert "locked to 300" in str(exc)
    else:
        raise AssertionError("expected locked stratification to reject non-300")


def _make_row(
    *,
    item_id: str,
    respondent_id: str,
    correct: bool,
    family: str = "stateful",
) -> ResponseRow:
    return ResponseRow(
        item_id=item_id,
        family=family,
        task_id=item_id,
        respondent_id=respondent_id,
        provider="codex",
        model="gpt-5.1-codex-mini",
        repeat_index=1,
        n_cases_total=3,
        n_cases_correct=(3 if correct else 1),
        correct=correct,
        requested_controls=RequestedControls(
            temperature=0.2,
            top_p=0.95,
            reasoning_effort="minimal",
        ),
        effective_controls=EffectiveControls(
            temperature=0.2,
            top_p=0.95,
            reasoning_effort="minimal",
        ),
        parse_error=False,
        runtime_error=False,
        timeout=False,
        raw_response_ref=None,
        run_id="run_synth",
    )


def test_fit_diagnostics_and_anchor_scoring_pipeline(tmp_path: Path) -> None:
    responses_path = tmp_path / "responses.jsonl"

    respondent_ids = [
        "codex:gpt-5.1-codex-mini#r1",
        "codex:gpt-5.1-codex-mini#r2",
        "claude-code:claude-sonnet-4-6#r1",
        "glm:GLM-4.5#r1",
    ]
    item_ids = [f"item_{idx}" for idx in range(6)]

    rows: list[ResponseRow] = []
    for ridx, respondent_id in enumerate(respondent_ids):
        for iidx, item_id in enumerate(item_ids):
            correct = (ridx + iidx) % 2 == 0
            rows.append(
                _make_row(
                    item_id=item_id,
                    respondent_id=respondent_id,
                    correct=correct,
                )
            )

    write_jsonl(responses_path, rows)

    fit_settings = FitSettings(
        fit_id="fit_synth",
        responses_path=responses_path,
        out_dir=tmp_path,
        min_item_respondents=2,
        min_respondent_items=2,
    )
    fit_result = fit_irt_models(fit_settings)

    assert fit_result.item_params_1pl_path.exists()
    assert fit_result.item_params_2pl_path.exists()
    assert fit_result.respondent_params_1pl_path.exists()
    assert fit_result.respondent_params_2pl_path.exists()
    assert fit_result.anchors_path.exists()

    diag_settings = DiagnosticsSettings(
        fit_id="fit_synth",
        fit_dir=fit_result.fit_dir,
        responses_path=responses_path,
    )
    diag_result = run_fit_diagnostics(diag_settings)
    assert diag_result.icc_path.exists()
    assert diag_result.item_information_path.exists()
    assert diag_result.local_dependence_path.exists()
    assert diag_result.summary_path.exists()

    score_settings = AnchorScoringSettings(
        fit_id="score_synth",
        anchors_path=fit_result.anchors_path,
        responses_path=responses_path,
        out_dir=tmp_path,
    )
    score_result = score_with_anchors(score_settings)
    assert score_result.theta_scores_path.exists()
    assert score_result.theta_summary_path.exists()


# Ensure the locked bank settings model still validates defaults used in CLI.
def test_bank_build_settings_defaults() -> None:
    settings = BankBuildSettings(bank_id="bank", out_dir=Path("data/irt/banks"))
    assert settings.per_family_count == 300
    assert settings.families == [
        "stateful",
        "simple_algorithms",
        "fsm",
        "bitops",
    ]


def test_cell_spaces_produce_valid_cells() -> None:
    for family, cell_space in [
        ("stateful", _STATEFUL_CELL_SPACE),
        ("simple_algorithms", _SIMPLE_ALGORITHMS_CELL_SPACE),
        ("fsm", _FSM_CELL_SPACE),
        ("bitops", _BITOPS_CELL_SPACE),
    ]:
        plan = get_strata_plan(family, 300)
        assert plan.cell_space is not None
        valid = set(cell_space.valid_cells())
        plan_cells = set(plan.target_counts.keys())
        assert valid == plan_cells, (
            f"{family}: cell space and plan disagree: "
            f"space-only={valid - plan_cells}, plan-only={plan_cells - valid}"
        )


def test_stateful_cell_space_excludes_impossible() -> None:
    cells = _STATEFUL_CELL_SPACE.valid_cells()
    for cell in cells:
        parts = cell.split("|")
        if parts[0] == "longest_run":
            assert parts[2] == "low", (
                f"longest_run should only have 'low' transform complexity, "
                f"got {parts[2]!r} in {cell!r}"
            )
    impossible = [
        "longest_run|parity|mixed",
        "longest_run|parity|high",
        "longest_run|comparison|mixed",
        "longest_run|comparison|high",
        "longest_run|modular|mixed",
        "longest_run|modular|high",
    ]
    cell_set = set(cells)
    for cell in impossible:
        assert cell not in cell_set, f"impossible cell {cell!r} found in space"
