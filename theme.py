"""시골쥐 스타일 화면: 화면 탭 바탕(회청), 표 안은 흰색, 머리글 남색, 입력 칸 분홍, 탭 맨 위 오른쪽 '업데이트일'.

모두 repeatCell(덮어쓰기)이라 반복 적용해도 같은 결과. migrate `_always` 맨 앞에서 적용하고, 그 뒤 요청
(구분 색·사람별 머리글·라벨 빨강/파랑·고정비 구역 머리글)이 위에 다시 칠한다.
"""
import align
import meritz_style
import sigol_tabs
from layout import (ASSET_STATUS, ASSETS, CAL, COUPLE, DASH, FAV, INVEST, MERITZ, MERITZ2, MERITZ_SLOTS, NETWORTH, RECUR,
                    SEARCH, SETTINGS, SHEET_ID, SMS, STOCK, STOCK2, TREND, TXN, a1_to_grid, v)
from styling import (CHECK_BG, FONT_FAMILY, HEADER_FONT, HEADERS, INPUT_BG, LABEL_BG, NAVY_HEAD, PAGE_BG, SECTION_FONT,
                     TITLE_FONT, WHITE)

VIEW_TABS = [DASH, ASSET_STATUS, *sigol_tabs.NAMES, COUPLE, TREND, INVEST, NETWORTH, CAL, SEARCH, STOCK, MERITZ, STOCK2, MERITZ2]
DAILY_STAMP = '=IF(계산!$C$5="","",계산!$C$5)'  # 매일 아침 자동 실행(dailyJob)이 마지막으로 돈 날 — 모든 탭 '업데이트일'이 같은 값
# 탭 → (라벨 칸, 날짜 칸, 날짜 서식). 날짜 칸 수식은 BADGE_FORMULAS
# 자산현황 K열은 숨김, 부부 E1:K1은 제목 병합이라 그 밖에 둔다
BADGES = {DASH: ("L1", "L2", "yyyy-mm-dd"), COUPLE: ("J2", "K2", "yyyy-mm-dd"), TREND: ("W1", "W2", "yyyy-mm-dd"),
          CAL: ("G1", "G2", "yyyy-mm-dd"), INVEST: ("I2", "I3", "yyyy-mm-dd"), NETWORTH: ("G1", "G2", "yyyy-mm-dd"),
          ASSET_STATUS: ("I1", "I2", "yyyy-mm-dd"),
          **{m.S: (*m.BADGE, "yyyy-mm-dd") for m in sigol_tabs.MODULES if hasattr(m, "BADGE")}}  # 시작하기는 날짜 배지 없음
BADGE_FORMULAS = {tab: DAILY_STAMP for tab in BADGES}
INPUTS = [f"{TXN}!A2:J5000", f"{RECUR}!A2:N50", f"{FAV}!A2:G50", f"{SMS}!A2:A500", f"{ASSETS}!A2:D50", f"{ASSETS}!F2:G50",
          f"{ASSETS}!I2:I50", f"{ASSETS}!J2:K50", f"{SETTINGS}!A2:B60", f"{SETTINGS}!D2:E60", f"{SETTINGS}!G2:G20", f"{SETTINGS}!J2:J4", f"{SETTINGS}!J8:J10",
          f"{SETTINGS}!K2:M60", f"{INVEST}!H7:I8", f"{INVEST}!H10:I11", f"{INVEST}!H1", f"{STOCK}!H1", f"{STOCK2}!H1", f"{ASSET_STATUS}!A36:A45", f"{ASSET_STATUS}!D36:G45",
          f"{ASSET_STATUS}!I36:I45", f"{DASH}!B1", f"{COUPLE}!B1", f"{TREND}!B1", f"{CAL}!B1", f"{SEARCH}!B1:B4"]
KPI_LABELS = [f"{DASH}!A5:M5", f"{ASSET_STATUS}!A4:F4", f"{ASSET_STATUS}!A8:C8"]
KPI_VALUES = [f"{DASH}!A6:M6", f"{ASSET_STATUS}!A5:F5", f"{ASSET_STATUS}!A9:C9",
              f"{ASSET_STATUS}!A13:F24", f"{ASSET_STATUS}!A28:C32", f"{ASSET_STATUS}!A36:I45",
              f"{ASSET_STATUS}!A50:E53", f"{ASSET_STATUS}!G50:H51", f"{ASSET_STATUS}!A58:D63", f"{ASSET_STATUS}!L48:N62",
              f"{ASSET_STATUS}!A68:M71", f"{CAL}!A5:G16"]  # 달력 칸도 흰 표  # 자산현황 표 몸통도 흰색
