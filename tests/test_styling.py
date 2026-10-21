import guide
import layout
import styling


def _seeds():
    return {s["range"]: s["values"] for s in layout.seed_values("a@b.com")}


def _cell_formats(reqs):
    """repeatCell 요청 → (range, userEnteredFormat) 목록."""
    return [(r["repeatCell"]["range"], r["repeatCell"]["cell"]["userEnteredFormat"])
            for r in reqs if "repeatCell" in r]


def _props(reqs):
    return [r["updateSheetProperties"]["properties"] for r in reqs if "updateSheetProperties" in r]


def test_guide_is_first_tab():
    titles = [s["properties"]["title"] for s in layout.create_body("t")["sheets"]]
    assert titles[:4] == ["사용법", "시작하기", "빠른입력", "내역"]  # 시작하기는 사용법 바로 다음


def test_users_are_couple_names_plus_shared():
    assert _seeds()["설정!E1:E4"] == [["사용자"], ["신랑"], ["신부"], ["공동"]]


def test_currency_column_shown_in_ledger_and_rate_table_hidden():
    # 2026-10-16: 외화 입력(환율 자동)을 쓰려면 내역 통화 칸이 보여야 한다. 통화표(설정 G:H)는 계속 숨김
    assert _seeds()["설정!G1:G6"] == [["통화"], ["KRW"], ["USD"], ["JPY"], ["EUR"], ["CNY"]]
    hidden = [(r["updateDimensionProperties"]["range"]["sheetId"],
               r["updateDimensionProperties"]["range"]["startIndex"],
               r["updateDimensionProperties"]["range"]["endIndex"])
              for r in styling.style_requests()
              if r.get("updateDimensionProperties", {}).get("properties", {}).get("hiddenByUser")]
    assert (layout.SHEET_ID["내역"], 8, 9) not in hidden      # I열 통화는 보임
    assert (layout.SHEET_ID["설정"], 6, 8) in hidden          # G:H 통화·환율


def test_every_visible_sheet_gets_bigger_base_font():
    fmts = _cell_formats(styling.style_requests())
    whole = {g["sheetId"]: f for g, f in fmts if set(g) == {"sheetId"}}
    for title, sid, *_rest, hidden in layout.SHEETS:
        if not hidden:
            assert whole[sid]["textFormat"]["fontSize"] == styling.BASE_FONT == 13, title  # 시골쥐 10pt + 3 (2026-10-14 사용자 요청)


def test_headers_and_titles_larger_than_body():
    fmts = _cell_formats(styling.style_requests())
    header = [f for g, f in fmts if g == layout.a1_to_grid("내역!A1:N1")][0]
    assert header["textFormat"]["fontSize"] == styling.HEADER_FONT and header["textFormat"]["bold"] is True
    title = [f for g, f in fmts if g == layout.a1_to_grid("대시보드!D1:H1")][0]
    assert title["textFormat"]["fontSize"] == styling.TITLE_FONT > styling.BASE_FONT
    kpi = [f for g, f in fmts if g == layout.a1_to_grid("대시보드!A6:I6")][0]
    assert kpi["textFormat"]["fontSize"] == styling.KPI_FONT > styling.BASE_FONT


def test_selectors_are_pink_input():
    fmts = _cell_formats(styling.style_requests())
    pink = [g for g, f in fmts if f.get("backgroundColor") == styling.INPUT_BG]
    for a1 in ("대시보드!B1", "추이!B1", "달력!B1", "검색!B1:B4"):
        assert layout.a1_to_grid(a1) in pink, a1


def test_every_visible_tab_colored_and_views_hide_gridlines():
    props = _props(styling.style_requests())
    colored = {p["sheetId"] for p in props if "tabColor" in p}
    visible = {sid for _t, sid, *_r, hidden in layout.SHEETS if not hidden}
    assert visible <= colored
    no_grid = {p["sheetId"] for p in props if p.get("gridProperties", {}).get("hideGridlines")}
    assert {layout.SHEET_ID[t] for t in ("사용법", "대시보드", "추이", "달력")} <= no_grid


def test_calendar_weekend_colors():
    fmts = _cell_formats(styling.style_requests())
    sun = [f for g, f in fmts if g == layout.a1_to_grid("달력!A4:A16")][0]
    sat = [f for g, f in fmts if g == layout.a1_to_grid("달력!G4:G16")][0]
    assert sun["textFormat"]["foregroundColor"] == styling.RED_TEXT
    assert sat["textFormat"]["foregroundColor"] == styling.BLUE_TEXT


