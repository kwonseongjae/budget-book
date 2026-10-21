import build_budget
import formulas
import invest
import layout


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_invest_tabs_defined_visible_and_hidden():
    props = {t: (sid, rows, cols, hidden) for t, sid, rows, cols, hidden in layout.SHEETS}
    assert props["투자"] == (1900, 100, 10, False)
    assert props["한투원본"] == (1950, 3, 7, True)
    assert props["투자기록"] == (2000, 1000, 12, True)
    assert "주식_신랑" in layout.TUCKED
    visible = [s["properties"]["title"] for s in layout.create_body("t")["sheets"] if not s["properties"]["hidden"]]
    assert visible == ["사용법", "시작하기", "빠른입력", "내역", "대시보드", "자산현황", "고정지출", "카드", "주식투자", "저축·연금", "부부", "자산기록", "투자", "즐겨찾기", "반복", "문자입력", "자산", "설정"]


def test_account_rows_prefer_manual_then_auto():
    vals = _by_range(invest.invest_values())
    row = vals["투자!A7:G7"][0]
    assert row[0] == "신랑 메리츠"
    fresh = 'AND(ISNUMBER(메리츠원본!$H$7),메리츠원본!$B$2<>"키없음",NOW()-N(메리츠원본!$H$8)<=3)'
    assert row[1] == f'=IF(ISNUMBER(H7),H7,IF({fresh},메리츠원본!$H$7,""))'
    # 원금 = 종목별 매입금액(매수 당시 환율 원화) 합계. 예전엔 여기에 현금·외화 예수금을 더했는데 결제 대기(D+2) 때문에
    # 날마다 수백만 원씩 출렁였다(2026-10-20). 총자산 조회의 매입금액은 해외분을 오늘 환율로 바꿔 쓰지 않는다.
    auto = '=IF(ISNUMBER(메리츠원본!$H$2),SUM(메리츠원본!$F$11:$F$110),"")'
    assert row[2] == f'=IF(NOT(ISNUMBER(B7)),"",IF(ISNUMBER(I7),I7,IF(ISNUMBER(H7),"",IF(ISNUMBER({auto[1:]}),{auto[1:]},""))))'
    assert '"직접입력"' in row[6] and '"오래됨"' in row[6] and '"자동"' in row[6]
    isa = vals["투자!A11:G11"][0]
    assert "한투원본!$F$3" in isa[1] and "한투원본!$G$3" in isa[2] and "한투원본!$B$3" in isa[6]


def test_stale_auto_values_drop_out_after_key_delete_or_3_days():
    # 키를 지웠거나 3일 넘게 갱신이 실패하면 마지막 성공 값이 합계·기록에 계속 들어가지 않게
    row = _by_range(invest.invest_values())["투자!A8:G8"][0]
    fresh = 'AND(ISNUMBER(한투원본!$F$2),한투원본!$B$2<>"키없음",NOW()-N(한투원본!$E$2)<=3)'
    assert row[1] == f'=IF(ISNUMBER(H8),H8,IF({fresh},한투원본!$F$2,""))'


def test_principal_counts_only_with_valuation():
    # 시트(원금 합)와 투자기록(평가 있는 계좌만)의 원금 규칙을 하나로
    row = _by_range(invest.invest_values())["투자!A8:G8"][0]
    assert row[2].startswith('=IF(NOT(ISNUMBER(B8)),"",')


def test_totals_kpi_and_changes_tolerate_empty_log():
    vals = _by_range(invest.invest_values())
    assert vals["투자!A9:G9"][0][1] == '=IF(COUNT(B7,B8)=0,"",SUM(B7,B8))'
    kpi = vals["투자!A4:F4"][0]
    assert kpi[0] == '=IF(COUNT(B7,B8,B10,B11)=0,"",SUM(B7,B8,B10,B11))'
    assert kpi[4].startswith("=IFERROR(") and kpi[5].startswith("=IFERROR(")
    assert "EOMONTH(last,-1)" in kpi[5]


def test_month_end_and_recent_30_tables():
    vals = _by_range(invest.invest_values())
    assert vals["투자!A40:C40"] == [["월", "합계 평가", "합계 원금"]]
    assert vals["투자!A41"][0][0].startswith("=IFERROR(SORT(UNIQUE(FILTER(")
    month = vals["투자!B41:C41"][0]
    assert "EOMONTH(m,0)" in month[0] and ",10,FALSE)" in month[0] and ",11,FALSE)" in month[1]
    assert "MAX(투자기록!A2:A)-29" in vals["투자!E41"][0][0]


def test_raw_and_log_headers():
    vals = _by_range(invest.invest_values())
    assert vals["한투원본!A1:G1"][0] == ["사람", "상태", "코드", "메시지", "마지막 성공", "평가금액", "원금"]
    assert vals["한투원본!A2:A3"] == [["신랑"], ["신부"]]
    assert len(vals["투자기록!A1:L1"][0]) == 12


def test_asset_sync_reads_invest_tab_for_all_four_accounts():
    e2 = _by_range(formulas.asset_values())["자산!E1:E2"][1][0]
    assert '{"메리츠_신랑","한투ISA_신랑","메리츠_신부","한투ISA_신부"}' in e2
    assert "투자!$B$7,투자!$B$8,투자!$B$10,투자!$B$11" in e2
    h2 = _by_range(formulas.asset_values())["자산!H1:H2"][1][0]
    assert "투자!$F$7" in h2 and '"직접입력"' in h2 and '"연동 "&TEXT(at,"mm/dd hh:mm")' in h2
    rules = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]
             for r in layout.validation_requests()}
    g = rules[tuple(sorted(layout.a1_to_grid("자산!G2:G50").items()))]
    assert [x["userEnteredValue"] for x in g["condition"]["values"]] == [n for n, _r in layout.INVEST_ACCOUNTS]


