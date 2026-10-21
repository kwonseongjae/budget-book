import align
import breakdown
import category_bars
import layout
import migrate_couple as mc
import readability
import styling


def _fmts(reqs, a1):
    g = layout.a1_to_grid(a1)
    return [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs
            if "repeatCell" in r and r["repeatCell"]["range"] == g]


def _red(c):
    return c["red"] > c["blue"]


def _blue(c):
    return c["blue"] > c["red"]


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_income_red_expense_blue_everywhere():
    assert _red(styling.INC_FG) and _red(styling.INC_BG) and _blue(styling.EXP_FG) and _blue(styling.EXP_BG)
    reqs = readability.requests(60)
    fg = lambda a1: _fmts(reqs, a1)[0]["textFormat"]["foregroundColor"]
    assert _red(fg("대시보드!A6")) and _blue(fg("대시보드!B6"))      # 수입·지출 큰 숫자
    assert _red(fg("부부!B5:B7")) and _blue(fg("부부!C5:C7"))


def test_loss_blue_profit_red_number_formats():
    assert "[Blue]" in readability.AMOUNT and "[Red]" not in readability.AMOUNT  # 음수(손실)는 파랑
    assert readability.PNL.startswith("[Red]") and "[Blue]" in readability.PNL
    reqs = readability.requests(60)
    pat = lambda a1: [f["numberFormat"]["pattern"] for f in _fmts(reqs, a1) if "numberFormat" in f]
    assert pat("대시보드!C6") == [readability.PNL] and pat("부부!E5:E7") == [readability.PNL]  # 잔액·남은 돈


def test_text_center_numbers_right_memo_left():
    reqs = align.requests()
    h = lambda a1: [f["horizontalAlignment"] for f in _fmts(reqs, a1)]
    assert h("내역!A2:D5000") == ["CENTER"] and h("내역!H2:H5000") == ["RIGHT"] and h("내역!J2:J5000") == ["LEFT"]
    assert h("반복!G2:G50") == ["RIGHT"] and h("자산!C2:E50") == ["RIGHT"] and h("자산기록!B2:D200") == ["RIGHT"]
    assert h("부부!B16:B55") == ["CENTER"] and h("부부!C16:K55") == ["RIGHT"]


def test_live_positions_follow_dashboard_and_trend():
    reqs = align.requests(dash_head=19, dash_base=41, trend_head=14)
    h = lambda a1: [f["horizontalAlignment"] for f in _fmts(reqs, a1)]
    assert h("대시보드!E20:F40") == ["CENTER"] and h("대시보드!D52:E71") == ["RIGHT"]
    assert h("추이!B15:D26") == ["RIGHT"]
    colors = readability.requests(19, base=41, trend_head=14)
    assert _red(_fmts(colors, "추이!B15:B26")[0]["textFormat"]["foregroundColor"])
    assert [f["numberFormat"]["pattern"] for f in _fmts(colors, "대시보드!B46") if "numberFormat" in f] == [readability.PNL]


def test_type_rules_recolored_in_place():
    old = {"ranges": [layout.a1_to_grid("내역!C2:C5000")], "booleanRule": {
        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": '=$C2="수입"'}]},
        "format": {"backgroundColor": {"blue": 0.99}, "textFormat": {"foregroundColor": {"blue": 0.7}, "bold": True}}}}
    fixes = mc.type_rule_fix([(100, 3, old)])
    rule = fixes[0]["updateConditionalFormatRule"]
    assert rule["sheetId"] == 100 and rule["index"] == 3
    assert rule["rule"]["booleanRule"]["format"]["backgroundColor"] == styling.INC_BG
    done = {**old, "booleanRule": {**old["booleanRule"], "format": fixes[0]["updateConditionalFormatRule"]["rule"]["booleanRule"]["format"]}}
    assert mc.type_rule_fix([(100, 3, done)]) == []
    other = {**old, "booleanRule": {**old["booleanRule"], "condition": {"type": "NUMBER_GREATER", "values": [{"userEnteredValue": "0"}]}}}
    assert mc.type_rule_fix([(100, 0, other)]) == []


def test_breakdown_follows_user_moved_block():
    vals = _by_range(breakdown.breakdown_values(41))
    assert vals["대시보드!A41"] == [["수입 대비 고정비·변동비"]] and "대시보드!A52" in vals and "대시보드!A95" not in vals
    assert vals["대시보드!A53:K71"] == [[""] * 11] * 19  # 펼침 자리에 남은 값(#REF! 원인) 지움
    assert "D52:D71/SUM(D52:D71)" in vals["대시보드!E52"][0][0]
    src = breakdown.chart_requests(41)[1]["addChart"]["chart"]["spec"]["pieChart"]["series"]["sourceRange"]["sources"][0]
    assert src["startRowIndex"] == 51 and src["endRowIndex"] == 71


def test_migration_keeps_moved_block_and_repairs_charts():
    broken = {"chartId": 7, "spec": {"title": "수입 대비 고정비·변동비", "pieChart": {
        "legendPosition": "LABELED_LEGEND", "domain": {"sourceRange": {"sources": [layout.a1_to_grid("대시보드!D40:D40")]}},
        "series": {"sourceRange": {"sources": [layout.a1_to_grid("대시보드!E40:E40")]}}}}}
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                     settings=[], budgets_empty=False, invest_charts=2, dash_rows=91,
                     dash_chart_titles=frozenset(breakdown.CHART_TITLES + category_bars.CHART_TITLES), dash_base=41, dash_charts=(broken,))
    structure, values, visual = mc.plan(state)
    # 91행 → 구역(41) + 분류별 막대그래프까지 95줄 = 136행
    assert {"appendDimension": {"sheetId": 400, "dimension": "ROWS", "length": 45}} in structure
    assert "대시보드!A41" in _by_range(values) and "대시보드!A95" not in _by_range(values)
    fix = [r["updateChartSpec"] for r in structure + visual if "updateChartSpec" in r and r["updateChartSpec"]["chartId"] == 7]
    assert fix and fix[0]["spec"]["pieChart"]["series"]["sourceRange"]["sources"][0]["startRowIndex"] == 42
    assert not any("addChart" in r for r in visual)


def test_category_table_stops_above_moved_block():
    # 운영: 표 머리글 19 + 31줄 = 50행까지인데 구역이 41행에 올라옴 → 표 서식이 C43:C47(수입 대비 %)을 덮으면 0·1로 보임
    colors, aligns = readability.requests(19, base=41), align.requests(dash_head=19, dash_base=41)
    assert not _fmts(colors, "대시보드!B20:C50") and _fmts(colors, "대시보드!B20:C40")
    assert not _fmts(aligns, "대시보드!B20:D50") and _fmts(aligns, "대시보드!B20:D40")
