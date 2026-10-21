"""대시보드 아래: 수입 대비 고정비·변동비, 고정비 세부(항목별), 변동비 세부(카테고리별)와 원형 그래프 3개.

기간은 대시보드 B2(적용 월). '나간 돈'과 대분류 기준은 대시보드 H6·I6(고정비·변동비)과 같다.
구역 시작 행(base)은 새 시트 95, 운영은 사용자가 옮긴 자리(제목 행, 옛 제목은 앞에 '💰')를 찾아 넘긴다.
"""
from charts import _src
from formulas import CAT, INC, MAJOR, OUTFLOW, TYPE, YM, per_row, sumifs
from layout import DASH, SETTINGS, SHEET_ID, a1_to_grid, number_format, v
from styling import HEADER_FONT, SECTION_FONT, VIEW_TAB, WHITE

M = "$B$2"
BASE = 95
TITLE = "수입 대비 고정비·변동비"


def rows(base: int = BASE) -> dict:
    """구역 안 행 번호: 수입표 첫 줄·총수입 줄, 세부 표 데이터 첫/끝 줄(각 20줄), 세부 그래프 위치(0부터)."""
    # 세부 그래프는 표 끝 바로 다음 행(0부터 = last) — 2026-10-14 간격 줄이기
    return {"inc": base + 2, "total": base + 6, "first": base + 11, "last": base + 30, "chart": base + 30}


def _income_table(base: int) -> list[dict]:
    i, t = rows(base)["inc"], rows(base)["total"]
    out_all = sumifs((YM, M), *OUTFLOW)
    body = [["고정비", f"={sumifs((YM, M), *OUTFLOW, (MAJOR, chr(34) + '고정비' + chr(34)))}"],
            ["변동비", f"={sumifs((YM, M), *OUTFLOW, (MAJOR, chr(34) + '변동비' + chr(34)))}"],
            ["대분류 없음", f"={out_all}-B{i}-B{i + 1}"],
            ["남은 돈", f"=B{t}-{out_all}"]]
    body = [r + [f'=IFERROR(B{i + k}/B{t},"")', f'=A{i + k}&" "&TEXT(C{i + k},"0.0%")', f"=MAX(0,B{i + k})"]
            for k, r in enumerate(body)]
    body.append(["총수입", f"={sumifs((YM, M), (TYPE, INC))}", f'=IF(B{t}=0,"",1)', "", ""])
    return [v(f"{DASH}!A{base}", [[TITLE]]),
            v(f"{DASH}!A{base + 1}:E{base + 1}", [["구분", "금액", "수입 대비", "그래프 이름표", "그래프 값"]]),
            v(f"{DASH}!A{i}:E{t}", body)]


def _fixed_items(base: int) -> list[dict]:
    """고정비는 항목이 적고 매달 같으니 내역 한 줄씩(카테고리·내용·사용자·금액), 큰 금액 순."""
    f, z = rows(base)["first"], rows(base)["last"]
    c = "내역!C2:C"
    items = (f'=IFERROR(SORT(FILTER({{내역!D2:D,내역!J2:J,내역!B2:B,내역!K2:K}},내역!L2:L={M},내역!M2:M="고정비",'
             f'{c}<>"",{c}<>"수입",{c}<>"이체"),4,FALSE),"")')
    d = f"D{f}:D{z}"
    share = f'=ARRAYFORMULA(IF({d}="","",{d}/SUM({d})))'
    a, b, c, e = (f"{x}{f}:{x}{z}" for x in "ABCE")
    # 내용이 카테고리와 같으면 생략, 사람 이름을 붙여 같은 항목도 조각이 따로 나오게
    label = (f'=ARRAYFORMULA(IF({a}="","",{a}&IF(({b}="")+({b}={a}),"","·"&{b})&" ("&{c}&")"'
             f'&" "&TEXT({e},"0.0%")))')
    return [v(f"{DASH}!A{f - 2}", [["고정비 세부 (항목별)"]]),
            v(f"{DASH}!A{f - 1}:F{f - 1}", [["카테고리", "내용", "사용자", "금액", "고정비 중", "그래프 이름표"]]),
            v(f"{DASH}!A{f}", [[items]]), v(f"{DASH}!E{f}", [[share]]), v(f"{DASH}!F{f}", [[label]])]


def _variable_categories(base: int) -> list[dict]:
    """변동비는 건수가 많아 카테고리별 합계, 큰 금액 순."""
    f, z = rows(base)["first"], rows(base)["last"]
    amt = sumifs((YM, M), *OUTFLOW, (CAT, "x"))
    cats = (f'=IFERROR(LET(c,FILTER({SETTINGS}!$A$2:$A,{SETTINGS}!$D$2:$D="변동비",{SETTINGS}!$B$2:$B<>"수입",'
            f'{SETTINGS}!$A$2:$A<>""),amt,MAP(c,LAMBDA(x,{amt})),SORT(FILTER({{c,amt}},amt>0),2,FALSE)),"")')
    i, h, j = f"I{f}:I{z}", f"H{f}:H{z}", f"J{f}:J{z}"
    return [v(f"{DASH}!H{f - 2}", [["변동비 세부 (카테고리별)"]]),
            v(f"{DASH}!H{f - 1}:K{f - 1}", [["카테고리", "금액", "변동비 중", "그래프 이름표"]]),
            v(f"{DASH}!H{f}", [[cats]]),
            v(f"{DASH}!J{f}", [[f'=ARRAYFORMULA(IF({i}="","",{i}/SUM({i})))']]),
            v(f"{DASH}!K{f}", [[f'=ARRAYFORMULA(IF({h}="","",{h}&" "&TEXT({j},"0.0%")))']])]


