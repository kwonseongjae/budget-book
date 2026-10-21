"""그래프가 표·값 칸이나 다른 그래프를 덮지 않게 크기를 줄인다 (운영 시트의 실제 행 높이·열 너비 기준).

내용 칸 = 값이 있거나 바탕이 화면 바탕(회청)이 아닌 칸. 덮이면 먼저 높이를, 안 되면 너비를 첫 장애물 앞까지 줄인다.
줄여도 MIN_H·MIN_W보다 작아지면 고치지 않고 문제로 보고한다(그래프 자리를 코드에서 옮겨야 함).
사용: python3 chart_fit.py          → 점검만 (문제 있으면 종료코드 1)
      migrate_couple.main()       → 적용 뒤 fit() 으로 바로 고침
"""
import sys

from googleapiclient.discovery import build

from styling import PAGE_BG, TARGET_W

GAP, MIN_H, MIN_W = 6, 150, 240
DEFAULT_ROW, DEFAULT_COL = 21, 100


def _edges(sizes: list, n: int, default: int) -> list:
    out = [0]
    for i in range(n):
        out.append(out[-1] + (sizes[i] if i < len(sizes) else default))
    return out


def _hits(rect, obstacles) -> list:
    x0, y0, x1, y1 = rect
    return [o for o in obstacles if o[0] < x1 - 1 and o[2] > x0 + 1 and o[1] < y1 - 1 and o[3] > y0 + 1]


def _rect(c, ry, cx) -> tuple:
    x0, y0 = cx[c["col"]] + c.get("dx", 0), ry[c["row"]] + c.get("dy", 0)
    return x0, y0, x0 + c["w"], y0 + c["h"]


def _fitted(rect, obstacles):
    """덮는 장애물이 없도록 줄인 (w, h). 못 줄이면 None."""
    x0, y0, x1, y1 = rect
    hits = _hits(rect, obstacles)
    if not hits:
        return x1 - x0, y1 - y0
    h = min(o[1] for o in hits) - y0 - GAP
    if h >= MIN_H and not _hits((x0, y0, x1, y0 + h), obstacles):
        return x1 - x0, h
    w = min(o[0] for o in hits) - x0 - GAP
    if w >= MIN_W and not _hits((x0, y0, x0 + w, y1), obstacles):
        return w, y1 - y0
    return None


def plan(grid: dict, charts: list) -> tuple[list, list]:
    """grid = {rows: [px], cols: [px], filled: {(행, 열)}} (0부터), charts = [{chartId, title, row, col, dx, dy, w, h}]."""
    ry = _edges(grid["rows"], 400, DEFAULT_ROW)
    cx = _edges(grid["cols"], 60, DEFAULT_COL)
    cells = [(cx[c], ry[r], cx[c + 1], ry[r + 1]) for r, c in grid["filled"]]
    placed, reqs, problems = [], [], []
    for c in sorted(charts, key=lambda c: (c["row"], c["col"])):
        rect = _rect(c, ry, cx)
        later = [_rect(o, ry, cx) for o in charts if o is not c and (o["row"], o["col"]) > (c["row"], c["col"])]
        wall = [(TARGET_W, -10 ** 9, 10 ** 9, 10 ** 9)]  # 한 화면 폭 오른쪽으로 나가지 않게
        size = _fitted(rect, cells + placed + later + wall)
        if size is None:
            problems.append(c["title"])
            placed.append(rect)
            continue
        w, h = size
        placed.append((rect[0], rect[1], rect[0] + w, rect[1] + h))
        if (w, h) != (c["w"], c["h"]):
            reqs.append({"updateEmbeddedObjectPosition": {"objectId": c["chartId"], "fields": "heightPixels,widthPixels",
                                                          "newPosition": {"overlayPosition": {"heightPixels": h, "widthPixels": w}}}})
    return reqs, problems


def _is_page(bg: dict) -> bool:
    return all(abs(bg.get(k, 0) - PAGE_BG[k]) < 0.01 for k in ("red", "green", "blue"))


def _grid(data: dict) -> dict:
    rows = [0 if r.get("hiddenByUser") else r.get("pixelSize", DEFAULT_ROW) for r in data.get("rowMetadata", [])]
    cols = [0 if c.get("hiddenByUser") else c.get("pixelSize", DEFAULT_COL) for c in data.get("columnMetadata", [])]
    filled = {(i, j) for i, r in enumerate(data.get("rowData", [])) for j, v in enumerate(r.get("values", []))
              if v.get("formattedValue") or ("effectiveFormat" in v and not _is_page(v["effectiveFormat"].get("backgroundColor", {})))}
    return {"rows": rows, "cols": cols, "filled": filled}


def _charts(sheet: dict) -> list:
    out = []
    for c in sheet.get("charts", []):
        p = c.get("position", {}).get("overlayPosition")
        if p:
            a = p["anchorCell"]
            out.append({"chartId": c["chartId"], "title": c["spec"].get("title", ""), "row": a.get("rowIndex", 0),
                        "col": a.get("columnIndex", 0), "dx": p.get("offsetXPixels", 0), "dy": p.get("offsetYPixels", 0),
                        "w": p.get("widthPixels", 600), "h": p.get("heightPixels", 371)})
    return out


def survey(sheets, sid: str) -> tuple[list, list]:
    """운영 시트 전체: (고칠 요청, ['탭: 그래프 제목' 문제])."""
    meta = sheets.get(spreadsheetId=sid, fields="sheets(properties(title),charts(chartId,spec(title),position))").execute()
    tabs = [s for s in meta["sheets"] if s.get("charts")]
    if not tabs:
        return [], []
    got = sheets.get(spreadsheetId=sid, ranges=[f"'{s['properties']['title']}'!A1:Z300" for s in tabs], includeGridData=True,
                     fields="sheets(data(rowMetadata(pixelSize,hiddenByUser),columnMetadata(pixelSize,hiddenByUser),"
                            "rowData(values(formattedValue,effectiveFormat(backgroundColor)))))").execute()["sheets"]
    reqs, problems = [], []
    for s, g in zip(tabs, got):
        r, p = plan(_grid(g["data"][0]), _charts(s))
        reqs += r
        problems += [f"{s['properties']['title']}: {t}" for t in p]
    return reqs, problems


def fit(sheets, sid: str) -> list:
    reqs, problems = survey(sheets, sid)
    if reqs:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": reqs}).execute()
    print(f"그래프 크기 맞춤 {len(reqs)}개" + (f", 자리 옮겨야 함: {problems}" if problems else ""))
    return problems


def main() -> int:
    from auth import get_credentials
    from migrate_couple import ID_FILE
    sheets = build("sheets", "v4", credentials=get_credentials()).spreadsheets()
    reqs, problems = survey(sheets, ID_FILE.read_text().strip())
    print(f"줄여야 할 그래프 {len(reqs)}개, 자리 옮겨야 할 그래프 {problems or '없음'}")
    return 1 if reqs or problems else 0


if __name__ == "__main__":
    sys.exit(main())
