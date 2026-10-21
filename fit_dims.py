"""행·열을 데이터 크기에 맞춘다 (2026-10-14 사용자 요청: '행·열마다 데이터 크기 맞춤').

- 행: 구글 시트 자체 '데이터에 맞게 크기 조정'(autoResizeDimensions).
- 열: 시트 자체 기능은 A1 제목·구역 제목·안내문처럼 옆 칸으로 넘쳐 보이게 둔 글까지 재서 열이 수백 px로 벌어진다.
  그래서 칸 글자 수·글꼴 크기로 너비를 계산하되 제목·구역 제목·병합 칸·긴 안내문(30자 초과)·오른쪽이 빈 칸으로
  넘치는 글은 빼고, MIN_W~MAX_W로 묶는다. 비었거나 숨긴 열(보조·간격 열)은 그대로.
사용: migrate_couple.main()이 적용 뒤 fit() 호출. 단독: python3 fit_dims.py
"""
import math
import sys

from googleapiclient.discovery import build

import theme
from layout import CARDS, CHECKLIST, DASH, GUIDE, SHEET_ID, TREND, TUCKED, a1_to_grid
from styling import TARGET_W

MIN_W, MAX_W, PAD, LONG = 50, 360, 16, 30
SPACER_W, WRAP_MIN = 20, 80   # 빈 열 폭, 줄바꿈으로 좁힐 때 글자 열 최소 폭
PINNED = {(SHEET_ID[CARDS], 3), (SHEET_ID[CHECKLIST], 4)}  # 크기를 고정한 열: 카드 D 혜택(사용자, 2026-10-15), 시작하기 E 하는 법(긴 문장) — 너비·줄바꿈 그대로
HINTS = [f"{DASH}!C1", f"{TREND}!C1"]  # '◀ 분홍 칸에서 …' 안내문 (옆으로 넘쳐 보이게 둔 글)
READ_ROWS = 1000


def text_px(text: str, pt: float, bold: bool = False) -> int:
    """한글·한자는 글꼴 크기만큼, 영문·숫자는 그 0.6배 폭으로 어림."""
    px = pt * 4 / 3
    wide = sum(1 for ch in text if ord(ch) >= 0x2E80)
    width = (wide + 0.6 * (len(text) - wide)) * px * (1.06 if bold else 1.0)
    return math.ceil(width) + PAD


def skip_cells(sid: int, merges: list) -> set:
    """너비 계산에서 뺄 칸 (행, 열): 제목·구역 제목·병합 칸."""
    out = set()
    for a1 in theme.TITLES + theme.SECTIONS + HINTS:
        g = a1_to_grid(a1)
        if g["sheetId"] == sid:
            out.add((g["startRowIndex"], g["startColumnIndex"]))
    for m in merges:
        out |= {(r, c) for r in range(m["startRowIndex"], m["endRowIndex"])
                for c in range(m["startColumnIndex"], m["endColumnIndex"])}
    return out


def _text(cell: dict) -> str:
    return str(cell.get("formattedValue", "") or "")


def _font(cell: dict) -> tuple:
    tf = cell.get("effectiveFormat", {}).get("textFormat", {})
    return tf.get("fontSize", 10), bool(tf.get("bold"))


def _overflows(cell: dict) -> bool:
    """옆 빈 칸으로 넘쳐 보일 수 있는 칸 = 왼쪽(기본) 정렬 글자. 숫자·날짜·가운데·오른쪽 정렬은 잘린다."""
    value = cell.get("effectiveValue", {"stringValue": ""})
    return "stringValue" in value and cell.get("effectiveFormat", {}).get("horizontalAlignment", "LEFT") == "LEFT"


def _col_req(sid: int, c: int, px: int) -> dict:
    return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": c, "endIndex": c + 1},
                                          "properties": {"pixelSize": px}, "fields": "pixelSize"}}


def _measure(tab: dict) -> tuple[dict, dict, dict, set]:
    """열마다 (가장 넓은 숫자 px, 가장 넓은 글자 px, 글자 칸 [(행, px)]), 값이 하나라도 있는 열."""
    rows, widths = tab["rows"], tab["widths"]
    num, txt, cells, used = {}, {}, {}, set()
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            text = _text(cell)
            if not text or c >= len(widths) or c in tab["hidden"]:
                continue
            used.add(c)
            if len(text) > LONG or (r, c) in tab["skip"]:
                continue
            px = text_px(text, *_font(cell))
            right_empty = c + 1 >= len(row) or not _text(row[c + 1])
            if right_empty and px > widths[c] and _overflows(cell):  # 옆 빈 칸으로 넘쳐 보이게 둔 글
                continue
            if "stringValue" in cell.get("effectiveValue", {"stringValue": ""}):
                txt[c] = max(txt.get(c, 0), px)
                cells.setdefault(c, []).append((r, px))
            else:
                num[c] = max(num.get(c, 0), px)
    return num, txt, cells, used


