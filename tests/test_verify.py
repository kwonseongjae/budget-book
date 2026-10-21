import datetime as dt

import verify_budget


def test_sample_rows_are_ten_columns_and_cover_three_types():
    rows = verify_budget.sample("2026-10-06")
    assert all(len(r) == 10 for r in rows)
    assert [r[2] for r in rows] == ["수입", "지출", "이체"]


def test_expected_covers_map_sums_and_trend_month():
    exp = verify_budget.expected(dt.date(2026, 10, 6))
    assert {"대시보드!B62", "대시보드!G62", "대시보드!J61", "자산!E2:E4"} <= set(exp)
    assert "추이!C48" in exp
