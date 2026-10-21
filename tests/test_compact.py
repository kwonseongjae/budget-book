"""대시보드·자산현황을 오밀조밀하게 (2026-10-14 사용자: 표·그래프 간격이 너무 띄엄띄엄)."""
import asset_status
import breakdown
import category_bars
import migrate_couple as mc


def _pos(req):
    p = req["addChart"]["chart"]["position"]["overlayPosition"]
    return p["anchorCell"]["rowIndex"], p["anchorCell"]["columnIndex"], p["widthPixels"], p["heightPixels"]


def test_breakdown_pies_sit_right_under_tables_and_are_smaller():
    r = breakdown.rows(46)
    for req in breakdown.chart_requests(46)[1:]:
        row, _c, _w, h = _pos(req)
        assert row == r["last"] and h <= 280  # 표 끝 줄 바로 다음 행(0부터 = last)


def test_category_section_follows_breakdown_charts_closely():
    assert category_bars.rows(46)["title"] - breakdown.rows(46)["last"] <= 14


def test_category_tables_evenly_spaced_with_charts_right_under_each():
    cols = [c for _k, c, _x in category_bars.TABLES]
    assert cols == ["A", "E", "I"]
    r = category_bars.rows(46)
    for req, col in zip(category_bars.chart_requests(46), cols):
        row, c, _w, h = _pos(req)
        assert c == ord(col) - 65 and row == r["last"] and h <= 280  # 표 끝 바로 다음 행


def test_old_expense_table_column_cleared():
    r = category_bars.rows(46)
    vals = {e["range"]: e["values"] for e in category_bars.values(46)}
    # 구역 전체(옛 자리 포함)를 먼저 비우고 새로 쓴다 — 옛 수식이 남아 새 펼침을 막지 않게
    first = category_bars.values(46)[0]
    assert first["range"] == f"대시보드!A{r['title']}:J{46 + 95}" and all(c == "" for row in first["values"] for c in row)


def test_status_right_band_charts_stacked_without_gaps():
    rows = [_pos(r)[0] for r in asset_status.chart_requests()]
    heights = [_pos(r)[3] for r in asset_status.chart_requests()]
    # 월별 저축률 → 자산 분포 → 자본 vs 부채 → 고정지출 비율: 앞 그래프가 끝나는 줄(약 24px/줄) 바로 다음
    for (r0, h0), r1 in zip(zip(rows, heights), rows[1:]):
        assert 0 <= r1 - (r0 + h0 / 24) <= 2, (rows, heights)


def test_status_fixed_table_and_horizontal_table_moved_up():
    vals = {e["range"]: e["values"] for e in asset_status.values()}
    assert vals[f"자산현황!L{asset_status.FIX_HEAD}:N{asset_status.FIX_HEAD}"] == [["카테고리", "월납입액", "비율"]]
    assert asset_status.FIX_HEAD <= 50 and asset_status.H_ROW <= 67
    clear = [e for e in asset_status.values() if e["range"] == "자산현황!L47:N80"]
    assert clear and asset_status.values().index(clear[0]) < list(vals).index(f"자산현황!L{asset_status.FIX_HEAD}:N{asset_status.FIX_HEAD}")


def test_live_oversized_chart_shrunk_to_code_size():
    big = ({"chartId": 9, "title": "고정비 구성 (항목별)", "sheetId": 400, "row": breakdown.rows(46)["last"], "col": 0,
            "w": 560, "h": 360},)
    moves = mc.chart_moves(big, 46)
    assert moves and moves[0]["updateEmbeddedObjectPosition"]["newPosition"]["overlayPosition"]["heightPixels"] == 280
    small = ({**big[0], "h": 200},)  # 이미 작으면(그래프 맞춤이 줄인 것) 그대로
    assert not mc.chart_moves(small, 46)


def test_live_category_bar_charts_repointed_to_moved_tables():
    # 표를 A/E/I로 옮긴 뒤 운영 막대그래프가 옛 범위(비워진 칸)를 읽어 빈 그래프가 됐다 (2026-10-14 리허설)
    want = category_bars.chart_requests(46)[1]["addChart"]["chart"]["spec"]
    old = {**want, "basicChart": {**want["basicChart"], "domains": [{"domain": {"sourceRange": {"sources": [
        {"sheetId": 400, "startRowIndex": 100, "endRowIndex": 112, "startColumnIndex": 3, "endColumnIndex": 4}]}}}]}}
    c = ({"chartId": 7, "title": want["title"], "sheetId": 400, "row": 0, "col": 0, "spec": old},)
    fixes = mc.chart_spec_fixes(c, 46)
    assert len(fixes) == 1 and fixes[0]["updateChartSpec"]["spec"] == want
    assert not mc.chart_spec_fixes(({**c[0], "spec": want},), 46)

