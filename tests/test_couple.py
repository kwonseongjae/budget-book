import build_budget
import couple
import formulas
import layout
import meritz_sheet as ms
import meritz_style as mst


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_new_tabs_and_meritz_slots_defined():
    titles = {t: (sid, hidden) for t, sid, _r, _c, hidden in layout.SHEETS}
    assert titles["부부"] == (1700, False)
    assert titles["자산기록"] == (1800, False)
    assert titles["주식_신부"] == (1550, False)
    assert titles["메리츠_신부"] == (1650, False)
    assert titles["메리츠원본2"] == (1450, True)
    assert "주식" not in titles and titles["주식_신랑"][0] == 1500
    assert [s.sync for s in layout.MERITZ_SLOTS] == ["메리츠_신랑", "메리츠_신부"]
    cols = {t: c for t, _s, _r, c, _h in layout.SHEETS}
    assert cols["설정"] == 13 and cols["자산"] == 12


def test_settings_per_user_budget_columns_and_total():
    vals = _by_range(build_budget.value_data("a@b.com"))
    assert vals["설정!K1:M1"] == [['=설정!E2&" 예산"', '=설정!E3&" 예산"', '=설정!E4&" 예산"']]
    c1 = vals["설정!C1"][0][0]
    assert c1.startswith("=ARRAYFORMULA(") and "K:K+L:L+M:M" in c1 and '"월 예산(합계)"' in c1


def test_asset_owner_column_and_meritz_sync_choices():
    rules = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]
             for r in layout.validation_requests()}
    owner = rules[tuple(sorted(layout.a1_to_grid("자산!I2:I50").items()))]
    assert owner["condition"] == {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": "=설정!$E$2:$E"}]}
    sync = rules[tuple(sorted(layout.a1_to_grid("자산!G2:G50").items()))]
    assert [x["userEnteredValue"] for x in sync["condition"]["values"]] == ["메리츠_신랑", "한투ISA_신랑", "메리츠_신부", "한투ISA_신부"]


def test_asset_balance_reads_the_chosen_meritz_slot():
    e2 = _by_range(formulas.asset_values())["자산!E1:E2"][1][0]
    assert "투자!$B$7" in e2 and "투자!$B$10" in e2


def test_month_end_projection_adds_pending_recurring_and_variable_pace():
    f6 = _by_range(formulas.dashboard_values())["대시보드!A5:I6"][1][5]
    assert f6.startswith("=B6+IF($B$2=계산!$C$2,")
    # SUMIFS의 "<>"&월 조건은 빈 칸(아직 안 생긴 항목)을 빼 버리므로 SUMPRODUCT로 비교 (실시트에서 확인)
    # 외화 반복은 원화로 환산해서 더한다 (2026-10-16)
    assert f"SUMPRODUCT({formulas.recur_krw()}*(반복!$A$2:$A$50=TRUE)*(반복!$D$2:$D$50=\"지출\")*(반복!$I$2:$I$50<>계산!$C$2))" in f6
    assert '내역!$M:$M,"변동비"' in f6


def test_couple_summary_rows_per_user():
    vals = _by_range(couple.couple_values())
    rows = vals["부부!A5:E7"]
    assert [r[0] for r in rows] == ["=설정!E2", "=설정!E3", "=설정!E4"]
    assert 'SUMIFS(내역!$K:$K,내역!$L:$L,$B$2,내역!$C:$C,"수입",내역!$B:$B,$A5)' in rows[0][1]
    assert rows[0][4] == "=B5-C5-D5"


def test_couple_settlement_uses_payment_owner_and_halves_difference():
    vals = _by_range(couple.couple_values())
    paid = vals["부부!A10:B11"]
    assert "VLOOKUP(내역!$F$2:$F,자산!$A$2:$I$50,9,FALSE)" in paid[0][1]
    assert "설정!$E$4" in paid[0][1] and "설정!$E$2" in paid[0][1]
    verdict = vals["부부!A12:B13"][0][1]
    assert "(B10-B11)/2" in verdict and '"정산할 금액 없음"' in verdict


def test_couple_category_table_per_user_spend_budget_rate():
    vals = _by_range(couple.couple_values())
    head = vals["부부!A15:K15"][0]
    assert head[:2] == ["카테고리", "구분"] and len(head) == 11
    row = vals["부부!A16:K16"][0]
    assert row[0].startswith("=IFERROR(SORT(FILTER(설정!$A$2:$B")
    assert "VLOOKUP($A16:$A55,설정!$A:$M,11,FALSE)" in row[3]  # 첫 사용자 예산 = K열
    assert "VLOOKUP($A16:$A55,설정!$A:$M,13,FALSE)" in row[9]  # 공동 = M열


def test_networth_tab_header():
    assert _by_range(couple.couple_values())["자산기록!A1:D1"] == [["월", "순자산", "자산(부채 제외)", "카드·대출 잔액"]]


def test_meritz_second_slot_reads_its_own_raw_tab():
    vals = _by_range(ms.all_values())
    row = vals["주식_신부!A16:P16"][0]
    assert all("메리츠원본2!A11:A110" in f for f in row)
    assert vals["메리츠_신부!A6:D6"][0][0] == "=주식_신부!A6"
    assert "신부" in vals["주식_신부!A1"][0][0]
    checks = [r["setDataValidation"]["range"] for r in mst.structure_requests() if "setDataValidation" in r]
    assert layout.a1_to_grid("주식_신부!H1") in checks and layout.a1_to_grid("주식_신랑!H1") in checks


def test_unregistered_payment_method_highlighted():
    import charts
    rules = [r["addConditionalFormatRule"]["rule"] for r in charts.conditional_requests()
             if "addConditionalFormatRule" in r]
    hit = [r for r in rules if r["ranges"] == [layout.a1_to_grid("내역!F2:G5000")]]
    assert hit and 'COUNTIF(INDIRECT("자산!A2:A50"),F2)=0' in hit[0]["booleanRule"]["condition"]["values"][0]["userEnteredValue"]


def test_rarely_used_view_tabs_start_hidden_but_keep_styling():
    import styling
    body = {s["properties"]["title"]: s["properties"]["hidden"] for s in layout.create_body("t")["sheets"]}
    tucked = {"추이", "달력", "검색", "주식_신랑", "메리츠_신랑", "메리츠_신부", "주식_신부"}
    assert {t for t, h in body.items() if h} == tucked | {"계산", "알림기록", "메리츠원본", "메리츠원본2", "한투원본", "투자기록", "한투종목"}
    assert {t for t, h in body.items() if not h} == {"사용법", "시작하기", "빠른입력", "내역", "대시보드", "자산현황", "고정지출", "카드", "주식투자", "저축·연금", "부부", "자산기록", "투자",
                                                     "즐겨찾기", "반복", "문자입력", "자산", "설정"}
    styled = {r["updateSheetProperties"]["properties"]["sheetId"] for r in styling.base_requests()
              if "tabColor" in r.get("updateSheetProperties", {}).get("properties", {})}
    assert {layout.SHEET_ID[t] for t in tucked} <= styled  # 숨겨도 꺼내 보면 같은 모양


def test_guide_starts_with_short_summary_and_menu_hint():
    import guide
    kinds = [k for k, _a, _b in guide.CONTENT]
    assert guide.CONTENT[1][1] == "이것만 기억하세요" and kinds[1] == "section"
    first = "\n".join(b for _k, _a, b in guide.CONTENT[2:10])  # 처음이라면·폰에서 입력 두 줄이 앞에 들어옴
    for must in ("[내역]", "[대시보드]", "[부부]", "[자산기록]", "메뉴 '가계부'"):
        assert must in first, must
