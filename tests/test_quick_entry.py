"""[빠른입력] 탭: 폰에서 내역 맨 아래 줄을 찾지 않고 값만 고르고 '추가' 체크 (2026-10-16 사용성 점검 B1)."""
import checklist
import layout
import migrate_couple as mc
import quick_entry
import sigol_tabs
import styling
import theme

ALL = {t for t, *_ in layout.SHEETS}
SID = layout.SHEET_ID[layout.QUICK]


def _vals(entries):
    return {e["range"]: e["values"] for e in entries}


def _validations():
    return {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]
            for r in quick_entry.formats() if "setDataValidation" in r}


def _rule(a1):
    return _validations()[tuple(sorted(layout.a1_to_grid(f"빠른입력!{a1}").items()))]


def test_tab_after_checklist_with_input_tab_color_and_no_badge():
    titles = [t for t, *_ in layout.SHEETS]
    assert titles[titles.index(layout.CHECKLIST) + 1] == layout.QUICK == "빠른입력" and SID == 2700
    assert quick_entry in sigol_tabs.MODULES and layout.QUICK not in theme.BADGES
    assert styling.TAB_COLORS[layout.QUICK] == styling.INPUT_TAB


def test_form_labels_and_input_cells_match_the_script_rows():
    vals = _vals(quick_entry.values())
    labels = [vals[f"빠른입력!A{r}"][0][0] for r in range(4, 14)]
    assert [l.split(" (")[0] for l in labels] == ["날짜", "사용자", "구분", "카테고리", "금액", "통화", "결제수단", "입금자산", "메모", "추가"]
    assert quick_entry.INPUTS == ["빠른입력!B4:B13"]  # 스크립트가 읽는 B4:B12 + 체크박스 B13
    assert vals["빠른입력!A14"] == [["결과"]] and "빠른입력!B14" not in vals  # 결과 칸은 스크립트가 쓴다 (값으로 덮어쓰지 않기)
    for a1 in ("B4", "B5", "B6", "B10"):
        assert f"빠른입력!{a1}" not in vals  # 사용자·구분·결제수단은 다음 입력에 남기는 값이라 덮어쓰면 안 됨


def test_dropdowns_follow_the_ledger_lists():
    assert _rule("B5")["condition"]["values"][0]["userEnteredValue"] == layout.USERS
    assert _rule("B6")["condition"]["values"][0]["userEnteredValue"] == layout.TYPES
    assert _rule("B10")["condition"]["values"][0]["userEnteredValue"] == layout.PAY_LIST
    assert _rule("B11")["condition"]["values"][0]["userEnteredValue"] == layout.ASSET_LIST
    assert _rule("B9")["condition"]["values"][0]["userEnteredValue"] == layout.CURRENCIES
    assert _rule("B13")["condition"]["type"] == "BOOLEAN"
    assert _rule("B4")["condition"]["type"] == "DATE_IS_VALID"


def test_category_dropdown_reads_hidden_list_that_follows_the_chosen_type():
    assert _rule("B7")["condition"]["values"][0]["userEnteredValue"] == "=$D$5:$D$60"
    f = _vals(quick_entry.values())["빠른입력!D5"][0][0]
    assert 'IF($B$6="","지출",$B$6)' in f and "설정!$B$2:$B$60" in f and "FILTER(" in f
    assert 3 in quick_entry.HIDDEN


def test_today_month_and_recent_blocks_use_ledger_krw_column():
    vals = _vals(quick_entry.values())
    today, month = vals["빠른입력!A17:B17"][0][1], vals["빠른입력!A18:B18"][0][1]
    assert "내역!$K$2:$K$5000" in today and "TODAY()" in today and '"지출"' in today
    assert "계산!$C$2" in month and "내역!$L$2:$L$5000" in month
    recent = vals["빠른입력!A21"][0][0]
    assert "SEQUENCE(ROWS(내역!$A$2:$A$5000),1,2)" in recent and "ROW(내역" not in recent  # 시트가 5000행보다 짧아도 크기가 맞게
    # HSTACK 열 순서(줄번호·날짜·사용자·카테고리·메모·금액)와 보여 주는 순서가 맞아야 한다 — 어긋나면 금액 자리에 메모가 나온다
    assert 'TEXT(INDEX(x,,2),"m/d")&" · "&INDEX(x,,4)&" · "&TEXT(INDEX(x,,6),"#,##0")&"원 · "&INDEX(x,,5)&" ("&INDEX(x,,3)&")"' in recent
    assert "HSTACK(SEQUENCE(ROWS(내역!$A$2:$A$5000),1,2),내역!$A$2:$A$5000,내역!$B$2:$B$5000,내역!$D$2:$D$5000,내역!$J$2:$J$5000,내역!$K$2:$K$5000)" in recent
    assert "ARRAY_CONSTRAIN(" in recent and ",5," in recent and "SORT(" in recent and "내역!$K$2:$K$5000" in recent.replace("K2:K5000", "$K$2:$K$5000")


def test_live_migration_creates_tab_once_and_never_overwrites_sticky_inputs():
    state = mc.State(titles=ALL - {layout.QUICK}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                     budgets_empty=False, invest_charts=2, dash_base=46)
    structure, values, _vi = mc.plan(state)
    assert [r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r].count(layout.QUICK) == 1
    again_s, again_v, _ = mc.plan(state._replace(titles=ALL))
    assert not [r for r in again_s if "addSheet" in r]
    ranges = set(_vals(again_v))
    assert not {f"빠른입력!B{r}" for r in range(4, 14)} & ranges  # 사용자가 쓰는 칸은 매번 다시 쓰지 않는다


def test_guide_points_phone_users_to_the_quick_tab():
    import guide
    assert any("빠른입력" in a or "빠른입력" in b for _k, a, b in guide.CONTENT[:12])


def test_checklist_unaffected_by_new_tab_order():
    assert checklist.S == "시작하기"
