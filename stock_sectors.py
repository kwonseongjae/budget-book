"""[주식투자] 탭: 두 메리츠 계좌 + 연동 안 된 주식 자산을 합친 보유 종목, 섹터별·종목별 비율 (시골쥐 '주식투자 시트').

섹터는 증권사 API가 주지 않으므로 '섹터 지정' 표에서 티커마다 한 번 고른다(분홍). 안 고른 종목은 '미지정'.
"""
from charts import _src
from names import localize as nm
from layout import ASSETS, KIS_HOLD, MERITZ_SLOTS, SHEET_ID, STOCKS as S, _protect, a1_to_grid, number_format, v
from styling import BLUE_TEXT, RED_TEXT

FIRST, LAST = 5, 124            # 보유 종목 120줄
# 오른쪽(K~N) 위에서부터: 합산 원형 2개(K·M, 4~16행) → 섹터별 표 → 사람별(원형 2개 + 종목 상위 표) ×2 → 섹터 지정 → 합산 상위 10
SEC_HEAD, SEC_FIRST, SEC_LAST = 17, 18, 31   # 260px 원형 바로 아래, 섹터별 14줄, 합계 32행
PERSON_TITLE = SEC_LAST + 3                  # 34행 제목
PERSON_CHART_ROWS = (PERSON_TITLE, PERSON_TITLE + 27)        # 그래프 35~47 · 62~74 (0부터 34·61)
PERSON_HEADS = tuple(r + 14 for r in PERSON_CHART_ROWS)       # 상위 표 머리글 48·75, 몸통 11줄, 합계 60·87
MAP_HEAD, MAP_FIRST, MAP_LAST = PERSON_HEADS[1] + 15, PERSON_HEADS[1] + 16, PERSON_HEADS[1] + 55   # 섹터 지정 90, 40줄 91~130
TOP_TITLE, TOP_HEAD = MAP_LAST + 2, MAP_LAST + 3              # 132행 제목, 133 머리글
TOP_FIRST, TOP_LAST = TOP_HEAD + 1, TOP_HEAD + 11             # 134~144, 합계 145
RIGHT = f"{S}!K4:N150"                                        # 오른쪽 영역 전체 (자리 옮길 때 한 번 비움)
MAP_TITLE_TEXT = "섹터 지정 — 티커마다 한 번 고르세요"
# 사람별 섹터 원형 원본: 숨김 열 (사람, 첫 열) — 2열씩
PEOPLE = [(nm("신랑"), "U"), (nm("신부"), "Y")]
HELPER = "T"                                  # 숨은 보조 열: 보유 티커 목록
SECTORS = ["반도체", "빅테크·플랫폼", "전기차·2차전지", "금융", "헬스케어", "소비재", "에너지·소재", "지수 ETF",
           "레버리지 ETF", "채권·현금성", "배당", "우주", "양자", "기타"]
CHART_TITLES = ["섹터별 보유 비율", "종목별 보유 비율"] + [f"{p} {k}" for p, _c in PEOPLE for k in ("섹터별", "종목별")]

TITLE = f"{S}!A1"
BADGE = ("N1", "N2")
SECTIONS = [f"{S}!A3", f"{S}!K3", f"{S}!K{PERSON_TITLE}", f"{S}!K{TOP_TITLE}", f"{S}!K{MAP_HEAD - 1}"]
HEADS = [f"{S}!A4:I4", f"{S}!K{SEC_HEAD}:N{SEC_HEAD}", f"{S}!K{TOP_HEAD}:M{TOP_HEAD}", f"{S}!K{MAP_HEAD}:L{MAP_HEAD}",
         f"{S}!N{MAP_HEAD}", f"{S}!G1"] + [f"{S}!K{h}:M{h}" for h in PERSON_HEADS]
