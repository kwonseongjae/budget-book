"""시골쥐 자산관리표 화면과 같게 (2026-10-14 2차): 글꼴·크기·행 높이·숫자 카드·표 줄·그래프 색·이모지 없는 제목, 그래프가 표를 덮지 않기."""
import re

import breakdown
import build_budget
import chart_fit
import couple
import invest
import layout
import migrate_couple as mc
import styling
import theme

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿⭐]")


def _live(**kw):
    pie = {"chartId": 1, "spec": {"pieChart": {"legendPosition": "LABELED_LEGEND",
           "series": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 1, "endColumnIndex": 2}]}},
           "domain": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 12, "endColumnIndex": 13}]}}}}}
    base = dict(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                budgets_empty=False, invest_charts=2, pie=pie, dash_rows=96, dash_chart_titles=frozenset(),
                dash_base=46, trend_head=14)
    return mc.State(**{**base, **kw})


def _last(reqs, a1):
    g = layout.a1_to_grid(a1)
    fm = [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs if "repeatCell" in r and r["repeatCell"]["range"] == g]
    return fm[-1] if fm else None


def test_sizes_match_sigol():
    assert (styling.BASE_FONT, styling.HEADER_FONT, styling.TITLE_FONT, styling.KPI_FONT) == (13, 13, 17, 15)  # 시골쥐 크기 + 3
    assert styling.ROW_PX == 21 and styling.FONT_FAMILY == "Nanum Gothic"


def test_faint_helper_text_also_bigger():
    import readability
    f = readability._faint("대시보드!A1")["repeatCell"]["cell"]["userEnteredFormat"]["textFormat"]
    assert f["fontSize"] == styling.BASE_FONT - 1 == 12


def test_spreadsheet_theme_font_and_blue_chart_palette():
    req = theme.spreadsheet_theme()["updateSpreadsheetProperties"]["properties"]["spreadsheetTheme"]
    assert req["primaryFontFamily"] == "Nanum Gothic"
    accents = [c["color"]["rgbColor"] for c in req["themeColors"] if c["colorType"].startswith("ACCENT")]
    assert len(accents) == 6 and all(c["blue"] > c["red"] for c in accents)
    assert theme.spreadsheet_theme() in build_budget.visual_requests()


def test_live_reapplies_fonts_rows_and_theme_every_run():
    structure, _v, _vi = mc.plan(_live())
    assert theme.spreadsheet_theme() in structure
    dash = layout.SHEET_ID["대시보드"]
    whole = [r["repeatCell"]["cell"]["userEnteredFormat"] for r in structure if "repeatCell" in r
             and r["repeatCell"]["range"] == {"sheetId": dash}]
    assert any(f.get("textFormat", {}).get("fontSize") == 13 for f in whole)
    rows = [r["updateDimensionProperties"] for r in structure if "updateDimensionProperties" in r
            and r["updateDimensionProperties"]["range"] == {"sheetId": dash, "dimension": "ROWS", "startIndex": 0}]
    assert rows and rows[0]["properties"]["pixelSize"] == 21
    assert _last(structure, "대시보드!D1:H1")["textFormat"]["fontSize"] == styling.TITLE_FONT


def test_kpi_labels_are_navy_bars_and_totals_gray():
    structure, _v, _vi = mc.plan(_live())
    for a1 in ("대시보드!A5:I5", "대시보드!J5:M5", "자산현황!A4:F4"):
        assert _last(structure, a1)["backgroundColor"] == styling.NAVY_HEAD, a1
    assert not any(_last(structure, a1) and _last(structure, a1).get("backgroundColor") in (styling.INC_BG, styling.SAVE_BG)
                   for a1 in ("대시보드!A5", "대시보드!G5"))
    assert styling.LABEL_BG == {"red": 242 / 255, "green": 242 / 255, "blue": 242 / 255}


def test_table_bodies_get_thin_gray_lines():
    borders = [r["updateBorders"] for r in theme.requests(19, 46, 14) if "updateBorders" in r]
    hit = [b for b in borders if b["range"] == layout.a1_to_grid("자산현황!A13:F24")]
    assert hit and hit[0]["innerHorizontal"]["color"] == theme.LINE and hit[0]["innerHorizontal"]["style"] == "SOLID"


def test_titles_have_no_emoji_and_old_title_still_found():
    texts = [c for e in build_budget.value_data("a@b.com") for row in e["values"] for c in row if isinstance(c, str)]
    titles = [t for t in texts if not t.startswith("=")]
    assert not [t for t in titles if EMOJI.match(t)]
    assert breakdown.find_base([[""]] * 40 + [["💰 수입 대비 고정비·변동비"]]) == 41
    assert breakdown.find_base([[""]] * 40 + [[breakdown.TITLE]]) == 41


