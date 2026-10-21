import asset_status as a
import layout
import styling


def _vals():
    return {e["range"]: e["values"] for e in a.values()}


def test_goal_card_reads_settings_and_handles_blank_and_overdue():
    v = _vals()
    assert v["자산현황!A4:F4"] == [["현재 순자산", "목표 순자산", "달성률", "남은 개월", "필요 월 저축", "목표 기한"]]
    row = v["자산현황!A5:F5"][0]
    assert row[0] == "=SUM(자산!E2:E50)" and row[1] == '=IF(설정!J8="","",설정!J8)'
    assert row[2] == '=IF(N(B5)=0,"",A5/B5)'
    assert row[3] == f'=IF(설정!J9="","",{a.months_left("설정!J9")})'
    assert row[4] == '=IF(OR(B5="",D5=""),"",IF(D5<=0,"기한 지남",MAX(0,(B5-A5)/D5)))'


def test_months_left_accepts_text_or_date():
    f = a.months_left("설정!J9")
    assert "ISTEXT(설정!J9)" in f and 'DATEVALUE(설정!J9&"-01")' in f and "MAX(0," in f


def test_monthly_savings_rate_uses_income_minus_spending_only():
    v = _vals()
    assert v["자산현황!A12:F12"] == [["월", "수입", "소비지출", "저축", "저축률", "귀속월"]]
    jan = v["자산현황!A13:F13"][0]
    assert jan[0] == "1월" and jan[5] == "=YEAR(TODAY())*100+1"
    assert jan[1] == '=SUMIFS(내역!$K:$K,내역!$L:$L,F13,내역!$C:$C,"수입")'
    assert jan[2] == '=SUMIFS(내역!$K:$K,내역!$L:$L,F13,내역!$C:$C,"지출")'  # 저축·이체 제외
    assert jan[3] == '=IF(AND(B13=0,C13=0),"",B13-C13)' and jan[4] == '=IF(OR(N(B13)=0,D13=""),"",D13/B13)'
    assert v["자산현황!A24:F24"][0][0] == "12월"
    assert v["자산현황!A8:C9"][1][0] == "=SUM(D13:D24)"


def test_distribution_groups_and_debt():
    v = _vals()
    rows = v["자산현황!A28:C33"]
    assert [r[0] for r in rows] == ["현금성", "주식", "청약", "연금·기타", "부채", "순자산"]
    # SUMIFS에 배열 조건을 주면 시트는 첫 조건만 본다(ARRAYFORMULA로도 안 됨, 통합 시험에서 확인) → FILTER+MATCH
    pick = 'IFERROR(SUM(FILTER(자산!$E$2:$E$50,ISNUMBER(MATCH(자산!$B$2:$B$50,{kinds},0)),ISNUMBER(자산!$E$2:$E$50))),0)'
    assert rows[0][1] == "=" + pick.format(kinds='{"현금","통장","계좌"}')
    assert rows[3][1] == "=" + pick.format(kinds='{"연금","기타"}')
    assert rows[4][1] == "=" + pick.format(kinds='{"카드","대출"}')
    assert rows[5][1] == "=SUM(B28:B32)" and rows[4][2] == ""


def test_debt_table_formulas_only_never_inputs():
    v = _vals()
    assert v["자산현황!A35:I35"] == [["대출명", "소유자", "현재 잔액", "금리", "월 상환액", "상환일", "만기", "남은 개월", "비고"]]
    assert v["자산현황!B36"] == [['=MAP(A36:A45,LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,자산!$A$2:$I$50,9,FALSE),""))))']]
    assert v["자산현황!C36"] == [['=MAP(A36:A45,LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,자산!$A$2:$E$50,5,FALSE),"자산 탭에 없음"))))']]
    assert v["자산현황!K36"] == [['=IFERROR(FILTER(자산!A2:A50,자산!B2:B50="대출"),"")']]
    for col in "ADEFGI":  # 사람 입력 열은 절대 쓰지 않는다
        assert not any(r.startswith(f"자산현황!{col}36") or r.startswith(f"자산현황!{col}37") for r in v), col
    assert v["자산현황!A46:E46"] == [["합계", "", "=SUM(C36:C45)", "", "=SUM(E36:E45)"]]


