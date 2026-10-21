"""투자 탭(부부 주식 계좌 4개 합산·증감·추이)과 숨김 탭 한투원본·투자기록의 값·서식·차트."""
from charts import _basic, _chart
from names import localize as nm
from layout import INVEST, INVEST_LOG, KIS_HOLD, KIS_RAW, RAW, RAW2, SHEET_ID, a1_to_grid, number_format, v
from meritz_style import _sign_rule
from styling import (BLUE_TEXT, CHECK_BG, HEADER_FONT, KPI_FONT, KPI_ROW_PX, LABEL_BG, RED_TEXT, SECTION_FONT, TITLE_FONT,
                     TITLE_ROW_PX, VIEW_TAB, WHITE,
                     _dim)

L = INVEST_LOG


def meritz_principal(raw: str) -> str:
    """원금 = 종목별 매입금액(매수 당시 환율 원화) 합계 — 현금·대출은 넣지 않는다. 한 번도 갱신 전이면 빈칸.
    현금(예수금)을 더하던 옛 추정은 결제 대기(D+2)·외화 예수금 때문에 날마다 수백만 원씩 출렁였다(2026-10-20).
    총자산 조회의 매입금액은 해외분을 오늘 환율로 바꿔 환율 손익이 빠지므로 쓰지 않는다."""
    return f'IF(ISNUMBER({raw}!$H$2),SUM({raw}!$F$11:$F$110),"")'


def meritz_stock(raw: str) -> str:
    """종목 평가 합계(유가증권 평가) — 손익·수익률의 기준. 평가금액(총자산)에서 이것을 빼면 현금."""
    return f'IF(ISNUMBER({raw}!$H$2),N({raw}!$H$3),"")'


def kis_cost(col: str) -> str:
    return f"SUM({KIS_HOLD}!${col}$2:${col}$101)"


def kis_principal(slot: int) -> str:
    """한투 ISA 원금 = 한투종목의 매입금액 합(종목 목록이 아직 없으면 조회 응답의 원금)."""
    c = "D" if slot == 0 else "J"
    return f"IF({kis_cost(c)}>0,{kis_cost(c)},{KIS_RAW}!$G${2 + slot})"


def kis_stock(slot: int) -> str:
    c, e = ("D", "E") if slot == 0 else ("J", "K")
    return f'IF({kis_cost(c)}>0,SUM({KIS_HOLD}!${e}$2:${e}$101),"")'

# (표시 이름, 행, 자동 평가(총자산), 자동 원금(매입금액 합), 마지막 성공, 상태, 메시지, 종목 평가 합)
ACCOUNT_ROWS = [
    (nm("신랑 메리츠"), 7, f"{RAW}!$H$7", meritz_principal(RAW), f"{RAW}!$H$8", f"{RAW}!$B$2", f"{RAW}!$D$2", meritz_stock(RAW)),
    (nm("신랑 ISA(한투)"), 8, f"{KIS_RAW}!$F$2", kis_principal(0), f"{KIS_RAW}!$E$2", f"{KIS_RAW}!$B$2", f"{KIS_RAW}!$D$2", kis_stock(0)),
    (nm("신부 메리츠"), 10, f"{RAW2}!$H$7", meritz_principal(RAW2), f"{RAW2}!$H$8", f"{RAW2}!$B$2", f"{RAW2}!$D$2", meritz_stock(RAW2)),
    (nm("신부 ISA(한투)"), 11, f"{KIS_RAW}!$F$3", kis_principal(1), f"{KIS_RAW}!$E$3", f"{KIS_RAW}!$B$3", f"{KIS_RAW}!$D$3", kis_stock(1)),
]
TOTAL_ROWS = [(nm("신랑 합계"), 9, 7, 8), (nm("신부 합계"), 12, 10, 11)]
KPI_HEAD = ["부부 합산 평가금액", "투자원금", "평가손익", "수익률", "전일 대비", "전월말 대비"]
TABLE_HEAD = ["계좌", "평가금액", "원금", "손익", "수익률", "마지막 갱신", "상태", "직접입력 평가", "직접입력 원금"]
CASH_HEAD = "현금(예수금)"  # J열: 평가금액(총자산) − 종목 평가. 손익·수익률은 현금을 뺀 종목 기준
LOG_HEAD = ["날짜", nm("신랑 메리츠 평가"), "원금", nm("신랑 ISA 평가"), "원금", nm("신부 메리츠 평가"), "원금",
            nm("신부 ISA 평가"), "원금", "합계 평가", "합계 원금", "빠진 계좌 수"]
