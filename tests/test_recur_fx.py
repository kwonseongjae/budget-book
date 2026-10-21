"""반복 통화 칸 + 환율 고정 (2026-10-16): 반복 N=통화, 내역 N=적용 환율(입력 시점 환율). 원화 환산은 환율 칸이 있으면 그것을 쓴다."""
import align
import charts
import fixed_costs
import formulas
import guide
import layout
import migrate_couple as mc
import styling
import theme

ALL = {t for t, *_ in layout.SHEETS}


def _vals(entries):
    return {e["range"]: e["values"] for e in entries}


def _state(**kw):
    return mc.State(titles=ALL, settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                    invest_charts=2, dash_base=46, **kw)


def _sheet(title):
    return next(s for s in layout.SHEETS if s[0] == title)


def test_layout_has_currency_and_rate_columns():
    assert layout.RECUR_HEADERS[-1] == "통화" and len(layout.RECUR_HEADERS) == 14
    assert _sheet(layout.TXN)[3] == 14 and _sheet(layout.RECUR)[3] == 14
    assert _vals(layout.seed_values(""))["내역!N1"] == [["적용 환율"]]


def test_krw_column_uses_pinned_rate_before_live_rate():
    k1 = _vals(formulas.txn_values())["내역!K1"][0][0]
    assert "IF(ISNUMBER(N:N),N:N,VLOOKUP(I:I,설정!$G:$H,2,FALSE))" in k1


def test_recurring_amount_converted_for_fixed_costs_and_projection():
    conv = formulas.recur_krw()
    assert "SUMIF(설정!$G$2:$G$20,반복!$N$2:$N$50,설정!$H$2:$H$20)" in conv and "반복!$G$2:$G$50" in conv
    assert conv in formulas.projection("$B$2")
    assert conv.replace("$", "") not in fixed_costs._list() and "ARRAYFORMULA" in fixed_costs._list()
    assert "반복!N2:N50" in fixed_costs._list()


def test_currency_dropdown_formats_widths_and_look():
    valid = [r["setDataValidation"]["range"] for r in layout.validation_requests() if "setDataValidation" in r]
    assert layout.a1_to_grid("반복!N2:N50") in valid
    fmts = [r["repeatCell"]["range"] for r in layout.format_requests() if "repeatCell" in r]
    assert layout.a1_to_grid("내역!N2:N5000") in fmts
    assert len(styling.COL_WIDTHS[layout.TXN]) == 14 and len(styling.COL_WIDTHS[layout.RECUR]) == 14
    assert "반복!A2:N50" in theme.INPUTS and "내역!A2:J5000" in theme.INPUTS  # 환율 칸(내역 N)은 입력 색을 칠하지 않음 (스크립트가 채움)


def test_alignment_runs_cover_new_columns():
    def last_col(sheet, row):
        sid = layout.SHEET_ID[sheet]
        cols = [r["repeatCell"]["range"]["endColumnIndex"] for r in align.requests()
                if r["repeatCell"]["range"]["sheetId"] == sid and r["repeatCell"]["range"]["startRowIndex"] == row]
        return max(cols)
    assert last_col(layout.TXN, 1) == 14 and last_col(layout.RECUR, 1) == 14


def test_live_columns_appended_and_headers_written():
    structure, values, _vi = mc.plan(_state(txn_cols=13, recur_cols=13))
    app = {(r["appendDimension"]["sheetId"], r["appendDimension"]["length"]) for r in structure if "appendDimension" in r}
    assert (layout.SHEET_ID[layout.TXN], 1) in app and (layout.SHEET_ID[layout.RECUR], 1) in app
    vals = _vals(values)
    assert vals["내역!N1"] == [["적용 환율"]] and vals["반복!J1:N1"] == [layout.RECUR_HEADERS[9:]]
    valid = [r["setDataValidation"]["range"] for r in structure if "setDataValidation" in r]
    assert layout.a1_to_grid("반복!N2:N50") in valid
    again = mc.plan(_state(txn_cols=14, recur_cols=14))[0]
    assert not [r for r in again if "appendDimension" in r and r["appendDimension"]["sheetId"] in
                (layout.SHEET_ID[layout.TXN], layout.SHEET_ID[layout.RECUR])]


def test_guide_explains_recurring_currency_and_rate_pinning():
    text = " ".join(f"{a} {b}" for _k, a, b in guide.CONTENT)
    assert "반복" in text and "통화" in text and "입력 시점" in text and "적용 환율" in text
