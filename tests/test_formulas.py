import formulas


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_sumifs_builder():
    assert formulas.sumifs(("내역!$L:$L", "$B$2"), ("내역!$C:$C", '"지출"')) == \
        'SUMIFS(내역!$K:$K,내역!$L:$L,$B$2,내역!$C:$C,"지출")'


def test_txn_ym_is_numeric_key():
    l1 = _by_range(formulas.core_values())["내역!L1"][0][0]
    assert "*100+MONTH(" in l1          # 202610 같은 숫자 키 — 문자열 "2026-10" 금지
    assert "TEXT(" not in l1
    assert "설정!$J$2" in l1             # 월 시작일 반영


def test_krw_amount_uses_rate_table():
    k1 = _by_range(formulas.core_values())["내역!K1"][0][0]
    assert k1.startswith("=ARRAYFORMULA(")
    assert "VLOOKUP(I:I,설정!$G:$H,2,FALSE)" in k1


def test_dashboard_prev_month_wraps_year():
    kpi = _by_range(formulas.core_values())["대시보드!A5:I6"][1]
    assert "-89" in kpi[3]               # 202601 → 202512


def test_uncategorized_is_total_minus_listed():
    row = _by_range(formulas.core_values())["대시보드!A61:B61"][0]
    assert row == ["미분류", "=B6+G6-SUM(B62:B91)"]


def test_asset_balance_includes_transfers_both_ways():
    e2 = _by_range(formulas.core_values())["자산!E1:E2"][1][0]
    assert e2.count('"이체"') == 4  # 보낸·받은 이체 × (전체 / 같은 이름 자산이면 소유자 것만)
    assert "내역!$G:$G" in e2


def test_per_row_sums_use_map_not_array_criteria():
    vals = _by_range(formulas.core_values())
    assert vals["대시보드!A62:E62"][0][1].startswith("=MAP(A62:A91,LAMBDA(x,")
    side = vals["대시보드!F61:L61"][0]
    assert side[1].startswith("=MAP(F61:F76,LAMBDA(x,") and side[4].startswith("=MAP(I61:I76,LAMBDA(x,")
    e2 = vals["자산!E1:E2"][1][0]
    assert e2.startswith("=MAP(A2:A,C2:C,F2:F,G2:G,I2:I,J2:J,K2:K,LAMBDA(x,init,link,sync,own,cur,fx,")
    assert ",init+" in e2 and 'IF(x="","",LET(krw,LET(net,' in e2
    assert "ARRAYFORMULA" not in e2


def test_krw_failed_rate_is_visible_not_one():
    k1 = _by_range(formulas.core_values())["내역!K1"][0][0]
    assert '"환율오류"' in k1
    assert "FALSE),1)" not in k1


def test_month_pick_handles_text_and_date():
    f = formulas.month_pick("B1")
    assert f.startswith("LET(pick,B1,")
    assert 'SUBSTITUTE(pick,"-","")' in f and "YEAR(pick)*100+MONTH(pick)" in f
    top = _by_range(formulas.core_values())["대시보드!A1:C3"]
    assert top[1][1] == "=" + f


def test_bad_date_marked_and_excluded_from_lists():
    vals = _by_range(formulas.core_values())
    assert '"날짜오류"' in vals["내역!L1"][0][0]
    calc = vals["계산!A1:C2"][1]
    assert "ISNUMBER(내역!L2:L)" in calc[0] and "ISNUMBER(내역!L2:L)" in calc[1]


def test_type_lists_built_from_settings_column_b():
    vals = _by_range(formulas.core_values())
    d, e = vals["계산!D1:E2"][1]
    assert '"수입";"지출"' in e and "설정!B2:B" in e and '<>"이체"' in e
    assert '"이체"' in d and "E2:E" in d


OUT = ('"<>"', '"<>수입"', '"<>이체"')


def test_asset_balance_subtracts_every_outflow_type():
    e2 = _by_range(formulas.core_values())["자산!E1:E2"][1][0]
    assert all(c in e2 for c in OUT)


