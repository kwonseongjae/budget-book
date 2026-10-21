"""운영 시트를 읽어 State를 만드는 _state — 값이 엉뚱한 칸으로 들어가지 않는지 (2026-10-16: 자산현황 행이 매번 77줄씩 늘어나 927줄이 됐다)."""
import layout
import migrate_couple as mc


class _Exec:
    def __init__(self, body):
        self._body = body

    def execute(self):
        return self._body


class _Values:
    def batchGet(self, **kw):
        return _Exec({"valueRanges": [{} for _ in kw["ranges"]]})


class _FakeSheets:
    """운영 시트: 자산현황 927행×24열(늘어난 상태), 반복 13열, 내역 13열(통화 칸 숨김)."""
    ROWS = {layout.ASSET_STATUS: 927}
    COLS = {layout.ASSET_STATUS: 24, layout.RECUR: 13, layout.TXN: 13}

    def get(self, **kw):
        if kw.get("ranges"):
            return _Exec({"sheets": [{"data": [{"columnMetadata": [{"hiddenByUser": True}]}]}]})
        sheets = [{"properties": {"sheetId": sid, "title": t, "gridProperties": {
            "rowCount": self.ROWS.get(t, rows), "columnCount": self.COLS.get(t, cols)}}} for t, sid, rows, cols, _h in layout.SHEETS]
        return _Exec({"sheets": sheets})

    def values(self):
        return _Values()


def test_state_reads_each_size_into_its_own_field():
    st = mc._state(_FakeSheets(), "sid")
    assert st.status_rows == 927 and st.status_cols == 24
    assert st.recur_cols == 13 and st.txn_cols == 13
    assert st.txn_currency_hidden is True


def test_existing_status_rows_are_not_appended_again():
    st = mc._state(_FakeSheets(), "sid")
    structure, _v, _vi = mc.plan(st)
    grew = [r for r in structure if "appendDimension" in r and r["appendDimension"]["sheetId"] == layout.SHEET_ID[layout.ASSET_STATUS]
            and r["appendDimension"]["dimension"] == "ROWS"]
    assert not grew
