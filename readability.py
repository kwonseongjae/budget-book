"""한눈에 보기: 0은 '-', 손실(음수)은 파랑·수익은 빨강, 수입 숫자는 빨강·지출 숫자는 파랑,
그래프용 보조 열은 흐리게, 부부 표는 사람마다 머리글 색.

모두 repeatCell(덮어쓰기)이라 몇 번 적용해도 같은 결과. 대시보드 표·추이 표는 운영에서 위치가 달라 머리글 행을 받는다.
"""
import breakdown
from couple import CAT_FIRST, CAT_LAST, TABLE_COLS
from layout import ASSETS, COUPLE, DASH, NETWORTH, TREND, a1_to_grid
from styling import BASE_FONT, BLUE_TEXT, RED_TEXT

AMOUNT = '#,##0;[Blue]-#,##0;"-"'
PNL = '[Red]#,##0;[Blue]-#,##0;"-"'   # 잔액·남은 돈처럼 남으면 수익, 모자라면 손실인 칸
FAINT = {"red": 0.6, "green": 0.6, "blue": 0.6}
PERSON_BG = [{"red": 31 / 255, "green": 56 / 255, "blue": 100 / 255},   # 신랑: 진한 남색
             {"red": 46 / 255, "green": 85 / 255, "blue": 151 / 255},   # 신부: 중간 남색
             {"red": 91 / 255, "green": 125 / 255, "blue": 184 / 255}]  # 공동: 연한 남색


def _cell(a1: str, fmt: dict, fields: str) -> dict:
    return {"repeatCell": {"range": a1_to_grid(a1), "cell": {"userEnteredFormat": fmt}, "fields": fields}}


def _amount(a1: str, pattern: str = AMOUNT) -> dict:
    return _cell(a1, {"numberFormat": {"type": "NUMBER", "pattern": pattern}}, "userEnteredFormat.numberFormat")


def _faint(a1: str) -> dict:
    return _cell(a1, {"textFormat": {"foregroundColor": FAINT, "fontSize": BASE_FONT - 1}},
                 "userEnteredFormat(textFormat.foregroundColor,textFormat.fontSize)")


def _ink(a1: str, color: dict) -> dict:
    return _cell(a1, {"textFormat": {"foregroundColor": color}}, "userEnteredFormat.textFormat.foregroundColor")


def dashboard(head: int, base: int = breakdown.BASE) -> list[dict]:
    """head = 카테고리 표 머리글 행 (코드 60, 운영 19), base = 고정비·변동비 구역 시작 행 (코드 95)."""
    a, z = head + 1, min(head + 31, base - 1)  # 표는 구역 바로 위에서 멈춤
    r = breakdown.rows(base)
    i, t, f, l = r["inc"], r["total"], r["first"], r["last"]
    money = [f"B{a}:C{z}", f"G{a}:G{z}", f"J{a}:K{z}", f"B{i}:B{t}", f"E{i}:E{t - 1}", f"D{f}:D{l}", f"I{f}:I{l}"]
    helpers = [f"M{a}:M{z}", f"D{i}:E{t - 1}", f"F{f}:F{l}", f"K{f}:K{l}"]
    return ([_amount(f"{DASH}!{x}") for x in money] + [_faint(f"{DASH}!{x}") for x in helpers]
            + [_amount(f"{DASH}!C6", PNL), _amount(f"{DASH}!B{t - 1}", PNL),
               _ink(f"{DASH}!A6", RED_TEXT), _ink(f"{DASH}!B6", BLUE_TEXT)])


def couple_tab() -> list[dict]:
    money = [f"{COUPLE}!B5:D7", f"{COUPLE}!B10:B11"] + [
        f"{COUPLE}!{c}{CAT_FIRST}:{chr(ord(c) + 1)}{CAT_LAST}" for c in TABLE_COLS]
    heads = [_cell(f"{COUPLE}!{c}{CAT_FIRST - 1}:{chr(ord(c) + 2)}{CAT_FIRST - 1}", {"backgroundColor": bg},
                   "userEnteredFormat.backgroundColor") for c, bg in zip(TABLE_COLS, PERSON_BG)]
    kind = _faint(f"{COUPLE}!B{CAT_FIRST}:B{CAT_LAST}")  # '지출/저축' 구분은 참고용
    signs = [_amount(f"{COUPLE}!E5:E7", PNL), _ink(f"{COUPLE}!B5:B7", RED_TEXT), _ink(f"{COUPLE}!C5:C7", BLUE_TEXT)]
    return [_amount(a1) for a1 in money] + heads + [kind] + signs


def trend_tab(head: int = 38) -> list[dict]:
    """추이 월별 표(머리글 head 행, 12달)·연도 표의 수입 열은 빨강, 지출 열은 파랑. 운영은 머리글이 14행."""
    a, z = head + 1, head + 12
    return [_ink(f"{TREND}!B{a}:B{z}", RED_TEXT), _ink(f"{TREND}!C{a}:C{z}", BLUE_TEXT),
            _ink(f"{TREND}!U{a}:U{z}", RED_TEXT), _ink(f"{TREND}!V{a}:V{z}", BLUE_TEXT)]


def assets_tabs() -> list[dict]:
    bold = _cell(f"{ASSETS}!E2:E50", {"textFormat": {"bold": True}}, "userEnteredFormat.textFormat.bold")
    return [_amount(f"{ASSETS}!C2:E50"), bold, _faint(f"{ASSETS}!H2:H50"),
            _amount(f"{NETWORTH}!B2:D200"), _faint(f"{NETWORTH}!E2:E200")]


def requests(dash_head: int, base: int = breakdown.BASE, trend_head: int = 38) -> list[dict]:
    return dashboard(dash_head, base) + couple_tab() + trend_tab(trend_head) + assets_tabs()
