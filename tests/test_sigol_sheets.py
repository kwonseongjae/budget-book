"""시골쥐 기능 시트 (2026-10-14 설계 docs/superpowers/specs/2026-10-14-sigol-sheets-design.md)."""
import asset_status
import build_budget
import cards
import category_bars
import fixed_costs
import layout
import migrate_couple as mc
import savings
import sigol_tabs
import stock_sectors
import theme

ALL = {t for t, *_ in layout.SHEETS}


def _state(**kw):
    base = dict(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                invest_charts=2, dash_rows=200, dash_chart_titles=frozenset(), dash_base=46, trend_head=14)
    return mc.State(**{**base, **kw})


def _cells(a1):
    """'탭!A5:C7' → {(행, 열)} (0부터)."""
    g = layout.a1_to_grid(a1)
    return {(g["sheetId"], r, c) for r in range(g["startRowIndex"], g["endRowIndex"])
            for c in range(g["startColumnIndex"], g["endColumnIndex"])}


def _written(values):
    out = set()
    for e in values:
        g = layout.a1_to_grid(e["range"])
        for i, row in enumerate(e["values"]):
            out |= {(g["sheetId"], g["startRowIndex"] + i, g["startColumnIndex"] + j) for j, _x in enumerate(row)}
    return out


def test_modules_never_write_their_own_input_cells():
    for m in sigol_tabs.MODULES:
        inputs = set().union(*[_cells(a1) for a1 in m.INPUTS]) if m.INPUTS else set()
        assert not _written(m.values()) & inputs, m.S


def test_inputs_pink_and_unprotected():
    reqs = theme.requests(19, 46, 14)
    pink = [r["repeatCell"]["range"] for r in reqs if "repeatCell" in r
            and r["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor") == theme.INPUT_BG]
    for m in sigol_tabs.MODULES:
        free = [g for p in sigol_tabs.protection([m.S]) for g in p["addProtectedRange"]["protectedRange"].get("unprotectedRanges", [])]
        for a1 in m.INPUTS:
            assert layout.a1_to_grid(a1) in pink and layout.a1_to_grid(a1) in free, a1


def test_fixed_costs_reads_recurring_and_sorts_by_settings_order():
    f = {e["range"]: e["values"] for e in fixed_costs.values()}["고정지출!A5"][0][0]
    assert "반복!A2:A50=TRUE" in f and '반복!D2:D50<>"수입"' in f and '반복!D2:D50<>"이체"' in f
    assert "MATCH(INDEX(d,,1),설정!$A$2:$A$60,0)" in f
    assert layout.RECUR_HEADERS[9:] == ["전체 금액", "금리", "만기", "비고", "통화"]


def test_cards_keyed_by_dropdown_and_expiry_warning():
    vals = {e["range"]: e["values"] for e in cards.values()}
    assert "REGEXEXTRACT(x" in vals["카드!B5"][0][0] and "FILTER(자산!$I$2:$I$50,자산!$A$2:$A$50=nm)" in vals["카드!B5"][0][0]
    assert '내역!$L:$L,계산!$C$2' in vals["카드!K5"][0][0]
    rules = [r for r in cards.formats() if "addConditionalFormatRule" in r]
    assert len(rules) == 2 and all("EDATE(TODAY(),2)" in str(r) for r in rules)


def test_stock_holdings_merge_both_accounts_and_loose_stock_assets():
    h = stock_sectors.holdings()
    assert "주식_신랑!B16:B115" in h and "주식_신부!B16:B115" in h and "(종목 미연동)" in h
    sector = {e["range"]: e["values"] for e in stock_sectors.values()}["주식투자!H5"][0][0]
    assert '"미지정"' in sector and "K91:K130" in sector


def test_top_stocks_never_uses_if_on_different_sized_arrays():
    # 시트의 IF는 배열 크기가 다르면 오류(IFERROR가 숨겨 빈 표가 됨) → 항상 VSTACK 후 FILTER
    top = {e["range"]: e["values"] for e in stock_sectors.values()}[f"주식투자!K{stock_sectors.TOP_FIRST}"][0][0]
    assert "IF(rest>0" not in top and "FILTER(o,INDEX(o,,2)>0)" in top


def test_no_excel_only_functions():
    # 구글 시트에 없는 함수(TAKE·DROP 등)는 #NAME? → IFERROR가 숨겨 빈 표가 된다 (2026-10-14 실제 발생)
    text = str(build_budget.value_data("a@b.com"))
    assert not any(f"{fn}(" in text for fn in ("TAKE", "DROP", "CHOOSECOLS", "TEXTSPLIT", "EXPAND"))


def test_savings_kinds_and_new_asset_kinds():
    assert savings.KINDS == {"N": ["통장", "계좌", "현금", "청약"], "O": ["연금"], "P": ["기타"]}
    kinds = [r for r in layout.validation_requests() if r["setDataValidation"]["range"] == layout.a1_to_grid("자산!B2:B50")]
    vals = [x["userEnteredValue"] for x in kinds[0]["setDataValidation"]["rule"]["condition"]["values"]]
    assert {"연금", "기타"} <= set(vals)


