"""탭마다 다르던 '업데이트일'을 하나로: 매일 아침 자동 실행이 마지막으로 돈 날 (2026-10-20 사용자 요청)."""
import checklist
import formulas
import guide
import layout
import theme


def test_every_tab_badge_shows_the_same_daily_stamp():
    assert theme.DAILY_STAMP == '=IF(계산!$C$5="","",계산!$C$5)'
    for tab, (_label, _date, pattern) in theme.BADGES.items():
        assert theme.BADGE_FORMULAS[tab] == theme.DAILY_STAMP, tab
        assert pattern == "yyyy-mm-dd", tab  # 투자의 '시각'·자산기록의 '월' 서식도 날짜로 통일
    assert {layout.DASH, layout.ASSET_STATUS, layout.COUPLE, layout.INVEST, layout.NETWORTH} <= set(theme.BADGES)


def test_calc_tab_labels_the_stamp_cell_but_never_writes_its_value():
    vals = {e["range"]: e["values"] for e in formulas.calc_values()}
    assert vals["계산!C4"] == [["자동 갱신일 (스크립트가 씀)"]]
    assert not [r for r in vals if r.startswith("계산!C5")]  # 값은 dailyJob만 쓴다(덮어쓰면 갱신 여부를 알 수 없다)


def test_checklist_uses_the_stamp_for_automatic_run():
    item = next(i for i in checklist.ITEMS if i[0] == "자동 갱신 켜짐")
    assert "계산!$C$5" in item[2] and "TODAY()" in item[2]


def test_guide_explains_the_update_date():
    text = " ".join(f"{a} {b}" for _k, a, b in guide.CONTENT)
    assert "업데이트일" in text and "자동 실행이 멈춘" in text


def test_live_migration_writes_the_stamp_label_only():
    import migrate_couple as mc
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                     budgets_empty=False, invest_charts=2, dash_base=46)
    ranges = [e["range"] for e in mc.plan(state)[1]]
    assert "계산!C4" in ranges and not [r for r in ranges if r.startswith("계산!C5")]
