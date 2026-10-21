"""행·열을 데이터 크기에 맞춤 (2026-10-14 사용자 요청)."""
import fit_dims


def _cell(text, size=13, bold=False):
    return {"formattedValue": text, "effectiveFormat": {"textFormat": {"fontSize": size, "bold": bold}}}


def _tab(rows, widths, hidden=(), skip=()):
    return {"sheetId": 7, "rows": rows, "widths": list(widths), "hidden": set(hidden), "skip": set(skip)}


def _widths(reqs):
    return {r["updateDimensionProperties"]["range"]["startIndex"]: r["updateDimensionProperties"]["properties"]["pixelSize"]
            for r in reqs if "updateDimensionProperties" in r}


def test_korean_wider_than_digits_and_bigger_font_wider():
    assert fit_dims.text_px("가나다", 13) > fit_dims.text_px("123", 13)
    assert fit_dims.text_px("가나다", 17) > fit_dims.text_px("가나다", 13)
    assert fit_dims.text_px("가나", 13, bold=True) > fit_dims.text_px("가나", 13)


def test_column_fits_longest_value_and_ignores_titles_and_long_notes():
    rows = [[_cell("우리집 가계부 — 이달의 살림 제목은 넘쳐도 됨", 17)],
            [_cell("카테고리")], [_cell("주거비")],
            [_cell("이 칸은 서른 글자가 넘는 긴 안내문이라 열 너비 계산에서 빠집니다 정말로")]]
    w = _widths(fit_dims.plan(_tab(rows, [300], skip={(0, 0)})))[0]
    assert w == fit_dims.text_px("카테고리", 13)


def test_clamped_and_hidden_or_empty_columns_untouched():
    # 0열: 긴 값(옆 칸에 값이 있어 넘치지 않음) → 최대 폭, 2열: 숨김, 3열: 빈 간격 열
    rows = [[_cell("가" * 29), _cell("y"), _cell("1"), _cell("")]]
    w = _widths(fit_dims.plan(_tab(rows, [100, 100, 100, 20], hidden={2})))
    assert w[0] == fit_dims.MAX_W and 2 not in w and 3 not in w


def test_text_overflowing_into_empty_neighbour_does_not_widen():
    rows = [[_cell("구역 제목처럼 옆으로 넘치는 글"), _cell("")], [_cell("값"), _cell("1")]]
    w = _widths(fit_dims.plan(_tab(rows, [100, 100])))
    assert w[0] == fit_dims.MIN_W


def test_narrow_values_get_minimum_and_unchanged_width_sends_nothing():
    rows = [[_cell("1")]]
    assert _widths(fit_dims.plan(_tab(rows, [100])))[0] == fit_dims.MIN_W
    assert not _widths(fit_dims.plan(_tab(rows, [fit_dims.MIN_W])))


def test_rows_auto_resize_whole_tab():
    reqs = fit_dims.plan(_tab([[_cell("가")]], [100]), row_count=60)
    auto = [r["autoResizeDimensions"]["dimensions"] for r in reqs if "autoResizeDimensions" in r]
    assert auto == [{"sheetId": 7, "dimension": "ROWS", "startIndex": 0, "endIndex": 60}]


def test_titles_sections_and_merges_are_skipped():
    import layout
    skip = fit_dims.skip_cells(layout.SHEET_ID["자산현황"], [{"startRowIndex": 0, "endRowIndex": 1, "startColumnIndex": 3,
                                                          "endColumnIndex": 8}])
    assert (0, 0) in skip and (2, 0) in skip and (0, 5) in skip  # A1 제목, A3 구역 제목, 병합 칸


def test_numbers_dates_and_centered_headers_never_count_as_overflow():
    # 숫자·날짜는 옆으로 넘치지 않고 잘리며, 가운데 정렬 머리글도 잘린다 → 열을 넓혀야 함 (주식투자 업데이트일 잘림)
    date = {"formattedValue": "2026-10-14", "effectiveValue": {"numberValue": 46309},
            "effectiveFormat": {"textFormat": {"fontSize": 13, "bold": True}, "horizontalAlignment": "CENTER"}}
    head = {"formattedValue": "섹터를 고를 종목", "effectiveValue": {"stringValue": "섹터를 고를 종목"},
            "effectiveFormat": {"textFormat": {"fontSize": 13, "bold": True}, "horizontalAlignment": "CENTER"}}
    w = _widths(fit_dims.plan(_tab([[date, _cell("")], [head, _cell("")]], [70, 20])))
    assert w[0] == fit_dims.text_px("섹터를 고를 종목", 13, bold=True)
