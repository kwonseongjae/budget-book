"""자주 쓰는 탭은 왼쪽, 자주 안 쓰는 탭은 숨겨 두고 메뉴로 꺼낸다 (2026-10-22 사용자: 탭이 많아 좌우로 움직여야 한다)."""
import re
from pathlib import Path

import layout

GS = (Path(__file__).parent.parent / "apps-script" / "triggers.gs").read_text(encoding="utf-8")

WEEKLY = ["대시보드", "빠른입력", "내역", "문자입력", "즐겨찾기", "부부", "주식투자", "투자", "자산현황"]   # 일주일 단위로 쓰는 탭 (왼쪽, 주식투자는 투자 바로 왼쪽)
MONTHLY_RIGHT = ["설정", "자산", "사용법"]                                                       # 달 1~2회 (오른쪽, 계속 보임)
MENU_ONLY = ["시작하기", "반복", "고정지출", "카드", "저축·연금", "자산기록", "증권계좌", "증권종목"]


def _visible():
    return [s["properties"]["title"] for s in layout.create_body("t")["sheets"] if not s["properties"]["hidden"]]


def test_visible_tabs_are_weekly_on_the_left_and_monthly_on_the_right():
    assert _visible() == WEEKLY + MONTHLY_RIGHT
    assert len(_visible()) <= 12                     # 한 화면(약 1,650px)에 좌우 이동 없이


def test_first_tab_is_dashboard_and_menu_only_tabs_follow_visible_ones():
    titles = [t for t, *_ in layout.SHEETS]
    assert titles[0] == "대시보드"
    visible_end = max(titles.index(t) for t in MONTHLY_RIGHT)
    assert all(titles.index(t) > visible_end for t in MENU_ONLY)


def test_menu_only_tabs_are_tucked_and_still_exist():
    assert set(MENU_ONLY) <= layout.TUCKED
    assert {"추이", "달력", "검색"} <= layout.TUCKED
    assert all(t in layout.SHEET_ID for t in MENU_ONLY)


def test_script_tuck_list_and_menu_cover_every_tucked_tab():
    listed = set(re.findall(r"'([^']+)'", re.search(r"var TUCKED_VIEWS = \[(.*?)\];", GS, re.S).group(1)))
    assert listed == layout.TUCKED                   # 숨기기 목록이 시트 구성과 같아야 한다
    for tab in MENU_ONLY + ["추이", "달력", "검색"]:
        assert f"showTab_('{tab}')" in GS, tab        # 메뉴에서 꺼낼 수 있어야 한다
    assert "addSubMenu" in GS and "탭 열기" in GS
