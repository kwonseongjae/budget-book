import build_budget
import layout
import meritz_style as mst
import styling


def _formats():
    return {tuple(sorted(r["repeatCell"]["range"].items())): r["repeatCell"]["cell"]["userEnteredFormat"]
            for r in mst.structure_requests() + mst.visual_requests() if "repeatCell" in r}


def _fmt(a1):
    return _formats()[tuple(sorted(layout.a1_to_grid(a1).items()))]


def test_refresh_checkbox_is_boolean():
    v = [r["setDataValidation"] for r in mst.structure_requests() if "setDataValidation" in r]
    rule = {"condition": {"type": "BOOLEAN"}, "strict": False, "showCustomUi": True}
    assert v == [{"range": layout.a1_to_grid(f"{s.stock}!H1"), "rule": rule} for s in layout.MERITZ_SLOTS]


def test_number_formats_for_money_percent_and_time():
    assert _fmt("메리츠원본!H8")["numberFormat"]["pattern"] == "yyyy-mm-dd hh:mm"
    assert _fmt("주식_신랑!B3")["numberFormat"]["pattern"] == "mm/dd hh:mm"  # 한 화면 폭 (2026-10-14)
    assert _fmt("주식_신랑!J16:J115")["numberFormat"]["type"] == "PERCENT"
    assert _fmt("주식_신랑!E16:I115")["numberFormat"]["pattern"] == "#,##0"
    assert _fmt("주식_신랑!D16:D115")["numberFormat"]["pattern"] == "#,##0.####"


def test_four_charts_on_meritz_tab_stacked():
    for s in layout.MERITZ_SLOTS:  # 계좌마다 자기 상세 탭에 4개
        charts = [r["addChart"]["chart"] for r in mst.chart_requests([s])]
        assert [c["spec"]["title"] for c in charts] == ["자산 구성", "국내·해외·기타", "종목별 평가금액", "종목별 수익률"]
        anchors = [c["position"]["overlayPosition"]["anchorCell"] for c in charts]
        assert all(a["sheetId"] == layout.SHEET_ID[s.meritz] and a["columnIndex"] == 0 for a in anchors)
    assert [a["rowIndex"] for a in anchors] == sorted(a["rowIndex"] for a in anchors)


def test_profit_red_loss_blue_only_on_stock_tabs():
    rules = [r["addConditionalFormatRule"]["rule"] for r in mst.conditional_requests()]
    sheets = {g["sheetId"] for r in rules for g in r["ranges"]}
    assert sheets == {1500, 1600, 1550, 1650}
    gt = [r for r in rules if r["booleanRule"]["condition"]["type"] == "NUMBER_GREATER"]
    lt = [r for r in rules if r["booleanRule"]["condition"]["type"] == "NUMBER_LESS"]
    assert gt and lt
    assert all(r["booleanRule"]["format"]["textFormat"]["foregroundColor"] == mst.RED_TEXT for r in gt)
    assert all(r["booleanRule"]["format"]["textFormat"]["foregroundColor"] == mst.BLUE_TEXT for r in lt)


def test_meritz_requests_included_in_build():
    assert any("addChart" in r and r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["sheetId"] == 1600
               for r in build_budget.visual_requests())
    assert any(r.get("setDataValidation", {}).get("range") == layout.a1_to_grid("주식_신랑!H1")
               for r in build_budget.structure_requests())


def test_widths_fit_kpi_and_time():
    w = styling.COL_WIDTHS
    for s in layout.MERITZ_SLOTS:
        assert min(w[s.stock][0], w[s.stock][1], w[s.stock][3]) >= 130
        assert w[s.meritz][4] >= 120 and w[s.meritz][5] == 30


def test_kpi_and_title_rows_tall():
    dims = [r["updateDimensionProperties"] for r in mst.visual_requests() if "updateDimensionProperties" in r]
    got = {(d["range"]["sheetId"], d["range"]["startIndex"]): d["properties"]["pixelSize"] for d in dims
           if d["range"]["dimension"] == "ROWS"}
    for sid in (1500, 1600):  # 시골쥐 크기: 기본 21px보다 조금 높게
        assert got[(sid, 0)] == styling.TITLE_ROW_PX > styling.ROW_PX and got[(sid, 5)] == styling.KPI_ROW_PX > styling.ROW_PX
