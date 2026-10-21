"""최종 검토에서 나온 문제를 고정하는 시험 (2026-10-14)."""
import align
import asset_status
import layout
import migrate_couple as mc
import readability
import styling
import theme


def _last(reqs, a1):
    g = layout.a1_to_grid(a1)
    fm = [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs
          if "repeatCell" in r and r["repeatCell"]["range"] == g]
    return fm[-1] if fm else None


def _live(titles=None):
    pie = {"chartId": 1, "spec": {"pieChart": {"legendPosition": "LABELED_LEGEND",
           "series": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 1, "endColumnIndex": 2}]}},
           "domain": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 12, "endColumnIndex": 13}]}}}}}
    return mc.State(titles=titles or {t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12,
                    networth_charts=1, settings=[], budgets_empty=False, invest_charts=2, pie=pie, dash_rows=96,
                    dash_chart_titles=frozenset(), dash_base=46, trend_head=14)


def test_badges_not_hidden_or_merged():
    # 자산현황 K열은 숨김, 부부 E1:K1은 제목 병합 → 배지는 그 밖에
    assert theme.BADGES[layout.ASSET_STATUS][:2] == ("I1", "I2")
    assert theme.BADGES[layout.COUPLE][:2] == ("J2", "K2")


def test_new_status_tab_gets_base_styling_and_all_tabs_get_colors_live():
    without = {t for t, *_ in layout.SHEETS} - {"자산현황"}
    structure, _v, _vi = mc.plan(_live(without))
    sid = layout.SHEET_ID["자산현황"]
    dims = [r["updateDimensionProperties"] for r in structure if "updateDimensionProperties" in r
            and r["updateDimensionProperties"]["range"]["sheetId"] == sid]
    assert any(d["range"]["dimension"] == "ROWS" and d["properties"].get("pixelSize") == styling.ROW_PX for d in dims)
    assert any(d["range"]["dimension"] == "COLUMNS" and d["properties"].get("pixelSize") == styling.COL_WIDTHS["자산현황"][0] for d in dims)
    s2, _v2, _vi2 = mc.plan(_live())
    colors = {r["updateSheetProperties"]["properties"]["sheetId"]: r["updateSheetProperties"]["properties"]["tabColor"]
              for r in s2 if "updateSheetProperties" in r and "tabColor" in r["updateSheetProperties"]["properties"]}
    assert colors[layout.SHEET_ID["대시보드"]] == styling.NAVY_HEAD and colors[layout.SHEET_ID["내역"]] == styling.INPUT_TAB_COLOR


def test_status_charts_clear_of_debt_table():
    # 행 30px 기준: 그래프 아래 끝이 부채 머리글(35행, index 34) 위
    for r in asset_status.chart_requests():
        pos = r["addChart"]["chart"]["position"]["overlayPosition"]
        bottom = pos["anchorCell"]["rowIndex"] + pos["heightPixels"] / 30
        assert bottom <= 34 or pos["anchorCell"]["columnIndex"] >= 9, r["addChart"]["chart"]["spec"]["title"]


def test_status_tables_navy_heads_white_bodies_aligned():
    reqs = theme.requests(19, 46, 14)
    for a1 in ("자산현황!A12:F12", "자산현황!A27:C27", "자산현황!A35:I35", "자산현황!A33:C33", "자산현황!A46:I46"):
        assert _last(reqs, a1)["backgroundColor"] == styling.NAVY_HEAD, a1
    for a1 in ("자산현황!A13:F24", "자산현황!A28:C32"):
        assert _last(reqs, a1)["backgroundColor"] == styling.WHITE, a1
    h = lambda a1: _last(align.requests(), a1)["horizontalAlignment"]
    assert h("자산현황!B13:E24") == "RIGHT"


def test_backgrounds_wiped_by_page_are_restored_live():
    structure, _v, _vi = mc.plan(_live())
    assert _last(structure, "부부!A9:K9")["backgroundColor"] == styling.NAVY_HEAD  # 정산 구역 띠
    assert _last(structure, "주식_신랑!G1")["backgroundColor"] == styling.CHECK_BG
    assert _last(structure, "메리츠_신랑!A2:A3")["backgroundColor"] == styling.LABEL_BG


def test_no_stray_navy_in_invest_gap_and_pink_matches_inputs():
    assert ("투자!F15:H15", styling.NAVY_HEAD) not in styling.HEADERS and ("투자!G15:I15", styling.NAVY_HEAD) in styling.HEADERS
    assert "투자!H7:I12" not in theme.INPUTS and {"투자!H7:I8", "투자!H10:I11", "투자!H1", "주식_신랑!H1"} <= set(theme.INPUTS)
    assert "설정!A2:E60" not in theme.INPUTS and {"설정!A2:B60", "설정!D2:E60"} <= set(theme.INPUTS)


def test_goal_kpi_matches_neighbours_and_bad_deadline_is_blank():
    fm = {tuple(sorted(r["repeatCell"]["range"].items())): r["repeatCell"]["cell"]["userEnteredFormat"]
          for r in styling.asset_status_style()}
    assert tuple(sorted(layout.a1_to_grid("대시보드!J6:M6").items())) in fm
    assert asset_status.months_left("x").startswith("IFERROR(")


def test_person_headers_are_navy_shades():
    assert len({str(c) for c in readability.PERSON_BG}) == 3
    assert all(c["blue"] > c["red"] for c in readability.PERSON_BG)  # 남색 계열
