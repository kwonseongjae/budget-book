"""사용성 점검 A14·A15·A18 마무리 (2026-10-21)."""
import layout
import migrate_couple as mc
import views


def _state():
    return mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                    budgets_empty=False, invest_charts=2, dash_rows=200, dash_base=46)


def _search(values):
    return {e["range"]: e["values"] for e in values if e["range"].startswith("검색!")}


def test_search_totals_skip_error_rows_like_dashboard_and_say_so():
    s = _search(views.search_totals())
    assert "ISNUMBER(내역!L2:L)" in s["검색!D1:E2"][0][1] and "ISNUMBER(내역!L2:L)" in s["검색!D1:E2"][1][1]
    note = s["검색!D3"][0][0]
    assert "합계에서 제외" in note and "ISNUMBER" in note


def test_search_totals_rewritten_on_live_migration():
    ranges = {e["range"] for e in mc.plan(_state())[1]}
    assert {"검색!D1:E2", "검색!D3"} <= ranges


def test_txn_dropdowns_reject_unknown_values():
    strict = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]["strict"]
              for r in layout.validation_requests() if "setDataValidation" in r}
    key = lambda col: tuple(sorted(layout.a1_to_grid(f"내역!{col}2:{col}5000").items()))
    for col in "BCFGI":
        assert strict[key(col)], col
    assert not strict[key("D")]  # 카테고리는 행의 구분별 목록(스크립트)이라 경고만


def test_strict_dropdowns_reapplied_to_live_sheet():
    structure = mc.plan(_state())[0]
    ranges = {c: r["setDataValidation"]["rule"]["strict"]
              for r in structure if "setDataValidation" in r
              for c in "BCFGI" if r["setDataValidation"]["range"] == layout.a1_to_grid(f"내역!{c}2:{c}5000")}
    assert ranges and all(ranges.values()) and len(ranges) == 5


def test_favorites_guide_explains_changing_amounts():
    import guide
    text = next(t for a, t in guide.GUIDE_ROWS if a == "[즐겨찾기]")
    assert "금액이 달라" in text and "[내역]" in text
