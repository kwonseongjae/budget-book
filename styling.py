"""보기 좋게: 글씨 크기, 머리글 색, 선택칸 강조, 탭 색, 열 너비, 숨김 열. 값 쓰기 뒤에 적용한다."""
from layout import (ASSET_STATUS, ASSETS, CAL, CARDS, CHECKLIST, COUPLE, QUICK, FIXED, SAVINGS, STOCKS, DASH, FAV, GUIDE, INVEST, MERITZ, MERITZ2, NETWORTH, RECUR, SEARCH, SETTINGS, SHEET_ID,
                    SHEETS, SMS, STOCK, STOCK2, TREND, TXN, a1_to_grid, v)

# 시골쥐 자산관리표 크기(본문·머리글 10, 제목 14, 구역·큰 숫자 12)에서 모두 +3 (2026-10-14 사용자: 글자가 너무 작음)
# 행 높이·열 너비는 fit_dims가 적용 뒤 데이터에 맞춘다. 나눔고딕 = 맑은 고딕과 가장 비슷
BASE_FONT, HEADER_FONT, TITLE_FONT, KPI_FONT, SECTION_FONT = 13, 13, 17, 15, 15
ROW_PX, TITLE_ROW_PX, KPI_ROW_PX = 21, 32, 28
FONT_FAMILY = "Nanum Gothic"
TARGET_W = 1650  # 탭 한 화면 폭: 1920px 모니터에서 브라우저 여백·행 번호 칸을 뺀 값 (2026-10-14 사용자 선택)
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
NAVY = {"red": 0.1, "green": 0.2, "blue": 0.4}
NAVY_HEAD = {"red": 31 / 255, "green": 56 / 255, "blue": 100 / 255}      # #1F3864 머리글·구역 띠
PAGE_BG = {"red": 233 / 255, "green": 238 / 255, "blue": 246 / 255}      # #E9EEF6 화면 탭 바탕
INPUT_BG = {"red": 252 / 255, "green": 228 / 255, "blue": 236 / 255}     # #FCE4EC 사람이 입력하는 칸
INPUT_TAB_COLOR = {"red": 0.94, "green": 0.56, "blue": 0.69}             # 입력 탭 이름 색(분홍)
GRAY_BG = {"red": 0.93, "green": 0.93, "blue": 0.93}
CHECK_BG = {"red": 0.85, "green": 0.95, "blue": 0.85}
LABEL_BG = {"red": 242 / 255, "green": 242 / 255, "blue": 242 / 255}  # #F2F2F2 합계 줄·이름 칸
RED_TEXT = {"red": 0.85, "green": 0.1, "blue": 0.1}
BLUE_TEXT = {"red": 0.1, "green": 0.3, "blue": 0.85}
INPUT_TAB = INPUT_TAB_COLOR
VIEW_TAB = NAVY_HEAD
SETUP_TAB = {"red": 0.5, "green": 0.5, "blue": 0.5}
GUIDE_TAB = {"red": 0.95, "green": 0.6, "blue": 0.1}
# 구분 색: 수입 빨강, 지출 파랑, 저축 노랑 (배경 + 진한 글씨)
EXP_BG, EXP_FG = {"red": 0.8, "green": 0.88, "blue": 0.99}, {"red": 0.0, "green": 0.25, "blue": 0.7}  # 지출(손실) 파랑
INC_BG, INC_FG = {"red": 0.98, "green": 0.8, "blue": 0.8}, {"red": 0.7, "green": 0.0, "blue": 0.0}   # 수입(수익) 빨강
SAVE_BG, SAVE_FG = {"red": 1.0, "green": 0.93, "blue": 0.5}, {"red": 0.5, "green": 0.38, "blue": 0.0}
TYPE_COLORS = [("지출", EXP_BG, EXP_FG), ("수입", INC_BG, INC_FG), ("저축", SAVE_BG, SAVE_FG)]
# 구분 열이 있는 범위: (칠할 범위, 구분 칸의 첫 행 참조)
TYPE_RANGES = [
    ("내역!C2:C5000", "$C2"), ("내역!H2:H5000", "$C2"), ("반복!D2:D50", "$D2"), ("반복!G2:G50", "$D2"),
    ("즐겨찾기!C2:C50", "$C2"), ("즐겨찾기!F2:F50", "$C2"), ("설정!B2:B60", "$B2"), ("검색!C7:C1000", "$C7"),
]

