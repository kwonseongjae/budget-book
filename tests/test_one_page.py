"""모든 탭을 가로 스크롤 없이 한 화면(1920px 모니터 → 탭 폭 1,650px)에 (2026-10-14 사용자 요청)."""
import asset_status
import category_bars
import chart_fit
import fit_dims
import layout
import migrate_couple as mc
import stock_sectors


def _cell(text, size=13, bold=False, number=False, align=None):
    fmt = {"textFormat": {"fontSize": size, "bold": bold}}
    if align:
        fmt["horizontalAlignment"] = align
    value = {"numberValue": 1} if number else {"stringValue": text}
    return {"formattedValue": text, "effectiveValue": value, "effectiveFormat": fmt}


def _tab(rows, widths, hidden=()):
    return {"sheetId": 7, "rows": rows, "widths": list(widths), "hidden": set(hidden), "skip": set()}


def _widths(reqs):
    return {r["updateDimensionProperties"]["range"]["startIndex"]: r["updateDimensionProperties"]["properties"]["pixelSize"]
            for r in reqs if "updateDimensionProperties" in r}


def test_target_width_for_1920_monitor():
    assert fit_dims.TARGET_W == 1650


def test_empty_visible_columns_become_thin_spacers():
    rows = [[_cell("가"), _cell(""), _cell("나")]]
    w = _widths(fit_dims.plan(_tab(rows, [100, 120, 100])))
    assert w[1] == fit_dims.SPACER_W


def test_too_wide_tab_wraps_text_columns_but_never_shrinks_numbers():
    long_name = _cell("아주 긴 종목 이름이 들어가는 칸입니다")   # 글자 → 줄바꿈하고 좁힘
    money = _cell("1,234,567,890", number=True)               # 숫자 → 그대로
    rows = [[long_name] + [money] * 12]
    reqs = fit_dims.plan(_tab(rows, [100] * 13))
    w = _widths(reqs)
    full = fit_dims.text_px("1,234,567,890", 13)
    assert all(w.get(c, 100) == full for c in range(1, 13))
    assert sum(w.values()) <= fit_dims.TARGET_W or w[0] == fit_dims.WRAP_MIN
    wraps = [r for r in reqs if "repeatCell" in r and r["repeatCell"]["cell"]["userEnteredFormat"].get("wrapStrategy") == "WRAP"]
    assert wraps and wraps[0]["repeatCell"]["range"]["startColumnIndex"] == 0


def test_hint_cells_skipped():
    skip = fit_dims.skip_cells(layout.SHEET_ID["대시보드"], [])
    assert (0, 2) in skip  # C1 '◀ 분홍 칸에서 월 선택' 안내문


def test_charts_kept_inside_target_width():
    g = {"rows": [21] * 40, "cols": [100] * 30, "filled": set()}
    chart = {"chartId": 1, "title": "t", "row": 0, "col": 12, "dx": 0, "dy": 0, "w": 600, "h": 200}
    reqs, problems = chart_fit.plan(g, [chart])
    assert not problems
    assert reqs[0]["updateEmbeddedObjectPosition"]["newPosition"]["overlayPosition"]["widthPixels"] == 1650 - 1200 - chart_fit.GAP


def test_stock_top10_panel_moved_under_sector_input_not_beside():
    pie = stock_sectors.chart_requests()[1]["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]
    assert pie["columnIndex"] == 12 and pie["rowIndex"] == 3  # 2026-10-15: 합산 원형 2개는 맨 위에 나란히
    vals = {e["range"]: e["values"] for e in stock_sectors.values()}
    assert f"주식투자!K{stock_sectors.TOP_FIRST}" in vals and "주식투자!P19" not in vals
    assert vals["주식투자!P18:R30"] == [[""] * 3] * 13  # 옛 자리 비우기


def test_status_horizontal_table_moved_to_bottom_left():
    vals = {e["range"]: e["values"] for e in asset_status.values()}
    assert vals["자산현황!A67:B67"] == [["구분", "=TRANSPOSE(A13:A24)"]]
    assert vals["자산현황!L17:X21"] == [[""] * 13] * 5  # 옛 자리 비우기
    assert next(r for t, _s, r, _c, _h in layout.SHEETS if t == "자산현황") >= 72


def test_short_monthly_target_header():
    vals = {e["range"]: e["values"] for e in category_bars.values(46)}
    head = vals[f"대시보드!A{category_bars.rows(46)['save_head']}:C{category_bars.rows(46)['save_head']}"][0]
    assert all(len(h) <= 8 for h in head)


def test_dashboard_title_rewritten_without_emoji():
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                     budgets_empty=False, invest_charts=2, dash_rows=200, dash_base=46)
    _s, values, _v = mc.plan(state)
    vals = {e["range"]: e["values"] for e in values}
    assert vals["대시보드!D1"] == [["우리집 가계부 — 이달의 살림"]]


def test_stock_detail_tabs_fit_by_short_time_and_hidden_foreign_price_columns():
    import meritz_style
    assert meritz_style.SHORT_TIME_FMT == "mm/dd hh:mm"
    structure, _v, _vi = mc.plan(mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12,
                                          networth_charts=1, settings=[], budgets_empty=False, invest_charts=2, dash_base=46))
    hide = {(g["sheetId"], i) for r in structure if "updateDimensionProperties" in r
            and r["updateDimensionProperties"]["properties"].get("hiddenByUser")
            for g in [r["updateDimensionProperties"]["range"]] for i in range(g["startIndex"], g.get("endIndex", g["startIndex"] + 1))}
    for s in layout.MERITZ_SLOTS:  # L·M = 평단가(외화)·현재가(외화)
        assert {(layout.SHEET_ID[s.stock], 11), (layout.SHEET_ID[s.stock], 12)} <= hide
    fmts = [r["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]["pattern"] for r in structure if "repeatCell" in r
            and r["repeatCell"]["range"] == layout.a1_to_grid("주식_신랑!B3") and "numberFormat" in r["repeatCell"]["cell"]["userEnteredFormat"]]
    assert fmts and fmts[-1] == "mm/dd hh:mm"


def test_old_table_spots_lose_their_borders_and_hint_is_short():
    import theme
    cleared = [r["updateBorders"]["range"] for r in theme.requests(19, 46, 14)
               if "updateBorders" in r and r["updateBorders"].get("top", {}).get("style") == "NONE"]
    assert layout.a1_to_grid("주식투자!P18:R30") in cleared and layout.a1_to_grid("자산현황!L17:X21") in cleared
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                     budgets_empty=False, invest_charts=2, dash_rows=200, dash_base=46)
    hint = {e["range"]: e["values"] for e in mc.plan(state)[1]}["대시보드!C1"][0][0]
    assert len(hint) <= 16


def test_card_benefit_column_width_pinned():
    # 2026-10-15 사용자: 카드 탭 D열(혜택) 지금 칸 크기 고정 — 그래프·글자 맞춤이 바꾸지 않게
    sid = layout.SHEET_ID[layout.CARDS]
    rows = [[_cell("카드"), _cell(""), _cell(""), _cell("1% 적립"), _cell("연회비")]]  # 짧은 글 → 맞춤이면 좁아질 칸
    tab = {**_tab(rows, [100, 100, 100, 261, 100]), "sheetId": sid}
    reqs = fit_dims.plan(tab)
    assert 3 not in _widths(reqs)
    assert not [r for r in reqs if "repeatCell" in r and r["repeatCell"]["range"]["startColumnIndex"] == 3]