# 표가 늘어나 남색 띠가 내려간 뒤 흰 글씨가 남은 줄 → 검은 보통 글씨로 되돌린다
STALE_TEXT = [f"{ASSET_STATUS}!A32:C32"]
# 표 자리를 통째로 옮긴 영역: 머리글을 칠하기 전에 글씨를 검은 보통으로 (옛 머리글·합계의 흰 글씨가 새 몸통에 남지 않게)
RESET_TEXT = ["주식투자!K4:N150"]
# 표를 옮긴 옛 자리: 가는 줄이 남아 빈 칸 상자로 보인다 → 줄 지우기 (바탕은 _page가 다시 칠함)
STALE_BORDERS = ["주식투자!P18:R30", "주식투자!K4:N150", f"{ASSET_STATUS}!L17:X21", f"{ASSET_STATUS}!L47:N80", f"{ASSET_STATUS}!A72:M86"]
TITLES = [f"{ASSET_STATUS}!A1"] + [m.TITLE for m in sigol_tabs.MODULES]
SECTIONS = ([f"{ASSET_STATUS}!A{r}" for r in (3, 7, 11, 26, 34, 48, 56, 66)] + [f"{ASSET_STATUS}!G48"]) + sigol_tabs.ranges("SECTIONS")
LINE = {"red": 217 / 255, "green": 217 / 255, "blue": 217 / 255}  # #D9D9D9 표 안 가는 줄
# 그래프 기본 색 = 테마 강조색 6개(진한 남색 → 연한 하늘색). 원형 조각이 이 순서로 칠해진다
ACCENTS = ["1F3864", "2F5597", "4472C4", "7F96D6", "A9B9E6", "D0DAF3"]
# 머리글 목록(styling.HEADERS)에 없는 남색 띠: 자산현황 표 머리글·합계 줄, 부부 정산 구역 띠
NAVY_STRIPS = [f"{ASSET_STATUS}!A12:F12", f"{ASSET_STATUS}!A27:C27", f"{ASSET_STATUS}!A35:I35",
               f"{ASSET_STATUS}!A33:C33", f"{ASSET_STATUS}!A46:I46", f"{COUPLE}!A9:K9",
               f"{ASSET_STATUS}!A49:E49", f"{ASSET_STATUS}!A54:E54", f"{ASSET_STATUS}!G49:H49", f"{ASSET_STATUS}!A57:D57",
               f"{ASSET_STATUS}!A64:D64", f"{ASSET_STATUS}!L47:N47", f"{ASSET_STATUS}!L63:N63", f"{ASSET_STATUS}!A67:M67"]


def _rgb(h: str) -> dict:
    return {"red": int(h[0:2], 16) / 255, "green": int(h[2:4], 16) / 255, "blue": int(h[4:6], 16) / 255}


def spreadsheet_theme() -> dict:
    """문서 테마: 기본 글꼴(나눔고딕)과 그래프 색 순서(남색 계열). 반복 적용해도 같은 결과."""
    colors = ([{"colorType": "TEXT", "color": {"rgbColor": _rgb("000000")}},
               {"colorType": "BACKGROUND", "color": {"rgbColor": _rgb("FFFFFF")}},
               {"colorType": "LINK", "color": {"rgbColor": _rgb("2F5597")}}]
              + [{"colorType": f"ACCENT{i}", "color": {"rgbColor": _rgb(h)}} for i, h in enumerate(ACCENTS, 1)])
    return {"updateSpreadsheetProperties": {"properties": {"spreadsheetTheme": {
        "primaryFontFamily": FONT_FAMILY, "themeColors": colors}}, "fields": "spreadsheetTheme"}}


