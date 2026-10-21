"""한투 ISA 종목 목록을 주식투자 탭에 종목별로 (2026-10-14 사용자: ISA 계좌 목록과 금액 제대로 반영)."""
import layout
import migrate_couple as mc
import stock_sectors

ALL = {t for t, *_ in layout.SHEETS}


def test_hidden_holdings_tab_fits_two_slots_of_100():
    t, _sid, rows, cols, hidden = next(s for s in layout.SHEETS if s[0] == layout.KIS_HOLD)
    assert t == "한투종목" and rows >= 101 and cols >= 11 and hidden


def test_holdings_tab_added_once_with_header():
    state = mc.State(titles=ALL - {layout.KIS_HOLD}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                     budgets_empty=False, invest_charts=2, dash_base=46)
    structure, values, _v = mc.plan(state)
    adds = [r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r]
    assert adds == ["한투종목"]
    vals = {e["range"]: e["values"] for e in values}
    assert vals["한투종목!A1:K1"][0][:5] == ["신랑 구분", "코드", "종목명", "매입금액", "평가금액"]
    again = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_base=46)
    assert not [r for r in mc.plan(again)[0] if "addSheet" in r]


def test_stock_sectors_lists_kis_holdings_per_owner_and_drops_total_line():
    h = stock_sectors.holdings()
    assert "한투종목!B2:B101" in h and "한투종목!H2:H101" in h
    assert '"신랑"' in h and '"신부"' in h
    assert 'LEFT(자산!G2:G50,2)<>"메리"' not in h and '(자산!G2:G50="")' in h  # 연동된 ISA 총액 줄은 종목 줄로 대체
