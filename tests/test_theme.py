import invest
import layout
import styling


def _bg(reqs):
    return [(r["repeatCell"]["range"], r["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor"))
            for r in reqs if "repeatCell" in r]


def test_color_tokens():
    assert styling.NAVY_HEAD == {"red": 31 / 255, "green": 56 / 255, "blue": 100 / 255}
    assert styling.PAGE_BG == {"red": 233 / 255, "green": 238 / 255, "blue": 246 / 255}
    assert styling.INPUT_BG == {"red": 252 / 255, "green": 228 / 255, "blue": 236 / 255}
    assert styling.VIEW_TAB == styling.NAVY_HEAD


def test_every_table_header_is_navy_and_no_yellow_left():
    reqs = styling.style_requests()
    heads = [layout.a1_to_grid(a1) for a1, _c in styling.HEADERS]
    got = dict((tuple(sorted(g.items())), c) for g, c in _bg(reqs))
    assert all(got[tuple(sorted(h.items()))] == styling.NAVY_HEAD for h in heads)
    assert not hasattr(styling, "YELLOW")
    assert all(c != {"red": 1.0, "green": 0.95, "blue": 0.6} for _g, c in _bg(reqs))


def test_tab_colors_view_navy_input_pink():
    t = styling.TAB_COLORS
    assert t[layout.DASH] == styling.NAVY_HEAD and t[layout.TXN] == styling.INPUT_TAB_COLOR
    assert t[layout.RECUR] == styling.INPUT_TAB_COLOR and t[layout.SETTINGS] == styling.SETUP_TAB


def test_signed_total_rows_stay_light():
    # 투자 합계 줄(9·12행)은 손익 빨강/파랑 글씨가 보이게 연한 바탕
    total = [c for g, c in _bg(invest.polish_requests()) if g == layout.a1_to_grid("투자!A9:G9")]
    assert total == [styling.LABEL_BG]


import theme


def _fmt_at(reqs, a1):
    """그 범위에 칠한 서식들, 마지막(= 시트에 남는 것)이 맨 앞."""
    g = layout.a1_to_grid(a1)
    return [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs
            if "repeatCell" in r and r["repeatCell"]["range"] == g][::-1]


def test_view_tabs_get_page_background_then_white_tables():
    reqs = theme.requests()
    whole = [r for r in reqs if "repeatCell" in r and set(r["repeatCell"]["range"]) == {"sheetId"}]
    assert {r["repeatCell"]["range"]["sheetId"] for r in whole} == {layout.SHEET_ID[t] for t in theme.VIEW_TABS}
    assert all(r["repeatCell"]["cell"]["userEnteredFormat"]["backgroundColor"] == styling.PAGE_BG for r in whole)
    first_white = next(i for i, r in enumerate(reqs) if "repeatCell" in r
                       and r["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor") == styling.WHITE)
    assert max(reqs.index(r) for r in whole) < first_white  # 바탕 먼저, 그 위에 흰 표
    assert _fmt_at(reqs, "부부!C16:K55")[0]["backgroundColor"] == styling.WHITE


def test_live_positions_shift_dashboard_and_trend_headers():
    reqs = theme.requests(dash_head=19, dash_base=46, trend_head=14)
    assert _fmt_at(reqs, "대시보드!A19:L19")[0]["backgroundColor"] == styling.NAVY_HEAD
    assert _fmt_at(reqs, "추이!A14:W14")[0]["backgroundColor"] == styling.NAVY_HEAD
    assert not _fmt_at(reqs, "대시보드!A60:L60")


def test_input_cells_pink():
    reqs = theme.requests()
    for a1 in ("내역!A2:J5000", "반복!A2:N50", "즐겨찾기!A2:G50", "자산!A2:D50", "설정!J8:J10", "투자!H7:I8",
               "자산현황!A36:A45", "자산현황!D36:G45", "자산현황!I36:I45", "대시보드!B1"):
        assert _fmt_at(reqs, a1)[0]["backgroundColor"] == styling.INPUT_BG, a1


def test_update_badges_show_the_daily_job_date():
    # 2026-10-20: 탭마다 다르던 기준(마지막 내역일·증권 갱신 시각 등)을 매일 아침 자동 실행 날짜 하나로 통일
    vals = {e["range"]: e["values"] for e in theme.badge_values()}
    assert vals["대시보드!L1"] == [["업데이트일"]]
    for a1 in ("대시보드!L2", "투자!I3", "자산기록!G2", "자산현황!I2", "부부!K2"):
        assert vals[a1] == [['=IF(계산!$C$5="","",계산!$C$5)']], a1
    reqs = theme.requests()
    assert _fmt_at(reqs, "대시보드!L1")[0]["backgroundColor"] == styling.NAVY_HEAD


import build_budget
import migrate_couple as mc


def _live_state():
    pie = {"chartId": 1, "spec": {"pieChart": {"legendPosition": "LABELED_LEGEND",
           "series": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 1, "endColumnIndex": 2}]}},
           "domain": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 12, "endColumnIndex": 13}]}}}}}
    return mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                    settings=[], budgets_empty=False, invest_charts=2, pie=pie, dash_rows=96,
                    dash_chart_titles=frozenset(), dash_base=46, trend_head=14)


def test_theme_runs_first_in_live_migration_and_follows_positions():
    structure, values, _v = mc.plan(_live_state())
    page = [i for i, r in enumerate(structure) if "repeatCell" in r and set(r["repeatCell"]["range"]) == {"sheetId"}]
    bg = [i for i, r in enumerate(structure) if "repeatCell" in r and set(r["repeatCell"]["range"]) == {"sheetId"}
          and "backgroundColor" in r["repeatCell"]["cell"]["userEnteredFormat"]]
    labels = [i for i, r in enumerate(structure) if "repeatCell" in r
              and r["repeatCell"]["range"] == layout.a1_to_grid("대시보드!A5:M5")]
    assert page and bg and labels and max(bg) < max(labels)  # 바탕 칠한 뒤 숫자 카드 남색 띠
    assert _fmt_at(structure, "대시보드!A19:L19")[0]["backgroundColor"] == styling.NAVY_HEAD
    assert "대시보드!L2" in {e["range"] for e in values}


def test_new_sheet_build_includes_theme():
    assert any(r in build_budget.visual_requests() for r in theme.requests())
    assert "대시보드!L2" in {e["range"] for e in build_budget.value_data("a@b.com")}


import guide


def test_guide_has_step_table_and_current_colors():
    text = " ".join(a + " " + b for _k, a, b in guide.CONTENT)
    assert "순서대로 시작하기" in text and "D+0" in text and "[자산현황]" in text and "대출" in text
    assert "노란 칸" not in text and "지출 빨강, 수입 파랑" not in text
    assert "분홍 칸" in text and "수입 빨강, 지출 파랑" in text


def test_hint_cells_say_pink():
    _s, values, _v = mc.plan(_live_state())
    hints = {e["range"]: e["values"] for e in values}
    assert hints["대시보드!C1"] == [["◀ 월 이동 ▶"]]
    assert hints["추이!C1"] == [[layout.YEAR_MOVE_HINT]]
