import pytest

import layout


def test_a1_to_grid_range():
    assert layout.a1_to_grid("내역!B2:D10") == {
        "sheetId": 100, "startRowIndex": 1, "endRowIndex": 10,
        "startColumnIndex": 1, "endColumnIndex": 4,
    }


def test_a1_to_grid_single_cell_and_double_letters():
    g = layout.a1_to_grid("추이!AA3")
    assert (g["startRowIndex"], g["endRowIndex"]) == (2, 3)
    assert (g["startColumnIndex"], g["endColumnIndex"]) == (26, 27)


def test_a1_to_grid_rejects_open_range():
    with pytest.raises(ValueError):
        layout.a1_to_grid("내역!A2:A")


def test_create_body_tabs_locale_and_unique_ids():
    body = layout.create_body("테스트")
    assert body["properties"]["locale"] == "ko_KR"
    assert body["properties"]["timeZone"] == "Asia/Seoul"
    props = [s["properties"] for s in body["sheets"]]
    assert [p["title"] for p in props][:4] == ["사용법", "시작하기", "빠른입력", "내역"]
    assert len({p["sheetId"] for p in props}) == len(props)
    hidden = {p["title"] for p in props if p["hidden"]}
    assert hidden == {"계산", "알림기록", "메리츠원본", "메리츠원본2", "한투원본", "투자기록", "한투종목"} | layout.TUCKED


def test_seed_settings_has_partner_email_and_start_day():
    seeds = {s["range"]: s["values"] for s in layout.seed_values("a@b.com")}
    assert seeds["설정!I1:J4"][1] == ["월 시작일", 1]
    assert seeds["설정!I1:J4"][3][1] == "a@b.com"
    assert ["공동"] in seeds["설정!E1:E4"]


def test_category_dropdown_uses_open_settings_range():
    reqs = layout.validation_requests()
    txn_d = [r["setDataValidation"] for r in reqs
             if r["setDataValidation"]["range"] == layout.a1_to_grid("내역!D2:D5000")][0]
    assert txn_d["rule"]["condition"] == {
        "type": "ONE_OF_RANGE", "values": [{"userEnteredValue": "=설정!$A$2:$A"}]}
    assert txn_d["rule"]["strict"] is False  # 이름 변경 직후/미분류 행이 거부되지 않도록


def test_view_tabs_protected_except_selector():
    reqs = [r["addProtectedRange"]["protectedRange"] for r in layout.protection_requests()]
    dash = [p for p in reqs if p["range"] == {"sheetId": 400}][0]
    assert dash["warningOnly"] is True
    assert dash["unprotectedRanges"] == [layout.a1_to_grid("대시보드!B1")]


def test_month_key_columns_use_month_format():
    reqs = layout.format_requests()
    l_col = [r for r in reqs if r.get("repeatCell", {}).get("range") == layout.a1_to_grid("내역!L2:L5000")][0]
    assert l_col["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]["pattern"] == '0000"-"00'


def test_amount_format_has_no_trailing_dot():
    reqs = layout.format_requests()
    h = [r for r in reqs if r.get("repeatCell", {}).get("range") == layout.a1_to_grid("내역!H2:H5000")][0]
    assert h["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]["pattern"] == "#,##0"


def test_type_dropdowns_follow_settings_list():
    rules = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]["condition"]
             for r in layout.validation_requests()}
    def cond(a1):
        return rules[tuple(sorted(layout.a1_to_grid(a1).items()))]
    with_trf = {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": "=계산!$D$2:$D"}]}
    no_trf = {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": "=계산!$E$2:$E"}]}
    assert cond("내역!C2:C5000") == with_trf
    assert cond("반복!D2:D50") == no_trf
    assert cond("즐겨찾기!C2:C50") == no_trf
    assert cond("설정!B2:B60") == no_trf


def test_settings_major_category_column_seeded_and_dropdown():
    seeds = {s["range"]: s["values"] for s in layout.seed_values("a@b.com")}
    assert seeds["설정!A1:B1"] == [["카테고리(중분류)", "구분"]] and seeds["설정!D1"] == [["대분류"]]
    rows = {r[0]: r for r in seeds[f"설정!A2:D{1 + len(layout.EXPENSE_CATS) + len(layout.INCOME_CATS)}"]}
    assert rows["주거·관리비"][3] == "고정비" and rows["식비"][3] == "변동비" and rows["월급"][3] == ""
    rules = [r["setDataValidation"] for r in layout.validation_requests()]
    d = [r for r in rules if r["range"] == layout.a1_to_grid("설정!D2:D60")][0]
    assert d["rule"]["condition"] == {"type": "ONE_OF_LIST",
                                      "values": [{"userEnteredValue": "고정비"}, {"userEnteredValue": "변동비"}]}


def test_txn_has_13_columns_with_protected_major_column():
    assert [s for s in layout.SHEETS if s[0] == "내역"][0][3] == 14  # +N 적용 환율
    ranges = [r["addProtectedRange"]["protectedRange"]["range"] for r in layout.protection_requests()]
    assert layout.a1_to_grid("내역!K1:M5000") in ranges


def test_assets_have_linked_category_column():
    seeds = {s["range"]: s["values"] for s in layout.seed_values("a@b.com")}
    assert seeds["자산!F1"] == [["적립 카테고리"]]
    assert [s for s in layout.SHEETS if s[0] == "자산"][0][3] == 12
    rules = [r["setDataValidation"] for r in layout.validation_requests()]
    f = [r for r in rules if r["range"] == layout.a1_to_grid("자산!F2:F50")][0]
    assert f["rule"]["condition"]["values"] == [{"userEnteredValue": "=설정!$A$2:$A"}]


def test_meritz_tabs_defined_and_raw_hidden():
    props = {t: (sid, rows, cols, hidden) for t, sid, rows, cols, hidden in layout.SHEETS}
    assert props["주식_신랑"] == (1500, 120, 16, False)
    assert props["메리츠_신랑"] == (1600, 100, 8, False)
    assert props["메리츠원본"] == (1400, 110, 14, True)
    assert props["자산"][2] == 12


def test_asset_link_column_dropdown_and_status_protected():
    seeds = {s["range"]: s["values"] for s in layout.seed_values("a@b.com")}
    assert seeds["자산!G1"] == [["연동"]]
    rules = [r["setDataValidation"] for r in layout.validation_requests()]
    g = [r for r in rules if r["range"] == layout.a1_to_grid("자산!G2:G50")][0]
    assert g["rule"]["condition"] == {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": n} for n in ["메리츠_신랑", "한투ISA_신랑", "메리츠_신부", "한투ISA_신부"]]}
    ranges = [r["addProtectedRange"]["protectedRange"]["range"] for r in layout.protection_requests()]
    assert layout.a1_to_grid("자산!H1:H50") in ranges


def test_stock_tab_protected_except_refresh_checkbox():
    prs = [r["addProtectedRange"]["protectedRange"] for r in layout.protection_requests()]
    stock = [p for p in prs if p["range"] == {"sheetId": 1500}][0]
    assert stock["unprotectedRanges"] == [layout.a1_to_grid("주식_신랑!H1")]
    assert any(p["range"] == {"sheetId": 1600} for p in prs)
    assert any(p["range"] == {"sheetId": 1400} for p in prs)