def test_dashboard_other_outflow_kpi_and_balance():
    kpi = _by_range(formulas.core_values())["대시보드!A5:I6"]
    assert kpi[0][6] == "저축·기타"
    assert '"<>지출"' in kpi[1][6] and all(c in kpi[1][6] for c in OUT)
    assert kpi[1][2] == "=A6-B6-G6"


def test_category_table_lists_every_non_income_category():
    row = _by_range(formulas.core_values())["대시보드!A62:E62"][0]
    assert '설정!$B$2:$B<>"수입"' in row[0]
    assert all(c in row[1] for c in OUT)


def test_txn_major_category_looked_up_from_settings():
    m1 = _by_range(formulas.core_values())["내역!M1"][0][0]
    assert m1.startswith("=ARRAYFORMULA(") and '"대분류"' in m1
    assert "VLOOKUP(D:D,설정!$A:$D,4,FALSE)" in m1


def test_dashboard_fixed_and_variable_totals():
    kpi = _by_range(formulas.core_values())["대시보드!A5:I6"]
    assert kpi[0][7:] == ["고정비", "변동비"]
    assert '내역!$M:$M,"고정비"' in kpi[1][7] and '내역!$M:$M,"변동비"' in kpi[1][8]
    assert all(c in kpi[1][7] for c in OUT)


def test_dashboard_category_table_shows_major():
    vals = _by_range(formulas.core_values())
    assert vals["대시보드!A60:L60"][0][4] == "대분류"
    assert "VLOOKUP(A62:A91,설정!$A:$D,4,FALSE)" in vals["대시보드!A62:E62"][0][4]


def test_category_lists_per_type_in_calc():
    vals = _by_range(formulas.core_values())
    head = vals["계산!G1"][0][0]
    assert head.startswith("=ARRAY_CONSTRAIN(TRANSPOSE(FILTER(E2:E,") and head.endswith(",1,10)")
    lists = vals["계산!G2:P2"][0]
    assert len(lists) == 10
    assert lists[0] == '=IF(G1="","",IFERROR(FILTER(설정!$A$2:$A,설정!$B$2:$B=G1),""))'
    assert lists[9].endswith('설정!$B$2:$B=P1),""))')


def test_asset_balance_adds_linked_saving_category():
    e2 = _by_range(formulas.core_values())["자산!E1:E2"][1][0]
    assert e2.startswith("=MAP(A2:A,C2:C,F2:F,G2:G,I2:I,J2:J,K2:K,LAMBDA(x,init,link,sync,own,cur,fx,")
    assert 'IF(link="",0,IF(OR(own="",own=설정!$E$4),SUMIFS(내역!$K:$K,내역!$D:$D,link,' in e2


def test_asset_balance_uses_meritz_net_when_linked():
    e2 = _by_range(formulas.core_values())["자산!E1:E2"][1][0]
    assert e2.startswith("=MAP(A2:A,C2:C,F2:F,G2:G,I2:I,J2:J,K2:K,LAMBDA(x,init,link,sync,own,cur,fx,")
    pick = 'IFERROR(CHOOSE(MATCH(sync,{"메리츠_신랑","한투ISA_신랑","메리츠_신부","한투ISA_신부"},0),투자!$B$7,투자!$B$8,투자!$B$10,투자!$B$11),"")'
    assert f'LET(net,{pick},IF(AND(sync<>"",ISNUMBER(net)),net,' in e2


def test_asset_link_status_shows_time_stale_or_missing():
    h = _by_range(formulas.core_values())["자산!H1:H2"]
    assert h[0] == ["연동 상태"]
    f = h[1][0]
    assert f.startswith("=MAP(A2:A,G2:G,J2:J,K2:K,LAMBDA(x,sync,cur,fx,")
    assert '"미갱신"' in f and '"오래됨 ("' in f and "NOW()-at>3" in f
    assert 'at,IFERROR(CHOOSE(MATCH(sync,{"메리츠_신랑","한투ISA_신랑","메리츠_신부","한투ISA_신부"},0),투자!$F$7,투자!$F$8,투자!$F$10,투자!$F$11),"")' in f
    assert '"연동 "&TEXT(at,"mm/dd hh:mm")' in f
