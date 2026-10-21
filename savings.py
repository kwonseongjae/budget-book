"""[저축·연금] 탭: 저축 및 현금성 / 연금 / 기타 자산 (시골쥐 '저축 및 현금성 자산 · 연금 · 기타 자산').

잔액은 [자산] 탭 그대로(순자산과 같은 숫자). 각 표 첫 열은 [자산]에서 그 종류 이름을 고르는 드롭다운이고,
이율·월 불입액·만기·원금 같은 이 시트에만 있는 정보만 분홍 칸에 적는다.
"""
from charts import _src
from layout import ASSETS, SAVINGS as S, SHEET_ID, a1_to_grid, number_format, v
from styling import BLUE_TEXT, RED_TEXT

CASH_FIRST, CASH_LAST = 5, 19        # 저축 및 현금성 15줄, 구분 소계 21~23, 합계 24
PEN_HEAD, PEN_FIRST, PEN_LAST = 28, 29, 38   # 연금 10줄, 합계 39
ETC_HEAD, ETC_FIRST, ETC_LAST = 43, 44, 53   # 기타 10줄, 합계 54
KINDS = {"N": ["통장", "계좌", "현금", "청약"], "O": ["연금"], "P": ["기타"]}  # 숨은 보조 열 → [자산] 종류
CASH_TYPES = ["예적금", "입출금", "기타"]
CHART_TITLE = "연금 비율"

TITLE = f"{S}!A1"
BADGE = ("L1", "L2")
SECTIONS = [f"{S}!A3", f"{S}!L3", f"{S}!A{PEN_HEAD - 1}", f"{S}!A{ETC_HEAD - 1}"]
HEADS = [f"{S}!A4:J4", f"{S}!L4", f"{S}!A{PEN_HEAD}:H{PEN_HEAD}", f"{S}!A{ETC_HEAD}:F{ETC_HEAD}"]
TOTALS = [f"{S}!A24:J24", f"{S}!A{PEN_LAST + 1}:H{PEN_LAST + 1}", f"{S}!A{ETC_LAST + 1}:F{ETC_LAST + 1}"]
SUBTOTALS = [f"{S}!A21:J23"]
BODIES = [f"{S}!A{CASH_FIRST}:J{CASH_LAST}", f"{S}!L{CASH_FIRST}:L{CASH_LAST}", f"{S}!A{PEN_FIRST}:H{PEN_LAST}",
          f"{S}!A{ETC_FIRST}:F{ETC_LAST}"]
INPUTS = [f"{S}!A{CASH_FIRST}:A{CASH_LAST}", f"{S}!D{CASH_FIRST}:G{CASH_LAST}", f"{S}!I{CASH_FIRST}:J{CASH_LAST}",
          f"{S}!A{PEN_FIRST}:A{PEN_LAST}", f"{S}!C{PEN_FIRST}:E{PEN_LAST}", f"{S}!H{PEN_FIRST}:H{PEN_LAST}",
          f"{S}!A{ETC_FIRST}:A{ETC_LAST}", f"{S}!C{ETC_FIRST}:C{ETC_LAST}", f"{S}!F{ETC_FIRST}:F{ETC_LAST}"]
RUNS = [("A", CASH_FIRST, CASH_LAST, "LCCCCRRRCL"), ("A", 21, 24, "L....R.R"), ("L", CASH_FIRST, CASH_LAST, "L"),
        ("A", PEN_FIRST, PEN_LAST + 1, "LCCCRRRL"), ("A", ETC_FIRST, ETC_LAST + 1, "LCRRRL")]


def _look(first: int, last: int, col: int) -> str:
    a = f"A{first}:A{last}"
    return f'=MAP({a},LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,{ASSETS}!$A$2:$I$50,{col},FALSE),""))))'


def _rate(cost: str, now: str) -> str:
    return f'=MAP({cost},{now},LAMBDA(b,p,IF(OR(p="",N(b)=0),"",p/b-1)))'


