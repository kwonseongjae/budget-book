"""[자산현황] 탭: 목표(순자산·올해 저축), 올해 월별 저축률, 자산 분포, 부채 표.

입력은 설정 J8:J10(목표)과 부채 표 A·D:G·I열(사람). 이 모듈은 라벨·수식만 쓴다 — 입력 칸은 절대 쓰지 않음.
대출은 [자산] 탭 종류 '대출' 한 줄(초기 잔액 음수), 상환은 내역 '이체'(통장 → 대출)라 잔액·순자산은 기존 계산 그대로.
"""
from charts import _src
from formulas import EXP, INC, TYPE, YM, sumifs
from layout import ASSET_STATUS as S, ASSETS, DASH, MONTH_FMT, SETTINGS, SHEET_ID, a1_to_grid, number_format, v
from styling import BLUE_TEXT, NAVY_HEAD, RED_TEXT

CHART_TITLES = ["월별 저축률", "자산 분포"]
EXTRA_TITLES = ["자본 vs 부채", "고정지출 비율 (요약)"]  # 2026-10-14 시골쥐 대시보드 보강 — 운영엔 제목이 없을 때만 추가
DEBT_FIRST, DEBT_LAST = 36, 45
GROUPS = [("현금성", ["현금", "통장", "계좌"]), ("주식", ["주식"]), ("청약", ["청약"]), ("연금·기타", ["연금", "기타"]),
          ("부채", ["카드", "대출"])]
DIST_LAST = 27 + len(GROUPS) + 1   # 순자산 줄 (33)


def months_left(cell: str) -> str:
    """기한 칸(텍스트 'yyyy-mm' 또는 날짜) → 그 달까지 남은 개월(이번 달 = 0, 지난 기한도 0)."""
    end = f'IF(ISTEXT({cell}),DATEVALUE({cell}&"-01"),{cell})'
    return f'IFERROR(MAX(0,(YEAR({end})-YEAR(TODAY()))*12+MONTH({end})-MONTH(TODAY())),"")'  # 형식이 틀리면 빈칸


def _goal() -> list[dict]:
    head = [["현재 순자산", "목표 순자산", "달성률", "남은 개월", "필요 월 저축", "목표 기한"]]
    row = ["=SUM(자산!E2:E50)", f'=IF({SETTINGS}!J8="","",{SETTINGS}!J8)', '=IF(N(B5)=0,"",A5/B5)',
           f'=IF({SETTINGS}!J9="","",{months_left(f"{SETTINGS}!J9")})',
           '=IF(OR(B5="",D5=""),"",IF(D5<=0,"기한 지남",MAX(0,(B5-A5)/D5)))', f'=IF({SETTINGS}!J9="","",{SETTINGS}!J9)']
    year = [["올해 저축 누적", "올해 저축 목표", "달성률"],
            ["=SUM(D13:D24)", f'=IF({SETTINGS}!J10="","",{SETTINGS}!J10)', '=IF(N(B9)=0,"",A9/B9)']]
    return [v(f"{S}!A1", [["우리집 자산현황"]]), v(f"{S}!A3", [["목표"]]),
            v(f"{S}!A4:F4", head), v(f"{S}!A5:F5", [row]), v(f"{S}!A7", [["올해 저축"]]), v(f"{S}!A8:C9", year)]


def _monthly() -> list[dict]:
    out = [v(f"{S}!A11", [["월별 저축률 (올해)"]]),
           v(f"{S}!A12:F12", [["월", "수입", "소비지출", "저축", "저축률", "귀속월"]])]
    for m in range(1, 13):
        r = 12 + m
        out.append(v(f"{S}!A{r}:F{r}", [[f"{m}월", f"={sumifs((YM, f'F{r}'), (TYPE, INC))}",
                                         f"={sumifs((YM, f'F{r}'), (TYPE, EXP))}",
                                         f'=IF(AND(B{r}=0,C{r}=0),"",B{r}-C{r})',
                                         f'=IF(OR(N(B{r})=0,D{r}=""),"",D{r}/B{r})', f"=YEAR(TODAY())*100+{m}"]]))
    return out


