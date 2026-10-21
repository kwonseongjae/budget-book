"""2026-10-16 사용성 점검 1·4·5번: 입력 오류를 눈에 띄게, 미등록 결제수단·음수 통장은 대시보드에서 알려 준다."""
import charts
import formulas
import layout
import migrate_couple as mc
import styling

TXN_SID = layout.SHEET_ID[layout.TXN]
ALL = {t for t, *_ in layout.SHEETS}


def _vals(entries):
    return {e["range"]: e["values"] for e in entries}


def _rule_texts(reqs, sheet_title):
    sid = layout.SHEET_ID[sheet_title]
    return [(r["addConditionalFormatRule"]["rule"]["ranges"][0], r["addConditionalFormatRule"]["rule"]["booleanRule"])
            for r in reqs if "addConditionalFormatRule" in r and "booleanRule" in r["addConditionalFormatRule"]["rule"]
            and r["addConditionalFormatRule"]["rule"]["ranges"][0]["sheetId"] == sid]


def test_amount_text_gets_its_own_error_label_not_exchange_error():
    k1 = _vals(formulas.txn_values())["내역!K1"][0][0]
    assert '"금액오류"' in k1 and '"환율오류"' in k1 and "ISNUMBER(H:H)" in k1


def test_bad_row_highlighted_across_whole_row_and_ranked_first():
    rule = next(r for r in charts.data_check_rules() if r["addConditionalFormatRule"]["rule"]["ranges"] == [layout.a1_to_grid("내역!A2:M5000")])
    assert rule["addConditionalFormatRule"]["index"] == 0
    f = rule["addConditionalFormatRule"]["rule"]["booleanRule"]["condition"]["values"][0]["userEnteredValue"]
    assert f == charts.BAD_ROW_FORMULA and "ISNUMBER($K2)" in f and "ISNUMBER($L2)" in f and '$B2=""' in f and '$H2<>""' in f


def test_unregistered_payment_also_marked_in_recurring_and_favorites():
    got = {}
    for r in charts.data_check_rules():
        rule = r["addConditionalFormatRule"]["rule"]
        g = rule["ranges"][0]
        got[(g["sheetId"], g["startColumnIndex"])] = rule["booleanRule"]["condition"]["values"][0]["userEnteredValue"]
    assert 'COUNTIF(INDIRECT("자산!A2:A50"),F2)=0' in got[(layout.SHEET_ID[layout.RECUR], 5)]
    assert 'COUNTIF(INDIRECT("자산!A2:A50"),E2)=0' in got[(layout.SHEET_ID[layout.FAV], 4)]


def test_dashboard_banner_formula_counts_three_kinds():
    f = formulas.attention_formula()
    assert f.startswith("=") and "TEXTJOIN" in f
    for text in ("내역 빨간 줄", "미등록 결제수단", "잔액 음수 통장"):
        assert text in f
    assert "내역!$F$2:$F$5000" in f and "반복!$F$2:$F$50" in f and "자산!$A$2:$A$50" in f
    assert 'IF(글="",""' in f  # 아무 문제 없으면 빈 칸


def test_banner_written_in_fresh_build_and_live_values():
    assert formulas.attention_values()[0]["range"] == "대시보드!D2"
    state = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_base=46)
    vals = _vals(mc.plan(state)[1])
    assert vals["대시보드!D2"][0][0] == formulas.attention_formula()
    assert vals["내역!K1"][0][0].count('"금액오류"') == 1  # 운영 시트도 새 오류 표시로


def test_banner_cell_styled_red_bold_left():
    reqs = styling.dashboard_requests()
    hit = [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs if "repeatCell" in r
           and r["repeatCell"]["range"] == layout.a1_to_grid("대시보드!D2")]
    assert hit and hit[-1]["textFormat"]["bold"] is True and hit[-1]["horizontalAlignment"] == "LEFT"
    assert hit[-1]["textFormat"]["fontSize"] >= 11  # 서식을 통째로 바꿔 글자 크기가 기본값으로 돌아가지 않게


def test_live_rules_added_once():
    state = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_base=46, dash_chart_titles=frozenset())
    first = [r for r in mc.plan(state)[2] if "addConditionalFormatRule" in r]
    assert any(r["addConditionalFormatRule"]["rule"]["ranges"][0] == layout.a1_to_grid("내역!A2:M5000") for r in first)
    seen = frozenset((r["addConditionalFormatRule"]["rule"]["ranges"][0]["sheetId"],
                      r["addConditionalFormatRule"]["rule"]["booleanRule"]["condition"]["values"][0]["userEnteredValue"])
                     for r in charts.data_check_rules())
    again = mc.plan(state._replace(rules_seen=seen))[2]
    assert not [r for r in again if "addConditionalFormatRule" in r
                and r["addConditionalFormatRule"]["rule"]["ranges"][0]["sheetId"] in (TXN_SID, layout.SHEET_ID[layout.RECUR], layout.SHEET_ID[layout.FAV])]


def test_guide_explains_red_rows():
    import guide
    assert any("빨갛게" in a or "빨간" in a for _k, a, _b in guide.CONTENT)


def test_banner_also_counts_recurring_rows_with_blank_amount():
    f = formulas.attention_formula()
    assert "금액 빈 반복" in f and "반복!$G$2:$G$50" in f and "반복!$A$2:$A$50=TRUE" in f


def test_recurring_blank_amount_cell_highlighted():
    rule = next(r for r in charts.data_check_rules() if r["addConditionalFormatRule"]["rule"]["ranges"] == [layout.a1_to_grid("반복!G2:G50")])
    f = rule["addConditionalFormatRule"]["rule"]["booleanRule"]["condition"]["values"][0]["userEnteredValue"]
    assert f == charts.BLANK_AMOUNT_FORMULA and "$A2=TRUE" in f and '$G2=""' in f


def test_guide_explains_recurring_skips():
    import guide
    text = " ".join(f"{a} {b}" for _k, a, b in guide.CONTENT)
    assert "금액을 비워" in text and "건너뛰" in text


def test_guide_explains_sms_dedupe_cancel_and_foreign():
    import guide
    text = " ".join(f"{a} {b}" for _k, a, b in guide.CONTENT)
    assert "건너뛰" in text and "음수" in text and "해외 결제" in text and "10월 5일" in text
