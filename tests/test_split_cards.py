"""같은 이름 자산(하나카드 신랑·신부)을 '이름_소유자'로 나누는 한 번짜리 정리 (2026-10-14 사용자 선택)."""
import layout
import split_names


ASSETS = [["현금", "현금"], ["하나카드", "카드", "", "300000", "", "", "", "", "신랑"],
          ["하나카드", "카드", "", "", "", "", "", "", "신부"], ["삼성카드", "카드", "", "", "", "", "", "", "신랑"]]


def test_renames_assets_and_each_row_by_its_user():
    data = {"assets": ASSETS,
            "txn": [["2026-10-07", "신부", "지출", "통신비", "", "하나카드", "", 95280],
                    ["2026-10-08", "신랑", "이체", "", "", "주거래통장", "하나카드", 1000],
                    ["2026-10-09", "공동", "지출", "식비", "", "하나카드", "", 5000]],
            "recur": [[True, 8, "신부", "지출", "통신비", "하나카드", 68050]],
            "fav": [[False, "신랑", "지출", "식비", "하나카드", 4500]],
            "cards": [["하나카드 (신랑)"], ["삼성카드"], ["하나카드 (신부)"]]}
    changes, unresolved = split_names.plan(data)
    got = {(c.range, c.new) for c in changes}
    assert ("자산!A3", "하나카드_신랑") in got and ("자산!A4", "하나카드_신부") in got
    assert ("내역!F2", "하나카드_신부") in got and ("내역!G3", "하나카드_신랑") in got
    assert ("반복!F2", "하나카드_신부") in got and ("즐겨찾기!E2", "하나카드_신랑") in got
    assert ("카드!A5", "하나카드_신랑") in got and ("카드!A7", "하나카드_신부") in got
    assert unresolved == ["내역!F4 (공동, 하나카드)"]  # 공동은 어느 카드인지 사람이 골라야 함
    assert not any(c.range == "자산!A5" for c in changes)  # 이름이 하나뿐인 자산은 그대로


def test_nothing_to_do_when_names_unique():
    data = {"assets": [["하나카드_신랑", "카드", "", "", "", "", "", "", "신랑"]], "txn": [], "recur": [], "fav": [], "cards": []}
    assert split_names.plan(data) == ([], [])


def test_duplicate_asset_names_warned_by_validation():
    rule = [r["setDataValidation"]["rule"] for r in layout.validation_requests()
            if r["setDataValidation"]["range"] == layout.a1_to_grid("자산!A2:A50")]
    assert rule and rule[0]["condition"]["values"][0]["userEnteredValue"] == "=COUNTIF($A$2:$A$50,A2)=1"
    assert "_" in rule[0].get("inputMessage", "")
