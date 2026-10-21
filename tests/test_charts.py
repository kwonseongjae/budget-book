import charts


def _specs():
    return [r["addChart"]["chart"]["spec"] for r in charts.chart_requests()]


def test_five_charts_with_expected_titles():
    assert [s["title"] for s in _specs()] == [
        "카테고리별 지출", "예산 대비 지출", "사용자별 지출", "월별 수입·지출·잔액", "연도별 수입·지출·잔액"]


def test_donut_has_hole():
    assert _specs()[0]["pieChart"]["pieHole"] == 0.5


def test_series_type_only_on_combo():
    combo = _specs()[3]["basicChart"]
    assert combo["chartType"] == "COMBO"
    assert [s["type"] for s in combo["series"]] == ["COLUMN", "COLUMN", "LINE"]
    column = _specs()[1]["basicChart"]
    assert all("type" not in s for s in column["series"])


def test_charts_stacked_vertically_for_phone():
    anchors = [r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]
               for r in charts.chart_requests()]
    assert all(a["columnIndex"] == 0 for a in anchors)


def test_budget_over_100_is_red_and_first():
    rules = [r["addConditionalFormatRule"] for r in charts.conditional_requests()]
    first = rules[0]
    assert first["index"] == 0
    assert first["rule"]["booleanRule"]["condition"]["values"] == [{"userEnteredValue": "1"}]
    assert first["rule"]["booleanRule"]["format"]["backgroundColor"] == charts.RED


def test_category_pie_labels_show_percent_next_to_slices():
    import formulas
    pie = [r["addChart"]["chart"]["spec"] for r in charts.chart_requests() if "pieChart" in r["addChart"]["chart"]["spec"]][0]
    assert pie["pieChart"]["legendPosition"] == "LABELED_LEGEND"
    assert pie["pieChart"]["domain"] == charts._src("대시보드!M61:M91")
    assert pie["pieChart"]["series"] == charts._src("대시보드!B61:B91")
    vals = {e["range"]: e["values"] for e in formulas.dashboard_values()}
    f = vals["대시보드!M60:M61"][1][0]
    assert f == ('=ARRAYFORMULA(IF((A61:A91="")+(B61:B91<=0),"",'
                 'A61:A91&" "&TEXT(B61:B91/SUM(B61:B91),"0.0%")))')