TOTALS = [f"{S}!K{SEC_LAST + 1}:N{SEC_LAST + 1}", f"{S}!K{TOP_LAST + 1}:M{TOP_LAST + 1}"] + [f"{S}!K{h + 12}:M{h + 12}" for h in PERSON_HEADS]
SUBTOTALS: list = []
BODIES = [f"{S}!A{FIRST}:I{LAST}", f"{S}!K{SEC_FIRST}:N{SEC_LAST}", f"{S}!K{TOP_FIRST}:M{TOP_LAST}",
          f"{S}!K{MAP_FIRST}:L{MAP_LAST}", f"{S}!N{MAP_FIRST}:N{MAP_LAST}", f"{S}!H1"] + [f"{S}!K{h + 1}:M{h + 11}" for h in PERSON_HEADS]
INPUTS = [f"{S}!K{MAP_FIRST}:L{MAP_LAST}"]
RUNS = [("A", FIRST, LAST, "CCCLRRRCR"), ("K", SEC_FIRST, SEC_LAST, "CRRR"), ("K", TOP_FIRST, TOP_LAST, "LRR"),
        ("K", MAP_FIRST, MAP_LAST, "CC"), ("N", MAP_FIRST, MAP_LAST, "C")] + [("K", h + 1, h + 11, "LRR") for h in PERSON_HEADS]


def _account(stock: str, owner: str) -> str:
    r = lambda c: f"{stock}!{c}16:{c}115"
    return f'HSTACK(IF({r("B")}<>"","{owner}",""),{r("A")},{r("B")},{r("C")},{r("G")},{r("H")})'


KIS_COLS = [("ABCDE", nm("신랑")), ("GHIJK", nm("신부"))]  # 한투종목 탭: 구분·코드·종목명·매입·평가 (kis.gs KIS_HOLD_COL)


def _kis(cols: str, owner: str) -> str:
    r = lambda c: f"{KIS_HOLD}!{c}2:{c}101"
    return f'HSTACK(IF({r(cols[1])}<>"","{owner}",""),' + ",".join(r(c) for c in cols) + ")"


def holdings() -> str:
    """계좌 · 구분 · 티커 · 종목명 · 매입금액 · 평가금액. 메리츠·한투 ISA는 종목별, 연동 안 된 '주식' 자산은 한 줄(티커 = 자산명)."""
    a = lambda c: f"{ASSETS}!{c}2:{c}50"
    loose = (f'HSTACK({a("I")},IF({a("A")}<>"","미연동",""),{a("A")},{a("A")}&" (종목 미연동)",{a("E")},{a("E")})')
    keys = ",".join([f"{s.stock}!B16:B115" for s in MERITZ_SLOTS] + [f"{KIS_HOLD}!{c[1]}2:{c[1]}101" for c, _o in KIS_COLS]
                    + [f'IF(({a("B")}="주식")*({a("G")}="")*({a("A")}<>""),{a("A")},"")'])
    parts = ",".join([_account(s.stock, s.owner) for s in MERITZ_SLOTS] + [_kis(c, o) for c, o in KIS_COLS] + [loose])
    return f'=IFERROR(FILTER(VSTACK({parts}),VSTACK({keys})<>""),"")'


def _sector_summary() -> str:
    h, f, e = f"H{FIRST}:H{LAST}", f"F{FIRST}:F{LAST}", f"E{FIRST}:E{LAST}"
    return (f'=ARRAYFORMULA(IFERROR(LET(s,UNIQUE(FILTER({h},{h}<>"")),p,MAP(s,LAMBDA(x,SUMIFS({f},{h},x))),'
            f'b,MAP(s,LAMBDA(x,SUMIFS({e},{h},x))),SORT(HSTACK(s,p,p/SUM(p),IF(b=0,"",p/b-1)),2,FALSE)),""))')


