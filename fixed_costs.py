"""[고정지출] 탭: [반복]의 지출·저축 항목을 카테고리별로 모아 보는 시트 (시골쥐 '고정지출 시트').

이 탭엔 입력칸이 없다 — 항목은 [반복]에서 추가하고, 전체 금액·금리·만기·비고는 [반복] J:M에 적는다.
"""
from charts import _src
from formulas import recur_krw
from layout import FIXED as S, RECUR, SETTINGS, SHEET_ID, a1_to_grid, number_format, v

FIRST, LAST = 5, 54            # 목록 (50줄)
SUM_FIRST, SUM_LAST = 5, 19    # 카테고리별 요약 (15줄), 합계는 20행
TIP_ROW = 36
CHART_TITLE = "고정지출 비율"
TIPS = [("주거비", "대출이 있으면 금리 비교(대환대출), 신혼부부·생애최초 정책대출 조건 확인"),
        ("관리비", "고지서 세부 항목 확인, 전기·가스 요금 할인(신혼·다자녀) 신청"),
        ("통신비", "알뜰폰 요금제 비교, 선택약정(25%)·가족 결합 할인 확인"),
        ("보험비", "실손·운전자 등 중복 보장 점검, 보험다모아에서 보장 대비 보험료 비교"),
        ("구독비", "최근 한 달 안 쓴 구독 해지, 가족·결합 요금제로 묶기"),
        ("용돈", "용돈 통장을 따로 두고 자동이체로 한도 관리"),
        ("계모임", "모임 통장 이자(파킹통장)와 회비 사용 내역 공유")]

TITLE = f"{S}!A1"
BADGE = ("N1", "N2")
SECTIONS = [f"{S}!A3", f"{S}!L3", f"{S}!L{TIP_ROW - 1}"]
HEADS = [f"{S}!A4:J4", f"{S}!L4:N4", f"{S}!L{TIP_ROW}:M{TIP_ROW}"]
TOTALS = [f"{S}!L{SUM_LAST + 1}:N{SUM_LAST + 1}"]
SUBTOTALS: list = []
BODIES = [f"{S}!A{FIRST}:J{LAST}", f"{S}!L{SUM_FIRST}:N{SUM_LAST}", f"{S}!L{TIP_ROW + 1}:M{TIP_ROW + 8}"]
INPUTS: list = []
RUNS = [("A", FIRST, LAST, "CLCCRRRCCL"), ("L", SUM_FIRST, SUM_LAST, "CRR"), ("L", TIP_ROW + 1, TIP_ROW + 8, "CL")]


def _list() -> str:
    r = lambda c: f"{RECUR}!{c}2:{c}50"
    # 카테고리 내용 사용자 납부수단 월납입액(원화 환산) 전체금액 금리 만기 납입일 비고
    cols = ",".join(recur_krw("G", False) if c == "G" else r(c) for c in "EHCFGJKLBM")
    data = f'FILTER({{{cols}}},{r("A")}=TRUE,{r("D")}<>"수입",{r("D")}<>"이체",{r("G")}<>"")'
    # 납입일 오름차순, 같은 날이면 [설정] 카테고리 순 (2026-10-14 사용자 요청)
    return (f'=IFERROR(LET(d,{data},SORT(d,INDEX(d,,9),TRUE,IFERROR(MATCH(INDEX(d,,1),{SETTINGS}!$A$2:$A$60,0),999),'
            f'TRUE)),"")')


def _summary() -> str:
    a, e = f"A{FIRST}:A{LAST}", f"E{FIRST}:E{LAST}"
    # LET 안 나눗셈은 ARRAYFORMULA로 감싸야 모든 줄이 계산된다(아니면 첫 줄만)
    return (f'=ARRAYFORMULA(IFERROR(LET(c,UNIQUE(FILTER({a},{a}<>"")),s,MAP(c,LAMBDA(x,SUMIFS({e},{a},x))),'
            f'SORT(HSTACK(c,s,s/SUM(s)),2,FALSE)),""))')  # 월납입액 큰 순


