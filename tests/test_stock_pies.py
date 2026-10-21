"""주식투자: 합산 섹터별·종목별 원형을 맨 위에 나란히 + 사람별 원형 4개 (2026-10-15 사용자 요청)."""
import layout
import migrate_couple as mc
import stock_sectors as ss

SID = layout.SHEET_ID[layout.STOCKS]


def _pos(req):
    o = req["addChart"]["chart"]["position"]["overlayPosition"]
    return o["anchorCell"]["rowIndex"], o["anchorCell"]["columnIndex"]


def _src_col(req, key):
    spec = req["addChart"]["chart"]["spec"]["pieChart"]
    return spec[key]["sourceRange"]["sources"][0]["startColumnIndex"]


def test_combined_pies_side_by_side_at_top():
    reqs = ss.chart_requests()
    assert [r["addChart"]["chart"]["spec"]["title"] for r in reqs[:2]] == ["섹터별 보유 비율", "종목별 보유 비율"]
    (r1, c1), (r2, c2) = _pos(reqs[0]), _pos(reqs[1])
    assert r1 == r2 == 3 and (c1, c2) == (10, 12)


def test_sector_table_right_under_top_pies():
    assert ss.SEC_HEAD == 17  # 260px 원형(4행~, 21px 줄) 끝 바로 다음


def test_person_blocks_under_sector_table_then_sector_map():
    reqs = ss.chart_requests()[2:]
    titles = [r["addChart"]["chart"]["spec"]["title"] for r in reqs]
    assert titles == ["신랑 섹터별", "신랑 종목별", "신부 섹터별", "신부 종목별"]
    rows = [_pos(r)[0] for r in reqs]
    assert rows[0] == rows[1] and rows[2] == rows[3] and {_pos(r)[1] for r in reqs} == {10, 12}
    assert rows[0] > ss.SEC_LAST  # 비율표 아래
    assert ss.PERSON_HEADS[0] >= rows[0] + 13 and ss.PERSON_HEADS[1] >= rows[2] + 13  # 그래프 바로 아래 상위 표
    assert ss.PERSON_HEADS[0] + 12 <= rows[2] and ss.MAP_HEAD > ss.PERSON_HEADS[1] + 12  # 섹터 지정은 사람별 아래
    assert reqs[0]["addChart"]["chart"]["spec"]["hiddenDimensionStrategy"] == "SHOW_ALL" and _src_col(reqs[0], "domain") >= 20
    assert _src_col(reqs[1], "domain") == 10  # 종목별은 보이는 상위 표(K)


def test_person_tables_filter_by_owner():
    vals = {e["range"]: e["values"] for e in ss.values()}
    for (owner, col), head in zip(ss.PEOPLE, ss.PERSON_HEADS):
        assert f'"{owner}"' in vals[f"주식투자!{col}{ss.FIRST}"][0][0]
        top = vals[f"주식투자!K{head + 1}"][0][0]
        assert f'"{owner}"' in top and "ARRAYFORMULA" in top
        assert vals[f"주식투자!K{head}:M{head}"] == [[f"{owner} 종목", "평가금액", "비율"]]


def test_live_map_inputs_move_to_new_rows_once():
    col_kl = [[""]] * 35 + [["섹터 지정 — 티커마다 한 번 고르세요"], ["티커", "섹터"], ["MU", "반도체"], [660, "반도체"]]
    structure, values = ss.relocate(col_kl, (77,))
    assert values[0]["range"] == "주식투자!K4:N150" and all(c == "" for r in values[0]["values"] for c in r)
    vals = {e["range"]: e["values"] for e in values}
    assert vals[f"주식투자!K{ss.MAP_FIRST}:L{ss.MAP_FIRST + 1}"] == [["MU", "반도체"], [660, "반도체"]]
    assert {"deleteProtectedRange": {"protectedRangeId": 77}} in structure
    assert any("addProtectedRange" in r for r in structure)
    assert any("setDataValidation" in r and "rule" not in r["setDataValidation"] for r in structure)
    moved = [[""]] * (ss.MAP_HEAD - 2) + [["섹터 지정 — 티커마다 한 번 고르세요"]]
    assert ss.relocate(moved, (77,)) == ([], [])  # 이미 새 자리면 아무것도 안 함
    assert ss.relocate([], ()) == ([], [])