TAB_COLORS = {GUIDE: GUIDE_TAB, TXN: INPUT_TAB, FAV: INPUT_TAB, RECUR: INPUT_TAB, SMS: INPUT_TAB,
              DASH: VIEW_TAB, TREND: VIEW_TAB, CAL: VIEW_TAB, SEARCH: VIEW_TAB, ASSETS: SETUP_TAB, SETTINGS: SETUP_TAB,
              STOCK: VIEW_TAB, MERITZ: VIEW_TAB, STOCK2: VIEW_TAB, MERITZ2: VIEW_TAB, COUPLE: VIEW_TAB, NETWORTH: VIEW_TAB, INVEST: VIEW_TAB,
              ASSET_STATUS: VIEW_TAB, FIXED: VIEW_TAB, CARDS: VIEW_TAB, STOCKS: VIEW_TAB, SAVINGS: VIEW_TAB, CHECKLIST: GUIDE_TAB, QUICK: INPUT_TAB}

# 표 머리글 → 모두 남색 (시골쥐 스타일)
HEADERS = [(a1, NAVY_HEAD) for a1 in (
    f"{TXN}!A1:N1", f"{FAV}!A1:G1", f"{RECUR}!A1:N1", f"{ASSETS}!A1:K1", f"{SETTINGS}!A1:D1", f"{SETTINGS}!E1",
    f"{SETTINGS}!I1:J1", f"{SETTINGS}!K1:M1", f"{COUPLE}!A4:E4", f"{COUPLE}!A15:K15", f"{NETWORTH}!A1:D1",
    f"{INVEST}!A3:F3", f"{INVEST}!A6:J6", f"{INVEST}!A40:C40", f"{INVEST}!E40:F40", f"{INVEST}!A15:D15",
    f"{INVEST}!G15:I15", f"{SEARCH}!A6:J6", f"{DASH}!A60:L60", f"{TREND}!A38:W38", f"{CAL}!A4:G4")]
SELECTORS = [f"{DASH}!B1", f"{TREND}!B1", f"{CAL}!B1", f"{SEARCH}!B1:B4", f"{COUPLE}!B1"]

COL_WIDTHS = {
    GUIDE: [230, 760],
    TXN: [110, 90, 70, 120, 110, 120, 110, 110, 60, 220, 110, 90, 90, 80],
    DASH: [130, 130, 130, 130, 120, 130, 120, 30, 120, 175, 175, 175, 80, 80],  # J~L: 자산 현황 큰 숫자
    TREND: [80, 110, 110, 110, 20, 120] + [85] * 12 + [20, 80, 110, 110, 110, 80, 80, 80],
    CAL: [120] * 7,
    SEARCH: [110, 140, 80, 110, 120, 120, 110, 110, 60, 220],
    FAV: [70, 90, 70, 120, 120, 100, 220],
    RECUR: [60, 100, 90, 70, 120, 120, 110, 180, 130, 110, 70, 90, 160, 60],
    SMS: [520, 90, 320],
    ASSETS: [170, 80, 120, 130, 130, 140, 130, 160, 90, 70, 110, 100],
    STOCK: [130, 130, 160, 130, 110, 110, 120, 130, 120, 90, 60, 100, 100, 110, 90, 70],
    MERITZ: [150, 150, 110, 170, 130, 30, 120, 120],
    STOCK2: [130, 130, 160, 130, 110, 110, 120, 130, 120, 90, 60, 100, 100, 110, 90, 70],
    MERITZ2: [150, 150, 110, 170, 130, 30, 120, 120],
    SETTINGS: [150, 70, 110, 100, 110, 30, 80, 80, 220, 260, 110, 110, 110],
    COUPLE: [170, 130, 120, 110, 110, 120, 110, 80, 120, 110, 80],
    NETWORTH: [90, 130, 150, 120, 90],
    INVEST: [170, 165, 165, 140, 140, 150, 220, 120, 120, 150],
    ASSET_STATUS: [130, 120, 110, 100, 110, 100, 100, 90, 140, 20, 120, 100, 100, 100, 100, 100],  # L~P: 그래프 띠
}

