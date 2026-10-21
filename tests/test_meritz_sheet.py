import json
from pathlib import Path

import build_budget
import layout
import meritz_sheet as ms

S0 = layout.MERITZ_SLOTS[0]

FIX = json.loads((Path(__file__).parent / "fixtures" / "meritz_expected.json").read_text(encoding="utf-8"))


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_raw_headers_match_block_layout():
    raw = _by_range(ms.raw_values(S0))
    assert raw["메리츠원본!A2:A5"] == [["총자산"], ["보유종목"], ["해외보유"], ["외화예수금"]]
    assert [r[0] for r in raw["메리츠원본!G1:G8"]] == [
        "총자산", "원화 현금", "유가증권 평가", "외화 예수금(원)", "대출", "자동투자 인출가능", "순자산", "갱신 시각"]
    assert len(raw["메리츠원본!A10:N10"][0]) == 14
    assert len(raw["메리츠원본!J1:N1"][0]) == 5


def test_holdings_header_width_matches_logic_rows():
    raw = _by_range(ms.raw_values(S0))
    assert len(raw["메리츠원본!A10:N10"][0]) == len(FIX["holdings"][0])


def test_stock_rows_read_raw_holdings_block():
    vals = _by_range(ms.stock_values(S0))
    row = vals["주식_신랑!A16:P16"][0]
    assert len(row) == 16
    assert all(f.startswith("=ARRAYFORMULA(IF(메리츠원본!A11:A110=\"\",\"\",") for f in row)
    assert "메리츠원본!G11:G110/메리츠원본!D11:D110" in row[5]  # 현재가(원) = 평가 ÷ 수량
    assert "메리츠원본!H11:H110/메리츠원본!F11:F110" in row[9]  # 수익률(원)
    assert "(메리츠원본!N11:N110-메리츠원본!M11:M110)/메리츠원본!M11:M110" in row[14]  # 수익률(외화)


def test_stock_summary_shows_before_first_refresh():
    vals = _by_range(ms.stock_values(S0))
    assert vals["주식_신랑!A5:G5"][0] == ["순자산", "유가증권 평가", "원화 현금", "외화 예수금(원)", "평가손익", "수익률", "자동투자 인출가능"]
    assert vals["주식_신랑!A6:G6"][0][0] == '=IF(ISNUMBER(메리츠원본!H7),메리츠원본!H7,"-")'
    assert '"아직 갱신 전"' in vals["주식_신랑!A3:B3"][0][1]
    assert vals["주식_신랑!G1:I1"][0][1] is False


def test_meritz_check_compares_documented_relations():
    vals = _by_range(ms.meritz_values(S0))
    b3 = vals["메리츠_신랑!A3:B3"][0][1]
    assert "SUM(메리츠원본!G11:G110)" in b3 and "메리츠원본!H3" in b3
    assert 'SUMIF(메리츠원본!A11:A110,"해외",메리츠원본!G11:G110)' in b3 and "SUM(메리츠원본!N2:N6)" in b3
    assert '"정상"' in b3


def test_meritz_values_included_in_build():
    ranges = {e["range"] for e in build_budget.value_data("a@b.com")}
    assert {"주식_신랑!A16:P16", "메리츠_신랑!A3:B3", "메리츠원본!A10:N10"} <= ranges