def test_live_tab_gets_helper_columns_hidden_and_missing_pies():
    titles = {t for t, *_ in layout.SHEETS}
    have = tuple({"chartId": i, "title": t, "sheetId": SID, "row": 3, "col": 10, "w": 440, "h": 270, "spec": None}
                 for i, t in enumerate(ss.CHART_TITLES[:2]))
    state = mc.State(titles=titles, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_base=46, charts=have, grid={SID: (150, 20)})
    structure, _values, visual = mc.plan(state)
    app = [r["appendDimension"] for r in structure if "appendDimension" in r and r["appendDimension"]["sheetId"] == SID]
    assert app == [{"sheetId": SID, "dimension": "COLUMNS", "length": 8}]
    hide = [r for r in structure if "updateDimensionProperties" in r and r["updateDimensionProperties"]["range"]["sheetId"] == SID
            and r["updateDimensionProperties"]["properties"].get("hiddenByUser")]
    assert hide and hide[0]["updateDimensionProperties"]["range"]["startIndex"] == 20
    added = [r["addChart"]["chart"]["spec"]["title"] for r in visual if "addChart" in r
             and r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["sheetId"] == SID]
    assert added == ["신랑 섹터별", "신랑 종목별", "신부 섹터별", "신부 종목별"]


def test_old_top_table_borders_cleared():
    import theme
    cleared = [r["updateBorders"]["range"] for r in theme.requests(19, 46, 14)
               if "updateBorders" in r and r["updateBorders"].get("top", {}).get("style") == "NONE"]
    assert layout.a1_to_grid("주식투자!K4:N150") in cleared


def test_live_plan_moves_map_appends_rows_and_keeps_bottom_table():
    titles = {t for t, *_ in layout.SHEETS}
    old = [[""]] * 35 + [[ss.MAP_TITLE_TEXT], ["티커", "섹터"], ["MU", "반도체"]]
    state = mc.State(titles=titles, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_base=46, grid={SID: (130, 28)}, stock_kl=tuple(map(tuple, old)), stock_protect=(5,))
    structure, values, _vi = mc.plan(state)
    assert {"appendDimension": {"sheetId": SID, "dimension": "ROWS", "length": 20}} in structure
    assert {"deleteProtectedRange": {"protectedRangeId": 5}} in structure
    ranges = [e["range"] for e in values]
    assert ranges.index("주식투자!K4:N150") < ranges.index(f"주식투자!K{ss.SEC_FIRST}")  # 비운 다음 새로 쓴다
    assert f"주식투자!K{ss.MAP_FIRST}:L{ss.MAP_FIRST}" in ranges and f"주식투자!K{ss.TOP_FIRST}" in ranges  # 늘린 줄까지 잘리지 않음
    again = state._replace(stock_kl=tuple(map(tuple, [[""]] * (ss.MAP_HEAD - 2) + [[ss.MAP_TITLE_TEXT]])), grid={SID: (150, 28)})
    s2, v2, _ = mc.plan(again)
    assert not any("deleteProtectedRange" in r for r in s2) and "주식투자!K4:N150" not in [e["range"] for e in v2]


def test_moved_area_text_reset_before_heads_are_painted():
    import theme
    reqs = theme.requests(19, 46, 14)
    grid = layout.a1_to_grid("주식투자!K4:N150")
    reset = next(i for i, r in enumerate(reqs) if "repeatCell" in r and r["repeatCell"]["range"] == grid
                 and r["repeatCell"]["cell"]["userEnteredFormat"].get("textFormat", {}).get("bold") is False)
    head = next(i for i, r in enumerate(reqs) if "repeatCell" in r
                and r["repeatCell"]["range"] == layout.a1_to_grid(f"주식투자!K{ss.SEC_HEAD}:N{ss.SEC_HEAD}"))
    assert reset < head


def test_person_tables_number_formats():
    pats = {(r["repeatCell"]["range"]["startRowIndex"], r["repeatCell"]["range"]["startColumnIndex"]):
            r["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]["pattern"]
            for r in ss.formats() if "repeatCell" in r and "numberFormat" in r["repeatCell"]["cell"]["userEnteredFormat"]}
    for h in ss.PERSON_HEADS:
        assert pats[(h, 11)] == "#,##0" and pats[(h, 12)] == "0.0%"  # 몸통 첫 줄(0부터 h) L·M