def _distribution() -> list[dict]:
    rows = []
    for i, (name, kinds) in enumerate(GROUPS):
        r = 28 + i
        crit = "{" + ",".join(f'"{k}"' for k in kinds) + "}"
        share = "" if name == "부채" else f'=IF(B{r}<=0,"",B{r}/SUMIF(B28:B{DIST_LAST - 2},">0"))'
        # SUMIFS는 배열 조건의 첫 값만 본다 → FILTER+MATCH로 여러 종류 합
        total = (f"IFERROR(SUM(FILTER({ASSETS}!$E$2:$E$50,ISNUMBER(MATCH({ASSETS}!$B$2:$B$50,{crit},0)),"
                 f"ISNUMBER({ASSETS}!$E$2:$E$50))),0)")
        rows.append([name, f"={total}", share])
    rows.append(["순자산", f"=SUM(B28:B{DIST_LAST - 1})", ""])
    return [v(f"{S}!A26", [["자산 분포"]]), v(f"{S}!A27:C27", [["묶음", "금액", "비율"]]), v(f"{S}!A28:C{DIST_LAST}", rows)]


def _debt() -> list[dict]:
    a, f, z = f"A{DEBT_FIRST}:A{DEBT_LAST}", DEBT_FIRST, DEBT_LAST
    owner = f'=MAP({a},LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,{ASSETS}!$A$2:$I$50,9,FALSE),""))))'
    balance = f'=MAP({a},LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,{ASSETS}!$A$2:$E$50,5,FALSE),"자산 탭에 없음"))))'
    left = f'=MAP(G{f}:G{z},LAMBDA(x,IF(x="","",{months_left("x")})))'
    return [v(f"{S}!A34", [["부채"]]),
            v(f"{S}!A35:I35", [["대출명", "소유자", "현재 잔액", "금리", "월 상환액", "상환일", "만기", "남은 개월", "비고"]]),
            v(f"{S}!B{f}", [[owner]]), v(f"{S}!C{f}", [[balance]]), v(f"{S}!H{f}", [[left]]),
            v(f"{S}!K35", [["대출 목록"]]), v(f"{S}!K{f}", [[f'=IFERROR(FILTER({ASSETS}!A2:A50,{ASSETS}!B2:B50="대출"),"")']]),
            v(f"{S}!A{z + 1}:E{z + 1}", [["합계", "", f"=SUM(C{f}:C{z})", "", f"=SUM(E{f}:E{z})"]])]


def _quarters() -> list[dict]:
    rows = [[f"{q}분기"] + [f"=SUM({c}{13 + 3 * (q - 1)}:{c}{15 + 3 * (q - 1)})" for c in "BCD"]
            + [f'=IF(N(B{49 + q})=0,"",D{49 + q}/B{49 + q})'] for q in range(1, 5)]
    rows.append(["합계", "=SUM(B50:B53)", "=SUM(C50:C53)", "=SUM(D50:D53)", '=IF(N(B54)=0,"",D54/B54)'])
    return [v(f"{S}!A48", [["올해 분기별"]]), v(f"{S}!A49:E49", [["분기", "수입", "소비지출", "저축", "저축률"]]),
            v(f"{S}!A50:E54", rows),
            v(f"{S}!G48", [["자본 vs 부채"]]), v(f"{S}!G49:H49", [["구분", "금액"]]),
            v(f"{S}!G50:H51", [["자본(순자산)", f"=MAX(0,B{DIST_LAST})"], ["부채", f"=-B{DIST_LAST - 1}"]])]


def _kinds() -> list[dict]:
    a = lambda c: f"{ASSETS}!${c}$2:${c}$50"
    loose_stock = f'SUMIFS({a("E")},{a("B")},"주식",{a("G")},"")'
    rows = [["주식", f"=투자!B4+{loose_stock}", "=B29"],
            ["저축·현금성", "=B28", "=B28"],
            ["청약", "=B30", "=B30"],
            ["연금", "='저축·연금'!E39", f'=SUMIFS({a("E")},{a("B")},"연금")'],
            ["기타", "='저축·연금'!C54", f'=SUMIFS({a("E")},{a("B")},"기타")'],
            ["부채", "", f"=B{DIST_LAST - 1}"]]
    rows = [r + [f'=IF(OR(B{58 + i}="",N(B{58 + i})=0),"",C{58 + i}/B{58 + i}-1)'] for i, r in enumerate(rows)]
    rows.append(["합계", "=SUM(B58:B62)", "=SUM(C58:C63)", ""])
    return [v(f"{S}!A56", [["종류별 원금·현재 금액"]]), v(f"{S}!A57:D57", [["종류", "원금(매수)", "현재 금액", "수익률"]]),
            v(f"{S}!A58:D64", rows)]