def _helper(col: str) -> str:
    kinds = ",".join(f'"{k}"' for k in KINDS[col])
    return f'=IFERROR(FILTER({ASSETS}!A2:A50,ISNUMBER(MATCH({ASSETS}!B2:B50,{{{kinds}}},0))),"")'


def values() -> list[dict]:
    c0, c1 = CASH_FIRST, CASH_LAST
    sub = [[f"{t} 합계", "", "", "", "", f"=SUMIFS(F{c0}:F{c1},E{c0}:E{c1},\"{t}\")", "",
            f"=SUMIFS(H{c0}:H{c1},E{c0}:E{c1},\"{t}\")"] for t in CASH_TYPES]
    p0, p1, e0, e1 = PEN_FIRST, PEN_LAST, ETC_FIRST, ETC_LAST
    n = f"N{c0}:N{c1 + 25}"
    return [v(TITLE, [["저축·연금·기타 자산"]]),
            v(f"{S}!A3", [["저축 및 현금성 — 자산은 [자산]에서 고르고 분홍 칸을 채우세요"]]),
            v(f"{S}!A4:J4", [["자산", "종류", "소유자", "은행", "구분", "월 불입액", "이율", "현재 잔액", "만기", "비고"]]),
            v(f"{S}!B{c0}", [[_look(c0, c1, 2)]]), v(f"{S}!C{c0}", [[_look(c0, c1, 9)]]), v(f"{S}!H{c0}", [[_look(c0, c1, 5)]]),
            v(f"{S}!A21:H23", sub),
            v(f"{S}!A24:H24", [["저축 및 현금성 합계", "", "", "", "", f"=SUM(F{c0}:F{c1})", "", f"=SUM(H{c0}:H{c1})"]]),
            v(f"{S}!L3", [["표에 없는 저축 자산"]]), v(f"{S}!L4", [["[자산]에만 있는 것"]]),
            v(f"{S}!L{c0}", [[f'=IFERROR(FILTER({n},{n}<>"",ISNA(MATCH({n},A{c0}:A{c1},0))),"모두 등록됨")']]),
            v(f"{S}!A{PEN_HEAD - 1}", [["연금"]]),
            v(f"{S}!A{PEN_HEAD}:H{PEN_HEAD}", [["자산", "소유자", "구분", "회사", "납입 원금", "평가금액", "수익률", "비고"]]),
            v(f"{S}!B{p0}", [[_look(p0, p1, 9)]]), v(f"{S}!F{p0}", [[_look(p0, p1, 5)]]),
            v(f"{S}!G{p0}", [[_rate(f"E{p0}:E{p1}", f"F{p0}:F{p1}")]]),
            v(f"{S}!A{p1 + 1}:G{p1 + 1}", [["연금 합계", "", "", "", f"=SUM(E{p0}:E{p1})", f"=SUM(F{p0}:F{p1})",
                                            f'=IF(N(E{p1 + 1})=0,"",F{p1 + 1}/E{p1 + 1}-1)']]),
            v(f"{S}!A{ETC_HEAD - 1}", [["기타 자산 (금·코인 등)"]]),
            v(f"{S}!A{ETC_HEAD}:F{ETC_HEAD}", [["자산", "소유자", "매수 금액", "현재 금액", "수익률", "비고"]]),
            v(f"{S}!B{e0}", [[_look(e0, e1, 9)]]), v(f"{S}!D{e0}", [[_look(e0, e1, 5)]]),
            v(f"{S}!E{e0}", [[_rate(f"C{e0}:C{e1}", f"D{e0}:D{e1}")]]),
            v(f"{S}!A{e1 + 1}:E{e1 + 1}", [["기타 합계", "", f"=SUM(C{e0}:C{e1})", f"=SUM(D{e0}:D{e1})",
                                            f'=IF(N(C{e1 + 1})=0,"",D{e1 + 1}/C{e1 + 1}-1)']]),
            v(f"{S}!N4:P4", [["저축 목록", "연금 목록", "기타 목록"]])] + [v(f"{S}!{c}{c0}", [[_helper(c)]]) for c in KINDS]


