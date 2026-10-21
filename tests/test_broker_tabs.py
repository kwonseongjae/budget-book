"""증권계좌·증권종목 탭 (다증권사 A단계). 주소·문구는 Apps Script(positions.gs)와 같아야 한다."""
import re
from pathlib import Path

import broker_accounts
import broker_positions
import layout
import migrate_couple as mc
import sigol_tabs
import styling

GS = (Path(__file__).parent.parent / "apps-script" / "positions.gs").read_text(encoding="utf-8")
ALL = {t for t, *_ in layout.SHEETS}


def _gs(name):
    return re.search(rf"var {name} = '([^']*)';", GS).group(1)


def _state(titles=ALL):
    return mc.State(titles=set(titles), settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                    invest_charts=2, dash_rows=200, dash_base=46)


def test_addresses_match_the_script():
    for py, gs in [("POS_ACCOUNT", "POS_ACCOUNT"), ("POS_CHECK", "POS_CHECK"), ("POS_RESULT", "POS_RESULT"), ("POS_PASTE", "POS_PASTE"),
                   ("POS_TABLE", "POS_TABLE"), ("ACCT_NAMES", "ACCT_NAMES"), ("ACCT_PASTED", "ACCT_PASTED"),
                   ("ACCOUNT_TAB_PREFIX", "ACCOUNT_TAB_PREFIX")]:
        assert getattr(layout, py) == _gs(gs), py
    assert (layout.BROKER_ACCTS, layout.BROKER_POS) == (_gs("ACCT_TAB"), _gs("POS_TAB")) == ("증권계좌", "증권종목")


def test_tabs_follow_invest_and_have_input_color():
    titles = [t for t, *_ in layout.SHEETS]
    i = titles.index(layout.INVEST)
    assert titles[i + 1:i + 3] == [layout.BROKER_ACCTS, layout.BROKER_POS]
    assert (layout.SHEET_ID[layout.BROKER_ACCTS], layout.SHEET_ID[layout.BROKER_POS]) == (2800, 2810)
    assert broker_accounts in sigol_tabs.MODULES and broker_positions in sigol_tabs.MODULES
    assert styling.TAB_COLORS[layout.BROKER_ACCTS] == styling.INPUT_TAB == styling.TAB_COLORS[layout.BROKER_POS]


def test_account_list_headers_input_cells_and_status_formula():
    vals = {e["range"]: e["values"] for e in broker_accounts.values()}
    assert vals["증권계좌!A4:G4"] == [["이름", "소유자", "증권사", "방식", "예수금", "마지막 붙여넣기", "상태"]]
    assert broker_accounts.INPUTS == ["증권계좌!A5:E14"]
    assert "증권계좌!F5" not in vals and not any(k.startswith("증권계좌!A5") for k in vals)   # 입력·스크립트 칸은 값으로 쓰지 않는다
    assert "붙여넣기 전" in vals["증권계좌!G5"][0][0] and "오래됨" in vals["증권계좌!G5"][0][0]


def test_name_validation_rejects_tab_forbidden_characters_and_duplicates():
    rule = next(r["setDataValidation"]["rule"] for r in broker_accounts.formats()
                if "setDataValidation" in r and r["setDataValidation"]["range"] == layout.a1_to_grid("증권계좌!A5:A14"))
    formula = rule["condition"]["values"][0]["userEnteredValue"]
    assert rule["strict"] is True and rule["condition"]["type"] == "CUSTOM_FORMULA"
    assert "COUNTIF($A$5:$A$14,A5)=1" in formula and "LEN(A5)<=90" in formula
    assert all(ch in formula for ch in r"\[\]*?:/\\")           # 스크립트 validAccountName과 같은 금지 문자


def test_positions_tab_layout_matches_script_cells():
    vals = {e["range"]: e["values"] for e in broker_positions.values()}
    assert vals["증권종목!H5:N5"] == [["계좌", "코드", "종목명", "수량", "매입금액", "평가금액", "통화"]]
    for written in ("증권종목!B2", "증권종목!B3", "증권종목!C3"):
        assert written not in vals                                   # 계좌 선택·체크·결과는 사용자/스크립트 칸
    assert broker_positions.INPUTS == ["증권종목!B2:B3", "증권종목!A6:F205"]
    rules = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]
             for r in broker_positions.formats() if "setDataValidation" in r}
    assert rules[tuple(sorted(layout.a1_to_grid("증권종목!B3").items()))]["condition"]["type"] == "BOOLEAN"
    pick = rules[tuple(sorted(layout.a1_to_grid("증권종목!B2").items()))]
    assert pick["condition"]["type"] == "ONE_OF_RANGE" and pick["condition"]["values"][0]["userEnteredValue"] == "=증권계좌!$A$5:$A$14"


def test_live_migration_adds_both_tabs_once():
    structure, values, _v = mc.plan(_state(ALL - {layout.BROKER_ACCTS, layout.BROKER_POS}))
    added = {r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r}
    assert {layout.BROKER_ACCTS, layout.BROKER_POS} <= added
    assert {"증권계좌!A4:G4", "증권종목!H5:N5"} <= {e["range"] for e in values}
    again = mc.plan(_state())[0]
    assert not {layout.BROKER_ACCTS, layout.BROKER_POS} & {r["addSheet"]["properties"]["title"] for r in again if "addSheet" in r}