H_ROW = 67     # 월별 저축률 가로형 표 머리글 행 (종류별 표 바로 아래, A~M열)
FIX_HEAD = 47  # 오른쪽 띠 고정지출 비율 표 머리글 (도넛 바로 아래)


def _horizontal() -> list[dict]:
    """월별 저축률 가로형 — 세로 표(A12:F24)를 그대로 돌려 보여 준다. 그래프 띠(L열~) 옆이면 탭이 화면보다 넓어져
    맨 아래 A~M열에 둔다(2026-10-14). 옛 자리 L17:X21은 비운다."""
    rows = [("구분", "A"), ("수입", "B"), ("소비지출", "C"), ("저축", "D"), ("저축률", "E")]
    return ([v(f"{S}!L17:X21", [[""] * 13] * 5), v(f"{S}!A80:M85", [[""] * 13] * 6),  # 옛 자리 비우기
             v(f"{S}!A{H_ROW - 1}", [["월별 저축률 (가로)"]])]
            + [v(f"{S}!A{H_ROW + i}:B{H_ROW + i}", [[name, f"=TRANSPOSE({c}13:{c}24)"]]) for i, (name, c) in enumerate(rows)])


def _fixed_panel() -> list[dict]:
    h = FIX_HEAD  # 먼저 옛 자리(62~78행)까지 비우고 도넛 바로 아래에 쓴다 — 옛 수식이 펼침을 막지 않게
    return [v(f"{S}!L47:N80", [[""] * 3] * 34), v(f"{S}!L{h}:N{h}", [["카테고리", "월납입액", "비율"]]),
            v(f"{S}!L{h + 1}", [["=ARRAYFORMULA(고정지출!L5:N19)"]]), v(f"{S}!L{h + 16}", [["=ARRAYFORMULA(고정지출!L20:N20)"]])]


def values() -> list[dict]:
    return _goal() + _monthly() + _distribution() + _debt() + _quarters() + _kinds() + _horizontal() + _fixed_panel()


def settings_labels() -> list[dict]:
    return [v(f"{SETTINGS}!I8:I10", [["목표 순자산"], ["목표 기한 (yyyy-mm)"], ["올해 저축 목표"]])]


def dashboard_kpi() -> list[dict]:
    return [v(f"{DASH}!M5:M6", [["목표 달성률"], [f'=IF({S}!C5="","",{S}!C5)']])]