def _width(c: int, num: dict, txt: dict, cap: int) -> int:
    return min(MAX_W, max(MIN_W, num.get(c, 0), min(txt.get(c, 0), cap)))


def _wrap_runs(sid: int, c: int, rows: list[int]) -> list[dict]:
    """줄바꿈은 좁아진 글자 칸에만 (같은 열의 제목·안내문은 그대로 옆으로 넘치게)."""
    out, rows = [], sorted(rows)
    while rows:
        a = b = rows.pop(0)
        while rows and rows[0] == b + 1:
            b = rows.pop(0)
        out.append({"repeatCell": {"range": {"sheetId": sid, "startRowIndex": a, "endRowIndex": b + 1,
                                             "startColumnIndex": c, "endColumnIndex": c + 1},
                                   "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                                   "fields": "userEnteredFormat.wrapStrategy"}})
    return out


def plan(tab: dict, row_count: int = 0) -> list[dict]:
    """tab = {sheetId, rows: [[셀]], widths: [px], hidden: {열}, skip: {(행, 열)}}.

    탭 폭(보이는 열 합)이 TARGET_W를 넘으면 글자 열에만 상한(cap)을 두고 줄바꿈 — 숫자 열은 잘리면 안 되므로 그대로.
    """
    sid, widths = tab["sheetId"], tab["widths"]
    num, txt, cells, used = _measure(tab)
    visible = [c for c in range(len(widths)) if c not in tab["hidden"]]
    pinned = {c for s, c in PINNED if s == sid}
    used = used | pinned
    sized = [c for c in visible if (c in num or c in txt) and c not in pinned]

    def total(cap: int) -> int:
        return sum(_width(c, num, txt, cap) if c in sized else (widths[c] if c in used else SPACER_W) for c in visible)

    cap = MAX_W
    if total(MAX_W) > TARGET_W:
        lo, hi = WRAP_MIN, MAX_W
        while lo < hi:  # TARGET_W 안에 드는 가장 큰 상한
            mid = (lo + hi + 1) // 2
            lo, hi = (mid, hi) if total(mid) <= TARGET_W else (lo, mid - 1)
        cap = lo
    reqs = []
    for c in visible:
        want = _width(c, num, txt, cap) if c in sized else (None if c in used else SPACER_W)
        if want is not None and want != widths[c]:
            reqs.append(_col_req(sid, c, want))
        narrowed = want is not None and c in cells and txt.get(c, 0) > want
        if narrowed:
            reqs += _wrap_runs(sid, c, [r for r, px in cells[c] if px > want])
    if row_count:
        reqs.append({"autoResizeDimensions": {"dimensions": {"sheetId": sid, "dimension": "ROWS", "startIndex": 0,
                                                             "endIndex": row_count}}})
    return reqs


def survey(sheets, sid: str) -> list[dict]:
    meta = sheets.get(spreadsheetId=sid, fields="sheets(properties(sheetId,title,hidden,gridProperties(rowCount,columnCount)),merges)").execute()
    tabs = [s for s in meta["sheets"] if (not s["properties"].get("hidden") or s["properties"]["title"] in TUCKED)
            and s["properties"]["sheetId"] != SHEET_ID[GUIDE]]  # 메뉴로 꺼내 보는 숨긴 보기 탭도
    reqs = []
    for s in tabs:  # 탭마다 따로 읽는다 (한 번에 읽으면 응답이 커서 시간 초과)
        p = s["properties"]
        rows = min(p["gridProperties"]["rowCount"], READ_ROWS)
        data = sheets.get(spreadsheetId=sid, ranges=[f"'{p['title']}'!1:{rows}"], includeGridData=True,
                          fields="sheets(data(columnMetadata(pixelSize,hiddenByUser),"
                                 "rowData(values(formattedValue,effectiveValue,effectiveFormat(horizontalAlignment,textFormat(fontSize,bold))))))").execute()
        d = data["sheets"][0]["data"][0]
        cols = d.get("columnMetadata", [])
        tab = {"sheetId": p["sheetId"], "rows": [r.get("values", []) for r in d.get("rowData", [])],
               "widths": [c.get("pixelSize", 100) for c in cols],
               "hidden": {i for i, c in enumerate(cols) if c.get("hiddenByUser")},
               "skip": skip_cells(p["sheetId"], s.get("merges", []))}
        reqs += plan(tab, p["gridProperties"]["rowCount"])
    return reqs


def fit(sheets, sid: str) -> int:
    reqs = survey(sheets, sid)
    if reqs:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": reqs}).execute()
    count = lambda key: sum(1 for r in reqs if key in r)
    print(f"열 너비 맞춤 {count('updateDimensionProperties')}개, 줄바꿈 {count('repeatCell')}곳, "
          f"행 높이 자동 맞춤 {count('autoResizeDimensions')}개 탭")
    return len(reqs)


def main() -> int:
    import socket
    from auth import get_credentials
    from migrate_couple import ID_FILE
    socket.setdefaulttimeout(300)
    fit(build("sheets", "v4", credentials=get_credentials()).spreadsheets(), ID_FILE.read_text().strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
