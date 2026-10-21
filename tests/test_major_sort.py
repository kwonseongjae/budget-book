import couple
import formulas
import layout
import migrate_couple as mc
import sort_settings
import views

SORTED = ('SORT(FILTER(설정!$A$2:$A,설정!$A$2:$A<>"",설정!$B$2:$B<>"수입"),'
          'FILTER(설정!$D$2:$D,설정!$A$2:$A<>"",설정!$B$2:$B<>"수입"),TRUE)')


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_dashboard_couple_trend_lists_grouped_by_major():
    assert _by_range(formulas.dashboard_values())["대시보드!A62:E62"][0][0] == f'=IFERROR({SORTED},"")'
    two = _by_range(couple.couple_values())[f"부부!A{couple.CAT_FIRST}:K{couple.CAT_FIRST}"][0][0]
    assert two.startswith('=IFERROR(SORT(FILTER(설정!$A$2:$B,') and ",FILTER(설정!$D$2:$D," in two
    assert any(e["values"] == [[f'=IFERROR({SORTED},"")']] for e in views.view_values())


def test_live_dashboard_list_cell_follows_pie_rows():
    pie = {"chartId": 1, "spec": {"pieChart": {"legendPosition": "LABELED_LEGEND",
           "series": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 50,
                                                    "startColumnIndex": 1, "endColumnIndex": 2}]}},
           "domain": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 50,
                                                    "startColumnIndex": 12, "endColumnIndex": 13}]}}}}}
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                     settings=[], budgets_empty=False, invest_charts=2, pie=pie)
    _s, values, _v = mc.plan(state)
    assert _by_range(values)["대시보드!A21"] == [[f'=IFERROR({SORTED},"")']]  # 운영: 머리글 19, 미분류 20


def test_settings_rows_sorted_fixed_then_variable_income_last_keeping_budgets():
    ad = [["식비", "지출", "", "변동비"], ["주거비", "지출", "", "고정비"], ["월급1", "수입", "", "변동비"],
          ["주택청약", "저축", "", "고정비"], ["새것", "지출", "", ""], ["교통비", "지출", "", "변동비"]]
    km = [["", "", 600000], [], ["", "", ""], ["", "", 100000], [], []]
    new_ad, new_km = sort_settings.sorted_rows(ad, km)
    assert [r[0] for r in new_ad] == ["주거비", "주택청약", "식비", "교통비", "새것", "월급1"]
    assert new_km[1] == ["", "", 100000] and new_km[2] == ["", "", 600000]  # 예산이 자기 카테고리를 따라감
    assert all(len(r) == 3 for r in new_km) and all(r[2] == "" for r in new_ad)  # C(합계 수식 자리)는 비워 둠
    assert sort_settings.sorted_rows(new_ad, new_km) == (new_ad, new_km)  # 두 번 해도 같음
