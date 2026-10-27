"""투자기록 14열·계좌별 기록 탭 (다증권사 B단계)."""
import layout
import migrate_couple as mc

ALL = {t for t, *_ in layout.SHEETS}


def _state(titles=ALL, grid=None):
    return mc.State(titles=set(titles), settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                    invest_charts=2, dash_rows=200, dash_base=46, grid=grid or {})


def test_log_has_14_columns_and_detail_tab_is_hidden_internal():
    props = {t: (sid, rows, cols, hidden) for t, sid, rows, cols, hidden in layout.SHEETS}
    assert props[layout.INVEST_LOG][2] == 14 and props[layout.BROKER_ACCTS][2] == 12
    assert props[layout.INVEST_LOG_DETAIL] == (2830, 5000, 4, True)


def test_headers_for_new_log_columns_and_detail_tab():
    import invest
    assert invest.LOG_HEAD[-2:] == ["기타 평가", "기타 원금"] and len(invest.LOG_HEAD) == 14
    ranges = {e["range"]: e["values"] for e in mc.plan(_state())[1]}
    assert ranges["투자기록_계좌!A1:D1"] == [["날짜", "계좌", "평가", "원금"]]
    assert ranges[f"{layout.INVEST_LOG}!A1:N1"][0][-2:] == ["기타 평가", "기타 원금"]


def test_live_tabs_grow_to_new_widths_once_and_detail_tab_is_added():
    grid = {layout.SHEET_ID[layout.INVEST_LOG]: (1000, 12), layout.SHEET_ID[layout.BROKER_ACCTS]: (40, 9)}
    st = _state(ALL - {layout.INVEST_LOG_DETAIL}, grid)
    structure = mc.plan(st)[0]
    grow = {r["appendDimension"]["sheetId"]: r["appendDimension"]["length"] for r in structure if "appendDimension" in r}
    assert grow[layout.SHEET_ID[layout.INVEST_LOG]] == 2 and grow[layout.SHEET_ID[layout.BROKER_ACCTS]] == 3
    assert layout.INVEST_LOG_DETAIL in {r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r}
    done = {layout.SHEET_ID[layout.INVEST_LOG]: (1000, 14), layout.SHEET_ID[layout.BROKER_ACCTS]: (40, 12)}
    again = {r["appendDimension"]["sheetId"] for r in mc.plan(_state(grid=done))[0] if "appendDimension" in r}
    assert layout.SHEET_ID[layout.INVEST_LOG] not in again and layout.SHEET_ID[layout.BROKER_ACCTS] not in again
