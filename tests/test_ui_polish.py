import couple
import invest
import layout
import migrate_couple as mc
import styling


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def _cells(reqs, a1):
    g = layout.a1_to_grid(a1)
    return [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs
            if "repeatCell" in r and r["repeatCell"]["range"] == g]


def _width(sheet, col):
    return styling.COL_WIDTHS[sheet][col]


def test_invest_title_and_kpi_stand_out():
    reqs = invest.polish_requests()
    assert _cells(reqs, "투자!A1")[0]["textFormat"]["fontSize"] == styling.TITLE_FONT
    kpi = _cells(reqs, "투자!A4:F4")[0]
    assert kpi["textFormat"]["fontSize"] == styling.KPI_FONT and kpi["horizontalAlignment"] == "CENTER"


def test_invest_total_rows_and_sections_look_different():
    reqs = invest.polish_requests()
    for a1 in ("투자!A9:G9", "투자!A12:G12"):
        fmt = _cells(reqs, a1)[0]
        assert fmt["textFormat"]["bold"] is True and fmt["backgroundColor"] == styling.LABEL_BG
    for a1 in ("투자!A15:D15", "투자!G15:I15"):
        assert _cells(reqs, a1)[0]["backgroundColor"] == styling.VIEW_TAB  # 한눈에 표 머리글
    assert _cells(reqs, "투자!A14")[0]["textFormat"]["bold"] is True


def test_invest_status_is_short_enough_for_its_column():
    row = _by_range(invest.invest_values())["투자!A8:G8"][0]
    assert 'IF(한투원본!$B$2="키없음","키 없음",' in row[6]
    assert 'LEFT(한투원본!$D$2,30)' in row[6]  # 오류 메시지는 30자까지만


def test_saving_details_use_wide_columns_and_chart_note_present():
    vals = _by_range(invest.invest_values())
    assert vals["투자!G15:I15"] == [["청약 계좌", "소유자", "잔액"]]
    assert vals["투자!G16"][0][0].startswith('=IFERROR(FILTER({자산!A2:A50,자산!I2:I50,자산!E2:E50}')
    assert "투자!F15:H15" not in vals and "투자!F16" not in vals
    assert "6시" in vals["투자!A21"][0][0]


def test_couple_labels_fit():
    vals = _by_range(couple.couple_values())
    assert vals["부부!A1:C2"][0][2] == "◀ 월 이동 ▶"
    assert vals["부부!A12:B13"][1][0] == "미지정 결제 건수"
    assert _width("부부", 4) >= 110  # 남은 돈·사용률 열


def test_networth_axis_uses_text_month_helper():
    vals = _by_range(couple.couple_values())
    assert vals["자산기록!A1:D1"] == [["월", "순자산", "자산(부채 제외)", "카드·대출 잔액"]]
    assert vals["자산기록!E1:E2"] == [["그래프 월"], ['=ARRAYFORMULA(IF(A2:A="","",TEXT(A2:A,"0000-00")))']]
    spec = couple.networth_chart()["addChart"]["chart"]["spec"]
    assert spec["basicChart"]["domains"][0]["domain"]["sourceRange"]["sources"][0]["startColumnIndex"] == 4


def test_dashboard_asset_status_columns_wide_enough_for_big_numbers():
    assert min(_width("대시보드", c) for c in (9, 10, 11)) >= 175  # J·K·L: 139,980,087 같은 KPI 글씨


def test_asset_owner_column_left_aligned():
    assert _cells(styling.style_requests(), "자산!I2:I50")[0]["horizontalAlignment"] == "LEFT"


LIVE_NET = {"chartId": 31, "spec": {"title": "월별 순자산", "basicChart": {"chartType": "LINE", "domains": [{"domain": {
    "sourceRange": {"sources": [{"sheetId": 1800, "startRowIndex": 0, "endRowIndex": 200,
                                 "startColumnIndex": 0, "endColumnIndex": 1}]}}}], "series": []}}}


def test_migration_applies_polish_every_run_and_fixes_networth_axis_once():
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                     settings=[], budgets_empty=False, invest_charts=2, networth_chart=LIVE_NET)
    structure, _v, _vi = mc.plan(state)
    assert _cells(structure, "투자!A4:F4") and _cells(structure, "자산!I2:I50")
    widths = {(r["updateDimensionProperties"]["range"]["sheetId"], r["updateDimensionProperties"]["range"]["startIndex"])
              for r in structure if "updateDimensionProperties" in r
              and r["updateDimensionProperties"]["range"]["dimension"] == "COLUMNS"}
    assert {(400, 9), (400, 10), (400, 11), (1900, 6), (1700, 4), (1800, 2)} <= widths
    assert (400, 0) not in widths  # 운영 대시보드의 다른 열 너비는 건드리지 않음
    fix = [r for r in structure if "updateChartSpec" in r and r["updateChartSpec"]["chartId"] == 31]
    assert fix[0]["updateChartSpec"]["spec"]["basicChart"]["domains"][0]["domain"]["sourceRange"]["sources"][0][
        "startColumnIndex"] == 4
    done = {"chartId": 31, "spec": fix[0]["updateChartSpec"]["spec"]}
    assert mc.networth_axis_fix(done) == []


def test_migration_clears_old_saving_list_cells():
    # 운영에서 실제로 겪음: 목록을 F→G로 옮긴 뒤 남은 옛 F16 수식이 새 G16 펼침과 겹쳐 #REF!
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                     settings=[], budgets_empty=False, invest_charts=2)
    _s, values, _vi = mc.plan(state)
    assert _by_range(values)["투자!F15:F16"] == [[""], [""]]


def test_invest_kpi_columns_fit_big_numbers():
    # 운영 PDF에서 '100,715,301|05,517,719'처럼 붙어 잘림 — KPI 글씨(20)로 9자리 금액이 들어갈 너비
    w = styling.COL_WIDTHS["투자"]
    assert w[0] >= 170 and min(w[1], w[2]) >= 165 and min(w[3], w[4]) >= 140 and w[5] >= 150
