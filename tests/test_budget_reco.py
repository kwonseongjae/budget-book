import budget_reco
import layout
import migrate_couple as mc


def _state():
    return mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                    budgets_empty=False, invest_charts=2, dash_rows=200, dash_base=46)


def test_label_and_checkbox_written_but_result_cell_left_to_script():
    _s, values, _v = mc.plan(_state())
    ranges = {e["range"] for e in values}
    assert {"설정!I12", "설정!J12"} <= ranges
    assert "설정!I13" not in ranges


def test_checkbox_validation_applied_every_run():
    structure, _v, _vi = mc.plan(_state())
    j12 = layout.a1_to_grid("설정!J12")
    assert any(r.get("setDataValidation", {}).get("range") == j12 and r["setDataValidation"]["rule"]["condition"]["type"] == "BOOLEAN"
               for r in structure)


def test_trigger_cell_matches_script_route():
    assert (budget_reco.CHECK, budget_reco.LABEL) == ("설정!J12", "설정!I12")