def test_status_charts_sit_right_of_tables():
    sid = layout.SHEET_ID["자산현황"]
    cols = next(c for t, s, _r, c, _h in layout.SHEETS if s == sid)
    assert cols >= 16
    for spot in mc.chart_spots().values():
        if spot[0] == sid:
            assert spot[2] >= 11  # L열부터: 표(A~I) 오른쪽


def test_live_moves_misplaced_charts():
    charts = ({"chartId": 7, "title": "고정비 구성 (항목별)", "sheetId": 400, "row": 71, "col": 0},
              {"chartId": 8, "title": "월별 순자산", "sheetId": layout.SHEET_ID["자산기록"], "row": 0, "col": 5},
              {"chartId": 9, "title": "최근 30일 합산 평가금액", "sheetId": layout.SHEET_ID["투자"], "row": 38, "col": 0},
              {"chartId": 10, "title": "자산 분포", "sheetId": layout.SHEET_ID["자산현황"], "row": 25, "col": 4})
    moves = {r["updateEmbeddedObjectPosition"]["objectId"]: r["updateEmbeddedObjectPosition"]["newPosition"]["overlayPosition"]["anchorCell"]
             for r in mc.chart_moves(charts, 46)}
    assert moves[7]["rowIndex"] == breakdown.rows(46)["chart"]
    assert moves[8]["rowIndex"] >= 3
    assert moves[9]["rowIndex"] == invest.CHART_ROWS[0] and moves[9]["columnIndex"] >= 4
    assert moves[10]["columnIndex"] >= 11
    assert not mc.chart_moves([{**charts[0], "row": breakdown.rows(46)["chart"]}], 46)


def test_status_tab_widened_live():
    structure, _v, _vi = mc.plan(_live(status_cols=11))
    add = [r["appendDimension"] for r in structure if "appendDimension" in r
           and r["appendDimension"]["sheetId"] == layout.SHEET_ID["자산현황"]]
    assert add and add[0]["length"] == 5  # 16열 (L~P 그래프 띠)
    s2, _v2, _vi2 = mc.plan(_live(status_cols=16))
    assert not any("appendDimension" in r and r["appendDimension"]["sheetId"] == layout.SHEET_ID["자산현황"] for r in s2)


def _grid():
    # 행 10개 × 21px, 열 6개 × 100px. 6행(index 5)부터 표 칸(A~C)
    return {"rows": [21] * 10, "cols": [100] * 6, "filled": {(r, c) for r in range(5, 10) for c in range(3)}}


def test_fit_shrinks_chart_above_table():
    chart = {"chartId": 1, "title": "t", "row": 0, "col": 0, "dx": 0, "dy": 0, "w": 250, "h": 230}
    g = {**_grid(), "rows": [40] * 10}  # 표 시작 y=200 → 높이 230은 표를 덮음 → 194
    reqs, problems = chart_fit.plan(g, [chart])
    assert not problems
    pos = reqs[0]["updateEmbeddedObjectPosition"]["newPosition"]["overlayPosition"]
    assert pos["heightPixels"] == 200 - chart_fit.GAP and reqs[0]["updateEmbeddedObjectPosition"]["fields"] == "heightPixels,widthPixels"


def test_fit_leaves_clear_chart_and_reports_buried_one():
    clear = {"chartId": 1, "title": "ok", "row": 0, "col": 3, "dx": 0, "dy": 0, "w": 250, "h": 200}
    buried = {"chartId": 2, "title": "bad", "row": 6, "col": 0, "dx": 0, "dy": 0, "w": 250, "h": 60}
    reqs, problems = chart_fit.plan(_grid(), [clear, buried])
    assert not reqs and problems == ["bad"]


def test_fit_avoids_other_charts():
    a = {"chartId": 1, "title": "a", "row": 0, "col": 3, "dx": 0, "dy": 0, "w": 250, "h": 400}
    b = {"chartId": 2, "title": "b", "row": 12, "col": 3, "dx": 0, "dy": 0, "w": 250, "h": 100}
    g = {"rows": [21] * 40, "cols": [100] * 8, "filled": set()}
    reqs, problems = chart_fit.plan(g, [a, b])
    assert not problems and reqs[0]["updateEmbeddedObjectPosition"]["objectId"] == 1
    assert reqs[0]["updateEmbeddedObjectPosition"]["newPosition"]["overlayPosition"]["heightPixels"] == 12 * 21 - chart_fit.GAP


def test_networth_chart_clear_of_badge():
    anchor = couple.networth_chart()["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]
    assert anchor["rowIndex"] >= 3
