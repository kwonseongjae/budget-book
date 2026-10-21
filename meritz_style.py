"""메리츠 연동 탭 서식: 체크박스 검증, 숫자 서식, 머리글·제목, 차트, 손익 색(수익 빨강·손실 파랑). 계좌 슬롯마다 한 벌."""
from charts import _basic, _chart, _src
from layout import MERITZ_SLOTS, SHEET_ID, Slot, a1_to_grid, number_format
from styling import (BLUE_TEXT, CHECK_BG, HEADER_FONT, KPI_FONT, KPI_ROW_PX, LABEL_BG, RED_TEXT, TITLE_FONT, TITLE_ROW_PX,
                     VIEW_TAB, WHITE,
                     _dim)

TIME_FMT = "yyyy-mm-dd hh:mm"
SHORT_TIME_FMT = "mm/dd hh:mm"  # 주식 탭 '마지막 갱신': 한 화면 폭 (연도는 자명)


def _each(fn, slots) -> list[dict]:
    return [r for s in (MERITZ_SLOTS if slots is None else slots) for r in fn(s)]


def header_ranges(s: Slot) -> list[str]:
    st, m, r = s.stock, s.meritz, s.raw
    return [f"{st}!A5:G5", f"{st}!A8:E8", f"{st}!A15:P15",
            f"{m}!A5:D5", f"{m}!A9:B9", f"{m}!D9:E9", f"{r}!A1:E1", f"{r}!A10:N10"]


