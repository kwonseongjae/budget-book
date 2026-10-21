"""시골쥐 기능 시트 4개(고정지출·카드·주식투자·저축·연금)를 한 목록으로: 각 모듈이 표 자리(머리글·합계·몸통·입력칸)를
선언하고, 여기서 바탕·서식·보호·열 너비·그래프 요청을 모아 만든다. 모듈 인터페이스:
S(탭 이름) TITLE SECTIONS HEADS TOTALS SUBTOTALS BODIES INPUTS RUNS BADGE WIDTHS HIDDEN, values() formats() chart_requests()
"""
import cards
import checklist
import fixed_costs
import quick_entry
import savings
import stock_sectors
from layout import SHEET_ID, _protect, a1_to_grid

MODULES = [checklist, quick_entry, fixed_costs, cards, stock_sectors, savings]
NAMES = [m.S for m in MODULES]


def values() -> list[dict]:
    return [e for m in MODULES for e in m.values()]


def formats(names=None) -> list[dict]:
    """번호 서식·드롭다운·조건부 서식(조건부 서식은 추가형이라 탭을 만들 때 한 번만)."""
    return [r for m in MODULES if names is None or m.S in names for r in m.formats()]


def chart_requests(names=None) -> list[dict]:
    return [r for m in MODULES if names is None or m.S in names for r in m.chart_requests()]


def protection(names=None) -> list[dict]:
    return [_protect({"sheetId": SHEET_ID[m.S]}, [a1_to_grid(a1) for a1 in m.INPUTS])
            for m in MODULES if names is None or m.S in names]


def _dim(sid: int, i: int, props: dict, fields: str) -> dict:
    return {"updateDimensionProperties": {"range": {"sheetId": sid, "dimension": "COLUMNS", "startIndex": i,
                                                    "endIndex": i + 1}, "properties": props, "fields": fields}}


def widths(names=None) -> list[dict]:
    mods = [m for m in MODULES if names is None or m.S in names]
    return ([_dim(SHEET_ID[m.S], i, {"pixelSize": w}, "pixelSize") for m in mods for i, w in enumerate(m.WIDTHS)]
            + [_dim(SHEET_ID[m.S], i, {"hiddenByUser": True}, "hiddenByUser") for m in mods for i in m.HIDDEN])


def ranges(attr: str) -> list[str]:
    return [a1 for m in MODULES for a1 in getattr(m, attr)]


def runs() -> list[tuple]:
    return [(m.S, *r) for m in MODULES for r in m.RUNS]