def _top(owner: str = "") -> str:
    d, f = f"D{FIRST}:D{LAST}", f"F{FIRST}:F{LAST}"
    who = f',A{FIRST}:A{LAST}="{owner}"' if owner else ""  # 사람별이면 그 사람 줄만
    return (f'=ARRAYFORMULA(IFERROR(LET(d,SORT(FILTER(HSTACK({d},{f}),{d}<>""{who}),2,FALSE),n,ROWS(d),t,SUM(INDEX(d,,2)),'
            f'top,ARRAY_CONSTRAIN(d,MIN(10,n),2),o,VSTACK(top,HSTACK("기타",t-SUM(INDEX(top,,2)))),'
            f'k,FILTER(o,INDEX(o,,2)>0),HSTACK(k,INDEX(k,,2)/t)),""))')  # 기타가 0이면 FILTER로 뺀다(IF는 배열 크기가 다르면 오류)


def _nx(col: str) -> str:
    """다음 열 문자 (U → V, Z → AA, AA → AB)."""
    n = 0
    for ch in col:
        n = n * 26 + ord(ch) - 64
    n += 1
    out = ""
    while n:
        n, r = divmod(n - 1, 26)
        out = chr(65 + r) + out
    return out


def _person_sectors(owner: str) -> str:
    a, h, f = f"A{FIRST}:A{LAST}", f"H{FIRST}:H{LAST}", f"F{FIRST}:F{LAST}"
    return (f'=ARRAYFORMULA(IFERROR(LET(s,UNIQUE(FILTER({h},{h}<>"",{a}="{owner}")),'
            f'p,MAP(s,LAMBDA(x,SUMIFS({f},{h},x,{a},"{owner}"))),SORT(HSTACK(s,p),2,FALSE)),""))')


def _person_values() -> list[dict]:
    out = [v(f"{S}!U4:AB30", [[""] * 8] * 27), v(f"{S}!K{PERSON_TITLE}", [["사람별 — 섹터별·종목별 보유 비율"]])]
    for (owner, sc), h in zip(PEOPLE, PERSON_HEADS):
        t = h + 12
        out += [v(f"{S}!{sc}4:{_nx(sc)}4", [[f"{owner} 섹터", "평가금액"]]), v(f"{S}!{sc}{FIRST}", [[_person_sectors(owner)]]),
                v(f"{S}!K{h}:M{h}", [[f"{owner} 종목", "평가금액", "비율"]]), v(f"{S}!K{h + 1}", [[_top(owner)]]),
                v(f"{S}!K{t}:M{t}", [["합계", f"=SUM(L{h + 1}:L{h + 11})", f'=IF(L{t}>0,1,"")']])]
    return out


def relocate(col_kl, protect_ids) -> tuple[list, list]:
    """운영 섹터 지정 표가 옛 자리면 한 번: 오른쪽 영역을 비우고 입력값을 새 자리로, 드롭다운·보호 범위도 새 자리로.
    col_kl = 운영 K:L 값(1행부터), protect_ids = 이 탭 보호 범위 id들. 이미 새 자리거나 못 찾으면 아무것도 안 함."""
    col = [str(r[0]) if r else "" for r in col_kl]
    if MAP_TITLE_TEXT not in col or col.index(MAP_TITLE_TEXT) + 1 == MAP_HEAD - 1:
        return [], []
    t = col.index(MAP_TITLE_TEXT) + 1
    data = [list(r[:2]) + [""] * (2 - len(r[:2])) for r in col_kl[t + 1:t + 41]]
    data = [r for r in data if any(str(x).strip() for x in r)]
    values = [v(RIGHT, [[""] * 4] * 147)] + ([v(f"{S}!K{MAP_FIRST}:L{MAP_FIRST + len(data) - 1}", data)] if data else [])
    structure = ([{"setDataValidation": {"range": a1_to_grid(RIGHT)}}] + _map_validation()
                 + _sign(f"{S}!N{SEC_FIRST}:N{SEC_LAST + 1}")
                 + [{"deleteProtectedRange": {"protectedRangeId": i}} for i in protect_ids]
                 + [_protect({"sheetId": SHEET_ID[S]}, [a1_to_grid(a1) for a1 in INPUTS])])
    return structure, values


