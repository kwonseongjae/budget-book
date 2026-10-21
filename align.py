"""칸 정렬: 짧은 글자(사용자·구분·카테고리·날짜)는 가운데, 숫자는 오른쪽, 메모·이름처럼 긴 글은 왼쪽.

머리글은 이미 가운데. 탭마다 '열별 정렬 글자'(C/R/L) 한 줄로 적고, 같은 정렬이 이어지는 열은 한 범위로 묶는다.
반복 적용해도 같은 결과(repeatCell). 대시보드·추이는 운영 위치가 코드와 달라 행을 받는다.
"""
from itertools import groupby

import breakdown
import category_bars
import sigol_tabs
from couple import CAT_FIRST, CAT_LAST
from layout import (ASSET_STATUS, ASSETS, COUPLE, DASH, FAV, INVEST, INVEST_LOG, MERITZ_SLOTS, NETWORTH, RECUR, SEARCH, SETTINGS,
                    TREND, TXN, a1_to_grid)

WORD = {"C": "CENTER", "R": "RIGHT", "L": "LEFT"}


def _runs(tab: str, col: str, first: int, last: int, spec: str) -> list[dict]:
    """spec 한 글자 = 한 열(col부터). '.'은 건너뜀."""
    out, i = [], 0
    for key, grp in groupby(spec):
        n = len(list(grp))
        if key != ".":
            c0, c1 = chr(ord(col) + i), chr(ord(col) + i + n - 1)
            out.append({"repeatCell": {"range": a1_to_grid(f"{tab}!{c0}{first}:{c1}{last}"),
                                       "cell": {"userEnteredFormat": {"horizontalAlignment": WORD[key]}},
                                       "fields": "userEnteredFormat.horizontalAlignment"}})
        i += n
    return out


def _entry_tabs() -> list[dict]:
    return (_runs(TXN, "A", 2, 5000, "CCCCLCCRCLRCCR")      # 날짜 사용자 구분 카테고리 소분류 결제 입금 금액 통화 메모 원화 귀속월 대분류
            + _runs(SEARCH, "A", 7, 1000, "CCCCLCCRCL")
            + _runs(RECUR, "A", 2, 50, "CCCCCCRLCRRCLC")
            + _runs(FAV, "A", 2, 50, "CCCCCRL")
            + _runs(SETTINGS, "A", 2, 60, "LCRCC.CR")       # 카테고리 구분 예산 대분류 사용자 · 통화 환율
            + _runs(SETTINGS, "K", 2, 60, "RRR"))


def _money_tabs() -> list[dict]:
    stocks = [r for s in MERITZ_SLOTS for r in _runs(s.stock, "A", 16, 115, "CCLRRRRRRRCRRRRR")]
    return (_runs(ASSETS, "A", 2, 50, "LCRRRCCCC")
            + _runs(NETWORTH, "A", 2, 200, "CRRRC")
            + _runs(INVEST_LOG, "A", 2, 1000, "C" + "R" * 11)
            + _runs(INVEST, "A", 41, 64, "CRR") + _runs(INVEST, "E", 41, 70, "CR")  # 하단 월별·30일 추이 표
            + _runs(INVEST, "A", 7, 12, "LRRRRCCRR") + _runs(INVEST, "A", 16, 20, "LRRR") + _runs(INVEST, "G", 16, 19, "LCR")
            + stocks)


def _views(dash_head: int, dash_base: int, trend_head: int) -> list[dict]:
    a, z = dash_head + 1, min(dash_head + 31, dash_base - 1)  # 표는 구역 바로 위에서 멈춤
    r = breakdown.rows(dash_base)
    return (_runs(DASH, "A", a, z, "LRRRCCR.CRRR")         # 카테고리 지출 예산 사용률 대분류 사용자 지출 · 카드 사용액 목표 달성률
            + _runs(DASH, "A", r["inc"], r["total"], "LRR")
            + _runs(DASH, "A", r["first"], r["last"], "CLCRR") + _runs(DASH, "H", r["first"], r["last"], "CRR")
            + _runs(TREND, "A", trend_head + 1, trend_head + 12, "CRRR") + _runs(TREND, "T", trend_head + 1, trend_head + 12, "CRR")
            + _runs(COUPLE, "A", 5, 7, "CRRRR") + _runs(COUPLE, "A", CAT_FIRST, CAT_LAST, "LCRRRRRRRRR")
            + _runs(ASSET_STATUS, "A", 13, 24, "CRRRRC") + _runs(ASSET_STATUS, "A", 28, 32, "CRR")
            + _runs(ASSET_STATUS, "A", 36, 45, "CCRRRCCRL")
            + _runs(ASSET_STATUS, "A", 50, 53, "CRRRR") + _runs(ASSET_STATUS, "G", 50, 51, "CR")
            + _runs(ASSET_STATUS, "A", 58, 63, "CRRR") + _runs(ASSET_STATUS, "L", 48, 62, "CRR")
            + _runs(ASSET_STATUS, "A", 68, 71, "C" + "R" * 12)
            + [r for tab, col, first, last, spec in sigol_tabs.runs() + category_bars.align_runs(dash_base)
               for r in _runs(tab, col, first, last, spec)])


def requests(dash_head: int = 60, dash_base: int = breakdown.BASE, trend_head: int = 38) -> list[dict]:
    return _entry_tabs() + _money_tabs() + _views(dash_head, dash_base, trend_head)
