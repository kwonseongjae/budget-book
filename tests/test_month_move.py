"""대시보드·부부 C1 '월 이동' 드롭다운 (2026-10-18 사용성 점검 A12). 문구는 Apps Script(logic.gs)와 같아야 한다."""
import re
from pathlib import Path

import couple
import formulas
import guide
import layout
import migrate_couple as mc

ALL = {t for t, *_ in layout.SHEETS}
GS = (Path(__file__).parent.parent / "apps-script" / "logic.gs").read_text(encoding="utf-8")


def _gs_const(name):
    return re.search(rf"var {name} = (.+?);", GS).group(1)


def test_texts_match_the_script():
    assert _gs_const("MONTH_MOVE_HINT").strip("'") == layout.MONTH_MOVE_HINT
    assert re.findall(r"'([^']+)'", _gs_const("MONTH_MOVES")) == layout.MONTH_MOVES
    assert re.findall(r"'([^']+)'", _gs_const("MONTH_SHEETS")) == [layout.DASH, layout.COUPLE]


def test_c1_dropdown_on_dashboard_and_couple():
    rules = {(r["setDataValidation"]["range"]["sheetId"], r["setDataValidation"]["range"]["startColumnIndex"],
              r["setDataValidation"]["range"]["startRowIndex"]): r["setDataValidation"]["rule"]
             for r in layout.validation_requests() if "setDataValidation" in r}
    for tab in (layout.DASH, layout.COUPLE):
        rule = rules[(layout.SHEET_ID[tab], 2, 0)]
        assert rule["condition"]["type"] == "ONE_OF_LIST"
        assert [x["userEnteredValue"] for x in rule["condition"]["values"]] == layout.MONTH_MOVES
        assert rule["strict"] is False  # 안내 문구('◀ 월 이동 ▶')가 칸에 있어도 되게


def test_hint_text_replaced_everywhere():
    assert layout.MONTH_MOVE_HINT == "◀ 월 이동 ▶"
    assert formulas.dashboard_values()[0]["values"][0][2] == layout.MONTH_MOVE_HINT
    assert couple.couple_values()[0]["values"][0][2] == layout.MONTH_MOVE_HINT
    state = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_base=46)
    structure, values, _vi = mc.plan(state)
    assert {e["range"]: e["values"] for e in values}["대시보드!C1"] == [[layout.MONTH_MOVE_HINT]]


def test_live_migration_reapplies_the_dropdown_each_run():
    state = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_base=46)
    ranges = [r["setDataValidation"]["range"] for r in mc.plan(state)[0] if "setDataValidation" in r]
    for tab in (layout.DASH, layout.COUPLE):
        assert layout.a1_to_grid(f"{tab}!C1") in ranges


def test_guide_explains_month_moving():
    text = " ".join(f"{a} {b}" for _k, a, b in guide.CONTENT)
    assert "◀ 이전 달" in text and "다음 달 ▶" in text
