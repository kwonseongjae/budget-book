"""2026-10-14 사용자 지적: 고정지출 정렬, 종목별 그래프, 같은 이름 카드(하나카드 ×2) 잔액, 투자 하단 표."""
import align
import cards
import fixed_costs
import formulas
import layout
import migrate_couple as mc
import theme

ALL = {t for t, *_ in layout.SHEETS}


def _vals(entries):
    return {e["range"]: e["values"] for e in entries}


def test_fixed_list_sorted_by_payment_day_and_summary_by_amount_desc():
    f = _vals(fixed_costs.values())
    lst = f["고정지출!A5"][0][0]
    assert "SORT(d,INDEX(d,,9),TRUE" in lst  # 9번째 열 = 납입일, 오름차순
    summary = f["고정지출!L5"][0][0]
    assert "SORT(HSTACK(c,s,s/SUM(s)),2,FALSE)" in summary


def test_live_chart_reading_old_range_is_repointed():
    old = {"pieChart": {"domain": {"sourceRange": {"sources": [layout.a1_to_grid("주식투자!P19:P29")]}},
                        "series": {"sourceRange": {"sources": [layout.a1_to_grid("주식투자!Q19:Q29")]}}}}
    charts = ({"chartId": 5, "title": "종목별 보유 비율", "sheetId": 2400, "row": 79, "col": 10, "spec": {"title": "종목별 보유 비율", **old}},)
    fixes = mc.chart_spec_fixes(charts)
    assert len(fixes) == 1 and fixes[0]["updateChartSpec"]["chartId"] == 5
    new = fixes[0]["updateChartSpec"]["spec"]["pieChart"]["domain"]["sourceRange"]["sources"][0]
    assert new == layout.a1_to_grid("주식투자!K134:K144")  # 2026-10-15: 섹터 지정 아래로 옮긴 합산 상위 10 표
    same = ({**charts[0], "spec": fixes[0]["updateChartSpec"]["spec"]},)
    assert not mc.chart_spec_fixes(same)  # 맞으면 아무것도 안 함 (매번 다시 쓰지 않기)


def test_same_name_assets_count_only_their_owners_rows():
    e = _vals(formulas.asset_values())["자산!E1:E2"][1][0]
    assert "COUNTIF($A$2:$A$50,x)>1" in e and '내역!$B:$B,own' in e


def test_card_lists_label_duplicates_with_owner_and_split_usage():
    label = formulas.CARD_LABELS
    assert 'COUNTIF(자산!$A$2:$A$50,a)>1,a&" ("&b&")"' in label
    usage = formulas.card_usage("x", "$B$2")
    assert 'REGEXREPLACE(x," \\([^)]*\\)$","")' in usage and "내역!$B:$B,ow" in usage
    cvals = _vals(cards.values())
    assert cvals["카드!P5"] == [[label]]
    assert "내역!$B:$B,ow" in cvals["카드!K5"][0][0]


def test_live_dashboard_card_column_rewritten_at_live_rows():
    pie = {"chartId": 1, "spec": {"pieChart": {"legendPosition": "LABELED_LEGEND",
           "series": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 1, "endColumnIndex": 2}]}},
           "domain": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 12, "endColumnIndex": 13}]}}}}}
    state = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, pie=pie, dash_rows=200, dash_base=46, trend_head=14)
    vals = _vals(mc.plan(state)[1])
    assert vals["대시보드!I20"] == [[formulas.CARD_LABELS]]
    assert "내역!$B:$B,ow" in vals["대시보드!J20"][0][0]


def test_invest_bottom_tables_are_aligned_white_tables():
    h = {r["repeatCell"]["range"]["startColumnIndex"]: r["repeatCell"]["cell"]["userEnteredFormat"]["horizontalAlignment"]
         for r in align.requests() if r["repeatCell"]["range"]["sheetId"] == 1900 and r["repeatCell"]["range"]["startRowIndex"] == 40}
    assert h[0] == "CENTER" and h[1] == "RIGHT" and h[4] == "CENTER" and h[5] == "RIGHT"
    white = [r["repeatCell"]["range"] for r in theme.requests(19, 46, 14) if "repeatCell" in r
             and r["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor") == theme.WHITE]
    assert any(g["sheetId"] == 1900 and g["startRowIndex"] == 40 and g["startColumnIndex"] == 0 for g in white)


# 사용자가 [카드] 탭 빈 줄을 지워 표를 줄였다 (카드 5~10행, 포인트 제목 12·머리글 13·입력 14~22·합계 23, 전체 36행)
USER_CARD_COL_A = ([["카드 및 포인트"], [""], ["보유 카드 목록"], ["카드"], ["하나카드"], ["삼성카드"], ["우리카드"]]
                   + [[""]] * 4 + [["포인트·마일리지"], ["구분"]] + [[""]] * 9 + [["합계"]])


def test_card_layout_follows_user_deleted_rows():
    assert cards.find_layout(USER_CARD_COL_A) == cards.Layout(5, 10, 13, 14, 22)
    assert cards.find_layout([]) == cards.DEFAULT


def test_live_card_values_written_at_users_rows_not_code_rows():
    state = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_rows=200, dash_base=46, card_col_a=tuple(map(tuple, USER_CARD_COL_A)))
    structure, values, _vi = mc.plan(state)
    vals = _vals(values)
    assert vals["카드!A13:G13"] == [["구분", "이름", "혜택", "잔액", "용도", "유효기간", "비고"]]
    assert "A5:A10" in vals["카드!B5"][0][0] and "카드!A31:G31" not in vals and "카드!A47:D47" not in vals
    card_rows = [r["repeatCell"]["range"]["endRowIndex"] for r in structure if "repeatCell" in r
                 and r["repeatCell"]["range"].get("sheetId") == 2300 and "endRowIndex" in r["repeatCell"]["range"]]
    assert max(card_rows) <= 36


def test_requests_and_values_clipped_to_live_grid():
    state = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_rows=200, dash_base=46, grid={2500: (30, 16)})
    structure, values, _vi = mc.plan(state)
    for r in structure:
        g = r.get("repeatCell", r.get("updateBorders", {})).get("range", {})
        if g.get("sheetId") == 2500:
            assert g.get("endRowIndex", 0) <= 30, r
    for e in values:
        if e["range"].startswith("저축·연금!"):
            g = layout.a1_to_grid(e["range"])
            assert g["startRowIndex"] + len(e["values"]) <= 30, e["range"]