TXN_NOTES = ["달력에서 선택", "누가 썼나요? 같이 쓴 돈은 '공동'", "수입 / 지출 / 이체(내 돈끼리 옮김)",
             "드롭다운에서 선택. 목록은 [설정]에서 추가", "자유 입력 (예: 점심, 마트)", "어디서 나갔나요? (자산 탭 목록)",
             "이체일 때만: 돈이 들어간 곳", "원 단위 숫자만", "", "자유 메모 (검색에 쓰임)",
             "자동 계산 — 수정 금지", "자동 계산(월 시작일 기준) — 수정 금지",
             "자동 표시: [설정]에서 정한 카테고리의 대분류(고정비/변동비)"]


def _fmt(grid: dict, fmt: dict, fields: str) -> dict:
    return {"repeatCell": {"range": grid, "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def _sheet_prop(sid: int, props: dict, fields: str) -> dict:
    return {"updateSheetProperties": {"properties": {"sheetId": sid, **props}, "fields": fields}}


def _dim(sid: int, dim: str, start: int, end: int, props: dict, fields: str) -> dict:
    return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": dim, "startIndex": start,
                                                    "endIndex": end}, "properties": props, "fields": fields}}


def base_requests() -> list[dict]:
    """모든 보이는 탭: 기본 글씨 키우기, 세로 가운데, 행 높이, 탭 색."""
    reqs = []
    for title, sid, rows, _cols, hidden in SHEETS:
        if hidden:
            continue
        reqs.append(_fmt({"sheetId": sid}, {"textFormat": {"fontSize": BASE_FONT, "fontFamily": FONT_FAMILY},
                                            "verticalAlignment": "MIDDLE"},
                         "userEnteredFormat(textFormat.fontSize,textFormat.fontFamily,verticalAlignment)"))
        reqs.append(_sheet_prop(sid, {"tabColor": TAB_COLORS[title]}, "tabColor"))
        if title != GUIDE:  # 사용법은 줄바꿈 길이에 맞춰 자동 높이
            reqs.append(all_rows(sid))
    for title in (GUIDE, CHECKLIST, QUICK, DASH, ASSET_STATUS, FIXED, CARDS, STOCKS, SAVINGS, TREND, CAL, STOCK, MERITZ, STOCK2, MERITZ2, COUPLE, INVEST):
        reqs.append(_sheet_prop(SHEET_ID[title], {"gridProperties": {"hideGridlines": True}},
                                "gridProperties.hideGridlines"))
    return reqs


def all_rows(sid: int) -> dict:
    """탭의 모든 행을 기본 높이로 (끝 번호 없이 = 운영 시트 행 수가 코드와 달라도 됨)."""
    return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "ROWS", "startIndex": 0},
                                          "properties": {"pixelSize": ROW_PX}, "fields": "pixelSize"}}


def layout_requests() -> list[dict]:
    """열 너비와 숨김 열(통화표·결제수단 목록 같은 보조 열). 내역 통화 칸은 외화 입력을 위해 보인다."""
    reqs = [_dim(SHEET_ID[t], "COLUMNS", i, i + 1, {"pixelSize": w}, "pixelSize")
            for t, widths in COL_WIDTHS.items() for i, w in enumerate(widths)]
    reqs.append(_dim(SHEET_ID[SETTINGS], "COLUMNS", 6, 8, {"hiddenByUser": True}, "hiddenByUser"))
    reqs.append(_dim(SHEET_ID[ASSETS], "COLUMNS", 11, 12, {"hiddenByUser": True}, "hiddenByUser"))  # L 결제수단 목록
    return reqs


