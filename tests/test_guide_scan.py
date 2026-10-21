"""사용법 탭을 한눈에 (2026-10-21 사용자: 글밖에 없어서 한눈에 안 들어온다)."""
import guide
import styling


def _rows():
    return {a: b for a, b in guide.GUIDE_ROWS if a}


def test_multi_sentence_rows_become_short_bullet_lines():
    b = _rows()["[문자입력]"]
    lines = b.split("\n")
    assert len(lines) >= 4 and all(l.startswith("• ") for l in lines)
    assert max(len(l) for l in lines) <= 140


def test_single_sentence_rows_stay_plain():
    b = _rows()["폰 설정"]
    assert "\n" not in b and not b.startswith("• ")


def test_split_only_after_korean_sentence_end():
    out = guide.bullets("날짜는 10/05·2026.10.05 형식을 읽습니다. 못 읽으면 직접 입력하세요.")
    assert out == "• 날짜는 10/05·2026.10.05 형식을 읽습니다.\n• 못 읽으면 직접 입력하세요."
    assert guide.bullets("한 문장입니다.") == "한 문장입니다."


def test_tab_map_section_near_top_lists_every_group():
    kinds = [(k, a) for k, a, _b in guide.CONTENT]
    i = kinds.index(("section", "탭 한눈에 보기"))
    assert i < 14
    labels = [a for k, a, _b in guide.CONTENT[i + 1:i + 7] if k == "row"]
    assert labels == ["입력", "보기", "투자", "관리", "숨김"]


def test_invest_row_uses_current_principal_definition():
    text = " ".join(b for _k, _a, b in guide.CONTENT)
    assert "매입금액+현금" not in text and "종목 매입금액" in text


def test_label_column_shaded_and_top_aligned():
    reqs = guide.guide_requests()
    cells = [r["repeatCell"] for r in reqs if "repeatCell" in r]
    label = [c for c in cells if c["range"]["endColumnIndex"] == 1 and c["range"]["endRowIndex"] - c["range"]["startRowIndex"] == 1
             and c["cell"]["userEnteredFormat"].get("backgroundColor") == styling.LABEL_BG]
    assert label and all(c["cell"]["userEnteredFormat"].get("verticalAlignment") == "TOP" for c in label)
    assert any(r.get("updateBorders") for r in reqs)
