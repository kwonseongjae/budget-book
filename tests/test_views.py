import views


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_heatmap_cell_uses_month_offset_and_row_category():
    cells = _by_range(views.view_values())["추이!G39:R68"]
    assert len(cells) == 30 and all(len(r) == 12 for r in cells)
    assert "$B$2*100+1," in cells[0][0] and "$F39" in cells[0][0]
    assert "$B$2*100+12," in cells[29][11] and "$F68" in cells[29][11]


def test_calendar_grid_has_date_and_amount_rows():
    grid = _by_range(views.view_values())["달력!A5:G16"]
    assert len(grid) == 12
    assert grid[0][0] == '=IF(AND($E$2+0>=$C$2,$E$2+0<=$D$2),$E$2+0,"")'
    assert grid[11][6].startswith('=IF(G15="","",SUMIFS(')


def test_search_blank_inputs_mean_no_filter():
    c = views.search_cond()
    for cell in ("$B$1", "$B$2", "$B$3", "$B$4"):
        assert f'(({cell}="")+' in c


def test_yearly_uses_range_not_text_match():
    yearly = _by_range(views.view_values())["추이!T39:W39"][0]
    assert yearly[1].startswith("=MAP(T39:T58,LAMBDA(x,")
    assert '">="&x*100' in yearly[1] and '"<"&(x+1)*100' in yearly[1]


def test_monthly_trend_uses_map_per_month():
    row = _by_range(views.view_values())["추이!A39:D39"][0]
    assert row[1].startswith("=MAP(SEQUENCE(12),LAMBDA(i,")
    assert "$B$2*100+i," in row[1] and '"<>수입"' in row[2]


def test_search_only_no_match_shows_empty_message():
    a7 = _by_range(views.view_values())["검색!A7"][0][0]
    assert a7.startswith("=IFNA(FILTER(내역!A2:J,")
    assert a7.endswith(',"결과 없음")')


def test_calendar_month_uses_month_pick():
    top = _by_range(views.view_values())["달력!A1:E2"]
    assert top[1][1].startswith("=LET(pick,B1,")


def test_yearly_years_skip_bad_dates():
    t39 = _by_range(views.view_values())["추이!T39:W39"][0][0]
    assert "ISNUMBER(내역!L2:L)" in t39


def test_trend_outflow_columns_include_new_types():
    vals = _by_range(views.view_values())
    assert '"<>수입"' in vals["추이!A39:D39"][0][2] and '"<>이체"' in vals["추이!A39:D39"][0][2]
    assert '"<>수입"' in vals["추이!T39:W39"][0][2]
    assert '설정!$B$2:$B<>"수입"' in vals["추이!F39"][0][0]