def _tips() -> str:
    cats = ";".join(f'"{c}","{t}"' for c, t in TIPS)
    return (f'=IFERROR(LET(t,{{{cats}}},FILTER(t,ISNUMBER(MATCH(INDEX(t,,1),L{SUM_FIRST}:L{SUM_LAST},0)))),'
            f'"해당 카테고리 팁 없음")')


def values() -> list[dict]:
    t = SUM_LAST + 1
    return [v(TITLE, [["고정지출"]]),
            v(f"{S}!A3", [["고정지출 목록 — [반복] 탭에서 자동 (전체 금액·금리·만기·비고는 [반복] J~M열에 입력)"]]),
            v(f"{S}!A4:J4", [["카테고리", "내용", "사용자", "납부수단", "월납입액", "전체 금액", "금리", "만기", "납입일", "비고"]]),
            v(f"{S}!A{FIRST}", [[_list()]]),
            v(f"{S}!L3", [["카테고리별"]]), v(f"{S}!L4:N4", [["카테고리", "월납입액", "비율"]]),
            v(f"{S}!L{SUM_FIRST}", [[_summary()]]),
            v(f"{S}!L{t}:N{t}", [["합계", f"=SUM(M{SUM_FIRST}:M{SUM_LAST})", f'=IF(M{t}>0,1,"")']]),
            v(f"{S}!L{TIP_ROW - 1}", [["절약 팁"]]), v(f"{S}!L{TIP_ROW}:M{TIP_ROW}", [["카테고리", "이렇게 줄여 보세요"]]),
            v(f"{S}!L{TIP_ROW + 1}", [[_tips()]])]


def formats() -> list[dict]:
    t = SUM_LAST + 1
    fmts = [(f"{S}!E{FIRST}:F{LAST}", "NUMBER", "#,##0"), (f"{S}!G{FIRST}:G{LAST}", "PERCENT", "0.00%"),
            (f"{S}!H{FIRST}:H{LAST}", "DATE", "yyyy-mm"), (f"{S}!I{FIRST}:I{LAST}", "NUMBER", '0"일"'),
            (f"{S}!M{SUM_FIRST}:M{t}", "NUMBER", "#,##0"), (f"{S}!N{SUM_FIRST}:N{t}", "PERCENT", "0.0%")]
    # 같은 카테고리가 이어지면 둘째 줄부터 카테고리 글자를 흐리게 → 묶음처럼 보이게
    fade = {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [a1_to_grid(f"{S}!A{FIRST + 1}:A{LAST}")], "booleanRule": {
        "condition": {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f"=AND($A{FIRST + 1}<>\"\",$A{FIRST + 1}=$A{FIRST})"}]},
        "format": {"textFormat": {"foregroundColor": {"red": 0.8, "green": 0.8, "blue": 0.8}}}}}}}
    return [number_format(a1, k, p) for a1, k, p in fmts] + [fade]


def chart_requests() -> list[dict]:
    spec = {"title": CHART_TITLE, "pieChart": {"legendPosition": "LABELED_LEGEND", "pieHole": 0.45,
                                               "domain": _src(f"{S}!L{SUM_FIRST}:L{SUM_LAST}"),
                                               "series": _src(f"{S}!M{SUM_FIRST}:M{SUM_LAST}")}}
    return [{"addChart": {"chart": {"spec": spec, "position": {"overlayPosition": {
        "anchorCell": {"sheetId": SHEET_ID[S], "rowIndex": SUM_LAST + 1, "columnIndex": 11},
        "widthPixels": 380, "heightPixels": 240}}}}}]


WIDTHS = [90, 170, 70, 110, 100, 110, 60, 80, 60, 140, 20, 100, 110, 70, 100, 100]
HIDDEN: list = []