HOLD_HEAD = ["코드", "종목명", "매입금액", "평가금액"]  # 한투종목 탭 (구분 다음 열들)
KIS_HEAD = ["사람", "상태", "코드", "메시지", "마지막 성공", "평가금액", "원금"]
CHART_ROWS, CHART_COLS = (21, 21), (0, 4)  # 그래프 자리(0부터): 한눈에 표(14~20행) 아래 나란히 — 40행 추이 표를 덮지 않게


def _pl(r: int, stock: str = '""') -> list[str]:
    """손익 = 자동 값이면 종목 평가 − 원금(매입금액) — 현금은 손익이 아니다. 직접입력이 있으면 평가 − 원금."""
    auto = f"AND(NOT(ISNUMBER(H{r})),NOT(ISNUMBER(I{r})),ISNUMBER({stock}))"
    return [f'=IF(AND(ISNUMBER(B{r}),ISNUMBER(C{r})),IF({auto},{stock}-C{r},B{r}-C{r}),"")',
            f'=IF(AND(ISNUMBER(D{r}),N(C{r})<>0),D{r}/C{r},"")']


def cash_cell(r: int, stock: str) -> str:
    """J열 현금(예수금) = 평가금액 − 종목 평가 (자동 값일 때만)."""
    return f'=IF(AND(ISNUMBER(B{r}),NOT(ISNUMBER(H{r})),ISNUMBER({stock})),B{r}-{stock},"")'


def account_row(name, r, value, principal, at, status, msg, stock='""') -> list[str]:
    """직접입력(H·I)이 있으면 그 값, 없으면 원본 탭 자동 값. 직접 평가만 있고 원금이 비면 원금은 모름(빈칸).
    자동 값은 키가 있고 마지막 성공이 3일 안일 때만 — 키 삭제·긴 오류 뒤 옛 값이 합계에 남지 않게.
    원금은 평가가 있을 때만 (투자기록과 같은 규칙)."""
    fresh = f'AND(ISNUMBER({value}),{status}<>"키없음",NOW()-N({at})<=3)'
    return ([name,
             f'=IF(ISNUMBER(H{r}),H{r},IF({fresh},{value},""))',
             f'=IF(NOT(ISNUMBER(B{r})),"",IF(ISNUMBER(I{r}),I{r},IF(ISNUMBER(H{r}),"",IF(ISNUMBER({principal}),{principal},""))))']
            + _pl(r, stock)
            + [f'=IF(ISNUMBER(H{r}),"",IF(ISNUMBER({at}),{at},""))',
               (f'=IF(ISNUMBER(H{r}),"직접입력",IF({status}="","아직 갱신 전",IF({status}="성공",'
                f'IF(NOW()-{at}>3,"오래됨","자동"),IF({status}="키없음","키 없음",'
                f'{status}&IF({msg}="",""," ("&LEFT({msg},30)&")")))))')])


def paired_principal(rows) -> str:
    """손익이 있는(평가·원금 둘 다 있는) 계좌의 원금 합 — 수익률 분모."""
    return "+".join(f"IF(ISNUMBER(D{r}),C{r},0)" for r in rows)


def total_row(name, r, a, b) -> list[str]:
    """손익은 계좌별 손익(D)의 합: 원금이 빈 계좌의 평가가 통째로 이익으로 잡히지 않게."""
    return [name, f'=IF(COUNT(B{a},B{b})=0,"",SUM(B{a},B{b}))', f'=IF(COUNT(C{a},C{b})=0,"",SUM(C{a},C{b}))',
            f'=IF(COUNT(D{a},D{b})=0,"",SUM(D{a},D{b}))', f'=IFERROR(D{r}/({paired_principal((a, b))}),"")', "", ""]


