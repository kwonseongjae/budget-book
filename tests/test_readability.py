import build_budget
import styling
import layout
import migrate_couple as mc
import readability


def _fmts(reqs, a1):
    g = layout.a1_to_grid(a1)
    return [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs
            if "repeatCell" in r and r["repeatCell"]["range"] == g]


def _pattern(reqs, a1):
    return [f["numberFormat"]["pattern"] for f in _fmts(reqs, a1) if "numberFormat" in f]


def test_zero_shows_dash_and_negative_blue_on_money_cells():
    reqs = readability.requests(60)
    assert readability.AMOUNT == '#,##0;[Blue]-#,##0;"-"'  # 손실(음수)은 파랑
    for a1 in ("대시보드!B61:C91", "대시보드!G61:G91", "대시보드!J61:K91", "대시보드!B97:B101",
               "부부!C16:D55", "부부!B5:D7", "자산!C2:E50", "자산기록!B2:D200"):
        assert _pattern(reqs, a1) == [readability.AMOUNT], a1


def test_live_dashboard_table_offset():
    # 운영 대시보드는 표 머리글이 19행 — 코드(60행)와 다르게 같은 열을 칠해야 한다
    assert _pattern(readability.requests(19), "대시보드!B20:C50") == [readability.AMOUNT]


def test_chart_helper_columns_are_faint():
    reqs = readability.requests(60)
    for a1 in ("대시보드!M61:M91", "대시보드!D97:E100", "대시보드!F106:F125", "대시보드!K106:K125", "자산기록!E2:E200"):
        tf = _fmts(reqs, a1)[0]["textFormat"]
        assert tf["foregroundColor"] == readability.FAINT and tf["fontSize"] < styling.BASE_FONT, a1


def test_couple_person_columns_have_own_header_colors():
    reqs = readability.requests(60)
    colors = [_fmts(reqs, a1)[0]["backgroundColor"] for a1 in ("부부!C15:E15", "부부!F15:H15", "부부!I15:K15")]
    assert len({str(c) for c in colors}) == 3


def test_wired_into_new_sheet_and_live_migration():
    assert any(r in build_budget.visual_requests() for r in readability.requests(60))
    pie = {"chartId": 1, "spec": {"pieChart": {"legendPosition": "LABELED_LEGEND",
           "series": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 50,
                                                    "startColumnIndex": 1, "endColumnIndex": 2}]}},
           "domain": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 50,
                                                    "startColumnIndex": 12, "endColumnIndex": 13}]}}}}}
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                     settings=[], budgets_empty=False, invest_charts=2, pie=pie)
    structure, _v, _vi = mc.plan(state)
    assert _pattern(structure, "대시보드!B20:C50") == [readability.AMOUNT]
    assert not _fmts(structure, "대시보드!B61:C91")  # 운영엔 코드 배치 칸을 칠하지 않음
