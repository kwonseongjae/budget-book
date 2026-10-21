"""추이 C1 '연도 이동' 드롭다운 (월 이동 A12의 짝). 문구는 Apps Script(logic.gs)와 같아야 한다."""
import re
from pathlib import Path

import layout
import migrate_couple as mc
import views

GS = (Path(__file__).parent.parent / "apps-script" / "logic.gs").read_text(encoding="utf-8")


def _gs_const(name):
    return re.search(rf"var {name} = (.+?);", GS).group(1)


def _state():
    return mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                    budgets_empty=False, invest_charts=2, dash_rows=200, dash_base=46)


def test_texts_match_the_script():
    assert _gs_const("YEAR_MOVE_HINT").strip("'") == layout.YEAR_MOVE_HINT
    assert re.findall(r"'([^']+)'", _gs_const("YEAR_MOVES")) == layout.YEAR_MOVES


def test_trend_c1_is_a_dropdown_and_hint_short():
    rule = next(r["setDataValidation"]["rule"] for r in layout.validation_requests()
                if "setDataValidation" in r and r["setDataValidation"]["range"] == layout.a1_to_grid("추이!C1"))
    assert [x["userEnteredValue"] for x in rule["condition"]["values"]] == layout.YEAR_MOVES and rule["strict"] is False
    assert views.trend_values()[0]["values"][0][2] == layout.YEAR_MOVE_HINT and len(layout.YEAR_MOVE_HINT) <= 16


def test_live_migration_rewrites_hint_and_reapplies_dropdown():
    structure, values, _v = mc.plan(_state())
    assert {e["range"]: e["values"] for e in values}["추이!C1"] == [[layout.YEAR_MOVE_HINT]]
    assert layout.a1_to_grid("추이!C1") in [r["setDataValidation"]["range"] for r in structure if "setDataValidation" in r]