def _kpi() -> list[str]:
    acc = "B7,B8,B10,B11"
    d, t = f"FILTER({L}!A2:A,{L}!A2:A<>\"\")", f"FILTER({L}!J2:J,{L}!A2:A<>\"\")"
    prev_day = f'=IFERROR(LET(t,{t},n,ROWS(t),IF(n<2,"",INDEX(t,n)-INDEX(t,n-1))),"")'
    prev_month = (f'=IFERROR(LET(d,{d},t,{t},last,MAX(d),pe,MAX(FILTER(d,d<=EOMONTH(last,-1))),'
                  f'INDEX(t,MATCH(last,d,0))-INDEX(t,MATCH(pe,d,0))),"")')
    return [f'=IF(COUNT({acc})=0,"",SUM({acc}))', f'=IF(COUNT(C7,C8,C10,C11)=0,"",SUM(C7,C8,C10,C11))',
            '=IF(COUNT(D7,D8,D10,D11)=0,"",SUM(D7,D8,D10,D11))', f'=IFERROR(C4/({paired_principal((7, 8, 10, 11))}),"")',
            prev_day, prev_month]


PEOPLE = ["설정!$E$2", "설정!$E$3"]  # 사용자 슬롯 1·2 (신랑·신부)


def _saving_paid(person: str) -> str:
    """이번 달(계산!C2) 그 사람이 청약 계좌의 적립 카테고리로 낸 돈."""
    cats = f'FILTER(자산!$F$2:$F$50,자산!$B$2:$B$50="청약",자산!$F$2:$F$50<>"")'
    return (f"=IFERROR(SUMPRODUCT((내역!$L$2:$L=계산!$C$2)*(내역!$B$2:$B={person})"
            f"*ISNUMBER(MATCH(내역!$D$2:$D,{cats},0))*IFERROR(내역!$K$2:$K*1,0)),0)")


def _overview() -> list[dict]:
    """청약·주식 한눈에: 사람별·부부 합계. 세부는 위 계좌 표(주식)와 오른쪽 청약 계좌 목록."""
    saving = [f'=SUMIFS(자산!$E$2:$E$50,자산!$B$2:$B$50,"청약",자산!$I$2:$I$50,{p})' for p in PEOPLE]
    rows = [["주식 (메리츠)", "=N(B7)", "=N(B10)"], ["주식 (ISA·한투)", "=N(B8)", "=N(B11)"], ["청약"] + saving,
            ["합계", "=SUM(B16:B18)", "=SUM(C16:C18)"], ["이번 달 청약 납입"] + [_saving_paid(p) for p in PEOPLE]]
    rows = [r + [f"=B{16 + i}+C{16 + i}"] for i, r in enumerate(rows)]
    detail = '=IFERROR(FILTER({자산!A2:A50,자산!I2:I50,자산!E2:E50},자산!B2:B50="청약"),"")'
    note = "추이 그래프 — 매일 아침 6시에 전날 값이 기록되고, 기록이 쌓이면 아래 그래프가 그려집니다."
    return [v(f"{INVEST}!A14", [["청약·주식 한눈에"]]),
            v(f"{INVEST}!A15:D15", [["구분", "=설정!E2", "=설정!E3", "부부 합계"]]), v(f"{INVEST}!A16:D20", rows),
            v(f"{INVEST}!G15:I15", [["청약 계좌", "소유자", "잔액"]]), v(f"{INVEST}!G16", [[detail]]),
            v(f"{INVEST}!A21", [[note]])]