def values() -> list[dict]:
    c, f, e = f"C{FIRST}:C{LAST}", f"F{FIRST}:F{LAST}", f"E{FIRST}:E{LAST}"
    k = f"K{MAP_FIRST}:K{MAP_LAST}"
    sector = f'=MAP({c},LAMBDA(x,IF(x="","",IFERROR(INDEX(L{MAP_FIRST}:L{MAP_LAST},MATCH(x,{k},0))&"","미지정"))))'
    fix = lambda s: f'=MAP({c},LAMBDA(x,IF(x="","",{s})))'
    rate = f'=MAP({e},{f},LAMBDA(b,p,IF(OR(b="",N(b)=0),"",p/b-1)))'
    share = f'=MAP({f},LAMBDA(p,IF(p="","",p/SUM({f}))))'
    hl = f"{HELPER}{FIRST}:{HELPER}{LAST}"
    s1, t1 = SEC_LAST + 1, TOP_LAST + 1
    usd = f'=IFERROR(VLOOKUP("USD",{MERITZ_SLOTS[0].stock}!A9:C12,3,FALSE),"")'
    return [v(TITLE, [["주식투자"]]), v(f"{S}!G1:H1", [["USD/KRW", usd]]),
            v(f"{S}!A3", [["보유 종목 — 두 메리츠 계좌 자동 + [자산]의 연동 안 된 주식"]]),
            v(f"{S}!A4:I4", [["계좌", "구분", "티커", "종목명", "매입금액", "평가금액", "수익률", "섹터", "비중"]]),
            v(f"{S}!A{FIRST}", [[holdings()]]), v(f"{S}!G{FIRST}", [[rate]]), v(f"{S}!H{FIRST}", [[sector]]),
            v(f"{S}!I{FIRST}", [[share]]),
            v(f"{S}!K3", [["부부 합산 — 섹터별·종목별 보유 비율"]]), v(f"{S}!K{SEC_HEAD}:N{SEC_HEAD}", [["섹터", "평가금액", "비율", "수익률"]]),
            v(f"{S}!K{SEC_FIRST}", [[_sector_summary()]]),
            v(f"{S}!K{s1}:N{s1}", [["합계", f"=SUM(L{SEC_FIRST}:L{SEC_LAST})", f'=IF(L{s1}>0,1,"")',
                                    f'=IFERROR(L{s1}/SUM({e})-1,"")']]),
            # 옛 자리(P~R, 업데이트일 R1:R2)는 비운다 — 매번 써도 다른 것이 없는 자리
            v(f"{S}!P3", [[""]]), v(f"{S}!P18:R30", [[""] * 3] * 13), v(f"{S}!R1:R2", [[""], [""]]),
            v(f"{S}!K{TOP_TITLE}", [["종목별 상위 10 (부부 합산)"]]), v(f"{S}!K{TOP_HEAD}:M{TOP_HEAD}", [["종목", "평가금액", "비율"]]),
            v(f"{S}!K{TOP_FIRST}", [[_top()]]),
            v(f"{S}!K{t1}:M{t1}", [["합계", f"=SUM(L{TOP_FIRST}:L{TOP_LAST})", f'=IF(L{t1}>0,1,"")']]),
            v(f"{S}!K{MAP_HEAD - 1}", [[MAP_TITLE_TEXT]]),
            v(f"{S}!K{MAP_HEAD}:L{MAP_HEAD}", [["티커", "섹터"]]), v(f"{S}!N{MAP_HEAD}", [["섹터를 고를 종목"]]),
            v(f"{S}!N{MAP_FIRST}", [[f'=IFERROR(FILTER({hl},{hl}<>"",ISNA(MATCH({hl},{k},0))),"모두 지정됨")']]),
            v(f"{S}!{HELPER}4", [["보유 티커"]]),
            v(f"{S}!{HELPER}{FIRST}", [[f'=IFERROR(SORT(UNIQUE(FILTER({c},{c}<>""))),"")']])] + _person_values()


