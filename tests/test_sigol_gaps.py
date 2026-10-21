"""남은 시골쥐 차이 + 미뤄 둔 작은 문제 (2026-10-14)."""
import asset_status
import build_budget
import formulas
import layout
import migrate_couple as mc
import theme

ALL = {t for t, *_ in layout.SHEETS}


def _state(**kw):
    base = dict(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                invest_charts=2, dash_rows=200, dash_chart_titles=frozenset({"수입 대비 고정비·변동비", "분류별 수입"}),
                dash_base=46, trend_head=14)
    return mc.State(**{**base, **kw})


def _rule(a1):
    g = layout.a1_to_grid(a1)
    return [r["setDataValidation"]["rule"] for r in layout.validation_requests() if r["setDataValidation"]["range"] == g]


def _last_bg(reqs, a1):
    g = layout.a1_to_grid(a1)
    bg = [r["repeatCell"]["cell"]["userEnteredFormat"]["backgroundColor"] for r in reqs if "repeatCell" in r
          and r["repeatCell"]["range"] == g and "backgroundColor" in r["repeatCell"]["cell"]["userEnteredFormat"]]
    return bg[-1] if bg else None


# 달러통장: [자산] J 통화 · K 외화 잔액 → 현재 잔액 = 외화 잔액 × 실시간 환율
def test_assets_have_currency_and_foreign_balance_columns():
    assert next(c for t, _s, _r, c, _h in layout.SHEETS if t == "자산") == 12
    seeds = {e["range"]: e["values"] for e in layout.seed_values("")}
    assert seeds["자산!J1:K1"] == [["통화", "외화 잔액"]]
    assert _rule("자산!K2:K50")[0]["condition"]["type"] == "NUMBER_GREATER_THAN_EQ"


def test_foreign_balance_converted_with_live_rate():
    e = {x["range"]: x["values"] for x in formulas.asset_values()}["자산!E1:E2"][1][0]
    assert "J2:J,K2:K" in e and 'GOOGLEFINANCE("CURRENCY:"&cur&"KRW")' in e


def test_payment_method_choices_exclude_loans_pensions_and_other():
    helper = {x["range"]: x["values"] for x in formulas.asset_values()}["자산!L1:L2"][1][0]
    assert '{"대출","연금","기타"}' in helper
    for a1 in ("내역!F2:F5000", "반복!F2:F50", "즐겨찾기!E2:E50"):
        assert _rule(a1)[0]["condition"]["values"][0]["userEnteredValue"] == "=자산!$L$2:$L$50", a1
    assert _rule("내역!G2:G5000")[0]["condition"]["values"][0]["userEnteredValue"] == layout.ASSET_LIST  # 입금자산은 대출 포함


def test_live_assets_widened_once_and_payment_rules_refreshed_every_run():
    s1, v1, _ = mc.plan(_state(asset_cols=9))
    assert {"appendDimension": {"sheetId": 300, "dimension": "COLUMNS", "length": 3}} in s1
    assert "자산!J1:K1" in {e["range"] for e in v1}
    s2, _v2, _ = mc.plan(_state())
    assert not any("appendDimension" in r and r["appendDimension"]["sheetId"] == 300 for r in s2)
    assert any(r.get("setDataValidation", {}).get("range") == layout.a1_to_grid("내역!F2:F5000") for r in s2)


# 월별 저축률 가로형 표 (시골쥐 대시보드처럼 그래프 아래)
def test_status_horizontal_monthly_table_under_chart():
    vals = {e["range"]: e["values"] for e in asset_status.values()}
    # 2026-10-14 한 화면 폭 요청으로 그래프 띠 옆(L17)에서 맨 아래 A81로 옮김 (test_one_page)
    assert vals["자산현황!A67:B67"] == [["구분", "=TRANSPOSE(A13:A24)"]]
    assert vals["자산현황!A71:B71"] == [["저축률", "=TRANSPOSE(E13:E24)"]]


# 작은 문제
def test_calendar_grid_is_white_table():
    assert _last_bg(theme.requests(19, 46, 14), "달력!A5:G16") == theme.WHITE


def test_new_sheet_build_keeps_checkbox_inputs_pink():
    # 새로 만들 때 theme가 styling(체크박스 연두)보다 먼저 와서 분홍이 덮였다 → 운영처럼 styling 뒤에 theme
    def covers(g, sid, r, c):
        return (g.get("sheetId") == sid and g.get("startRowIndex", 0) <= r < g.get("endRowIndex", 10 ** 6)
                and g.get("startColumnIndex", 0) <= c < g.get("endColumnIndex", 10 ** 6))
    bg = [r["repeatCell"]["cell"]["userEnteredFormat"]["backgroundColor"] for r in build_budget.visual_requests()
          if "repeatCell" in r and covers(r["repeatCell"]["range"], 800, 1, 0)
          and "backgroundColor" in r["repeatCell"]["cell"]["userEnteredFormat"]]
    assert bg[-1] == theme.INPUT_BG  # 반복!A2 (사용 체크박스)


def test_foreign_currency_inputs_marked_pink():
    assert "자산!J2:K50" in theme.INPUTS