def test_settings_labels_dashboard_kpi_and_loan_kind():
    assert {e["range"]: e["values"] for e in a.settings_labels()}["설정!I8:I10"] == [
        ["목표 순자산"], ["목표 기한 (yyyy-mm)"], ["올해 저축 목표"]]
    kpi = {e["range"]: e["values"] for e in a.dashboard_kpi()}
    assert kpi["대시보드!M5:M6"] == [["목표 달성률"], ['=IF(자산현황!C5="","",자산현황!C5)']]
    loan = [r for r in layout.validation_requests() if r["setDataValidation"]["range"] == layout.a1_to_grid("자산!B2:B50")]
    assert {"userEnteredValue": "대출"} in loan[0]["setDataValidation"]["rule"]["condition"]["values"]


def test_charts():
    specs = [r["addChart"]["chart"]["spec"] for r in a.chart_requests()]
    assert [s["title"] for s in specs] == a.CHART_TITLES + a.EXTRA_TITLES
    combo = specs[0]["basicChart"]
    assert combo["chartType"] == "COMBO" and combo["series"][2]["targetAxis"] == "RIGHT_AXIS"
    assert [x["colorStyle"]["rgbColor"] for x in combo["series"]] == [styling.RED_TEXT, styling.BLUE_TEXT, styling.NAVY_HEAD]
    assert specs[1]["pieChart"]["series"]["sourceRange"]["sources"][0] == layout.a1_to_grid("자산현황!B28:B31")


import build_budget
import migrate_couple as mc


def _state(titles, charts=frozenset()):
    return mc.State(titles=titles, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                    budgets_empty=False, invest_charts=2, dash_rows=96, dash_chart_titles=charts, dash_base=46)


def _status_charts(reqs):
    return [r["addChart"]["chart"]["spec"]["title"] for r in reqs if "addChart" in r
            and r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["sheetId"] == 2100]


def test_status_tab_added_once_with_charts():
    without = {t for t, *_ in layout.SHEETS} - {"자산현황"}
    s1, _v1, vis1 = mc.plan(_state(without))
    assert mc._add_sheet("자산현황") in s1
    assert _status_charts(vis1) == a.CHART_TITLES + a.EXTRA_TITLES
    s2, _v2, vis2 = mc.plan(_state({t for t, *_ in layout.SHEETS}))
    assert not any("addSheet" in r and r["addSheet"]["properties"]["title"] == "자산현황" for r in s2)
    assert not _status_charts(vis2)


def test_live_values_never_touch_inputs():
    _s, values, _v = mc.plan(_state({t for t, *_ in layout.SHEETS}))
    ranges = {e["range"] for e in values}
    assert "자산현황!A5:F5" in ranges and "설정!I8:I10" in ranges and "대시보드!M5:M6" in ranges
    assert not any(r.startswith(("설정!J8", "설정!J9", "설정!J10")) for r in ranges)
    assert not any(r.startswith(f"자산현황!{c}36") for r in ranges for c in "ADEFGI")


def test_status_protected_except_inputs():
    prot = [r["addProtectedRange"]["protectedRange"] for r in layout.protection_requests()
            if r["addProtectedRange"]["protectedRange"]["range"] == {"sheetId": 2100}]
    free = prot[0]["unprotectedRanges"]
    assert layout.a1_to_grid("자산현황!A36:A45") in free and layout.a1_to_grid("자산현황!D36:G45") in free


def test_new_sheet_build_has_status():
    assert "자산현황!A5:F5" in {e["range"] for e in build_budget.value_data("a@b.com")}
    assert any(r in build_budget.visual_requests() for r in a.chart_requests())
