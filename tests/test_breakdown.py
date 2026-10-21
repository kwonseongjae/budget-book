import breakdown
import build_budget
import layout
import migrate_couple as mc


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_income_split_by_major_category():
    vals = _by_range(breakdown.breakdown_values())
    assert vals["대시보드!A95"] == [["수입 대비 고정비·변동비"]]
    assert vals["대시보드!A96:E96"] == [["구분", "금액", "수입 대비", "그래프 이름표", "그래프 값"]]
    rows = vals["대시보드!A97:E101"]
    assert [r[0] for r in rows] == ["고정비", "변동비", "대분류 없음", "남은 돈", "총수입"]
    assert '내역!$M:$M,"고정비"' in rows[0][1] and '내역!$M:$M,"변동비"' in rows[1][1]
    assert rows[3][1].startswith("=B101-") and rows[4][1].count('"수입"') == 1
    assert rows[0][2] == '=IFERROR(B97/B101,"")' and rows[0][4] == "=MAX(0,B97)"
    assert rows[4][3] == "" and rows[4][4] == ""


def test_fixed_cost_items_listed_one_by_one():
    vals = _by_range(breakdown.breakdown_values())
    assert vals["대시보드!A105:F105"] == [["카테고리", "내용", "사용자", "금액", "고정비 중", "그래프 이름표"]]
    f = vals["대시보드!A106"][0][0]
    assert f.startswith("=IFERROR(SORT(FILTER({내역!D2:D,내역!J2:J,내역!B2:B,내역!K2:K},")
    assert '내역!M2:M="고정비"' in f and "내역!L2:L=$B$2" in f and ",4,FALSE)" in f
    assert "D106:D125/SUM(D106:D125)" in vals["대시보드!E106"][0][0]


def test_fixed_labels_unique_per_person_without_repeating_category():
    # 운영에서 본 문제: '주택청약·주택청약' 반복, 두 사람의 같은 항목이 같은 이름표 → 원형 조각이 합쳐짐
    label = _by_range(breakdown.breakdown_values())["대시보드!F106"][0][0]
    assert '(B106:B125="")+(B106:B125=A106:A125)' in label and '" ("&C106:C125&")"' in label


def test_variable_cost_summed_per_category():
    vals = _by_range(breakdown.breakdown_values())
    assert vals["대시보드!H105:K105"] == [["카테고리", "금액", "변동비 중", "그래프 이름표"]]
    f = vals["대시보드!H106"][0][0]
    assert '설정!$D$2:$D="변동비"' in f and "SORT(FILTER({c,amt},amt>0),2,FALSE)" in f


def test_three_pie_charts_with_percent_labels():
    pies = [r["addChart"]["chart"] for r in breakdown.chart_requests()]
    assert [p["spec"]["title"] for p in pies] == ["수입 대비 고정비·변동비", "고정비 구성 (항목별)", "변동비 구성"]
    assert all(p["spec"]["pieChart"]["legendPosition"] == "LABELED_LEGEND" for p in pies)
    assert pies[0]["spec"]["pieChart"]["series"]["sourceRange"]["sources"][0]["startColumnIndex"] == 4  # MAX(0,…) 값
    rows = {t: (rows, cols) for t, _sid, rows, cols, _h in layout.SHEETS}
    assert rows["대시보드"][0] >= 145
    assert any("addChart" in r and r["addChart"]["chart"]["spec"]["title"] == "변동비 구성"
               for r in build_budget.visual_requests())


def test_migration_extends_live_dashboard_and_adds_charts_once():
    base = dict(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                settings=[], budgets_empty=False, invest_charts=2)
    live = mc.State(**base, dash_rows=59, dash_chart_titles=frozenset({"카테고리별 지출"}))
    structure, values, visual = mc.plan(live)
    assert {"appendDimension": {"sheetId": 400, "dimension": "ROWS", "length": 131}} in structure
    assert "대시보드!A106" in _by_range(values)
    assert [r["addChart"]["chart"]["spec"]["title"] for r in visual if "addChart" in r] == [
        "수입 대비 고정비·변동비", "고정비 구성 (항목별)", "변동비 구성", "분류별 수입", "분류별 지출", "분류별 저축"]
    done = mc.State(**base, dash_rows=190, dash_chart_titles=frozenset({"수입 대비 고정비·변동비", "분류별 수입"}))
    s2, _v2, vi2 = mc.plan(done)
    assert not any("appendDimension" in r and r["appendDimension"]["sheetId"] == 400 for r in s2)
    assert not any("addChart" in r for r in vi2)
