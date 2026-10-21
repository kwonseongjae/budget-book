"""대시보드 맨 아래: 분류별 수입·지출·저축 표 + 가로 막대그래프 3개, 이번 달 저축 대비 월 목표 (시골쥐 '가계부 예시').

조회 월은 대시보드 B2(적용 월). 위치는 고정비·변동비 구역(base) 아래 52행부터 — 운영은 base를 찾아 넘긴다.
"""
from charts import _src
from layout import DASH, SHEET_ID, a1_to_grid, number_format, v
from styling import BLUE_TEXT, HEADER_FONT, NAVY_HEAD, RED_TEXT, SECTION_FONT, WHITE

M = "$B$2"
TABLES = [("수입", "A", RED_TEXT), ("지출", "E", BLUE_TEXT), ("저축", "I", NAVY_HEAD)]  # 고른 간격, 그래프가 각 표 바로 밑
CHART_TITLES = [f"분류별 {t}" for t, _c, _k in TABLES]


def rows(base: int) -> dict:
    c = base + 43  # 고정비·변동비 그래프(표 끝 다음 행부터 280px) 바로 아래
    return {"title": c, "save_head": c + 1, "save": c + 2, "head": c + 4, "first": c + 5, "last": c + 16, "chart": c + 16}


def _nxt(col: str) -> str:
    return chr(ord(col) + 1)


def _by_category(kind: str) -> str:
    sums = f'SUMIFS(내역!$K:$K,내역!$L:$L,{M},내역!$C:$C,"{kind}",내역!$D:$D,x)'
    return (f'=IFERROR(LET(c,UNIQUE(FILTER(내역!$D$2:$D,내역!$L$2:$L={M},내역!$C$2:$C="{kind}",내역!$D$2:$D<>"")),'
            f'a,MAP(c,LAMBDA(x,{sums})),SORT(FILTER(HSTACK(c,a),a>0),2,FALSE)),"")')


def values(base: int) -> list[dict]:
    r = rows(base)
    s = r["save"]
    end = base + 95  # 대시보드 맨 아래 — 옛 자리(구역이 base+52에서 시작하던 때) 값까지 먼저 비운다
    out = [v(f"{DASH}!A{r['title']}:J{end}", [[""] * 10] * (end - r["title"] + 1)),
           v(f"{DASH}!A{r['title']}", [["분류별 수입·지출·저축 (조회 월)"]]),
           v(f"{DASH}!A{r['save_head']}:C{r['save_head']}", [["이번 달 저축", "월 목표", "달성률"]]),  # 월 목표 = 올해 저축 목표÷12
           v(f"{DASH}!A{s}:C{s}", [[f'=SUMIFS(내역!$K:$K,내역!$L:$L,{M},내역!$C:$C,"저축")',
                                    '=IF(N(자산현황!B9)=0,"",자산현황!B9/12)', f'=IF(N(B{s})=0,"",A{s}/B{s})']]),
           ]
    for kind, col, _color in TABLES:
        out += [v(f"{DASH}!{col}{r['head']}:{_nxt(col)}{r['head']}", [[f"분류별 {kind}", "금액"]]),
                v(f"{DASH}!{col}{r['first']}", [[_by_category(kind)]])]
    return out


def _fmt(a1: str, fmt: dict, fields: str) -> dict:
    return {"repeatCell": {"range": a1_to_grid(a1), "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def style_requests(base: int) -> list[dict]:
    r = rows(base)
    head = {"backgroundColor": NAVY_HEAD, "horizontalAlignment": "CENTER",
            "textFormat": {"fontSize": HEADER_FONT, "bold": True, "foregroundColor": WHITE}}
    hf = "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
    heads = [f"{DASH}!A{r['save_head']}:C{r['save_head']}"] + [f"{DASH}!{c}{r['head']}:{_nxt(c)}{r['head']}" for _k, c, _x in TABLES]
    s = r["save"]
    fmts = ([(f"{DASH}!A{s}:B{s}", "NUMBER", "#,##0"), (f"{DASH}!C{s}", "PERCENT", "0%")]
            + [(f"{DASH}!{_nxt(c)}{r['first']}:{_nxt(c)}{r['last']}", "NUMBER", "#,##0") for _k, c, _x in TABLES])
    title = _fmt(f"{DASH}!A{r['title']}", {"textFormat": {"fontSize": SECTION_FONT, "bold": True, "foregroundColor": NAVY_HEAD}},
                 "userEnteredFormat.textFormat")
    return [_fmt(a1, head, hf) for a1 in heads] + [number_format(a1, k, p) for a1, k, p in fmts] + [title]


def align_runs(base: int) -> list[tuple]:
    r = rows(base)
    return ([(DASH, "A", r["save"], r["save"], "RRR")]
            + [(DASH, c, r["first"], r["last"], "LR") for _k, c, _x in TABLES])


def chart_requests(base: int) -> list[dict]:
    r = rows(base)
    out = []
    for (kind, col, color), title in zip(TABLES, CHART_TITLES):
        spec = {"title": title, "basicChart": {
            "chartType": "BAR", "legendPosition": "NO_LEGEND", "headerCount": 0,
            "domains": [{"domain": _src(f"{DASH}!{col}{r['first']}:{col}{r['last']}")}],
            "series": [{"series": _src(f"{DASH}!{_nxt(col)}{r['first']}:{_nxt(col)}{r['last']}"),
                        "targetAxis": "BOTTOM_AXIS", "colorStyle": {"rgbColor": color}}]}}
        out.append({"addChart": {"chart": {"spec": spec, "position": {"overlayPosition": {
            "anchorCell": {"sheetId": SHEET_ID[DASH], "rowIndex": r["chart"], "columnIndex": ord(col) - 65},
            "widthPixels": 520, "heightPixels": 260}}}}})  # 옆 그래프에 닿으면 chart_fit이 줄임
    return out
