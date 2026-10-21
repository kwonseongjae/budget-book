"""보기 탭 수식: 추이(월별·카테고리×월·연도별), 달력, 검색."""
from formulas import CAT, DATE_COL, EXP, INC, OUTFLOW, START, TYPE, YM, by_major, month_pick, per_row, sumifs
from layout import CAL, CALC, MONTH_FMT, SEARCH, TREND, TXN_HEADERS, YEAR_MOVE_HINT, number_format, v

TR_HEAD, TR_FIRST, HEAT_LAST, YEAR_LAST = 38, 39, 68, 58


def _trend_monthly(y: str) -> list[dict]:
    row = ['=ARRAYFORMULA(SEQUENCE(12)&"월")',
           f"=MAP(SEQUENCE(12),LAMBDA(i,{sumifs((YM, f'{y}*100+i'), (TYPE, INC))}))",
           f"=MAP(SEQUENCE(12),LAMBDA(i,{sumifs((YM, f'{y}*100+i'), *OUTFLOW)}))",
           "=ARRAYFORMULA(B39:B50-C39:C50)"]
    return [v(f"{TREND}!A39:D39", [row])]


def _trend_heatmap(y: str) -> list[dict]:
    cats = f"={by_major()}"
    cells = []
    for r in range(TR_FIRST, HEAT_LAST + 1):
        cells.append([f'=IF($F{r}="","",{sumifs((YM, f"{y}*100+{i}"), *OUTFLOW, (CAT, f"$F{r}"))})'
                      for i in range(1, 13)])
    return [v(f"{TREND}!F39", [[cats]]), v(f"{TREND}!G39:R68", cells)]


def _trend_yearly() -> list[dict]:
    years = "T39:T58"
    row = ['=IFERROR(ARRAYFORMULA(TO_TEXT(SORT(UNIQUE(FILTER(INT(내역!L2:L/100),ISNUMBER(내역!L2:L)))))),"")',
           "=" + per_row(years, sumifs((YM, '">="&x*100'), (YM, '"<"&(x+1)*100'), (TYPE, INC))),
           "=" + per_row(years, sumifs((YM, '">="&x*100'), (YM, '"<"&(x+1)*100'), *OUTFLOW)),
           f'=ARRAYFORMULA(IF({years}="","",U39:U58-V39:V58))']
    return [v(f"{TREND}!T39:W39", [row])]


def trend_values() -> list[dict]:
    y = "$B$2"
    top = [["연도", "", YEAR_MOVE_HINT], ["적용 연도", f'=IF(B1="",INT({CALC}!$C$2/100),B1)', ""]]
    head = [["월", "수입", "지출·저축", "잔액", "", "카테고리"] + [f"{i}월" for i in range(1, 13)]
            + ["", "연도", "수입", "지출·저축", "잔액"]]
    return ([v(f"{TREND}!A1:C2", top), v(f"{TREND}!A38:W38", head)]
            + _trend_monthly(y) + _trend_heatmap(y) + _trend_yearly())


def calendar_values() -> list[dict]:
    top = [["조회 월", "", "기간 시작", "기간 끝", "그리드 시작"],
           ["적용 월", f"={month_pick('B1')}", f"=DATE(INT(B2/100),MOD(B2,100),{START})",
            "=EDATE(C2,1)-1", "=C2-WEEKDAY(C2)+1"]]
    grid = []
    for w in range(6):
        date_row = 5 + 2 * w
        grid.append([f'=IF(AND($E$2+{w * 7 + c}>=$C$2,$E$2+{w * 7 + c}<=$D$2),$E$2+{w * 7 + c},"")'
                     for c in range(7)])
        grid.append([f'=IF({col}{date_row}="","",{sumifs((DATE_COL, f"{col}{date_row}"), (TYPE, EXP))})'
                     for col in "ABCDEFG"])
    week = [["일", "월", "화", "수", "목", "금", "토"]]
    return [v(f"{CAL}!A1:E2", top), v(f"{CAL}!A4:G4", week), v(f"{CAL}!A5:G16", grid)]


def search_cond() -> str:
    """빈 입력칸은 조건 없음으로 취급하는 FILTER 조건(숫자 배열)."""
    return ('(내역!A2:A<>"")'
            '*((($B$1="")+ISNUMBER(SEARCH($B$1,내역!D2:D&" "&내역!E2:E&" "&내역!J2:J)))>0)'
            '*((($B$2="")+(내역!A2:A>=$B$2))>0)'
            '*((($B$3="")+(내역!A2:A<=$B$3))>0)'
            '*((($B$4="")+(내역!B2:B=$B$4))>0)')


def search_totals() -> list[dict]:
    """합계는 대시보드와 같게 귀속월(L)이 숫자인 줄만 — 날짜·금액 오류 줄은 빼고, 몇 건 뺐는지 D3에 알린다 (A14)."""
    c = search_cond()
    ok = "ISNUMBER(내역!L2:L)*ISNUMBER(내역!K2:K)"
    totals = [["지출 합계", f'=IFERROR(SUM(FILTER(내역!K2:K,{c}*{ok}*(내역!C2:C="지출"))),0)'],
              ["수입 합계", f'=IFERROR(SUM(FILTER(내역!K2:K,{c}*{ok}*(내역!C2:C="수입"))),0)']]
    skipped = f'IFERROR(ROWS(FILTER(내역!A2:A,{c}*(1-{ok}))),0)'
    note = f'=LET(n,{skipped},IF(n>0,"※ 날짜·금액 오류 "&n&"건은 합계에서 제외 (내역 빨간 줄)",""))'
    return [v(f"{SEARCH}!D1:E2", totals), v(f"{SEARCH}!D3", [[note]])]


def search_values() -> list[dict]:
    c = search_cond()
    return [v(f"{SEARCH}!A1:A4", [["키워드"], ["시작일"], ["종료일"], ["사용자"]]),
            *search_totals(),
            v(f"{SEARCH}!A6:J6", [TXN_HEADERS]),
            v(f"{SEARCH}!A7", [[f'=IFNA(FILTER(내역!A2:J,{c}),"결과 없음")']])]


def view_values() -> list[dict]:
    return trend_values() + calendar_values() + search_values()


def view_formats() -> list[dict]:
    fmts = [(f"{TREND}!B39:D50", "NUMBER", "#,##0"), (f"{TREND}!G39:R68", "NUMBER", "#,##0"),
            (f"{TREND}!U39:W58", "NUMBER", "#,##0"),
            (f"{CAL}!B2", "NUMBER", MONTH_FMT), (f"{CAL}!C2:E2", "DATE", "yyyy-mm-dd"),
            (f"{SEARCH}!E1:E2", "NUMBER", "#,##0"), (f"{SEARCH}!A7:A1000", "DATE", "yyyy-mm-dd"),
            (f"{SEARCH}!H7:H1000", "NUMBER", "#,##0")]
    for w in range(6):
        fmts.append((f"{CAL}!A{5 + 2 * w}:G{5 + 2 * w}", "DATE", "m/d"))
        fmts.append((f"{CAL}!A{6 + 2 * w}:G{6 + 2 * w}", "NUMBER", "#,##0;-#,##0;"))
    return [number_format(a1, kind, pattern) for a1, kind, pattern in fmts]