def formats() -> list[dict]:
    money, pct = "NUMBER", "PERCENT"
    fmts = [(f"{S}!A5:B5", money, "#,##0"), (f"{S}!C5", pct, "0.0%"), (f"{S}!D5", money, "0"),
            (f"{S}!E5", money, "#,##0"), (f"{S}!A9:B9", money, "#,##0"), (f"{S}!C9", pct, "0.0%"),
            (f"{S}!B13:D24", money, "#,##0"), (f"{S}!E13:E24", pct, "0.0%"), (f"{S}!F13:F24", money, MONTH_FMT),
            (f"{S}!B28:B{DIST_LAST}", money, "#,##0"), (f"{S}!C28:C{DIST_LAST - 2}", pct, "0.0%"), (f"{S}!C36:C46", money, "#,##0"),
            (f"{S}!D36:D45", pct, "0.00%"), (f"{S}!E36:E46", money, "#,##0"), (f"{S}!H36:H45", money, "0"),
            (f"{DASH}!M6", pct, "0.0%"), (f"{SETTINGS}!J8", money, "#,##0"), (f"{SETTINGS}!J10", money, "#,##0")]
    pick = {"setDataValidation": {"range": a1_to_grid(f"{S}!A{DEBT_FIRST}:A{DEBT_LAST}"), "rule": {
        "condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={S}!$K${DEBT_FIRST}:$K${DEBT_LAST}"}]},
        "strict": False, "showCustomUi": True}}}
    hide = {"updateDimensionProperties": {"range": {"sheetId": SHEET_ID[S], "dimension": "COLUMNS",
                                                    "startIndex": 10, "endIndex": 11},
                                          "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}}
    return [number_format(a1, k, p) for a1, k, p in fmts] + [pick, hide] + extra_formats()


def extra_formats() -> list[dict]:
    """보강 구역 번호 서식 (repeatCell이라 운영에서 매번 적용해도 같음)."""
    money, pct = "NUMBER", "PERCENT"
    fmts = [(f"{S}!B50:D54", money, "#,##0"), (f"{S}!E50:E54", pct, "0.0%"), (f"{S}!H50:H51", money, "#,##0"),
            (f"{S}!B58:C64", money, "#,##0"), (f"{S}!D58:D64", pct, "0.0%"), (f"{S}!M{FIX_HEAD + 1}:M{FIX_HEAD + 16}", money, "#,##0"),
            (f"{S}!N{FIX_HEAD + 1}:N{FIX_HEAD + 16}", pct, "0.0%"), (f"{S}!B{H_ROW + 1}:M{H_ROW + 3}", money, "#,##0"), (f"{S}!B{H_ROW + 4}:M{H_ROW + 4}", pct, "0%"), (f"{S}!B28:B{DIST_LAST}", money, "#,##0"), (f"{S}!C28:C{DIST_LAST - 2}", pct, "0.0%")]
    return [number_format(a1, k, p) for a1, k, p in fmts]


def chart_requests() -> list[dict]:
    combo = {"title": CHART_TITLES[0], "basicChart": {
        "chartType": "COMBO", "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
        "domains": [{"domain": _src(f"{S}!A12:A24")}],
        "series": [{"series": _src(f"{S}!B12:B24"), "targetAxis": "LEFT_AXIS", "type": "COLUMN",
                    "colorStyle": {"rgbColor": RED_TEXT}},      # 수입 빨강
                   {"series": _src(f"{S}!C12:C24"), "targetAxis": "LEFT_AXIS", "type": "COLUMN",
                    "colorStyle": {"rgbColor": BLUE_TEXT}},     # 소비지출 파랑
                   {"series": _src(f"{S}!E12:E24"), "targetAxis": "RIGHT_AXIS", "type": "LINE",
                    "colorStyle": {"rgbColor": NAVY_HEAD}}]}}  # 저축률 남색
    pie = {"title": CHART_TITLES[1], "pieChart": {"legendPosition": "LABELED_LEGEND", "pieHole": 0.4,
                                                 "domain": _src(f"{S}!A28:A{DIST_LAST - 2}"),
                                                 "series": _src(f"{S}!B28:B{DIST_LAST - 2}")}}

    def at(row: int, col: int, w: int, h: int) -> dict:
        return {"overlayPosition": {"anchorCell": {"sheetId": SHEET_ID[S], "rowIndex": row, "columnIndex": col},
                                    "widthPixels": w, "heightPixels": h}}
    # 표(A~I열) 오른쪽 L열에 위아래로: 행 높이가 바뀌어도 표를 덮지 않는다
    # 오른쪽 띠: 월별 저축률 → 자산 분포 → 자본 vs 부채 → 고정지출 비율 (약 24px/줄로 빈틈없이)
    return [{"addChart": {"chart": {"spec": combo, "position": at(1, 11, 560, 280)}}},
            {"addChart": {"chart": {"spec": pie, "position": at(13, 11, 560, 280)}}}] + extra_chart_requests()


def extra_chart_requests() -> list[dict]:
    def at(row: int, h: int) -> dict:
        return {"overlayPosition": {"anchorCell": {"sheetId": SHEET_ID[S], "rowIndex": row, "columnIndex": 11},
                                    "widthPixels": 560, "heightPixels": h}}
    cap = {"title": EXTRA_TITLES[0], "pieChart": {"legendPosition": "LABELED_LEGEND",
                                                 "domain": _src(f"{S}!G50:G51"), "series": _src(f"{S}!H50:H51")}}
    fixed = {"title": EXTRA_TITLES[1], "pieChart": {"legendPosition": "LABELED_LEGEND", "pieHole": 0.45,
                                                   "domain": _src(f"{S}!L{FIX_HEAD + 1}:L{FIX_HEAD + 15}"),
                                                   "series": _src(f"{S}!M{FIX_HEAD + 1}:M{FIX_HEAD + 15}")}}
    return [{"addChart": {"chart": {"spec": cap, "position": at(25, 240)}}},
            {"addChart": {"chart": {"spec": fixed, "position": at(35, 260)}}}]
