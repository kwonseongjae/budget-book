"""[시작하기] 탭: 처음 쓸 때 할 일을 ✓/✗로 (2026-10-16 사용성 점검 B2)."""
import checklist
import formulas
import layout
import migrate_couple as mc
import sigol_tabs
import theme

ALL = {t for t, *_ in layout.SHEETS}
SID = layout.SHEET_ID[layout.CHECKLIST]


def _vals(entries):
    return {e["range"]: e["values"] for e in entries}


def test_tab_sits_right_after_guide_with_own_id():
    titles = [t for t, *_ in layout.SHEETS]
    assert titles[titles.index(layout.GUIDE) + 1] == layout.CHECKLIST == "시작하기"
    ids = [sid for _t, sid, *_ in layout.SHEETS]
    assert len(ids) == len(set(ids)) and SID == 2600


def test_registered_as_sigol_module_without_update_badge():
    assert checklist in sigol_tabs.MODULES and layout.CHECKLIST in sigol_tabs.NAMES
    assert layout.CHECKLIST in theme.VIEW_TABS and layout.CHECKLIST not in theme.BADGES


def test_every_item_has_required_flag_status_and_link():
    vals = _vals(checklist.values())
    assert vals["시작하기!A4:F4"] == [["항목", "구분", "상태", "지금", "하는 법", "바로가기"]]
    assert len(checklist.ITEMS) >= 12
    for n in range(checklist.FIRST, checklist.LAST + 1):
        row = vals[f"시작하기!A{n}:F{n}"][0]
        assert row[0] and row[1] in ("필수", "선택") and row[4]
        assert row[2].startswith("=IF(") and '"✓ 완료"' in row[2] and f"B{n}" in row[2]
        assert row[3].startswith("=")
        assert row[5].startswith('=HYPERLINK("#gid=')


def test_progress_line_counts_required_and_optional_separately():
    p = _vals(checklist.values())["시작하기!A2"][0][0]
    assert p.startswith("=") and 'COUNTIFS(B5:B' in p and '"필수"' in p and '"선택"' in p and "✓*" in p


def test_checks_reuse_the_same_counts_as_the_dashboard_banner():
    banner = formulas.attention_formula()
    for expr in (formulas.bad_rows_expr(), formulas.negative_accounts_expr(), formulas.blank_recurring_expr()):
        assert expr in banner
    body = " ".join(" ".join(r[0][2:4]) for r in (_vals(checklist.values())[f"시작하기!A{n}:F{n}"] for n in range(5, checklist.LAST + 1)))
    assert formulas.bad_rows_expr() in body and formulas.negative_accounts_expr() in body
    assert formulas.missing_payments_count_expr() in body


def test_how_to_column_wraps_and_is_pinned_and_blank_recurring_is_required():
    import fit_dims
    assert (SID, 4) in fit_dims.PINNED
    wrap = [r for r in checklist.formats() if "repeatCell" in r]
    assert wrap and wrap[0]["repeatCell"]["range"] == layout.a1_to_grid(f"시작하기!E5:E{checklist.LAST}")
    item = next(i for i in checklist.ITEMS if "반복 금액" in i[0])
    assert item[1] == "필수" and formulas.blank_recurring_expr() in item[2]
    assert checklist.SECTIONS == []  # 안내 문장은 굵은 구역 제목이 아니라 본문


def test_status_colors_added_once_with_the_tab():
    rules = [r for r in checklist.formats() if "addConditionalFormatRule" in r]
    texts = {r["addConditionalFormatRule"]["rule"]["booleanRule"]["condition"]["values"][0]["userEnteredValue"] for r in rules}
    assert texts == {"✓", "✗", "△"}


def test_live_migration_creates_tab_once():
    state = mc.State(titles=ALL - {layout.CHECKLIST}, settings_cols=13, asset_cols=12, networth_charts=1, settings=[],
                     budgets_empty=False, invest_charts=2, dash_base=46)
    structure, values, _vi = mc.plan(state)
    assert [r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r] == [layout.CHECKLIST]
    assert "시작하기!A5:F5" in _vals(values)
    again = mc.plan(state._replace(titles=ALL))
    assert not [r for r in again[0] if "addSheet" in r] and not [r for r in again[0] if "addConditionalFormatRule" in r]
    assert "시작하기!A5:F5" in _vals(again[1])  # 수식은 매번 다시 (바뀐 문구 반영)


def test_guide_points_new_users_to_the_checklist():
    import guide
    assert any("시작하기" in a or "시작하기" in b for _k, a, b in guide.CONTENT[:12])


def test_card_payment_item_is_optional_and_reads_card_tab():
    item = next(i for i in checklist.ITEMS if i[0] == "카드 결제일·계좌")
    assert item[1] == "선택" and "카드!$I$5:$I$40" in item[2] and "카드!$J$5:$J$40" in item[2] and item[5] == "카드"


def test_guide_explains_automatic_card_payment():
    import guide
    text = " ".join(f"{a} {b}" for _k, a, b in guide.CONTENT)
    assert "결제 계좌 → 카드" in text and "카드 잔액이 0" in text


def test_card_payment_account_is_picked_from_assets():
    import cards
    rules = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]
             for r in cards.formats() if "setDataValidation" in r}
    rule = rules[tuple(sorted(layout.a1_to_grid(f"카드!J{cards.FIRST}:J{cards.LAST}").items()))]
    assert rule["condition"]["values"][0]["userEnteredValue"] == layout.PAY_LIST and rule["strict"] is False


def test_live_migration_reapplies_card_payment_account_dropdown():
    state = mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                     invest_charts=2, dash_base=46)
    ranges = [r["setDataValidation"]["range"] for r in mc.plan(state)[0] if "setDataValidation" in r]
    import cards
    assert layout.a1_to_grid(f"카드!J{cards.FIRST}:J{cards.LAST}") in ranges