def _sign(a1: str) -> list[dict]:
    def rule(ctype, color):
        return {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [a1_to_grid(a1)], "booleanRule": {
            "condition": {"type": ctype, "values": [{"userEnteredValue": "0"}]},
            "format": {"textFormat": {"foregroundColor": color}}}}}}
    return [rule("NUMBER_GREATER", RED_TEXT), rule("NUMBER_LESS", BLUE_TEXT)]


def formats() -> list[dict]:
    s1, t1 = SEC_LAST + 1, TOP_LAST + 1
    fmts = [(f"{S}!E{FIRST}:F{LAST}", "NUMBER", "#,##0"), (f"{S}!G{FIRST}:G{LAST}", "PERCENT", "0.0%"),
            (f"{S}!I{FIRST}:I{LAST}", "PERCENT", "0.0%"), (f"{S}!L{SEC_FIRST}:L{s1}", "NUMBER", "#,##0"),
            (f"{S}!M{SEC_FIRST}:N{s1}", "PERCENT", "0.0%"), (f"{S}!L{TOP_FIRST}:L{t1}", "NUMBER", "#,##0"),
            (f"{S}!M{TOP_FIRST}:M{t1}", "PERCENT", "0.0%"), (f"{S}!H1", "NUMBER", "#,##0.00")]
    fmts += [x for h in PERSON_HEADS for x in ((f"{S}!L{h + 1}:L{h + 12}", "NUMBER", "#,##0"),
                                               (f"{S}!M{h + 1}:M{h + 12}", "PERCENT", "0.0%"))]
    return ([number_format(a1, k, p) for a1, k, p in fmts] + _map_validation()
            + _sign(f"{S}!G{FIRST}:G{LAST}") + _sign(f"{S}!N{SEC_FIRST}:N{s1}"))


def _map_validation() -> list[dict]:
    rng = lambda formula: {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": formula}]},
                           "strict": False, "showCustomUi": True}
    return [{"setDataValidation": {"range": a1_to_grid(f"{S}!K{MAP_FIRST}:K{MAP_LAST}"),
                                   "rule": rng(f"={S}!${HELPER}${FIRST}:${HELPER}${LAST}")}},
            {"setDataValidation": {"range": a1_to_grid(f"{S}!L{MAP_FIRST}:L{MAP_LAST}"), "rule": {
                "condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": x} for x in SECTORS]},
                "strict": False, "showCustomUi": True}}}]


def chart_requests() -> list[dict]:
    def pie(title, col, rows, row, at, hidden=False):
        a, b = rows
        spec = {"title": title, "pieChart": {"legendPosition": "LABELED_LEGEND", "domain": _src(f"{S}!{col}{a}:{col}{b}"),
                                             "series": _src(f"{S}!{_nx(col)}{a}:{_nx(col)}{b}")}}
        if hidden:  # 원본이 숨김 열 — 숨긴 칸도 그린다
            spec["hiddenDimensionStrategy"] = "SHOW_ALL"
        return {"addChart": {"chart": {"spec": spec, "position": {"overlayPosition": {
            "anchorCell": {"sheetId": SHEET_ID[S], "rowIndex": row, "columnIndex": at}, "widthPixels": 340, "heightPixels": 260}}}}}
    out = [pie(CHART_TITLES[0], "K", (SEC_FIRST, SEC_LAST), 3, 10), pie(CHART_TITLES[1], "K", (TOP_FIRST, TOP_LAST), 3, 12)]
    titles = iter(CHART_TITLES[2:])
    for (_o, sc), row, h in zip(PEOPLE, PERSON_CHART_ROWS, PERSON_HEADS):
        out += [pie(next(titles), sc, (FIRST, FIRST + 13), row, 10, True), pie(next(titles), "K", (h + 1, h + 11), row, 12)]
    return out


WIDTHS = [70, 60, 80, 220, 110, 110, 70, 110, 60, 20, 110, 110, 90, 110, 20, 160, 110, 70, 20, 100] + [100] * 8
HELPER_COLS = list(range(20, 28))  # U~AB: 사람별 그래프 원본
HIDDEN = [19] + HELPER_COLS  # T: 보유 티커 보조 열
