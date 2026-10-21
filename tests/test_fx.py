"""환율 자동: [설정] 통화표에 USD·JPY·EUR·CNY를 미리 넣어 둔다 (환율은 H열 GOOGLEFINANCE가 자동). 2026-10-16 사용성 점검 A2."""
import layout
import migrate_couple as mc

ALL = {t for t, *_ in layout.SHEETS}


def _vals(entries):
    return {e["range"]: e["values"] for e in entries}


def _state(**kw):
    return mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                    invest_charts=2, dash_base=46, **kw)


def test_new_workbook_seeds_common_currencies():
    seed = _vals(layout.seed_values(""))
    assert seed["설정!G1:G6"] == [["통화"], ["KRW"], ["USD"], ["JPY"], ["EUR"], ["CNY"]]


def test_live_currency_table_filled_only_when_empty():
    filled = _vals(mc.plan(_state(settings_fx=()))[1])
    assert filled["설정!G3:G6"] == [["USD"], ["JPY"], ["EUR"], ["CNY"]]
    kept = _vals(mc.plan(_state(settings_fx=("USD", "GBP")))[1])
    assert "설정!G3:G6" not in kept  # 사용자가 이미 적은 통화표는 건드리지 않는다


def test_rate_column_is_automatic_for_every_listed_currency():
    import formulas
    rate = _vals(formulas.settings_values())["설정!H1:H20"]
    assert "GOOGLEFINANCE" in rate[2][0] and rate[2][0].count("{") == 0  # H3(USD 자리)도 수식


def test_live_ledger_currency_column_unhidden_once():
    unhide = lambda st: [r for r in mc.plan(st)[0] if "updateDimensionProperties" in r
                         and r["updateDimensionProperties"]["range"] == {"sheetId": layout.SHEET_ID["내역"], "dimension": "COLUMNS",
                                                                          "startIndex": 8, "endIndex": 9}
                         and r["updateDimensionProperties"]["properties"] == {"hiddenByUser": False}]
    assert len(unhide(_state(txn_currency_hidden=True))) == 1
    assert not unhide(_state(txn_currency_hidden=False))  # 이미 보이면 아무것도 안 함
    assert not unhide(_state(txn_currency_hidden=True, settings_fx=("USD",)))  # 통화표를 이미 채운 뒤 사용자가 숨기면 그대로


def test_guide_explains_currency_column():
    import guide
    assert any("통화" in a and "환율" in b for _k, a, b in guide.CONTENT)