def _trend_tables() -> list[dict]:
    months = (f'=IFERROR(SORT(UNIQUE(FILTER(ARRAYFORMULA(DATE(YEAR({L}!A2:A),MONTH({L}!A2:A),1)),'
              f'{L}!A2:A<>""))),"")')
    month_end = lambda col: (f'=MAP(A41:A100,LAMBDA(m,IF(m="","",IFERROR(VLOOKUP(MAX(FILTER({L}!$A$2:$A,'
                             f'{L}!$A$2:$A>=m,{L}!$A$2:$A<=EOMONTH(m,0))),{L}!$A$2:$K,{col},FALSE),""))))')
    recent = f'=IFERROR(SORT(FILTER({{{L}!A2:A,{L}!J2:J}},{L}!A2:A<>"",{L}!A2:A>=MAX({L}!A2:A)-29)),"")'
    return [v(f"{INVEST}!A40:C40", [["월", "합계 평가", "합계 원금"]]), v(f"{INVEST}!A41", [[months]]),
            v(f"{INVEST}!B41:C41", [[month_end(10), month_end(11)]]),
            v(f"{INVEST}!E40:F40", [["날짜", "합계 평가"]]), v(f"{INVEST}!E41", [[recent]])]


def invest_values() -> list[dict]:
    note = ("평가금액=현금 포함 총자산 · 원금=종목 매입금액 합계 · 손익·수익률=현금을 뺀 종목 기준 · "
            "H·I에 숫자를 적으면 그 계좌는 직접입력 값")
    out = [v(f"{INVEST}!A1", [["우리집 투자"]]),
           v(f"{INVEST}!G1:I1", [["지금 갱신", False, "◀ 체크하면 자동 갱신을 켠 사람의 계좌를 바로 갱신"]]),
           v(f"{INVEST}!A2", [[note]]), v(f"{INVEST}!A3:F3", [KPI_HEAD]), v(f"{INVEST}!A4:F4", [_kpi()]),
           v(f"{INVEST}!A6:I6", [TABLE_HEAD])]
    out += [v(f"{INVEST}!A{r[1]}:G{r[1]}", [account_row(*r)]) for r in ACCOUNT_ROWS]
    out += [v(f"{INVEST}!A{r[1]}:G{r[1]}", [total_row(*r)]) for r in TOTAL_ROWS]
    out += ([v(f"{INVEST}!J6", [[CASH_HEAD]])] + [v(f"{INVEST}!J{r[1]}", [[cash_cell(r[1], r[7])]]) for r in ACCOUNT_ROWS]
            + [v(f"{INVEST}!J{r[1]}", [[f'=IF(COUNT(J{r[2]},J{r[3]})=0,"",SUM(J{r[2]},J{r[3]}))']]) for r in TOTAL_ROWS])
    return (out + _overview() + _trend_tables()
            # 머리글·사람 이름만: B2:G3은 스크립트가 쓰는 결과라 재실행 때 지우면 안 된다
            + [v(f"{KIS_RAW}!A1:G1", [KIS_HEAD]), v(f"{KIS_RAW}!A2:A3", [[nm("신랑")], [nm("신부")]]),
               v(f"{L}!A1:L1", [LOG_HEAD]),
               v(f"{KIS_HOLD}!A1:K1", [[nm("신랑 구분"), *HOLD_HEAD, "", nm("신부 구분"), *HOLD_HEAD]])])


def structure_requests() -> list[dict]:
    check = {"setDataValidation": {"range": a1_to_grid(f"{INVEST}!H1"), "rule": {
        "condition": {"type": "BOOLEAN"}, "strict": False, "showCustomUi": True}}}
    fmts = [(f"{INVEST}!A4:C4", "NUMBER", "#,##0"), (f"{INVEST}!D4", "PERCENT", "0.0%"),
            (f"{INVEST}!E4:F4", "NUMBER", "+#,##0;-#,##0;0"), (f"{INVEST}!B7:D12", "NUMBER", "#,##0"), (f"{INVEST}!J7:J12", "NUMBER", "#,##0"),
            (f"{INVEST}!E7:E12", "PERCENT", "0.0%"), (f"{INVEST}!F7:F12", "DATE_TIME", "mm/dd hh:mm"),
            (f"{INVEST}!H7:I12", "NUMBER", "#,##0"), (f"{INVEST}!A41:A100", "DATE", "yyyy-mm"),
            (f"{INVEST}!B41:C100", "NUMBER", "#,##0"), (f"{INVEST}!E41:E100", "DATE", "m/d"),
            (f"{INVEST}!F41:F100", "NUMBER", "#,##0"), (f"{KIS_RAW}!E2:E3", "DATE_TIME", "yyyy-mm-dd hh:mm"),
            (f"{KIS_RAW}!F2:G3", "NUMBER", "#,##0"), (f"{L}!A2:A1000", "DATE", "yyyy-mm-dd"),
            (f"{L}!B2:K1000", "NUMBER", "#,##0"), (f"{INVEST}!B16:D20", "NUMBER", "#,##0"),
            (f"{INVEST}!I16:I19", "NUMBER", "#,##0")]
    return [check] + [number_format(a1, kind, pattern) for a1, kind, pattern in fmts]


