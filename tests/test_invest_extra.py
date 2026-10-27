"""투자기록 14열·계좌별 기록 탭 (다증권사 B단계)."""
import layout
import migrate_couple as mc

ALL = {t for t, *_ in layout.SHEETS}


def _state(titles=ALL, grid=None):
    return mc.State(titles=set(titles), settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                    invest_charts=2, dash_rows=200, dash_base=46, grid=grid or {})


def test_log_has_14_columns_and_detail_tab_is_hidden_internal():
    props = {t: (sid, rows, cols, hidden) for t, sid, rows, cols, hidden in layout.SHEETS}
    assert props[layout.INVEST_LOG][2] == 14 and props[layout.BROKER_ACCTS][2] == 12
    assert props[layout.INVEST_LOG_DETAIL] == (2830, 5000, 4, True)


def test_headers_for_new_log_columns_and_detail_tab():
    import invest
    assert invest.LOG_HEAD[-2:] == ["기타 평가", "기타 원금"] and len(invest.LOG_HEAD) == 14
    ranges = {e["range"]: e["values"] for e in mc.plan(_state())[1]}
    assert ranges["투자기록_계좌!A1:D1"] == [["날짜", "계좌", "평가", "원금"]]
    assert ranges[f"{layout.INVEST_LOG}!A1:N1"][0][-2:] == ["기타 평가", "기타 원금"]


def test_live_tabs_grow_to_new_widths_once_and_detail_tab_is_added():
    grid = {layout.SHEET_ID[layout.INVEST_LOG]: (1000, 12), layout.SHEET_ID[layout.BROKER_ACCTS]: (40, 9)}
    st = _state(ALL - {layout.INVEST_LOG_DETAIL}, grid)
    structure = mc.plan(st)[0]
    grow = {r["appendDimension"]["sheetId"]: r["appendDimension"]["length"] for r in structure if "appendDimension" in r}
    assert grow[layout.SHEET_ID[layout.INVEST_LOG]] == 2 and grow[layout.SHEET_ID[layout.BROKER_ACCTS]] == 3
    assert layout.INVEST_LOG_DETAIL in {r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r}
    done = {layout.SHEET_ID[layout.INVEST_LOG]: (1000, 14), layout.SHEET_ID[layout.BROKER_ACCTS]: (40, 12)}
    again = {r["appendDimension"]["sheetId"] for r in mc.plan(_state(grid=done))[0] if "appendDimension" in r}
    assert layout.SHEET_ID[layout.INVEST_LOG] not in again and layout.SHEET_ID[layout.BROKER_ACCTS] not in again


def test_account_list_has_per_account_value_columns_with_blank_safe_formulas():
    import broker_accounts
    vals = {e["range"]: e["values"] for e in broker_accounts.values()}
    assert vals["증권계좌!A4:L4"][0][7:] == ["종목평가", "원금(매입)", "평가금액(총)", "손익", "수익률"]
    row5 = vals["증권계좌!H5:L14"][0]
    h, i, j, k, l = row5
    assert 'SUMIFS(증권종목표!$F$2:$F$1001,증권종목표!$A$2:$A$1001,$A5)' in h
    assert 'COUNTIFS(증권종목표!$A$2:$A$1001,$A5,증권종목표!$E$2:$E$1001,"")>0' in i       # 매입금액이 빈 종목이 있으면 원금은 비움
    assert 'COUNTIF(증권종목표!$A$2:$A$1001,$A5)=0' in j and 'N(E5)' in j                     # 종목이 없으면(붙여넣기 전) 총평가도 빈칸
    assert k == '=IF(OR(J5="",I5=""),"",H5-I5)' and l == '=IF(OR(K5="",N(I5)=0),"",K5/I5)'
    assert len(vals["증권계좌!H5:L14"]) == 10
    assert not any(a in vals for a in ("증권계좌!A5", "증권계좌!E5", "증권계좌!F5"))          # 입력·스크립트 칸은 값으로 쓰지 않는다