def _cell(grid: dict, fmt: dict, fields: str) -> dict:
    return {"repeatCell": {"range": grid, "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def _bg(a1: str, color: dict) -> dict:
    return _cell(a1_to_grid(a1), {"backgroundColor": color}, "userEnteredFormat.backgroundColor")


def _head(a1: str) -> dict:
    fmt = {"backgroundColor": NAVY_HEAD, "horizontalAlignment": "CENTER",
           "textFormat": {"fontSize": HEADER_FONT, "bold": True, "foregroundColor": WHITE}}
    return _cell(a1_to_grid(a1), fmt, "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)")


def _page() -> list[dict]:
    return [_cell({"sheetId": SHEET_ID[t]}, {"backgroundColor": PAGE_BG}, "userEnteredFormat.backgroundColor")
            for t in VIEW_TABS]


def _bodies(dash_head: int, dash_base: int, trend_head: int) -> list[dict]:
    """표 몸통 = 정렬 규칙(align)이 아는 화면 탭 표 + 숫자 카드 값 줄."""
    view_ids = {SHEET_ID[t] for t in VIEW_TABS}
    return ([r["repeatCell"]["range"] for r in align.requests(dash_head, dash_base, trend_head)
             if r["repeatCell"]["range"]["sheetId"] in view_ids]
            + [a1_to_grid(a1) for a1 in KPI_VALUES + sigol_tabs.ranges("BODIES")])


def _tables(dash_head: int, dash_base: int, trend_head: int) -> list[dict]:
    """표 안은 흰 바탕 + 연회색 가는 줄, 숫자 카드 이름표는 남색 띠."""
    line = {"style": "SOLID", "color": LINE}
    bodies = _bodies(dash_head, dash_base, trend_head)
    return ([_cell(g, {"backgroundColor": WHITE}, "userEnteredFormat.backgroundColor") for g in bodies]
            + [{"updateBorders": {"range": g, **{k: line for k in ("top", "bottom", "left", "right",
                                                                   "innerHorizontal", "innerVertical")}}} for g in bodies]
            + [_head(a1) for a1 in KPI_LABELS])


def _text(a1: str, size: int) -> dict:
    return _cell(a1_to_grid(a1), {"textFormat": {"fontSize": size, "bold": True, "foregroundColor": NAVY_HEAD}},
                 "userEnteredFormat.textFormat")


def _shift(a1: str, dash_head: int, trend_head: int) -> str:
    """코드 위치 머리글(대시보드 60행·추이 38행)을 운영 위치로. 열 문자엔 숫자가 없어 행 번호만 바뀐다."""
    tab, ref = a1.split("!")
    row = {DASH: (60, dash_head), TREND: (38, trend_head)}.get(tab)
    return a1 if not row else f"{tab}!{ref.replace(str(row[0]), str(row[1]))}"


def _heads(dash_head: int, trend_head: int) -> list[dict]:
    stock = [a1 for s in MERITZ_SLOTS for a1 in meritz_style.header_ranges(s)]
    return [_head(_shift(a1, dash_head, trend_head)) for a1, _c in HEADERS] + [_head(a1) for a1 in stock]


def _restore() -> list[dict]:
    """바탕 칠하기가 지운 고정 배경 중 운영 migrate가 다시 칠하지 않는 것 (증권 탭 '지금 갱신'·상세 라벨)."""
    return ([_bg(f"{s.stock}!G1", CHECK_BG) for s in MERITZ_SLOTS]
            + [_bg(f"{s.meritz}!A2:A3", LABEL_BG) for s in MERITZ_SLOTS])


def _badges() -> list[dict]:
    out = []
    for tab, (label, date, pattern) in BADGES.items():
        kind = "DATE_TIME" if "h" in pattern else "NUMBER" if "0" in pattern else "DATE"
        out.append(_head(f"{tab}!{label}"))
        out.append(_cell(a1_to_grid(f"{tab}!{date}"), {
            "backgroundColor": WHITE, "horizontalAlignment": "CENTER", "textFormat": {"bold": True},
            "numberFormat": {"type": kind, "pattern": pattern}},
            "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat.bold,numberFormat)"))
    return out


def badge_values() -> list[dict]:
    return ([v(f"{tab}!{label}", [["업데이트일"]]) for tab, (label, _d, _p) in BADGES.items()]
            + [v(f"{tab}!{date}", [[BADGE_FORMULAS[tab]]]) for tab, (_l, date, _p) in BADGES.items()])


def requests(dash_head: int = 60, dash_base: int = 95, trend_head: int = 38) -> list[dict]:
    # 옛 표 자리 줄 지우기는 표 그리기 전에 (새 표가 겹치는 자리에 다시 줄을 긋도록)
    stale = STALE_BORDERS + [f"{DASH}!A{dash_base + 43}:J{dash_base + 95}"]  # 분류별 구역(옛 자리 base+52~ 포함)
    clear = [{"updateBorders": {"range": a1_to_grid(a1), **{k: {"style": "NONE"} for k in (
        "top", "bottom", "left", "right", "innerHorizontal", "innerVertical")}}} for a1 in stale]
    black = {"textFormat": {"foregroundColor": {"red": 0, "green": 0, "blue": 0}, "bold": False}}
    reset = [_cell(a1_to_grid(a1), black, "userEnteredFormat(textFormat.foregroundColor,textFormat.bold)") for a1 in RESET_TEXT]
    return (_page() + clear + reset + _tables(dash_head, dash_base, trend_head) + _heads(dash_head, trend_head)
            + [_head(a1) for a1 in NAVY_STRIPS + sigol_tabs.ranges("HEADS") + sigol_tabs.ranges("TOTALS")]
            + [_cell(a1_to_grid(a1), {"backgroundColor": LABEL_BG, "textFormat": {"bold": True}},
                     "userEnteredFormat(backgroundColor,textFormat.bold)") for a1 in sigol_tabs.ranges("SUBTOTALS")]
            + [_cell(a1_to_grid(a1), {"textFormat": {"foregroundColor": {"red": 0, "green": 0, "blue": 0}, "bold": False}},
                     "userEnteredFormat(textFormat.foregroundColor,textFormat.bold)") for a1 in STALE_TEXT]
            + [_text(a1, TITLE_FONT) for a1 in TITLES]
            + [_text(a1, SECTION_FONT) for a1 in SECTIONS] + _restore() + [_bg(a1, INPUT_BG) for a1 in INPUTS + sigol_tabs.ranges("INPUTS")] + _badges())