def header_requests() -> list[dict]:
    head_fields = "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment)"
    reqs = [_fmt(a1_to_grid(a1), {"backgroundColor": color, "horizontalAlignment": "CENTER",
                                  "textFormat": {"fontSize": HEADER_FONT, "bold": True, "foregroundColor": WHITE}},
                 head_fields) for a1, color in HEADERS]
    notes = [{"note": n} for n in TXN_NOTES]
    reqs.append({"updateCells": {"range": a1_to_grid(f"{TXN}!A1:M1"), "rows": [{"values": notes}], "fields": "note"}})
    return reqs


def highlight_requests() -> list[dict]:
    bg = "userEnteredFormat.backgroundColor"
    sel = [_fmt(a1_to_grid(a1), {"backgroundColor": INPUT_BG, "textFormat": {"fontSize": SECTION_FONT, "bold": True}},
                "userEnteredFormat(backgroundColor,textFormat)") for a1 in SELECTORS]
    gray = [_fmt(a1_to_grid(a1), {"backgroundColor": GRAY_BG}, bg)
            for a1 in (f"{TXN}!K2:M5000", f"{ASSETS}!E2:E50")]
    check = [_fmt(a1_to_grid(a1), {"backgroundColor": CHECK_BG}, bg)
             for a1 in (f"{FAV}!A2:A50", f"{RECUR}!A2:A50", f"{SMS}!B1")]
    sms_tip = _fmt(a1_to_grid(f"{SMS}!A1"), {"backgroundColor": INPUT_BG, "textFormat": {"fontSize": SECTION_FONT, "bold": True}},
                   "userEnteredFormat(backgroundColor,textFormat)")
    wrap = _fmt(a1_to_grid(f"{SMS}!A2:A500"), {"wrapStrategy": "WRAP"}, "userEnteredFormat.wrapStrategy")
    return sel + gray + check + [sms_tip, wrap]


NAVY_LABEL = {"backgroundColor": NAVY_HEAD, "horizontalAlignment": "CENTER",
              "textFormat": {"fontSize": HEADER_FONT, "bold": True, "foregroundColor": WHITE}}  # 숫자 카드 이름표 = 남색 띠


def dashboard_requests() -> list[dict]:
    title = _fmt(a1_to_grid(f"{DASH}!D1:H1"), {"textFormat": {"fontSize": TITLE_FONT, "bold": True,
                                                              "foregroundColor": NAVY}},
                 "userEnteredFormat.textFormat")
    merge = {"mergeCells": {"mergeType": "MERGE_ALL", "range": a1_to_grid(f"{DASH}!D1:H1")}}
    label = _fmt(a1_to_grid(f"{DASH}!A5:I5"), NAVY_LABEL, "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)")
    kpi = _fmt(a1_to_grid(f"{DASH}!A6:I6"), {"horizontalAlignment": "CENTER",
                                             "textFormat": {"fontSize": KPI_FONT, "bold": True}},
               "userEnteredFormat(horizontalAlignment,textFormat)")
    tall = _dim(SHEET_ID[DASH], "ROWS", 5, 6, {"pixelSize": KPI_ROW_PX}, "pixelSize")
    title_rows = [_dim(SHEET_ID[s], "ROWS", 0, 1, {"pixelSize": TITLE_ROW_PX}, "pixelSize") for s in (DASH, TREND)]
    trend_title = _fmt(a1_to_grid(f"{TREND}!D1:H1"), {"textFormat": {"fontSize": TITLE_FONT, "bold": True,
                                                                     "foregroundColor": NAVY}},
                       "userEnteredFormat.textFormat")
    trend_merge = {"mergeCells": {"mergeType": "MERGE_ALL", "range": a1_to_grid(f"{TREND}!D1:H1")}}
    alert = _fmt(a1_to_grid(f"{DASH}!D2"), {"horizontalAlignment": "LEFT", "textFormat": {"fontSize": BASE_FONT - 1, "bold": True, "foregroundColor": RED_TEXT}},
                 "userEnteredFormat(horizontalAlignment,textFormat)")  # '확인 필요' 한 줄 (D2, 오른쪽 빈 칸으로 이어짐)
    return [merge, title, label, kpi, tall, trend_merge, trend_title, alert] + title_rows + couple_title_requests() + asset_status_style()