def _sign(a1: str) -> list[dict]:
    def rule(ctype, color):
        return {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [a1_to_grid(a1)], "booleanRule": {
            "condition": {"type": ctype, "values": [{"userEnteredValue": "0"}]},
            "format": {"textFormat": {"foregroundColor": color}}}}}}
    return [rule("NUMBER_GREATER", RED_TEXT), rule("NUMBER_LESS", BLUE_TEXT)]


def formats() -> list[dict]:
    c0, c1, p0, p1, e0, e1 = CASH_FIRST, CASH_LAST, PEN_FIRST, PEN_LAST, ETC_FIRST, ETC_LAST
    fmts = [(f"{S}!F{c0}:F24", "NUMBER", "#,##0"), (f"{S}!G{c0}:G{c1}", "PERCENT", "0.00%"),
            (f"{S}!H{c0}:H24", "NUMBER", "#,##0"), (f"{S}!I{c0}:I{c1}", "DATE", "yyyy-mm"),
            (f"{S}!E{p0}:F{p1 + 1}", "NUMBER", "#,##0"), (f"{S}!G{p0}:G{p1 + 1}", "PERCENT", "0.0%"),
            (f"{S}!C{e0}:D{e1 + 1}", "NUMBER", "#,##0"), (f"{S}!E{e0}:E{e1 + 1}", "PERCENT", "0.0%")]
    opt = lambda vals: {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": x} for x in vals]},
                        "strict": False, "showCustomUi": True}
    rng = lambda col: {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={S}!${col}${c0}:${col}${c1 + 25}"}]},
                       "strict": False, "showCustomUi": True}
    rules = [(f"{S}!A{c0}:A{c1}", rng("N")), (f"{S}!E{c0}:E{c1}", opt(CASH_TYPES)),
             (f"{S}!G{c0}:G{c1}", {"condition": {"type": "NUMBER_BETWEEN", "values": [{"userEnteredValue": "0"}, {"userEnteredValue": "1"}]},
                                   "strict": False}),  # 이율 3%는 3%·0.03 (3이면 300%)
             (f"{S}!A{p0}:A{p1}", rng("O")), (f"{S}!C{p0}:C{p1}", opt(["개인연금", "연금저축", "퇴직연금 DC", "IRP", "기타"])),
             (f"{S}!A{e0}:A{e1}", rng("P"))]
    valid = [{"setDataValidation": {"range": a1_to_grid(a1), "rule": rule}} for a1, rule in rules]
    return ([number_format(a1, k, p) for a1, k, p in fmts] + valid
            + _sign(f"{S}!G{p0}:G{p1 + 1}") + _sign(f"{S}!E{e0}:E{e1 + 1}"))


def chart_requests() -> list[dict]:
    spec = {"title": CHART_TITLE, "pieChart": {"legendPosition": "LABELED_LEGEND",
                                               "domain": _src(f"{S}!A{PEN_FIRST}:A{PEN_LAST}"),
                                               "series": _src(f"{S}!F{PEN_FIRST}:F{PEN_LAST}")}}
    return [{"addChart": {"chart": {"spec": spec, "position": {"overlayPosition": {
        "anchorCell": {"sheetId": SHEET_ID[S], "rowIndex": PEN_HEAD - 2, "columnIndex": 11},
        "widthPixels": 380, "heightPixels": 240}}}}}]


WIDTHS = [150, 80, 80, 110, 80, 100, 70, 110, 80, 160, 20, 150, 20, 100, 100, 100]
HIDDEN = [13, 14, 15]  # N·O·P: [자산] 종류별 이름 목록