def _fmt(a1: str, fmt: dict, fields: str) -> dict:
    return {"repeatCell": {"range": a1_to_grid(a1), "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def _formats(s: Slot) -> list[dict]:
    r, st, m = s.raw, s.stock, s.meritz
    fmts = [(f"{r}!H1:H7", "NUMBER", "#,##0"), (f"{r}!H8", "DATE_TIME", TIME_FMT),
            (f"{r}!E2:E5", "DATE_TIME", TIME_FMT),
            (f"{st}!B3", "DATE_TIME", SHORT_TIME_FMT), (f"{st}!A6:E6", "NUMBER", "#,##0"),
            (f"{st}!F6", "PERCENT", "0.00%"), (f"{st}!G6", "NUMBER", "#,##0"),
            (f"{st}!B9:C13", "NUMBER", "#,##0.00"), (f"{st}!D9:E13", "NUMBER", "#,##0"),
            (f"{st}!D16:D115", "NUMBER", "#,##0.####"), (f"{st}!E16:I115", "NUMBER", "#,##0"),
            (f"{st}!J16:J115", "PERCENT", "0.00%"), (f"{st}!L16:N115", "NUMBER", "#,##0.00"),
            (f"{st}!O16:O115", "PERCENT", "0.00%"), (f"{st}!P16:P115", "PERCENT", "0.0%"),
            (f"{m}!A6:B6", "NUMBER", "#,##0"), (f"{m}!C6", "PERCENT", "0.00%"),
            (f"{m}!B10:B12", "NUMBER", "#,##0"), (f"{m}!E10:E12", "NUMBER", "#,##0")]
    return [number_format(a1, kind, pattern) for a1, kind, pattern in fmts]


def _structure(s: Slot) -> list[dict]:
    check = {"setDataValidation": {"range": a1_to_grid(f"{s.stock}!H1"), "rule": {
        "condition": {"type": "BOOLEAN"}, "strict": False, "showCustomUi": True}}}
    return [check] + _formats(s)


def hide_requests() -> list[dict]:
    """주식 탭 L·M(평단가·현재가 외화)은 숨김 — 원화 값·외화 수익률은 남기고 한 화면 폭(1,650px) 안에. 다시 펼칠 수 있음."""
    return [{"updateDimensionProperties": {"range": {"sheetId": SHEET_ID[s.stock], "dimension": "COLUMNS", "startIndex": 11,
                                                     "endIndex": 13}, "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}}
            for s in MERITZ_SLOTS]


def structure_requests(slots=None) -> list[dict]:
    return _each(_structure, slots)


def _style(s: Slot) -> list[dict]:
    st, m = s.stock, s.meritz
    head = {"backgroundColor": VIEW_TAB, "horizontalAlignment": "CENTER",
            "textFormat": {"fontSize": HEADER_FONT, "bold": True, "foregroundColor": WHITE}}
    reqs = [_fmt(a1, head, "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)")
            for a1 in header_ranges(s)]
    title = {"textFormat": {"fontSize": TITLE_FONT, "bold": True}}
    reqs += [_fmt(a1, title, "userEnteredFormat.textFormat") for a1 in (f"{st}!A1", f"{m}!A1")]
    kpi = {"horizontalAlignment": "CENTER", "textFormat": {"fontSize": KPI_FONT, "bold": True}}
    reqs += [_fmt(a1, kpi, "userEnteredFormat(horizontalAlignment,textFormat)")
             for a1 in (f"{st}!A6:G6", f"{m}!A6:D6")]
    reqs.append(_fmt(f"{st}!G1:H1", {"backgroundColor": CHECK_BG, "textFormat": {"bold": True}},
                     "userEnteredFormat(backgroundColor,textFormat.bold)"))
    reqs.append(_fmt(f"{m}!A2:A3", {"backgroundColor": LABEL_BG, "textFormat": {"bold": True}},
                     "userEnteredFormat(backgroundColor,textFormat.bold)"))
    for sheet in (st, m):  # 제목 줄과 큰 숫자 줄은 기본 행보다 조금 높게
        reqs.append(_dim(SHEET_ID[sheet], "ROWS", 0, 1, {"pixelSize": TITLE_ROW_PX}, "pixelSize"))
        reqs.append(_dim(SHEET_ID[sheet], "ROWS", 5, 6, {"pixelSize": KPI_ROW_PX}, "pixelSize"))
    return reqs


def _charts(s: Slot) -> list[dict]:
    m, st = s.meritz, s.stock
    donut = {"title": "자산 구성", "pieChart": {"legendPosition": "RIGHT_LEGEND", "pieHole": 0.5,
                                            "domain": _src(f"{m}!A10:A12"), "series": _src(f"{m}!B10:B12")}}
    return [_chart(donut, m, 13),
            _chart(_basic("국내·해외·기타", "COLUMN", f"{m}!D9:D12", [(f"{m}!E9:E12", "COLUMN")]), m, 30),
            _chart(_basic("종목별 평가금액", "COLUMN", f"{st}!C15:C115", [(f"{st}!H15:H115", "COLUMN")]), m, 47),
            _chart(_basic("종목별 수익률", "COLUMN", f"{st}!C15:C115", [(f"{st}!J15:J115", "COLUMN")]), m, 64)]


def _sign_rule(a1: str, ctype: str, color: dict) -> dict:
    cond = {"type": ctype, "values": [{"userEnteredValue": "0"}]}
    return {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [a1_to_grid(a1)], "booleanRule": {
        "condition": cond, "format": {"textFormat": {"foregroundColor": color, "bold": True}}}}}}


def _conditional(s: Slot) -> list[dict]:
    ranges = [f"{s.stock}!I16:J115", f"{s.stock}!O16:O115", f"{s.stock}!E6:F6", f"{s.meritz}!B6:C6"]
    return ([_sign_rule(a1, "NUMBER_GREATER", RED_TEXT) for a1 in ranges]
            + [_sign_rule(a1, "NUMBER_LESS", BLUE_TEXT) for a1 in ranges])


def style_requests(slots=None) -> list[dict]:
    return _each(_style, slots)


def chart_requests(slots=None) -> list[dict]:
    return _each(_charts, slots)


def conditional_requests(slots=None) -> list[dict]:
    return _each(_conditional, slots)


def visual_requests(slots=None) -> list[dict]:
    return style_requests(slots) + chart_requests(slots) + conditional_requests(slots)