def breakdown_values(base: int = BASE) -> list[dict]:
    """펼침 자리(첫 줄 아래)를 먼저 비운다: 남은 값이 있으면 펼침이 막혀 #REF!가 된다."""
    f, z = rows(base)["first"], rows(base)["last"]
    clear = [v(f"{DASH}!A{f + 1}:K{z}", [[""] * 11] * (z - f))]
    return clear + _income_table(base) + _fixed_items(base) + _variable_categories(base)


def _fmt(a1: str, fmt: dict, fields: str) -> dict:
    return {"repeatCell": {"range": a1_to_grid(a1), "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def style_requests(base: int = BASE) -> list[dict]:
    """숫자 서식·머리글·구역 제목. 병합 없이 반복 적용해도 같은 결과."""
    i, t, f, z = rows(base)["inc"], rows(base)["total"], rows(base)["first"], rows(base)["last"]
    fmts = [(f"{DASH}!B{i}:B{t}", "NUMBER", "#,##0"), (f"{DASH}!C{i}:C{t}", "PERCENT", "0.0%"),
            (f"{DASH}!E{i}:E{t - 1}", "NUMBER", "#,##0"), (f"{DASH}!D{f}:D{z}", "NUMBER", "#,##0"),
            (f"{DASH}!E{f}:E{z}", "PERCENT", "0.0%"), (f"{DASH}!I{f}:I{z}", "NUMBER", "#,##0"),
            (f"{DASH}!J{f}:J{z}", "PERCENT", "0.0%")]
    head = {"backgroundColor": VIEW_TAB, "horizontalAlignment": "CENTER",
            "textFormat": {"fontSize": HEADER_FONT, "bold": True, "foregroundColor": WHITE}}
    heads = [_fmt(a1, head, "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)")
             for a1 in (f"{DASH}!A{base + 1}:E{base + 1}", f"{DASH}!A{f - 1}:F{f - 1}", f"{DASH}!H{f - 1}:K{f - 1}")]
    titles = [_fmt(a1, {"textFormat": {"fontSize": SECTION_FONT, "bold": True, "foregroundColor": VIEW_TAB}}, "userEnteredFormat.textFormat")
              for a1 in (f"{DASH}!A{base}", f"{DASH}!A{f - 2}", f"{DASH}!H{f - 2}")]
    total = [_fmt(f"{DASH}!A{t}:C{t}", {"textFormat": {"bold": True}}, "userEnteredFormat.textFormat.bold")]
    return [number_format(a1, k, p) for a1, k, p in fmts] + heads + titles + total


CHART_TITLES = ["수입 대비 고정비·변동비", "고정비 구성 (항목별)", "변동비 구성"]


def _spec(title: str, domain: str, series: str) -> dict:
    return {"title": title, "pieChart": {"legendPosition": "LABELED_LEGEND", "pieHole": 0.4,
                                         "domain": _src(domain), "series": _src(series)}}


def specs(base: int = BASE) -> list[dict]:
    d, i, f, z = DASH, rows(base)["inc"], rows(base)["first"], rows(base)["last"]
    return [_spec(CHART_TITLES[0], f"{d}!D{i}:D{i + 3}", f"{d}!E{i}:E{i + 3}"),
            _spec(CHART_TITLES[1], f"{d}!F{f}:F{z}", f"{d}!D{f}:D{z}"),
            _spec(CHART_TITLES[2], f"{d}!K{f}:K{z}", f"{d}!I{f}:I{z}")]


def chart_requests(base: int = BASE) -> list[dict]:
    spots = [(base - 1, 6, 480, 270), (rows(base)["chart"], 0, 560, 280), (rows(base)["chart"], 7, 560, 280)]
    return [{"addChart": {"chart": {"spec": spec, "position": {"overlayPosition": {
        "anchorCell": {"sheetId": SHEET_ID[DASH], "rowIndex": row, "columnIndex": col},
        "widthPixels": w, "heightPixels": h}}}}}
            for spec, (row, col, w, h) in zip(specs(base), spots)]


def chart_fixes(charts, base: int = BASE) -> list[dict]:
    """이미 있는 세 그래프가 다른 행을 읽으면(행 삭제·이동 뒤) 지금 구역을 읽게 고친다. 맞으면 아무것도 안 함."""
    want = {s["title"]: s for s in specs(base)}
    return [{"updateChartSpec": {"chartId": c["chartId"], "spec": {**c["spec"], "pieChart": {
        **c["spec"]["pieChart"], "domain": want[c["spec"]["title"]]["pieChart"]["domain"],
        "series": want[c["spec"]["title"]]["pieChart"]["series"]}}}}
            for c in charts if c["spec"].get("title") in want and "pieChart" in c["spec"]
            and (c["spec"]["pieChart"].get("series") != want[c["spec"]["title"]]["pieChart"]["series"]
                 or c["spec"]["pieChart"].get("domain") != want[c["spec"]["title"]]["pieChart"]["domain"])]


def find_base(col_a: list) -> int:
    """대시보드 A열 값에서 구역 제목 행을 찾는다. 없으면 기본 95."""
    for n, row in enumerate(col_a, 1):
        if row and str(row[0]).removeprefix("💰 ") == TITLE:
            return n
    return BASE


__all__ = ["breakdown_values", "style_requests", "chart_requests", "chart_fixes", "find_base", "CHART_TITLES", "per_row"]