def test_invest_tab_protected_except_refresh_and_manual_cells():
    prs = [r["addProtectedRange"]["protectedRange"] for r in layout.protection_requests()]
    tab = [p for p in prs if p["range"] == {"sheetId": 1900}][0]
    assert tab["unprotectedRanges"] == [layout.a1_to_grid(a) for a in ("투자!H1", "투자!H7:I8", "투자!H10:I11")]


def test_two_charts_and_build_wiring():
    charts = [r["addChart"]["chart"] for r in invest.visual_requests() if "addChart" in r]
    assert [c["spec"]["title"] for c in charts] == ["월별 투자 추이 (월말)", "최근 30일 합산 평가금액"]
    assert all(c["position"]["overlayPosition"]["anchorCell"]["sheetId"] == 1900 for c in charts)
    assert any("투자!A7:G7" == e["range"] for e in build_budget.value_data("a@b.com"))
    assert any("setDataValidation" in r and r["setDataValidation"]["range"] == layout.a1_to_grid("투자!H1")
               for r in build_budget.structure_requests())


def test_meritz_principal_no_longer_kept_in_raw_tab():
    import meritz_sheet as ms
    vals = _by_range(ms.raw_values(layout.MERITZ_SLOTS[1]))
    assert "메리츠원본2!G9" not in vals  # 원금은 [투자] 수식이 종목 블록에서 바로 계산


def test_guide_points_to_invest_tab_and_kis_menu():
    import guide
    text = "\n".join(b for _k, _a, b in guide.CONTENT)
    assert "[투자]" in "\n".join(b for _k, _a, b in guide.CONTENT[2:8])
    assert "증권 연동" in text and "한투 ISA 키 입력" in text


def test_pnl_counts_only_accounts_with_both_value_and_principal():
    # 검토 지적: 평가만 있고 원금이 빈 계좌의 평가 전체가 손익으로 잡혔다 (A4−B4)
    vals = _by_range(invest.invest_values())
    kpi = vals["투자!A4:F4"][0]
    assert kpi[2] == '=IF(COUNT(D7,D8,D10,D11)=0,"",SUM(D7,D8,D10,D11))'
    paired = "IF(ISNUMBER(D7),C7,0)+IF(ISNUMBER(D8),C8,0)+IF(ISNUMBER(D10),C10,0)+IF(ISNUMBER(D11),C11,0)"
    assert kpi[3] == f'=IFERROR(C4/({paired}),"")'
    total = vals["투자!A9:G9"][0]
    assert total[3] == '=IF(COUNT(D7,D8)=0,"",SUM(D7,D8))'
    assert total[4] == '=IFERROR(D9/(IF(ISNUMBER(D7),C7,0)+IF(ISNUMBER(D8),C8,0)),"")'


def test_rerun_never_overwrites_kis_results():
    # 검토 지적: 마이그레이션 재실행 때 한투원본 B2:G3(상태·시각·평가·원금)을 빈 값으로 덮어썼다
    kis = [e["range"] for e in invest.invest_values() if e["range"].startswith("한투원본!")]
    assert sorted(kis) == ["한투원본!A1:G1", "한투원본!A2:A3"]


def test_gain_is_holdings_value_minus_cost_and_cash_is_shown_separately():
    vals = _by_range(invest.invest_values())
    stock = '=IF(ISNUMBER(메리츠원본!$H$2),N(메리츠원본!$H$3),"")'[1:]
    d, e = vals["투자!A7:G7"][0][3], vals["투자!A7:G7"][0][4]
    assert d == (f'=IF(AND(ISNUMBER(B7),ISNUMBER(C7)),IF(AND(NOT(ISNUMBER(H7)),NOT(ISNUMBER(I7)),ISNUMBER({stock})),'
                 f'{stock}-C7,B7-C7),"")')
    assert e == '=IF(AND(ISNUMBER(D7),N(C7)<>0),D7/C7,"")'
    assert vals["투자!J7"][0][0] == f'=IF(AND(ISNUMBER(B7),NOT(ISNUMBER(H7)),ISNUMBER({stock})),B7-{stock},"")'
    assert vals["투자!J6"] == [["현금(예수금)"]] and vals["투자!J9"][0][0] == '=IF(COUNT(J7,J8)=0,"",SUM(J7,J8))'


def test_isa_cost_and_value_come_from_holdings_list_with_fallback_to_response():
    vals = _by_range(invest.invest_values())
    c0 = "SUM(한투종목!$D$2:$D$101)"
    assert invest.kis_principal(0) == f"IF({c0}>0,{c0},한투원본!$G$2)"
    assert invest.kis_stock(1) == 'IF(SUM(한투종목!$J$2:$J$101)>0,SUM(한투종목!$K$2:$K$101),"")'
    assert invest.kis_principal(1) in vals["투자!A11:G11"][0][2]  # 신부 ISA 원금 칸이 종목 매입 합을 읽는다


def test_note_explains_the_new_definition():
    vals = _by_range(invest.invest_values())
    note = vals["투자!A2"][0][0]
    assert "종목 매입금액 합계" in note and "현금을 뺀 종목 기준" in note and "'매입금액+현금'" not in note
    import fit_dims, styling
    room = sum(styling.COL_WIDTHS[invest.INVEST][:8])  # A2 글이 이어지는 A~H열 (I2는 업데이트일 배지)
    assert fit_dims.text_px(note, 13, False) < room


def test_cash_column_is_wide_and_navy_header():
    import layout
    import styling
    assert styling.COL_WIDTHS[invest.INVEST][9] >= 120
    heads = [r["repeatCell"]["range"] for r in styling.header_requests() if "repeatCell" in r]
    assert layout.a1_to_grid("투자!A6:J6") in heads
