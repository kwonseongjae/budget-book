import json
from pathlib import Path

import verify_meritz as vm

EXP = json.loads((Path(__file__).parent / "fixtures" / "meritz_expected.json").read_text(encoding="utf-8"))


def test_raw_data_writes_only_raw_blocks_and_asset_link_row():
    data = vm.raw_data(EXP, 46000.5)
    ranges = {d["range"] for d in data}
    assert ranges == {"메리츠원본!H1:H8", "메리츠원본!B2:E5", "메리츠원본!J2:N2",
                      f"메리츠원본!A11:N{10 + len(EXP['holdings'])}", "자산!A5:D5", "자산!G5"}
    h = [d for d in data if d["range"] == "메리츠원본!H1:H8"][0]["values"]
    assert [r[0] for r in h] == EXP["summary"] + [46000.5]


def test_checks_cover_net_profit_rate_count_and_asset():
    c = vm.checks(EXP)
    assert c["주식_신랑!A6"] == 6092500
    assert c["주식_신랑!E6"] == 168500
    assert abs(c["주식_신랑!F6"] - 168500 / 5084000) < 1e-9
    assert c["메리츠_신랑!B3"] == "정상"
    assert c["메리츠_신랑!D6"] == "5개 (3 / 1)"
    assert c["자산!E5"] == 6092500