def asset_status_style() -> list[dict]:
    """대시보드 자산 현황(J5:L6)도 월간 숫자 줄(A5:I6)과 같은 모양."""
    label = _fmt(a1_to_grid(f"{DASH}!J5:M5"), NAVY_LABEL, "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)")
    kpi = _fmt(a1_to_grid(f"{DASH}!J6:M6"), {"horizontalAlignment": "CENTER",
                                             "textFormat": {"fontSize": KPI_FONT, "bold": True}},
               "userEnteredFormat(horizontalAlignment,textFormat)")
    return [label, kpi]


def couple_title_requests() -> list[dict]:
    title = _fmt(a1_to_grid(f"{COUPLE}!E1:K1"), {"textFormat": {"fontSize": TITLE_FONT, "bold": True,
                                                                "foregroundColor": NAVY}},
                 "userEnteredFormat.textFormat")
    section = _fmt(a1_to_grid(f"{COUPLE}!A9:K9"), NAVY_LABEL, "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat)")
    return [{"mergeCells": {"mergeType": "MERGE_ALL", "range": a1_to_grid(f"{COUPLE}!E1:K1")}}, title, section,
            {"mergeCells": {"mergeType": "MERGE_ALL", "range": a1_to_grid(f"{COUPLE}!A9:K9")}},
            _dim(SHEET_ID[COUPLE], "ROWS", 0, 1, {"pixelSize": TITLE_ROW_PX}, "pixelSize")]


def calendar_requests() -> list[dict]:
    fg = "userEnteredFormat.textFormat.foregroundColor"
    reqs = [_fmt(a1_to_grid(f"{CAL}!A4:A16"), {"textFormat": {"foregroundColor": RED_TEXT}}, fg),
            _fmt(a1_to_grid(f"{CAL}!G4:G16"), {"textFormat": {"foregroundColor": BLUE_TEXT}}, fg)]
    for w in range(6):
        amount_row = 6 + 2 * w
        reqs.append(_fmt(a1_to_grid(f"{CAL}!A{amount_row}:G{amount_row}"),
                         {"horizontalAlignment": "CENTER", "textFormat": {"fontSize": SECTION_FONT, "bold": True}},
                         "userEnteredFormat(horizontalAlignment,textFormat.fontSize,textFormat.bold)"))
        reqs.append(_dim(SHEET_ID[CAL], "ROWS", amount_row - 1, amount_row, {"pixelSize": KPI_ROW_PX}, "pixelSize"))
    return reqs



def type_color_requests() -> list[dict]:
    """구분 값(지출·수입·저축)에 따라 구분·금액 칸 색칠 (조건부 서식)."""
    reqs = []
    for a1, ref in TYPE_RANGES:
        for word, bg, fg in TYPE_COLORS:
            cond = {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f'={ref}="{word}"'}]}
            fmt = {"backgroundColor": bg, "textFormat": {"foregroundColor": fg, "bold": True}}
            reqs.append({"addConditionalFormatRule": {"index": 0, "rule": {
                "ranges": [a1_to_grid(a1)], "booleanRule": {"condition": cond, "format": fmt}}}})
    return reqs


def title_values() -> list[dict]:
    return [v(f"{DASH}!D1", [["우리집 가계부 — 이달의 살림"]]), v(f"{TREND}!D1", [["연간 추이"]])]


def asset_align_requests() -> list[dict]:
    """자산 소유자(I열)는 왼쪽 정렬 — 드롭다운으로 고른 칸과 API로 쓴 칸의 정렬이 달라 줄이 안 맞았다."""
    return [_fmt(a1_to_grid(f"{ASSETS}!I2:I50"), {"horizontalAlignment": "LEFT"}, "userEnteredFormat.horizontalAlignment")]


def style_requests() -> list[dict]:
    return (base_requests() + layout_requests() + header_requests() + highlight_requests() + asset_align_requests()
            + dashboard_requests() + calendar_requests() + type_color_requests())