def test_status_quarters_and_kinds_table():
    vals = {e["range"]: e["values"] for e in asset_status.values()}
    q = vals["자산현황!A50:E54"]
    assert q[0][1] == "=SUM(B13:B15)" and q[3][1] == "=SUM(B22:B24)" and q[4][0] == "합계"
    kinds = vals["자산현황!A58:D64"]
    assert [r[0] for r in kinds] == ["주식", "저축·현금성", "청약", "연금", "기타", "부채", "합계"]
    assert kinds[0][1].startswith("=투자!B4+")


def test_category_bars_three_tables_below_breakdown():
    r = category_bars.rows(46)
    assert r["title"] == 89  # 고정비·변동비 그래프 바로 아래 (2026-10-14 간격 줄임)
    vals = {e["range"]: e["values"] for e in category_bars.values(46)}
    for kind, col, _c in category_bars.TABLES:
        assert f'내역!$C$2:$C="{kind}"' in vals[f"대시보드!{col}{r['first']}"][0][0]
    titles = [c["addChart"]["chart"]["spec"]["title"] for c in category_bars.chart_requests(46)]
    assert titles == ["분류별 수입", "분류별 지출", "분류별 저축"]


def test_live_adds_new_tabs_once_with_charts_and_recur_columns():
    s1, v1, vi1 = mc.plan(_state(titles=ALL - set(sigol_tabs.NAMES), recur_cols=9))
    added = [r["addSheet"]["properties"]["title"] for r in s1 if "addSheet" in r]
    assert added == sigol_tabs.NAMES
    assert {"appendDimension": {"sheetId": 800, "dimension": "COLUMNS", "length": 5}} in s1
    new_charts = {c["addChart"]["chart"]["spec"]["title"] for c in vi1 if "addChart" in c}
    assert {"고정지출 비율", "섹터별 보유 비율", "종목별 보유 비율", "연금 비율"} <= new_charts
    assert "반복!J1:N1" in {e["range"] for e in v1}
    s2, _v2, vi2 = mc.plan(_state(dash_chart_titles=frozenset({"수입 대비 고정비·변동비", "분류별 수입"})))
    assert not any("addSheet" in r for r in s2) and not any("addChart" in r for r in vi2)


def test_live_status_extras_added_once_and_old_pie_range_fixed():
    old_pie = {"title": "자산 분포", "pieChart": {"domain": {}, "series": {}}}
    charts = ({"chartId": 1, "title": "월별 저축률", "sheetId": 2100, "row": 1, "col": 11, "spec": {"title": "월별 저축률"}},
              {"chartId": 2, "title": "자산 분포", "sheetId": 2100, "row": 17, "col": 11, "spec": old_pie})
    _s, _v, vi = mc.plan(_state(charts=charts, dash_chart_titles=frozenset({"수입 대비 고정비·변동비", "분류별 수입"})))
    added = [c["addChart"]["chart"]["spec"]["title"] for c in vi if "addChart" in c
             and c["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["sheetId"] == 2100]
    assert added == asset_status.EXTRA_TITLES
    assert any("updateChartSpec" in r and r["updateChartSpec"]["chartId"] == 2 for r in vi)


def test_new_sheet_build_includes_everything():
    vals = {e["range"] for e in build_budget.value_data("a@b.com")}
    assert {"고정지출!A5", "카드!B5", "주식투자!A5", "저축·연금!B5", "대시보드!A138"} <= vals
    titles = {r["addChart"]["chart"]["spec"]["title"] for r in build_budget.visual_requests() if "addChart" in r}
    assert {"고정지출 비율", "섹터별 보유 비율", "연금 비율", "자본 vs 부채", "분류별 지출"} <= titles


def test_sectors_match_live_list_with_space_and_quantum():
    # 2026-10-14 사용자가 운영 드롭다운에 우주·양자를 추가 → 새로 만들 때도 같은 목록
    assert stock_sectors.SECTORS[-3:] == ["우주", "양자", "기타"]


def test_old_total_row_text_reset_after_distribution_grew():
    # 순자산 합계(남색 띠·흰 글씨)가 32→33행으로 내려가 32행(부채)에 흰 글씨가 남았다 → 검은 보통 글씨로
    reqs = theme.requests(19, 46, 14)
    g = layout.a1_to_grid("자산현황!A32:C32")
    fmts = [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs if "repeatCell" in r and r["repeatCell"]["range"] == g
            and "textFormat" in r["repeatCell"]["cell"]["userEnteredFormat"]]
    assert fmts and fmts[-1]["textFormat"]["foregroundColor"] == {"red": 0, "green": 0, "blue": 0}
