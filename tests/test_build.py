import re

import pytest

import build_budget
import layout


def _cells(entry):
    title, ref = entry["range"].split("!")
    m = re.fullmatch(r"([A-Z]+)(\d+)(?::[A-Z]+\d+)?", ref)
    c0, r0 = layout.col_index(m.group(1)), int(m.group(2))
    return {(title, r0 + i, c0 + j) for i, row in enumerate(entry["values"]) for j in range(len(row))}


def test_value_shapes_match_declared_ranges():
    for e in build_budget.value_data("a@b.com"):
        g = layout.a1_to_grid(e["range"])
        assert len(e["values"]) == g["endRowIndex"] - g["startRowIndex"], e["range"]
        for row in e["values"]:
            assert len(row) == g["endColumnIndex"] - g["startColumnIndex"], e["range"]


def test_no_two_writes_hit_same_cell():
    # 예외: 옛 자리를 먼저 비우는 '빈칸만' 묶음(그 뒤에 새로 씀)은 의도된 겹침
    seen = set()
    for e in build_budget.value_data("a@b.com"):
        if all(c == "" for row in e["values"] for c in row):
            continue
        cells = _cells(e)
        assert not (seen & cells), e["range"]
        seen |= cells


def test_formula_parentheses_balanced():
    for e in build_budget.value_data("a@b.com"):
        for row in e["values"]:
            for cell in row:
                if isinstance(cell, str) and cell.startswith("="):
                    depth = 0
                    for ch in re.sub(r'"[^"]*"', "", cell):
                        depth += {"(": 1, ")": -1}.get(ch, 0)
                        assert depth >= 0, cell
                    assert depth == 0, cell


def test_every_request_is_single_op():
    for r in build_budget.structure_requests() + build_budget.visual_requests():
        assert len(r) == 1


@pytest.mark.parametrize("bad", ["", "nope", "a@b", "a b@c.com"])
def test_partner_email_validated(monkeypatch, bad):
    monkeypatch.setenv("BUDGET_PARTNER_EMAIL", bad)
    with pytest.raises(ValueError):
        build_budget.partner_email()


def test_partner_email_missing(monkeypatch):
    monkeypatch.delenv("BUDGET_PARTNER_EMAIL", raising=False)
    with pytest.raises(ValueError, match="BUDGET_PARTNER_EMAIL not set"):
        build_budget.partner_email()


from unittest import mock

from googleapiclient.errors import HttpError


def test_build_refuses_when_sheet_already_created(tmp_path, monkeypatch):
    idf = tmp_path / ".spreadsheet_id"
    idf.write_text("abc")
    monkeypatch.setattr(build_budget, "ID_FILE", idf)
    with mock.patch.object(build_budget, "get_credentials") as creds:
        with pytest.raises(FileExistsError, match="abc"):
            build_budget.build_sheet("t", "a@b.com")
        creds.assert_not_called()


def test_share_failure_is_reported_not_raised(capsys):
    drive = mock.MagicMock()
    drive.permissions().create().execute.side_effect = HttpError(mock.Mock(status=400), b"owner")
    assert build_budget.share(drive, "sid", "a@b.com") is False
    assert "공유 실패" in capsys.readouterr().out


def test_share_success():
    drive = mock.MagicMock()
    assert build_budget.share(drive, "sid", "a@b.com") is True


def test_every_chart_anchor_inside_its_tab_grid():
    size = {sid: (rows, cols) for _t, sid, rows, cols, _h in layout.SHEETS}
    for r in build_budget.visual_requests():
        if "addChart" in r:
            a = r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]
            rows, cols = size[a["sheetId"]]
            assert a["rowIndex"] < rows and a["columnIndex"] < cols, a