def test_guide_covers_every_visible_tab_and_faq():
    text = "\n".join(str(c) for row in guide.GUIDE_ROWS for c in row)
    for title, _sid, *_r, hidden in layout.SHEETS:
        if not hidden and title != "사용법":
            assert f"[{title}]" in text, title
    for must in ("처음 시작", "자주 묻는 질문", "고정지출", "카드 문자", "이름"):
        assert must in text, must


def test_guide_values_fit_two_columns_and_styles_sections():
    vals = guide.guide_values()
    assert vals[0]["range"] == f"사용법!A1:B{len(guide.GUIDE_ROWS)}"
    assert all(len(r) == 2 for r in vals[0]["values"])
    fmts = _cell_formats(guide.guide_requests())
    sizes = [f["textFormat"]["fontSize"] for _g, f in fmts if "fontSize" in f.get("textFormat", {})]
    assert max(sizes) == styling.TITLE_FONT and min(sizes) == styling.BASE_FONT


def test_merges_never_cross_frozen_first_row():
    for r in styling.style_requests():
        if "mergeCells" in r:
            g = r["mergeCells"]["range"]
            assert not (g["startRowIndex"] == 0 and g["endRowIndex"] > 1), g


def _cf_rules():
    return [r["addConditionalFormatRule"]["rule"] for r in styling.type_color_requests()]


def test_type_colors_on_every_type_column():
    rules = _cf_rules()
    for a1 in ("내역!C2:C5000", "반복!D2:D50", "즐겨찾기!C2:C50", "설정!B2:B60", "검색!C7:C1000"):
        grid = layout.a1_to_grid(a1)
        colors = {r["booleanRule"]["condition"]["values"][0]["userEnteredValue"]: r["booleanRule"]["format"]["backgroundColor"]
                  for r in rules if grid in r["ranges"]}
        assert any("지출" in k for k in colors) and any("수입" in k for k in colors) and any("저축" in k for k in colors), a1
    by_word = {}
    for r in rules:
        f = r["booleanRule"]["condition"]["values"][0]["userEnteredValue"]
        for w in ("지출", "수입", "저축"):
            if f'"{w}"' in f:
                by_word.setdefault(w, set()).add(tuple(sorted(r["booleanRule"]["format"]["backgroundColor"].items())))
    assert by_word["지출"] == {tuple(sorted(styling.EXP_BG.items()))}
    assert by_word["수입"] == {tuple(sorted(styling.INC_BG.items()))}
    assert by_word["저축"] == {tuple(sorted(styling.SAVE_BG.items()))}


def test_txn_amount_colored_by_type():
    grid = layout.a1_to_grid("내역!H2:H5000")
    assert any(grid in r["ranges"] for r in _cf_rules())


def test_dashboard_kpi_labels_are_navy_bars():
    fmts = dict((tuple(sorted(g.items())), f) for g, f in _cell_formats(styling.style_requests()))
    label = fmts[tuple(sorted(layout.a1_to_grid("대시보드!A5:I5").items()))]
    assert label["backgroundColor"] == styling.NAVY_HEAD and label["textFormat"]["foregroundColor"] == styling.WHITE


def test_guide_requests_can_start_from_new_rows():
    full = guide.guide_requests()
    tail = guide.guide_requests(start=len(guide.CONTENT) - 2)
    assert len(tail) < len(full)
    starts = [r["repeatCell"]["range"]["startRowIndex"] for r in tail if "repeatCell" in r
              and r["repeatCell"]["range"]["endRowIndex"] - r["repeatCell"]["range"]["startRowIndex"] == 1]
    assert min(starts) == len(guide.CONTENT) - 2


def test_guide_explains_meritz_owner_and_colors():
    text = "\n".join(str(c) for row in guide.GUIDE_ROWS for c in row)
    for must in ("[주식_신랑]", "[주식_신부]", "소유자", "자동 갱신 켜기", "자동투자", "수익이 빨강"):
        assert must in text, must


def test_guide_states_key_exposure_risk_and_reissue():
    row = [r for r in guide.CONTENT if r[1] == "키 입력 (각자)"][0][2]
    assert "스크립트 코드를 고칠 수 있" in row
    assert "재발급" in row
