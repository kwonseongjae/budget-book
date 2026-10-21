"""차트(폰에서 보기 좋게 세로로 쌓음)와 조건부 서식."""
from layout import CAL, DASH, SHEET_ID, TREND, a1_to_grid, v

RED = {"red": 0.96, "green": 0.8, "blue": 0.8}
ORANGE = {"red": 1.0, "green": 0.9, "blue": 0.7}
GREEN = {"red": 0.8, "green": 0.94, "blue": 0.8}
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
HEAT = {"red": 0.9, "green": 0.4, "blue": 0.4}


def _src(a1: str) -> dict:
    return {"sourceRange": {"sources": [a1_to_grid(a1)]}}


def _chart(spec: dict, sheet: str, row: int, col: int = 0) -> dict:
    anchor = {"sheetId": SHEET_ID[sheet], "rowIndex": row, "columnIndex": col}
    return {"addChart": {"chart": {"spec": spec, "position": {"overlayPosition": {
        "anchorCell": anchor, "widthPixels": 600, "heightPixels": 320}}}}}


def _basic(title: str, kind: str, domain: str, series: list[tuple[str, str]]) -> dict:
    out = []
    for a1, stype in series:
        s = {"series": _src(a1), "targetAxis": "LEFT_AXIS"}
        if kind == "COMBO":
            s["type"] = stype
        out.append(s)
    return {"title": title, "basicChart": {"chartType": kind, "legendPosition": "BOTTOM_LEGEND",
                                           "headerCount": 1, "domains": [{"domain": _src(domain)}],
                                           "series": out}}


def chart_requests() -> list[dict]:
    d, t = DASH, TREND
    pie = {"title": "카테고리별 지출", "pieChart": {"legendPosition": "LABELED_LEGEND", "pieHole": 0.5,
                                              "domain": _src(f"{d}!M61:M91"), "series": _src(f"{d}!B61:B91")}}
    return [
        _chart(pie, d, 7),
        _chart(_basic("예산 대비 지출", "COLUMN", f"{d}!A60:A91",
                      [(f"{d}!B60:B91", "COLUMN"), (f"{d}!C60:C91", "COLUMN")]), d, 24),
        _chart(_basic("사용자별 지출", "COLUMN", f"{d}!F60:F76", [(f"{d}!G60:G76", "COLUMN")]), d, 41),
        _chart(_basic("월별 수입·지출·잔액", "COMBO", f"{t}!A38:A50",
                      [(f"{t}!B38:B50", "COLUMN"), (f"{t}!C38:C50", "COLUMN"), (f"{t}!D38:D50", "LINE")]), t, 3),
        _chart(_basic("연도별 수입·지출·잔액", "COLUMN", f"{t}!T38:T58",
                      [(f"{t}!U38:U58", "COLUMN"), (f"{t}!V38:V58", "COLUMN"), (f"{t}!W38:W58", "COLUMN")]), t, 20),
    ]


PIE_LABEL_COL = 12  # 대시보드 M열: 원형 그래프 이름표 "카테고리 비율%"


def pie_labels(first: int, last: int) -> dict:
    """대시보드 카테고리(A)·지출(B) first~last행 → M열 이름표. 시트 API엔 조각 비율 표시 옵션이 없어 이름에 붙인다."""
    a, b = f"A{first}:A{last}", f"B{first}:B{last}"
    label = f'=ARRAYFORMULA(IF(({a}="")+({b}<=0),"",{a}&" "&TEXT({b}/SUM({b}),"0.0%")))'
    return v(f"{DASH}!M{first - 1}:M{first}", [["비율 표시"], [label]])


def _bool_rule(a1: str, value: float, color: dict, index: int) -> dict:
    cond = {"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": str(value)}]}
    return {"addConditionalFormatRule": {"index": index, "rule": {
        "ranges": [a1_to_grid(a1)], "booleanRule": {"condition": cond, "format": {"backgroundColor": color}}}}}


def _gradient(ranges: list[str]) -> dict:
    return {"addConditionalFormatRule": {"index": 0, "rule": {
        "ranges": [a1_to_grid(a) for a in ranges],
        "gradientRule": {"minpoint": {"type": "MIN", "color": WHITE}, "maxpoint": {"type": "MAX", "color": HEAT}}}}}


BAD_ROW_FORMULA = '=AND($H2<>"",OR(NOT(ISNUMBER($K2)),NOT(ISNUMBER($L2)),$B2=""))'  # 금액·날짜 오류 또는 사용자 빈칸
BLANK_AMOUNT_FORMULA = '=AND($A2=TRUE,$B2<>"",OR($G2="",$G2=0))'  # 사용 중인데 금액이 빈 반복 (자동으로 못 만든다)
DARK_RED = {"red": 0.7, "green": 0.0, "blue": 0.0}


def _custom_rule(a1: str, formula: str, fmt: dict, index: int = 0) -> dict:
    cond = {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": formula}]}
    return {"addConditionalFormatRule": {"index": index, "rule": {
        "ranges": [a1_to_grid(a1)], "booleanRule": {"condition": cond, "format": fmt}}}}


def data_check_rules() -> list[dict]:
    """입력 확인용 조건부 서식 4개: 내역 오류 줄(전체 빨강·굵게), 반복·즐겨찾기의 [자산]에 없는 결제수단, 금액이 빈 반복."""
    no_asset = '=AND({c}2<>"",COUNTIF(INDIRECT("자산!A2:A50"),{c}2)=0)'
    return [_custom_rule("내역!A2:M5000", BAD_ROW_FORMULA, {"backgroundColor": RED, "textFormat": {"bold": True, "foregroundColor": DARK_RED}}),
            _custom_rule("반복!F2:F50", no_asset.format(c="F"), {"backgroundColor": RED}),
            _custom_rule("즐겨찾기!E2:E50", no_asset.format(c="E"), {"backgroundColor": RED}),
            _custom_rule("반복!G2:G50", BLANK_AMOUNT_FORMULA, {"backgroundColor": RED})]


def conditional_requests() -> list[dict]:
    budget = f"{DASH}!D62:D91"
    return [
        _bool_rule(budget, 1, RED, 0),
        _bool_rule(budget, 0.8, ORANGE, 1),
        _bool_rule(f"{DASH}!L61:L76", 1, GREEN, 2),
        _gradient([f"{TREND}!G39:R68"]),
        _gradient([f"{CAL}!A{r}:G{r}" for r in range(6, 17, 2)]),
        unregistered_payment_rule(),
    ] + data_check_rules()


def unregistered_payment_rule() -> dict:
    """내역 결제수단·입금자산이 [자산] 목록에 없으면 빨간 배경 (다른 탭 참조는 INDIRECT만 허용)."""
    cond = {"type": "CUSTOM_FORMULA",
            "values": [{"userEnteredValue": '=AND(F2<>"",COUNTIF(INDIRECT("자산!A2:A50"),F2)=0)'}]}
    return {"addConditionalFormatRule": {"index": 0, "rule": {
        "ranges": [a1_to_grid("내역!F2:G5000")], "booleanRule": {"condition": cond, "format": {"backgroundColor": RED}}}}}