def _fmt(a1: str, fmt: dict, fields: str) -> dict:
    return {"repeatCell": {"range": a1_to_grid(a1), "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def polish_requests() -> list[dict]:
    """한눈에 보이게: 제목·합계 숫자 크게, 합계 행 구분, 한눈에 표 머리글. 병합 없이 반복 적용해도 같은 결과."""
    head = {"backgroundColor": VIEW_TAB, "horizontalAlignment": "CENTER",
            "textFormat": {"fontSize": HEADER_FONT, "bold": True, "foregroundColor": WHITE}}
    head_f = "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
    total = {"backgroundColor": LABEL_BG, "textFormat": {"bold": True}}
    section = {"textFormat": {"fontSize": SECTION_FONT, "bold": True}}
    sid = SHEET_ID[INVEST]
    return ([_fmt(f"{INVEST}!A1", {"textFormat": {"fontSize": TITLE_FONT, "bold": True}}, "userEnteredFormat.textFormat"),
             _fmt(f"{INVEST}!A4:F4", {"horizontalAlignment": "CENTER", "textFormat": {"fontSize": KPI_FONT, "bold": True}},
                  "userEnteredFormat(horizontalAlignment,textFormat)")]
            + [_fmt(a1, total, "userEnteredFormat(backgroundColor,textFormat.bold)") for a1 in (f"{INVEST}!A9:G9", f"{INVEST}!A12:G12")]
            + [_fmt(a1, head, head_f) for a1 in (f"{INVEST}!A15:D15", f"{INVEST}!G15:I15")]
            + [_fmt(a1, section, "userEnteredFormat.textFormat") for a1 in (f"{INVEST}!A14", f"{INVEST}!A21")]
            + [_dim(sid, "ROWS", 0, 1, {"pixelSize": TITLE_ROW_PX}, "pixelSize"),
               _dim(sid, "ROWS", 3, 4, {"pixelSize": KPI_ROW_PX}, "pixelSize")])


def visual_requests() -> list[dict]:
    monthly = _basic("월별 투자 추이 (월말)", "LINE", f"{INVEST}!A40:A100",
                     [(f"{INVEST}!B40:B100", "LINE"), (f"{INVEST}!C40:C100", "LINE")])
    recent = _basic("최근 30일 합산 평가금액", "LINE", f"{INVEST}!E40:E100", [(f"{INVEST}!F40:F100", "LINE")])
    signs = [f"{INVEST}!C4", f"{INVEST}!E4:F4", f"{INVEST}!D7:E12"]
    manual = {"repeatCell": {"range": a1_to_grid(f"{INVEST}!H7:I12"), "cell": {"userEnteredFormat": {
        "backgroundColor": CHECK_BG}}, "fields": "userEnteredFormat.backgroundColor"}}
    return ([_chart(monthly, INVEST, CHART_ROWS[0], CHART_COLS[0]), _chart(recent, INVEST, CHART_ROWS[1], CHART_COLS[1]), manual] + polish_requests()
            + [_sign_rule(a1, "NUMBER_GREATER", RED_TEXT) for a1 in signs]
            + [_sign_rule(a1, "NUMBER_LESS", BLUE_TEXT) for a1 in signs])
