"""부부 탭(사람별 요약·반반 정산·카테고리×사람 예산)과 자산기록 탭(순자산 추이)."""
from charts import ORANGE, RED, _basic, _bool_rule
from formulas import EXP, INC, OUTFLOW, TYPE, USER, YM, CAT, by_major, month_pick, per_row, sumifs
from layout import ASSETS, COUPLE, MONTH_FMT, MONTH_MOVE_HINT, NETWORTH, SETTINGS, SHEET_ID, TXN, number_format, v

USER_CELLS = [f"{SETTINGS}!$E${r}" for r in (2, 3, 4)]  # 사용자 슬롯: 사람1, 사람2, 공동 (예산 K·L·M열 순서)
BUDGET_COLS = [11, 12, 13]                                # 설정 A:M에서 K·L·M의 열 번호
CAT_FIRST, CAT_LAST = 16, 55
CATS = f"$A{CAT_FIRST}:$A{CAT_LAST}"
TABLE_COLS = ["C", "F", "I"]                              # 사람별 [지출, 예산, 사용률] 시작 열
NET_HEADERS = ["월", "순자산", "자산(부채 제외)", "카드·대출 잔액"]


def _summary() -> list[dict]:
    rows = []
    for i, user in enumerate(USER_CELLS):
        r, me = 5 + i, f"$A{5 + i}"
        rows.append([f"={user.replace('$', '')}",
                     f"={sumifs((YM, '$B$2'), (TYPE, INC), (USER, me))}",
                     f"={sumifs((YM, '$B$2'), (TYPE, EXP), (USER, me))}",
                     f"={sumifs((YM, '$B$2'), *OUTFLOW, (TYPE, '\"<>지출\"'), (USER, me))}",
                     f"=B{r}-C{r}-D{r}"])
    return [v(f"{COUPLE}!A4:E4", [["사람", "수입", "지출", "저축·기타", "남은 돈"]]), v(f"{COUPLE}!A5:E7", rows)]


def _joint_base() -> tuple[str, str]:
    """(결제수단 소유자 배열, 이 달 공동 나가는 돈 행 = 1인 배열) — SUMPRODUCT 안에서 쓴다."""
    owner = f'IFERROR(VLOOKUP({TXN}!$F$2:$F,{ASSETS}!$A$2:$I$50,9,FALSE),"")'
    c = f"{TXN}!$C$2:$C"
    base = (f'({TXN}!$B$2:$B={USER_CELLS[2]})*({TXN}!$L$2:$L=$B$2)'
            f'*({c}<>"")*({c}<>"수입")*({c}<>"이체")')
    return owner, base


def _settlement() -> list[dict]:
    owner, base = _joint_base()
    krw = f"IFERROR({TXN}!$K$2:$K*1,0)"
    paid = [[f'={p}&" 결제분 (공동)"', f"=ARRAYFORMULA(LET(o,{owner},SUMPRODUCT({base}*(o={p})*{krw})))"]
            for p in USER_CELLS[:2]]
    p1, p2 = USER_CELLS[0], USER_CELLS[1]
    verdict = (f'=IF(B10=B11,"정산할 금액 없음",IF(B10>B11,{p2}&" → "&{p1},{p1}&" → "&{p2})'
               f'&" "&TEXT(ABS((B10-B11)/2),"#,##0")&"원")')
    known = "+".join(f"(o={u})" for u in USER_CELLS)
    unknown = f"=ARRAYFORMULA(LET(o,{owner},b,{base},SUMPRODUCT(b)-SUMPRODUCT(b*({known}))))"
    title = "공동 지출 정산 (반반) — 사용자 '공동'으로 적은 지출을 결제수단 소유자([자산] I열)가 낸 것으로 계산"
    return [v(f"{COUPLE}!A9", [[title]]), v(f"{COUPLE}!A10:B11", paid),
            v(f"{COUPLE}!A12:B13", [["정산", verdict], ["미지정 결제 건수", unknown]])]


def _category_table() -> list[dict]:
    head = ["카테고리", "구분"]
    row = [f"={by_major('B')}", ""]
    for user, bcol, start in zip(USER_CELLS, BUDGET_COLS, TABLE_COLS):
        spend_col = start
        budget_col = chr(ord(start) + 1)
        rng = lambda c: f"{c}{CAT_FIRST}:{c}{CAT_LAST}"
        head += [f'={user}&" 지출"', "예산", "사용률"]
        row += [f"={per_row(CATS, sumifs((YM, '$B$2'), *OUTFLOW, (CAT, 'x'), (USER, user)))}",
                f'=ARRAYFORMULA(IF({CATS}="","",IFERROR(1/(1/VLOOKUP({CATS},{SETTINGS}!$A:$M,{bcol},FALSE)),"")))',
                f'=ARRAYFORMULA(IF(({CATS}="")+({rng(budget_col)}=""),"",{rng(spend_col)}/{rng(budget_col)}))']
    return [v(f"{COUPLE}!A15:K15", [head]), v(f"{COUPLE}!A16:K16", [row])]


def couple_values() -> list[dict]:
    top = [["조회 월", "", MONTH_MOVE_HINT], ["적용 월", f"={month_pick('B1')}", ""]]
    return ([v(f"{COUPLE}!A1:C2", top), v(f"{COUPLE}!E1", [["부부 — 사람별 살림과 정산"]])]
            + _summary() + _settlement() + _category_table()
            + [v(f"{NETWORTH}!A1:D1", [NET_HEADERS]),
               # 그래프 가로축용 글자 월 — 숫자(202610)를 그대로 쓰면 축이 0000-00, 1000-00 … 숫자 눈금이 된다
               v(f"{NETWORTH}!E1:E2", [["그래프 월"], ['=ARRAYFORMULA(IF(A2:A="","",TEXT(A2:A,"0000-00")))']])])


def couple_formats() -> list[dict]:
    money = [f"{COUPLE}!B5:E7", f"{COUPLE}!B10:B11"] + [
        f"{COUPLE}!{c}{CAT_FIRST}:{chr(ord(c) + 1)}{CAT_LAST}" for c in TABLE_COLS]
    return ([number_format(f"{COUPLE}!B2", "NUMBER", MONTH_FMT)]
            + [number_format(a1, "NUMBER", "#,##0") for a1 in money]
            + [number_format(a1, "PERCENT", "0%") for a1 in rate_ranges()])


def rate_ranges() -> list[str]:
    return [f"{COUPLE}!{chr(ord(c) + 2)}{CAT_FIRST}:{chr(ord(c) + 2)}{CAT_LAST}" for c in TABLE_COLS]


def couple_conditional() -> list[dict]:
    reqs = []
    for a1 in rate_ranges():
        reqs += [_bool_rule(a1, 1, RED, 0), _bool_rule(a1, 0.8, ORANGE, 1)]
    return reqs


def networth_chart() -> dict:
    spec = _basic("월별 순자산", "LINE", f"{NETWORTH}!E1:E200",
                  [(f"{NETWORTH}!B1:B200", "LINE"), (f"{NETWORTH}!C1:C200", "LINE"), (f"{NETWORTH}!D1:D200", "LINE")])
    anchor = {"sheetId": SHEET_ID[NETWORTH], "rowIndex": 3, "columnIndex": 5}  # 1~2행 G열 '업데이트일' 아래
    return {"addChart": {"chart": {"spec": spec, "position": {"overlayPosition": {
        "anchorCell": anchor, "widthPixels": 600, "heightPixels": 320}}}}}


def visual_requests() -> list[dict]:
    return couple_conditional() + [networth_chart()]

