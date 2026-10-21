# 시골쥐 스타일 재구성 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 지금 운영 가계부 시트를 제자리에서 시골쥐 색·모양(남색 머리글·회청색 바탕·분홍 입력 칸·업데이트일)으로 바꾸고, 새 [자산현황] 탭(목표·저축률·자산 분포·부채)과 단계형 사용법을 더한다.

**Architecture:** 색은 `styling.py` 토큰 한곳. 화면 탭 바탕·표 흰 바탕·머리글·입력 칸·업데이트일은 새 `theme.py`가 운영 위치(dash_head·dash_base·trend_head)를 받아 repeatCell로 만든다. 자산현황은 새 `asset_status.py`(breakdown.py와 같은 모양: 값·서식·그래프 함수). 운영 반영은 `migrate_couple.py`의 반복 안전 단계(`_structure`·`_values`·`_always`·`_visual`)에 끼워 넣는다.

**Tech Stack:** Python 3.12 (Sheets API 요청 생성), pytest, Apps Script V8 + node --test, google-api-python-client.

**Spec:** `docs/superpowers/specs/2026-10-14-asset-status-design.md`

## Global Constraints

- 재구성은 지금 파일 제자리. 새 파일·데이터 이동 없음. 수식·데이터·칸 위치·기존 기능은 바꾸지 않는다.
- 색 토큰: PAGE_BG #E9EEF6, 머리글·구역 띠 NAVY #1F3864(흰 굵은 글씨), INPUT_BG #FCE4EC, 그래프 연파랑→남색.
- 유지 규칙: 수입·수익 빨강 / 지출·손실 파랑, 0은 "-", 숫자 오른쪽·글자 가운데(align.py), 보조 열 흐리게.
- 운영 위치: 대시보드 표 머리글 19행(dash_head), 고정비·변동비 구역 46행(dash_base), 추이 머리글 14행(trend_head). 코드 기본값은 60·95·38.
- 운영 적용은 `migrate_couple.py`로만, 두 번 실행해도 같은 결과. 적용 전 드라이브 백업.
- 사람 입력 칸(설정 J8:J10, 자산현황 부채 표 입력 열)은 migrate가 절대 덮어쓰지 않는다.
- git: 파일 경로를 지정해 add (`git add -A` 금지). `메리츠.txt`는 커밋 금지. 커밋 끝에 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- 사용자 보고는 한국어, 결론 먼저.
- 읽기 한도 분당 60회 → 통합 시험은 batchGet으로 한 번에 읽기.

## Rulings (계획 작성 때 정한 것)

- 원형 그래프 조각 색은 Sheets API로 정할 수 없다 → 원형은 기본 색, 콤보 그래프 막대·선만 색 지정(수입 빨강·소비지출 파랑·저축률 남색) — 틀리면: 원형 색이 시골쥐와 다름(기능 영향 없음).
- 합계 줄 남색(설계)은 손익 부호 색이 있는 투자 합계 줄(9·12행)에 적용하지 않고 LABEL_BG 유지 — 남색 위 빨강/파랑 글씨가 안 읽힘. 틀리면: 투자 합계 줄만 시골쥐와 다름.
- 업데이트일 위치: 대시보드 L1:L2, 부부 K1:K2, 추이 W1:W2, 달력 G1:G2, 투자 I2:I3, 자산기록 G1:G2, 자산현황 K1:K2 (운영에서 비어 있음 2026-10-14 확인). 자산기록 G열은 그래프에 가려질 수 있음 — 틀리면: 그 탭만 배지가 안 보임.

## Review Focus

- 목표 기한을 날짜(2029-12-01)로 넣거나 텍스트("2029-12")로 넣거나 → 둘 다 같은 남은 개월. (Task 4 시험에 둘 다)
- 남은 개월 0(이번 달이 기한) → 0으로 나누지 않고 "기한 지남". (Task 4·7)
- 대출이 하나도 없음 / 부채 표가 비어 있음 → 합계 0, 오류 칸 없음. (Task 7)
- 바탕을 칠한 뒤 이미 칠해 둔 칸(구분 색 조건부 서식, 사람별 머리글, 대시보드 라벨 A5:B5 빨강·파랑)이 덮이지 않음 → theme 요청을 `_always` 맨 앞에 둔다. (Task 3 시험: 순서)
- 합계 줄을 남색으로 칠하면 빨강/파랑 손익 글씨가 안 보임 → 손익 부호 색이 있는 합계 줄(투자 9·12행)은 LABEL_BG 유지. (Task 1 시험)

---

### Task 1: 색 토큰 — 남색 머리글·분홍 입력·탭 색

**Files:**
- Modify: `styling.py` (상수 7~31행, HEADERS 34~43행, highlight_requests 122~133행)
- Modify: `tests/test_styling.py:58-62` (노랑 → 분홍)
- Test: `tests/test_theme.py` (새)

**Interfaces:**
- Produces: `styling.NAVY_HEAD: dict`, `styling.PAGE_BG: dict`, `styling.INPUT_BG: dict`, `styling.INPUT_TAB_COLOR: dict`; `styling.VIEW_TAB`은 NAVY_HEAD와 같은 값(기존 모듈 breakdown·invest·meritz_style 머리글이 자동으로 남색).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_theme.py
import invest
import layout
import styling


def _bg(reqs):
    return [(r["repeatCell"]["range"], r["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor"))
            for r in reqs if "repeatCell" in r]


def test_color_tokens():
    assert styling.NAVY_HEAD == {"red": 31 / 255, "green": 56 / 255, "blue": 100 / 255}
    assert styling.PAGE_BG == {"red": 233 / 255, "green": 238 / 255, "blue": 246 / 255}
    assert styling.INPUT_BG == {"red": 252 / 255, "green": 228 / 255, "blue": 236 / 255}
    assert styling.VIEW_TAB == styling.NAVY_HEAD


def test_every_table_header_is_navy_and_no_yellow_left():
    reqs = styling.style_requests()
    heads = [layout.a1_to_grid(a1) for a1, _c in styling.HEADERS]
    got = dict((tuple(sorted(g.items())), c) for g, c in _bg(reqs))
    assert all(got[tuple(sorted(h.items()))] == styling.NAVY_HEAD for h in heads)
    assert not hasattr(styling, "YELLOW")
    assert all(c != {"red": 1.0, "green": 0.95, "blue": 0.6} for _g, c in _bg(reqs))


def test_tab_colors_view_navy_input_pink():
    t = styling.TAB_COLORS
    assert t[layout.DASH] == styling.NAVY_HEAD and t[layout.TXN] == styling.INPUT_TAB_COLOR
    assert t[layout.RECUR] == styling.INPUT_TAB_COLOR and t[layout.SETTINGS] == styling.SETUP_TAB


def test_signed_total_rows_stay_light():
    # 투자 합계 줄(9·12행)은 손익 빨강/파랑 글씨가 보이게 연한 바탕
    total = [c for g, c in _bg(invest.polish_requests()) if g == layout.a1_to_grid("투자!A9:G9")]
    assert total == [styling.LABEL_BG]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_theme.py`
Expected: FAIL — `AttributeError: module 'styling' has no attribute 'NAVY_HEAD'`

- [ ] **Step 3: Write minimal implementation** — `styling.py`

상수 블록에서 `YELLOW` 줄을 지우고 아래로 바꾼다 (`NAVY`는 제목 글씨용으로 그대로 둔다):

```python
NAVY_HEAD = {"red": 31 / 255, "green": 56 / 255, "blue": 100 / 255}      # #1F3864 머리글·구역 띠
PAGE_BG = {"red": 233 / 255, "green": 238 / 255, "blue": 246 / 255}      # #E9EEF6 화면 탭 바탕
INPUT_BG = {"red": 252 / 255, "green": 228 / 255, "blue": 236 / 255}     # #FCE4EC 사람이 입력하는 칸
INPUT_TAB_COLOR = {"red": 0.94, "green": 0.56, "blue": 0.69}             # 입력 탭 이름 색(분홍)
```

`INPUT_TAB = ...`, `VIEW_TAB = ...` 두 줄을 아래로 바꾼다:

```python
INPUT_TAB = INPUT_TAB_COLOR
VIEW_TAB = NAVY_HEAD
```

HEADERS의 색을 전부 `NAVY_HEAD`로 (주석도 "표 머리글 → 남색"으로):

```python
# 표 머리글 → 모두 남색 (시골쥐 스타일)
HEADERS = [(a1, NAVY_HEAD) for a1 in (
    f"{TXN}!A1:M1", f"{FAV}!A1:G1", f"{RECUR}!A1:I1", f"{ASSETS}!A1:I1", f"{SETTINGS}!A1:D1", f"{SETTINGS}!E1",
    f"{SETTINGS}!I1:J1", f"{SETTINGS}!K1:M1", f"{COUPLE}!A4:E4", f"{COUPLE}!A15:K15", f"{NETWORTH}!A1:D1",
    f"{INVEST}!A3:F3", f"{INVEST}!A6:I6", f"{INVEST}!A40:C40", f"{INVEST}!E40:F40", f"{INVEST}!A15:D15",
    f"{INVEST}!F15:H15", f"{SEARCH}!A6:J6", f"{DASH}!A60:L60", f"{TREND}!A38:W38", f"{CAL}!A4:G4")]
```

highlight_requests에서 `YELLOW` 두 곳을 `INPUT_BG`로:

```python
    sel = [_fmt(a1_to_grid(a1), {"backgroundColor": INPUT_BG, "textFormat": {"fontSize": 14, "bold": True}},
                "userEnteredFormat(backgroundColor,textFormat)") for a1 in SELECTORS]
    ...
    sms_tip = _fmt(a1_to_grid(f"{SMS}!A1"), {"backgroundColor": INPUT_BG, "textFormat": {"fontSize": 13, "bold": True}},
                   "userEnteredFormat(backgroundColor,textFormat)")
```

18행 주석 `# 구분 색: 지출 빨강, 수입 파랑, 저축 노랑` → `# 구분 색: 수입 빨강, 지출 파랑, 저축 노랑`.

`tests/test_styling.py`의 `test_selectors_are_yellow`를 이름·내용 교체:

```python
def test_selectors_are_pink_input():
    fmts = _cell_formats(styling.style_requests())
    pink = [g for g, f in fmts if f.get("backgroundColor") == styling.INPUT_BG]
    for a1 in ("대시보드!B1", "추이!B1", "달력!B1", "검색!B1:B4"):
        assert layout.a1_to_grid(a1) in pink, a1
```

`invest.polish_requests`의 `total`은 이미 `LABEL_BG`라 그대로 둔다(시험이 그 사실을 고정).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q`
Expected: 전부 PASS (test_ui_polish의 `== styling.VIEW_TAB` 비교도 VIEW_TAB이 NAVY_HEAD라 통과)

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add styling.py tests/test_styling.py tests/test_theme.py && git commit -m "style: 시골쥐 색 토큰 — 머리글 남색, 입력 칸 분홍, 탭 색

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: theme.py — 화면 탭 바탕·표 흰 바탕·머리글·입력 칸·업데이트일

**Files:**
- Create: `theme.py`
- Modify: `layout.py` (ASSET_STATUS 상수와 탭 정의 — Task 4가 쓰지만 VIEW_TABS에 필요해 여기서 추가)
- Test: `tests/test_theme.py` (추가)

**Interfaces:**
- Consumes: `styling.NAVY_HEAD/PAGE_BG/INPUT_BG/LABEL_BG/WHITE/HEADER_FONT/HEADERS`, `align.requests(dash_head, dash_base, trend_head)`, `meritz_style.header_ranges(slot)`, `layout.MERITZ_SLOTS`.
- Produces:
  - `layout.ASSET_STATUS = "자산현황"`, SHEETS에 `(ASSET_STATUS, 2100, 80, 11, False)`를 DASH 바로 다음에.
  - `theme.VIEW_TABS: list[str]`
  - `theme.requests(dash_head: int = 60, dash_base: int = 95, trend_head: int = 38) -> list[dict]` — 순서: 바탕 → 표 흰 바탕 → KPI 라벨 → 머리글 → 입력 칸 → 업데이트일 서식
  - `theme.badge_values() -> list[dict]` — 업데이트일 라벨·날짜 수식 값
  - `theme.BADGES: dict[str, tuple[str, str, str]]` — 탭 → (라벨 칸, 날짜 칸, 날짜 서식)

- [ ] **Step 1: Write the failing test** (tests/test_theme.py 끝에 추가)

```python
import theme


def _fmt_at(reqs, a1):
    g = layout.a1_to_grid(a1)
    return [r["repeatCell"]["cell"]["userEnteredFormat"] for r in reqs
            if "repeatCell" in r and r["repeatCell"]["range"] == g]


def test_view_tabs_get_page_background_then_white_tables():
    reqs = theme.requests()
    whole = [r for r in reqs if "repeatCell" in r and set(r["repeatCell"]["range"]) == {"sheetId"}]
    assert {r["repeatCell"]["range"]["sheetId"] for r in whole} == {layout.SHEET_ID[t] for t in theme.VIEW_TABS}
    assert all(r["repeatCell"]["cell"]["userEnteredFormat"]["backgroundColor"] == styling.PAGE_BG for r in whole)
    first_white = next(i for i, r in enumerate(reqs) if "repeatCell" in r
                       and r["repeatCell"]["cell"]["userEnteredFormat"].get("backgroundColor") == styling.WHITE)
    assert max(reqs.index(r) for r in whole) < first_white  # 바탕 먼저, 그 위에 흰 표
    assert _fmt_at(reqs, "부부!C16:K55")[0]["backgroundColor"] == styling.WHITE


def test_live_positions_shift_dashboard_and_trend_headers():
    reqs = theme.requests(dash_head=19, dash_base=46, trend_head=14)
    assert _fmt_at(reqs, "대시보드!A19:L19")[0]["backgroundColor"] == styling.NAVY_HEAD
    assert _fmt_at(reqs, "추이!A14:W14")[0]["backgroundColor"] == styling.NAVY_HEAD
    assert not _fmt_at(reqs, "대시보드!A60:L60")


def test_input_cells_pink():
    reqs = theme.requests()
    for a1 in ("내역!A2:J5000", "반복!A2:I50", "즐겨찾기!A2:G50", "자산!A2:D50", "설정!J8:J10", "투자!H7:I12",
               "자산현황!A36:A45", "자산현황!D36:G45", "자산현황!I36:I45", "대시보드!B1"):
        assert _fmt_at(reqs, a1)[0]["backgroundColor"] == styling.INPUT_BG, a1


def test_update_badges_point_at_sources():
    vals = {e["range"]: e["values"] for e in theme.badge_values()}
    assert vals["대시보드!L1"] == [["업데이트일"]]
    assert vals["대시보드!L2"] == [['=IF(COUNT(내역!A2:A)=0,"",MAX(내역!A2:A))']]
    assert vals["투자!I3"] == [['=IF(COUNT(투자!F7:F12)=0,"",MAX(투자!F7:F12))']]
    assert vals["자산기록!G2"] == [['=IF(COUNT(자산기록!A2:A)=0,"",MAX(자산기록!A2:A))']]
    assert "투자!F7:F12" in vals["자산현황!K2"][0][0] and "내역!A2:A" in vals["자산현황!K2"][0][0]
    reqs = theme.requests()
    assert _fmt_at(reqs, "대시보드!L1")[0]["backgroundColor"] == styling.NAVY_HEAD
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_theme.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'theme'`

- [ ] **Step 3: Write minimal implementation**

`layout.py`: 11행 아래에 상수, SHEETS의 `(DASH, 400, 145, 14, False),` 다음 줄에 탭 추가.

```python
ASSET_STATUS = "자산현황"
```

```python
    (ASSET_STATUS, 2100, 80, 11, False),  # K열: 부채 표 대출명 선택지(숨은 보조 열)
```

`styling.py` TAB_COLORS에 `ASSET_STATUS: VIEW_TAB` 추가, COL_WIDTHS에 `ASSET_STATUS: [150, 140, 120, 110, 130, 110, 110, 100, 160, 30, 120]` 추가, import에 ASSET_STATUS.
`base_requests`의 눈금선 숨김 목록에 ASSET_STATUS 추가.

`theme.py`:

```python
"""시골쥐 스타일 화면: 화면 탭 바탕(회청), 표 안은 흰색, 머리글 남색, 입력 칸 분홍, 탭 맨 위 오른쪽 '업데이트일'.

모두 repeatCell(덮어쓰기)이라 반복 적용해도 같은 결과. migrate `_always` 맨 앞에서 적용하고, 그 뒤 요청
(구분 색·사람별 머리글·라벨 빨강/파랑·고정비 구역 머리글)이 위에 다시 칠한다.
"""
import align
from layout import (ASSET_STATUS, ASSETS, CAL, COUPLE, DASH, FAV, INVEST, MERITZ, MERITZ2, MERITZ_SLOTS, NETWORTH, RECUR,
                    SEARCH, SETTINGS, SHEET_ID, SMS, STOCK, STOCK2, TREND, TXN, a1_to_grid, v)
import meritz_style
from styling import HEADER_FONT, HEADERS, INPUT_BG, LABEL_BG, NAVY_HEAD, PAGE_BG, WHITE

VIEW_TABS = [DASH, ASSET_STATUS, COUPLE, TREND, INVEST, NETWORTH, CAL, SEARCH, STOCK, MERITZ, STOCK2, MERITZ2]
TXN_MAX = '=IF(COUNT(내역!A2:A)=0,"",MAX(내역!A2:A))'
# 탭 → (라벨 칸, 날짜 칸, 날짜 서식). 날짜 칸 수식은 BADGE_FORMULAS
BADGES = {DASH: ("L1", "L2", "yyyy-mm-dd"), COUPLE: ("K1", "K2", "yyyy-mm-dd"), TREND: ("W1", "W2", "yyyy-mm-dd"),
          CAL: ("G1", "G2", "yyyy-mm-dd"), INVEST: ("I2", "I3", "mm/dd hh:mm"), NETWORTH: ("G1", "G2", '0000"-"00'),
          ASSET_STATUS: ("K1", "K2", "yyyy-mm-dd")}
BADGE_FORMULAS = {DASH: TXN_MAX, COUPLE: TXN_MAX, TREND: TXN_MAX, CAL: TXN_MAX,
                  INVEST: '=IF(COUNT(투자!F7:F12)=0,"",MAX(투자!F7:F12))',
                  NETWORTH: '=IF(COUNT(자산기록!A2:A)=0,"",MAX(자산기록!A2:A))',
                  ASSET_STATUS: '=IF(COUNT(내역!A2:A,투자!F7:F12)=0,"",MAX(MAX(내역!A2:A),INT(MAX(투자!F7:F12))))'}
INPUTS = [f"{TXN}!A2:J5000", f"{RECUR}!A2:I50", f"{FAV}!A2:G50", f"{SMS}!A2:A500", f"{ASSETS}!A2:D50", f"{ASSETS}!F2:G50",
          f"{ASSETS}!I2:I50", f"{SETTINGS}!A2:E60", f"{SETTINGS}!G2:G20", f"{SETTINGS}!J2:J4", f"{SETTINGS}!J8:J10",
          f"{SETTINGS}!K2:M60", f"{INVEST}!H7:I12", f"{ASSET_STATUS}!A36:A45", f"{ASSET_STATUS}!D36:G45",
          f"{ASSET_STATUS}!I36:I45", f"{DASH}!B1", f"{COUPLE}!B1", f"{TREND}!B1", f"{CAL}!B1", f"{SEARCH}!B1:B4"]
KPI_LABELS = [f"{DASH}!A5:M5", f"{ASSET_STATUS}!A4:F4", f"{ASSET_STATUS}!A8:C8"]
KPI_VALUES = [f"{DASH}!A6:M6", f"{ASSET_STATUS}!A5:F5", f"{ASSET_STATUS}!A9:C9"]


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


def _tables(dash_head: int, dash_base: int, trend_head: int) -> list[dict]:
    """표 안 흰 바탕 = 정렬 규칙(align)이 아는 표 몸통 중 화면 탭 것 + 숫자 카드."""
    view_ids = {SHEET_ID[t] for t in VIEW_TABS}
    bodies = [r["repeatCell"]["range"] for r in align.requests(dash_head, dash_base, trend_head)
              if r["repeatCell"]["range"]["sheetId"] in view_ids]
    return ([_cell(g, {"backgroundColor": WHITE}, "userEnteredFormat.backgroundColor") for g in bodies]
            + [_bg(a1, WHITE) for a1 in KPI_VALUES] + [_bg(a1, LABEL_BG) for a1 in KPI_LABELS])


def _shift(a1: str, dash_head: int, trend_head: int) -> str:
    """코드 위치 머리글(대시보드 60행·추이 38행)을 운영 위치로."""
    tab, ref = a1.split("!")
    row = {DASH: (60, dash_head), TREND: (38, trend_head)}.get(tab)
    return a1 if not row else f"{tab}!{ref.replace(str(row[0]), str(row[1]))}"


def _heads(dash_head: int, trend_head: int) -> list[dict]:
    stock = [a1 for s in MERITZ_SLOTS for a1 in meritz_style.header_ranges(s)]
    return [_head(_shift(a1, dash_head, trend_head)) for a1, _c in HEADERS] + [_head(a1) for a1 in stock]


def _badges() -> list[dict]:
    out = []
    for tab, (label, date, pattern) in BADGES.items():
        out.append(_head(f"{tab}!{label}"))
        out.append(_cell(a1_to_grid(f"{tab}!{date}"), {
            "backgroundColor": WHITE, "horizontalAlignment": "CENTER", "textFormat": {"bold": True},
            "numberFormat": {"type": "DATE_TIME" if "h" in pattern else "NUMBER" if "0" in pattern else "DATE",
                             "pattern": pattern}},
            "userEnteredFormat(backgroundColor,horizontalAlignment,textFormat.bold,numberFormat)"))
    return out


def badge_values() -> list[dict]:
    return ([v(f"{tab}!{label}", [["업데이트일"]]) for tab, (label, _d, _p) in BADGES.items()]
            + [v(f"{tab}!{date}", [[BADGE_FORMULAS[tab]]]) for tab, (_l, date, _p) in BADGES.items()])


def requests(dash_head: int = 60, dash_base: int = 95, trend_head: int = 38) -> list[dict]:
    return (_page() + _tables(dash_head, dash_base, trend_head) + _heads(dash_head, trend_head)
            + [_bg(a1, INPUT_BG) for a1 in INPUTS] + _badges())
```

주의: `_shift`의 `ref.replace("60", ...)`은 `A60:L60`처럼 행 번호만 들어 있는 머리글 범위에만 쓰인다(대시보드·추이 HEADERS는 각각 1개). 열 문자에는 숫자가 없어서 안전하다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q`
Expected: 전부 PASS. (test_every_visible_tab_colored: 새 탭이 TAB_COLORS에 있어 통과. 자산현황 A36 등은 아직 값이 없어도 a1_to_grid만 쓰므로 통과)

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add theme.py layout.py styling.py tests/test_theme.py && git commit -m "feat: theme.py — 화면 탭 회청 바탕·흰 표·남색 머리글·분홍 입력 칸·업데이트일

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: theme을 새 시트 생성과 운영 migrate에 연결

**Files:**
- Modify: `build_budget.py:50` (value_data), `build_budget.py:58` (visual_requests)
- Modify: `migrate_couple.py` (`_values`, `_always`)
- Test: `tests/test_theme.py` (추가)

**Interfaces:**
- Consumes: `theme.requests(dash_head, dash_base, trend_head)`, `theme.badge_values()`, `migrate_couple._dash_head(pie)`, `State.dash_base`, `State.trend_head`.
- Produces: `migrate_couple._theme(s: State) -> list[dict]` — 대시보드 위치를 모르면(pie 없음) 대시보드 탭 요청은 뺀다.

- [ ] **Step 1: Write the failing test**

```python
import build_budget
import migrate_couple as mc


def _live_state():
    pie = {"chartId": 1, "spec": {"pieChart": {"legendPosition": "LABELED_LEGEND",
           "series": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 1, "endColumnIndex": 2}]}},
           "domain": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 44,
                                                    "startColumnIndex": 12, "endColumnIndex": 13}]}}}}}
    return mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=9, networth_charts=1,
                    settings=[], budgets_empty=False, invest_charts=2, pie=pie, dash_rows=96,
                    dash_chart_titles=frozenset(), dash_base=46, trend_head=14)


def test_theme_runs_first_in_live_migration_and_follows_positions():
    structure, values, _v = mc.plan(_live_state())
    page = [i for i, r in enumerate(structure) if "repeatCell" in r and set(r["repeatCell"]["range"]) == {"sheetId"}]
    labels = [i for i, r in enumerate(structure) if "repeatCell" in r
              and r["repeatCell"]["range"] == layout.a1_to_grid("대시보드!A5")]
    assert page and labels and max(page) < min(labels)  # 바탕이 수입 라벨 빨강을 덮지 않게
    assert _fmt_at(structure, "대시보드!A19:L19")[0]["backgroundColor"] == styling.NAVY_HEAD
    assert "대시보드!L2" in {e["range"] for e in values}


def test_new_sheet_build_includes_theme():
    assert any(r in build_budget.visual_requests() for r in theme.requests())
    assert "대시보드!L2" in {e["range"] for e in build_budget.value_data("a@b.com")}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_theme.py`
Expected: FAIL — `assert page and labels ...` (theme이 아직 migrate에 없음)

- [ ] **Step 3: Write minimal implementation**

`migrate_couple.py`: import에 `import theme` 추가. `_align_and_labels` 위에:

```python
def _theme(s: State) -> list[dict]:
    """시골쥐 화면(바탕·흰 표·남색 머리글·분홍 입력·업데이트일). 대시보드 위치를 모르면 대시보드는 건너뜀."""
    head = _dash_head(s.pie)
    reqs = theme.requests(head if head is not None else 60, s.dash_base, s.trend_head)
    if head is None:
        reqs = [r for r in reqs if _sheet_ids(r) != {SHEET_ID[DASH]}]
    return reqs
```

`_always`의 return을 theme이 맨 앞이 되게:

```python
    return (_theme(s) + kinds + fmts + dash + invest_chart_moves(list(s.invest_chart_rows)) + invest.polish_requests()
            + _widths() + styling.asset_align_requests() + networth_axis_fix(s.networth_chart)
            + breakdown.style_requests(s.dash_base) + _readability(s) + _align_and_labels(s))
```

`_values`의 return 끝에 `+ theme.badge_values()` 추가.

`build_budget.py`: import에 `import theme`, value_data 끝에 `+ theme.badge_values()`, visual_requests를 theme이 맨 앞이 되게
`return (theme.requests() + styling.style_requests() + ...` (기존 나머지 그대로).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add migrate_couple.py build_budget.py tests/test_theme.py && git commit -m "feat: 시골쥐 화면을 새 시트·운영 migrate에 연결 (다른 서식보다 먼저)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: asset_status.py — 목표·저축률·자산 분포·부채 수식

**Files:**
- Create: `asset_status.py`
- Modify: `layout.py` (자산 종류 선택지에 `대출`, 설정 I8:I10 라벨 seed, 자산현황 검증·서식)
- Test: `tests/test_asset_status.py` (새)

**Interfaces:**
- Consumes: `formulas.sumifs`, `formulas.AMT/YM/TYPE/INC/EXP`, `layout.ASSET_STATUS/ASSETS/SETTINGS/DASH/MONTH_FMT/v/a1_to_grid/number_format`.
- Produces:
  - `asset_status.values() -> list[dict]` — 라벨·수식만(사람 입력 칸 제외)
  - `asset_status.settings_labels() -> list[dict]` — 설정 I8:I10 라벨
  - `asset_status.dashboard_kpi() -> list[dict]` — 대시보드 M5:M6
  - `asset_status.formats() -> list[dict]` — 숫자·백분율 서식, 검증(부채 대출명 드롭다운·설정 J8 숫자)
  - `asset_status.chart_requests() -> list[dict]` — 저축률 콤보 + 자산 분포 원형
  - `asset_status.CHART_TITLES = ["월별 저축률", "자산 분포"]`
  - `asset_status.months_left(cell: str) -> str` — 기한 칸 → 남은 개월 수식 조각

- [ ] **Step 1: Write the failing test**

```python
# tests/test_asset_status.py
import asset_status as a
import layout
import styling


def _vals():
    return {e["range"]: e["values"] for e in a.values()}


def test_goal_card_reads_settings_and_handles_blank_and_overdue():
    v = _vals()
    assert v["자산현황!A4:F4"] == [["현재 순자산", "목표 순자산", "달성률", "남은 개월", "필요 월 저축", "목표 기한"]]
    row = v["자산현황!A5:F5"][0]
    assert row[0] == "=SUM(자산!E2:E50)" and row[1] == '=IF(설정!J8="","",설정!J8)'
    assert row[2] == '=IF(N(B5)=0,"",A5/B5)'
    assert row[3] == f'=IF(설정!J9="","",{a.months_left("설정!J9")})'
    assert row[4] == '=IF(OR(B5="",D5=""),"",IF(D5<=0,"기한 지남",MAX(0,(B5-A5)/D5)))'


def test_months_left_accepts_text_or_date():
    f = a.months_left("설정!J9")
    assert "ISTEXT(설정!J9)" in f and 'DATEVALUE(설정!J9&"-01")' in f and "MAX(0," in f


def test_monthly_savings_rate_uses_income_minus_spending_only():
    v = _vals()
    assert v["자산현황!A12:F12"] == [["월", "수입", "소비지출", "저축", "저축률", "귀속월"]]
    jan = v["자산현황!A13:F13"][0]
    assert jan[0] == "1월" and jan[5] == "=YEAR(TODAY())*100+1"
    assert jan[1] == '=SUMIFS(내역!$K:$K,내역!$L:$L,F13,내역!$C:$C,"수입")'
    assert jan[2] == '=SUMIFS(내역!$K:$K,내역!$L:$L,F13,내역!$C:$C,"지출")'  # 저축·이체 제외
    assert jan[3] == '=IF(AND(B13=0,C13=0),"",B13-C13)' and jan[4] == '=IF(OR(N(B13)=0,D13=""),"",D13/B13)'
    assert v["자산현황!A24:F24"][0][0] == "12월"
    assert v["자산현황!A9:C9"][0][0] == "=SUM(D13:D24)"


def test_distribution_groups_and_debt():
    v = _vals()
    rows = v["자산현황!A28:C32"]
    assert [r[0] for r in rows] == ["현금성", "주식", "청약", "부채", "순자산"]
    assert rows[0][1] == '=SUM(SUMIFS(자산!$E$2:$E$50,자산!$B$2:$B$50,{"현금","통장","계좌"}))'
    assert rows[3][1] == '=SUM(SUMIFS(자산!$E$2:$E$50,자산!$B$2:$B$50,{"카드","대출"}))'
    assert rows[4][1] == "=SUM(B28:B31)" and rows[3][2] == ""


def test_debt_table_formulas_only_never_inputs():
    v = _vals()
    assert v["자산현황!A35:I35"] == [["대출명", "소유자", "현재 잔액", "금리", "월 상환액", "상환일", "만기", "남은 개월", "비고"]]
    assert v["자산현황!B36"] == [['=MAP(A36:A45,LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,자산!$A$2:$I$50,9,FALSE),""))))']]
    assert v["자산현황!C36"] == [['=MAP(A36:A45,LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,자산!$A$2:$E$50,5,FALSE),"자산 탭에 없음"))))']]
    assert v["자산현황!K36"] == [['=IFERROR(FILTER(자산!A2:A50,자산!B2:B50="대출"),"")']]
    written = set(v)
    for col in "ADEFGI":  # 사람 입력 열은 절대 쓰지 않는다
        assert not any(r.startswith(f"자산현황!{col}36") or r.startswith(f"자산현황!{col}37") for r in written), col
    assert v["자산현황!A46:E46"] == [["합계", "", "=SUM(C36:C45)", "", "=SUM(E36:E45)"]]


def test_settings_labels_dashboard_kpi_and_loan_kind():
    assert {e["range"]: e["values"] for e in a.settings_labels()}["설정!I8:I10"] == [
        ["목표 순자산"], ["목표 기한 (yyyy-mm)"], ["올해 저축 목표"]]
    kpi = {e["range"]: e["values"] for e in a.dashboard_kpi()}
    assert kpi["대시보드!M5:M6"] == [["목표 달성률"], ['=IF(자산현황!C5="","",자산현황!C5)']]
    loan = [r for r in layout.validation_requests() if r["setDataValidation"]["range"] == layout.a1_to_grid("자산!B2:B50")]
    assert {"userEnteredValue": "대출"} in loan[0]["setDataValidation"]["rule"]["condition"]["values"]


def test_charts():
    specs = [r["addChart"]["chart"]["spec"] for r in a.chart_requests()]
    assert [s["title"] for s in specs] == a.CHART_TITLES
    combo = specs[0]["basicChart"]
    assert combo["chartType"] == "COMBO" and combo["series"][2]["targetAxis"] == "RIGHT_AXIS"
    assert [x["colorStyle"]["rgbColor"] for x in combo["series"]] == [styling.RED_TEXT, styling.BLUE_TEXT, styling.NAVY_HEAD]
    assert specs[1]["pieChart"]["series"]["sourceRange"]["sources"][0] == layout.a1_to_grid("자산현황!B28:B30")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_asset_status.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'asset_status'`

- [ ] **Step 3: Write minimal implementation**

`layout.py` validation_requests의 자산 종류 줄:

```python
        (f"{ASSETS}!B2:B50", _rule("ONE_OF_LIST", "통장", "계좌", "카드", "현금", "청약", "주식", "대출")),
```

`asset_status.py`:

```python
"""[자산현황] 탭: 목표(순자산·올해 저축), 올해 월별 저축률, 자산 분포, 부채 표.

입력은 설정 J8:J10(목표)과 부채 표 A·D:G·I열(사람). 이 모듈은 라벨·수식만 쓴다 — 입력 칸은 절대 쓰지 않음.
대출은 [자산] 탭 종류 '대출' 한 줄(초기 잔액 음수), 상환은 내역 '이체'(통장 → 대출)라 잔액·순자산은 기존 계산 그대로.
"""
from charts import _src
from formulas import INC, EXP, TYPE, YM, sumifs
from layout import ASSET_STATUS as S, ASSETS, DASH, MONTH_FMT, SETTINGS, SHEET_ID, a1_to_grid, number_format, v
from styling import BLUE_TEXT, NAVY_HEAD, RED_TEXT

CHART_TITLES = ["월별 저축률", "자산 분포"]
DEBT_FIRST, DEBT_LAST = 36, 45
GROUPS = [("현금성", ["현금", "통장", "계좌"]), ("주식", ["주식"]), ("청약", ["청약"]), ("부채", ["카드", "대출"])]


def months_left(cell: str) -> str:
    """기한 칸(텍스트 'yyyy-mm' 또는 날짜) → 그 달까지 남은 개월(이번 달 = 0, 지난 기한도 0)."""
    end = f'IF(ISTEXT({cell}),DATEVALUE({cell}&"-01"),{cell})'
    return (f"MAX(0,(YEAR({end})-YEAR(TODAY()))*12+MONTH({end})-MONTH(TODAY()))")


def _goal() -> list[dict]:
    head = [["현재 순자산", "목표 순자산", "달성률", "남은 개월", "필요 월 저축", "목표 기한"]]
    row = ["=SUM(자산!E2:E50)", f'=IF({SETTINGS}!J8="","",{SETTINGS}!J8)', '=IF(N(B5)=0,"",A5/B5)',
           f'=IF({SETTINGS}!J9="","",{months_left(f"{SETTINGS}!J9")})',
           '=IF(OR(B5="",D5=""),"",IF(D5<=0,"기한 지남",MAX(0,(B5-A5)/D5)))', f'=IF({SETTINGS}!J9="","",{SETTINGS}!J9)']
    year = [["올해 저축 누적", "올해 저축 목표", "달성률"],
            ["=SUM(D13:D24)", f'=IF({SETTINGS}!J10="","",{SETTINGS}!J10)', '=IF(N(B9)=0,"",A9/B9)']]
    return [v(f"{S}!A1", [["🏦 우리집 자산현황"]]), v(f"{S}!A3", [["🎯 목표"]]),
            v(f"{S}!A4:F4", head), v(f"{S}!A5:F5", [row]), v(f"{S}!A7", [["💰 올해 저축"]]), v(f"{S}!A8:C9", year)]


def _monthly() -> list[dict]:
    out = [v(f"{S}!A11", [["📈 월별 저축률 (올해)"]]),
           v(f"{S}!A12:F12", [["월", "수입", "소비지출", "저축", "저축률", "귀속월"]])]
    for m in range(1, 13):
        r = 12 + m
        out.append(v(f"{S}!A{r}:F{r}", [[f"{m}월", f"={sumifs((YM, f'F{r}'), (TYPE, INC))}",
                                         f"={sumifs((YM, f'F{r}'), (TYPE, EXP))}",
                                         f'=IF(AND(B{r}=0,C{r}=0),"",B{r}-C{r})',
                                         f'=IF(OR(N(B{r})=0,D{r}=""),"",D{r}/B{r})', f"=YEAR(TODAY())*100+{m}"]]))
    return out


def _distribution() -> list[dict]:
    rows = []
    for i, (name, kinds) in enumerate(GROUPS):
        r = 28 + i
        crit = "{" + ",".join(f'"{k}"' for k in kinds) + "}"
        share = "" if name == "부채" else f'=IF(B{r}<=0,"",B{r}/SUMIF(B28:B30,">0"))'
        rows.append([name, f"=SUM(SUMIFS({ASSETS}!$E$2:$E$50,{ASSETS}!$B$2:$B$50,{crit}))", share])
    rows.append(["순자산", "=SUM(B28:B31)", ""])
    return [v(f"{S}!A26", [["🧩 자산 분포"]]), v(f"{S}!A27:C27", [["묶음", "금액", "비율"]]), v(f"{S}!A28:C32", rows)]


def _debt() -> list[dict]:
    a, f, z = f"A{DEBT_FIRST}:A{DEBT_LAST}", DEBT_FIRST, DEBT_LAST
    owner = f'=MAP({a},LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,{ASSETS}!$A$2:$I$50,9,FALSE),""))))'
    balance = f'=MAP({a},LAMBDA(x,IF(x="","",IFERROR(VLOOKUP(x,{ASSETS}!$A$2:$E$50,5,FALSE),"자산 탭에 없음"))))'
    left = f'=MAP(G{f}:G{z},LAMBDA(x,IF(x="","",{months_left("x")})))'
    return [v(f"{S}!A34", [["🏛 부채"]]),
            v(f"{S}!A35:I35", [["대출명", "소유자", "현재 잔액", "금리", "월 상환액", "상환일", "만기", "남은 개월", "비고"]]),
            v(f"{S}!B{f}", [[owner]]), v(f"{S}!C{f}", [[balance]]), v(f"{S}!H{f}", [[left]]),
            v(f"{S}!K35", [["대출 목록"]]), v(f"{S}!K{f}", [[f'=IFERROR(FILTER({ASSETS}!A2:A50,{ASSETS}!B2:B50="대출"),"")']]),
            v(f"{S}!A{z + 1}:E{z + 1}", [["합계", "", f"=SUM(C{f}:C{z})", "", f"=SUM(E{f}:E{z})"]])]


def values() -> list[dict]:
    return _goal() + _monthly() + _distribution() + _debt()


def settings_labels() -> list[dict]:
    return [v(f"{SETTINGS}!I8:I10", [["목표 순자산"], ["목표 기한 (yyyy-mm)"], ["올해 저축 목표"]])]


def dashboard_kpi() -> list[dict]:
    return [v(f"{DASH}!M5:M6", [["목표 달성률"], [f'=IF({S}!C5="","",{S}!C5)']])]


def formats() -> list[dict]:
    money, pct = "NUMBER", "PERCENT"
    fmts = [(f"{S}!A5:B5", money, "#,##0"), (f"{S}!C5", pct, "0.0%"), (f"{S}!D5", money, "0"),
            (f"{S}!E5", money, "#,##0"), (f"{S}!A9:B9", money, "#,##0"), (f"{S}!C9", pct, "0.0%"),
            (f"{S}!B13:D24", money, "#,##0"), (f"{S}!E13:E24", pct, "0.0%"), (f"{S}!F13:F24", money, MONTH_FMT),
            (f"{S}!B28:B32", money, "#,##0"), (f"{S}!C28:C30", pct, "0.0%"), (f"{S}!C36:C46", money, "#,##0"),
            (f"{S}!D36:D45", pct, "0.00%"), (f"{S}!E36:E46", money, "#,##0"), (f"{S}!H36:H45", money, "0"),
            (f"{DASH}!M6", pct, "0.0%"), (f"{SETTINGS}!J8", money, "#,##0"), (f"{SETTINGS}!J10", money, "#,##0")]
    pick = {"setDataValidation": {"range": a1_to_grid(f"{S}!A{DEBT_FIRST}:A{DEBT_LAST}"), "rule": {
        "condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={S}!$K${DEBT_FIRST}:$K${DEBT_LAST}"}]},
        "strict": False, "showCustomUi": True}}}
    hide = {"updateDimensionProperties": {"range": {"sheetId": SHEET_ID[S], "dimension": "COLUMNS",
                                                    "startIndex": 10, "endIndex": 11},
                                          "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}}
    return [number_format(a1, k, p) for a1, k, p in fmts] + [pick, hide]


def chart_requests() -> list[dict]:
    combo = {"title": CHART_TITLES[0], "basicChart": {
        "chartType": "COMBO", "legendPosition": "BOTTOM_LEGEND", "headerCount": 1,
        "domains": [{"domain": _src(f"{S}!A12:A24")}],
        "series": [{"series": _src(f"{S}!B12:B24"), "targetAxis": "LEFT_AXIS", "type": "COLUMN",
                    "colorStyle": {"rgbColor": RED_TEXT}},      # 수입 빨강
                   {"series": _src(f"{S}!C12:C24"), "targetAxis": "LEFT_AXIS", "type": "COLUMN",
                    "colorStyle": {"rgbColor": BLUE_TEXT}},     # 소비지출 파랑
                   {"series": _src(f"{S}!E12:E24"), "targetAxis": "RIGHT_AXIS", "type": "LINE",
                    "colorStyle": {"rgbColor": NAVY_HEAD}}]}}  # 저축률 남색
    pie = {"title": CHART_TITLES[1], "pieChart": {"legendPosition": "LABELED_LEGEND", "pieHole": 0.4,
                                                 "domain": _src(f"{S}!A28:A30"), "series": _src(f"{S}!B28:B30")}}
    at = lambda row, col, w, h: {"overlayPosition": {"anchorCell": {"sheetId": SHEET_ID[S], "rowIndex": row,
                                                                    "columnIndex": col}, "widthPixels": w, "heightPixels": h}}
    return [{"addChart": {"chart": {"spec": combo, "position": at(10, 7, 620, 330)}}},
            {"addChart": {"chart": {"spec": pie, "position": at(25, 4, 420, 260)}}}]
```

`layout.seed_values`의 설정 I1:J4 다음 줄에 새 시트용 라벨(값은 비움):

```python
        v(f"{SETTINGS}!I8:I10", [["목표 순자산"], ["목표 기한 (yyyy-mm)"], ["올해 저축 목표"]]),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add asset_status.py layout.py tests/test_asset_status.py && git commit -m "feat: 자산현황 탭 수식 — 목표·월별 저축률·자산 분포·부채 표, 자산 종류 '대출'

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 자산현황을 새 시트·운영 migrate에 연결 (탭 1회 추가, 입력 칸 보존)

**Files:**
- Modify: `migrate_couple.py` (STATUS_TABS, `_structure`, `_values`, `_visual`, `_always`)
- Modify: `build_budget.py` (value_data, visual_requests, structure)
- Modify: `layout.py` `protection_requests` (자산현황: 입력 칸만 열어 둠)
- Test: `tests/test_asset_status.py` (추가)

**Interfaces:**
- Consumes: `asset_status.values/settings_labels/dashboard_kpi/formats/chart_requests/CHART_TITLES`, `migrate_couple._add_sheet`, `_only`, `layout.protection_requests`.
- Produces: 운영에 자산현황 탭이 없으면 그 실행에서 탭·서식·보호·그래프를 한 번 만들고, 있으면 값(수식·라벨)만 다시 쓴다.

- [ ] **Step 1: Write the failing test**

```python
import build_budget
import migrate_couple as mc


def _state(titles, charts=frozenset()):
    return mc.State(titles=titles, settings_cols=13, asset_cols=9, networth_charts=1, settings=[],
                    budgets_empty=False, invest_charts=2, dash_rows=96, dash_chart_titles=charts, dash_base=46)


def test_status_tab_added_once_with_charts():
    without = {t for t, *_ in layout.SHEETS} - {"자산현황"}
    s1, v1, vis1 = mc.plan(_state(without))
    assert {"addSheet": mc._add_sheet("자산현황")["addSheet"]} in s1
    assert [r["addChart"]["chart"]["spec"]["title"] for r in vis1 if "addChart" in r
            and r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["sheetId"] == 2100] == a.CHART_TITLES
    s2, v2, vis2 = mc.plan(_state({t for t, *_ in layout.SHEETS}))
    assert not any("addSheet" in r and r["addSheet"]["properties"]["title"] == "자산현황" for r in s2)
    assert not any("addChart" in r and r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["sheetId"] == 2100
                   for r in vis2)


def test_live_values_never_touch_inputs():
    _s, values, _v = mc.plan(_state({t for t, *_ in layout.SHEETS}))
    ranges = {e["range"] for e in values}
    assert "자산현황!A5:F5" in ranges and "설정!I8:I10" in ranges and "대시보드!M5:M6" in ranges
    assert not any(r.startswith("설정!J8") or r.startswith("설정!J9") or r.startswith("설정!J10") for r in ranges)
    assert not any(r.startswith(f"자산현황!{c}36") for r in ranges for c in "ADEFGI")


def test_status_protected_except_inputs():
    prot = [r["addProtectedRange"]["protectedRange"] for r in layout.protection_requests()
            if r["addProtectedRange"]["protectedRange"]["range"] == {"sheetId": 2100}]
    free = prot[0]["unprotectedRanges"]
    assert layout.a1_to_grid("자산현황!A36:A45") in free and layout.a1_to_grid("자산현황!D36:G45") in free


def test_new_sheet_build_has_status():
    assert "자산현황!A5:F5" in {e["range"] for e in build_budget.value_data("a@b.com")}
    assert any(r in build_budget.visual_requests() for r in a.chart_requests())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_asset_status.py`
Expected: FAIL — addSheet 자산현황이 계획에 없음

- [ ] **Step 3: Write minimal implementation**

`layout.protection_requests`의 `whole` 목록에 추가:

```python
             (ASSET_STATUS, ["A36:A45", "D36:G45", "I36:I45"]),
```

`migrate_couple.py`: import `asset_status`, 상수 `STATUS_TABS = (ASSET_STATUS,)` (layout import에 ASSET_STATUS 추가).
`_structure`에서 new_invest 계산 다음 줄:

```python
    new_status = [t for t in STATUS_TABS if t not in s.titles]
    reqs += [_add_sheet(t) for t in new + new_invest + new_status]
```

(기존 `reqs += [_add_sheet(t) for t in new + new_invest]` 줄을 위 줄로 교체), 그리고 `if new_invest:` 블록 다음에:

```python
    if new_status:  # 탭이 생기는 묶음에서만: 서식·검증·보호
        ids = {SHEET_ID[t] for t in new_status}
        reqs += asset_status.formats() + _only(layout.protection_requests(), ids)
```

`_values` return 끝에 `+ asset_status.values() + asset_status.settings_labels() + asset_status.dashboard_kpi()` 추가.

`_visual`에 (breakdown 그래프 블록 다음):

```python
    if ASSET_STATUS not in s.titles:  # 탭을 이번에 만들면 그래프도 이번에 한 번
        out += asset_status.chart_requests()
```

`_always`에 매번 같은 결과인 서식만 다시(숫자 서식은 repeatCell이라 안전, 검증·숨김 열은 탭 생성 때만):

```python
            + [r for r in asset_status.formats() if "repeatCell" in r]
```

을 `breakdown.style_requests(s.dash_base)` 앞에 추가.

`build_budget.py`: value_data 끝에 `+ asset_status.values() + asset_status.settings_labels() + asset_status.dashboard_kpi()`,
visual_requests에 `+ asset_status.chart_requests()`, structure_requests(검증·서식 묶음)에 `+ asset_status.formats()`. import `asset_status`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q`
Expected: 전부 PASS

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add migrate_couple.py build_budget.py layout.py tests/test_asset_status.py && git commit -m "feat: 자산현황 탭을 새 시트·운영에 연결 — 탭·그래프 1회, 입력 칸 보존·보호 예외

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 대출을 부채로 기록 (자산기록 D열 '카드·대출 잔액')

**Files:**
- Modify: `apps-script/logic.gs:334-340` (netWorthRow)
- Modify: `couple.py:11` (NET_HEADERS)
- Test: `tests/couple.test.js:83-87`

**Interfaces:**
- Produces: `netWorthRow(assets) -> [순자산, 부채 외 합계, 카드·대출 합계]`

- [ ] **Step 1: Write the failing test** — couple.test.js의 netWorthRow 시험 아래에 추가

```javascript
test('netWorthRow: 대출도 카드처럼 부채 칸으로', () => {
  const assets = [['IBK', '계좌', 0, '', 4000000], ['전세대출', '대출', -50000000, '', -49000000],
    ['현대카드', '카드', 0, '', -220000]];
  assert.deepEqual(plain(ctx.netWorthRow(assets)), [-45220000, 4000000, -49220000]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && node --test tests/couple.test.js`
Expected: FAIL — 실제 `[-45220000, -45000000, -220000]`

- [ ] **Step 3: Write minimal implementation**

logic.gs:

```javascript
// 자산 A:E 행 → [순자산, 부채 외 합계, 카드·대출 합계]. E(현재 잔액)가 숫자인 행만.
function netWorthRow(assets) {
  var pos = 0, debt = 0;
  assets.forEach(function (r) {
    if (isBlank(r[0]) || typeof r[4] !== 'number') return;
    if (r[1] === '카드' || r[1] === '대출') debt += r[4]; else pos += r[4];
  });
  return [pos + debt, pos, debt];
}
```

couple.py: `NET_HEADERS = ["월", "순자산", "자산(부채 제외)", "카드·대출 잔액"]`

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)" && python3 -m pytest -q`
Expected: node fail 0, pytest 전부 PASS (NET_HEADERS를 비교하는 파이썬 시험이 있으면 새 문구로 고친다)

- [ ] **Step 5: Commit** (Apps Script 배포는 Task 9에서 deploy_script.py로)

```bash
cd "/mnt/d/budget book" && git add apps-script/logic.gs couple.py tests/couple.test.js && git commit -m "feat: 대출을 카드와 함께 부채 칸으로 기록 — 자산기록 D '카드·대출 잔액'

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 사용법 단계표와 안내 문구 (노랑→분홍, 색 설명 바로잡기)

**Files:**
- Modify: `guide.py` (CONTENT)
- Modify: `formulas.py:128` (대시보드 C1 안내), `views.py:36` (추이 C1 안내)
- Modify: `migrate_couple.py` `_values` (운영 대시보드·추이 C1 안내 문구 덮어쓰기)
- Test: `tests/test_theme.py` (추가)

**Interfaces:**
- Produces: `guide.CONTENT`에 "🗓 순서대로 시작하기" 구역(단계 행 7개)과 [자산현황] 설명 행.

- [ ] **Step 1: Write the failing test**

```python
import guide


def test_guide_has_step_table_and_current_colors():
    text = " ".join(a + " " + b for _k, a, b in guide.CONTENT)
    assert "🗓 순서대로 시작하기" in text and "D+0" in text and "[자산현황]" in text and "대출" in text
    assert "노란 칸" not in text and "지출 빨강, 수입 파랑" not in text
    assert "분홍 칸" in text and "수입 빨강, 지출 파랑" in text


def test_hint_cells_say_pink():
    _s, values, _v = mc.plan(_live_state())
    hints = {e["range"]: e["values"] for e in values}
    assert hints["대시보드!C1"] == [["◀ 분홍 칸에서 월 선택 (비우면 이번 달)"]]
    assert hints["추이!C1"] == [["◀ 분홍 칸에서 연도 선택 (비우면 올해)"]]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_theme.py`
Expected: FAIL — "🗓 순서대로 시작하기" 없음

- [ ] **Step 3: Write minimal implementation**

`guide.py` CONTENT의 `("section", "📖 자세한 설명", "")` 바로 앞에 삽입:

```python
    ("section", "🗓 순서대로 시작하기", ""),
    ("row", "D+0 ① 설정", "[설정] 카테고리·사용자·사람별 예산을 우리 집에 맞게 고칩니다. 분홍 칸만 쓰면 나머지는 자동입니다."),
    ("row", "D+0 ② 자산", "[자산] 통장·카드·현금·청약·주식을 적고 초기 잔액을 넣습니다. 대출은 종류 '대출'로, 초기 잔액은 마이너스(예: -50,000,000)."),
    ("row", "D+0 ③ 목표", "[설정] J8~J10에 목표 순자산·목표 기한(예: 2029-12)·올해 저축 목표를 적으면 [자산현황]에 달성률과 필요 월 저축이 나옵니다."),
    ("row", "D+0 ④ 증권 키", "각자 PC 메뉴 '증권 연동'에서 메리츠·한투 키를 넣고 자동 갱신을 켭니다."),
    ("row", "D+0 ⑤ 반복", "[반복]에 월급·월세·보험·대출 상환(구분 이체: 통장 → 대출)을 등록합니다."),
    ("row", "매일", "[내역]에 적거나 [문자입력]에 카드 문자를 붙여넣습니다."),
    ("row", "매달", "[대시보드]로 이번 달 살림, [자산현황]으로 목표·저축률·부채, [부부]로 정산을 확인합니다."),
```

같은 CONTENT에서 문구 바꾸기:
- `[내역]` 행: `"구분에 따라 색이 칠해집니다: 지출 빨강, 수입 파랑, 저축 노랑."` → `"구분에 따라 색이 칠해집니다: 수입 빨강, 지출 파랑, 저축 노랑."`
- `"노란 칸"` → `"분홍 칸"` (대시보드·추이·검색·문제 해결 행 4곳)
- `[자산기록]` 행의 `"(순자산, 카드 제외 자산, 카드 잔액)"` → `"(순자산, 부채 제외 자산, 카드·대출 잔액)"`
- `[자산기록]` 행 다음에 추가:

```python
    ("row", "[자산현황]", "목표 순자산 달성률·남은 개월·필요 월 저축, 올해 저축 목표 달성률, 올해 월별 저축률(수입−소비지출)과 그래프, 자산 분포(현금성·주식·청약·부채), 부채 표(대출명을 고르면 소유자·잔액 자동, 금리·월 상환·상환일·만기는 직접)를 봅니다."),
```

`formulas.py:128`: `"◀ 노란 칸에서 월 선택 (비우면 이번 달)"` → `"◀ 분홍 칸에서 월 선택 (비우면 이번 달)"`.
`views.py:36`: `"◀ 노란 칸에서 연도 선택 (비우면 올해)"` → `"◀ 분홍 칸에서 연도 선택 (비우면 올해)"`.
`migrate_couple._values`의 `dash = [...]` 목록에 추가:

```python
    hints = [v(f"{DASH}!C1", [["◀ 분홍 칸에서 월 선택 (비우면 이번 달)"]]),
             v(f"{layout.TREND}!C1", [["◀ 분홍 칸에서 연도 선택 (비우면 올해)"]])]
```

그리고 return에 `+ hints`.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q`
Expected: 전부 PASS (사용법 행 수를 세는 기존 시험이 있으면 CONTENT 길이 기준이라 그대로 통과)

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add guide.py formulas.py views.py migrate_couple.py tests/test_theme.py && git commit -m "docs: 사용법 단계표(D+0·매일·매달)와 자산현황 설명, 안내 문구 분홍·색 규칙 바로잡기

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 임시 시트 통합 시험 — 대출·저축률·목표

**Files:**
- Create: `verify_asset_status.py`
- Test: 실행 자체 (임시 시트 생성 → 확인 → 휴지통)

**Interfaces:**
- Consumes: `build_budget.structure_requests/value_data/visual_requests`, `verify_meritz._same`, `layout.create_body/v`.

- [ ] **Step 1: Write the script (실패할 기대값부터)**

```python
"""자산현황 통합 시험 — 임시 시트에 대출·내역·목표를 넣고 자산현황 값을 확인한 뒤 휴지통으로. 운영 시트는 건드리지 않음.

사용: python3 verify_asset_status.py  (종료코드 0 = 통과)
"""
import datetime as dt
import sys
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

import build_budget
import layout
from auth import get_credentials
from verify_meritz import _same


def sample(day: str, ym: str) -> list[dict]:
    t = lambda typ, cat, pay, to, amt: [day, "공동", typ, cat, "", pay, to, amt, "KRW", "검증"]
    return [layout.v("자산!A5:I5", [["전세대출", "대출", -50000000, "", "", "", "", "", "공동"]]),
            layout.v("설정!A15:D15", [["적금", "저축", "", "고정비"]]),
            layout.v("내역!A2:J5", [t("수입", "월급", "주거래통장", "", 3000000),
                                    t("지출", "식비", "신용카드1", "", 1000000),
                                    t("저축", "적금", "주거래통장", "", 500000),
                                    t("이체", "", "주거래통장", "전세대출", 1000000)]),
            layout.v("자산현황!A36", [["전세대출"]]),
            layout.v("자산현황!D36:G36", [[0.035, 1000000, 25, ym]])]


def checks(month: int) -> dict:
    r = 12 + month
    return {"자산!E5": -49000000, "자산현황!C36": -49000000, "자산현황!B36": "공동",
            f"자산현황!B{r}": 3000000, f"자산현황!C{r}": 1000000, f"자산현황!D{r}": 2000000, f"자산현황!E{r}": 2 / 3,
            # 부채 묶음 = 대출 −49,000,000 + 시험 카드(신용카드1) 식비 −1,000,000
            "자산현황!A9": 2000000, "자산현황!B31": -50000000, "자산현황!H36": 0,
            "자산현황!B5": "", "자산현황!C5": "", "자산현황!E5": "", "대시보드!M6": ""}


def run(sheets, vals, drive) -> list[str]:
    sid = sheets.create(body=layout.create_body("자산현황 시험 (자동 삭제)"), fields="spreadsheetId").execute()["spreadsheetId"]
    try:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.structure_requests()}).execute()
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": build_budget.value_data("nobody@example.com")}).execute()
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.visual_requests()}).execute()
        now = dt.datetime.now(ZoneInfo("Asia/Seoul")).date()
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": sample(now.isoformat(), now.strftime("%Y-%m"))}).execute()
        want = checks(now.month)
        got = vals.batchGet(spreadsheetId=sid, ranges=list(want), valueRenderOption="UNFORMATTED_VALUE").execute()
        actual = {a1: (r.get("values") or [[""]])[0][0] for a1, r in zip(want, got["valueRanges"])}
        errors = [f"{a1}: 기대 {w!r}, 실제 {actual[a1]!r}" for a1, w in want.items() if not _same(actual[a1], w)]
        # 목표를 넣으면 달성률·필요 월 저축이 나온다 (기한 = 이번 달 → 기한 지남)
        vals.update(spreadsheetId=sid, range="설정!J8:J10", valueInputOption="USER_ENTERED",
                    body={"values": [[100000000], [now.strftime("%Y-%m")], [30000000]]}).execute()
        g = vals.batchGet(spreadsheetId=sid, ranges=["자산현황!C5:E5", "자산현황!C9", "대시보드!M6"],
                          valueRenderOption="UNFORMATTED_VALUE").execute()["valueRanges"]
        c5, d5, e5 = (g[0].get("values") or [["", "", ""]])[0][:3]
        if not (isinstance(c5, (int, float)) and d5 == 0 and e5 == "기한 지남"):
            errors.append(f"목표 입력 뒤 자산현황 C5:E5 기대 (숫자, 0, '기한 지남'), 실제 {(c5, d5, e5)!r}")
        if not _same((g[1].get("values") or [[None]])[0][0], 2000000 / 30000000):
            errors.append(f"자산현황!C9 기대 {2000000 / 30000000}, 실제 {g[1].get('values')!r}")
        bad = vals.get(spreadsheetId=sid, range="자산현황!A1:K46").execute().get("values", [])
        errs = [c for row in bad for c in row if str(c)[:2] in ("#R", "#N", "#V", "#D", "#E")]
        return errors + ([f"자산현황 오류 칸 {errs}"] if errs else [])
    finally:
        drive.files().update(fileId=sid, body={"trashed": True}).execute()


def main() -> int:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    errors = run(sheets, sheets.values(), build("drive", "v3", credentials=creds))
    print("\n".join(errors) if errors else f"통과: 자산현황 {len(checks(1)) + 3}개 항목 일치 (임시 시트는 휴지통으로)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run it**

Run: `cd "/mnt/d/budget book" && timeout 600 python3 verify_asset_status.py`
Expected: `통과: 자산현황 17개 항목 일치 (임시 시트는 휴지통으로)`. 다르면 메시지의 칸을 superpowers:systematic-debugging으로 원인부터 찾는다(기대값을 맞추려고 고치지 않는다).

- [ ] **Step 3: 기존 통합 시험도 그대로인지**

Run: `cd "/mnt/d/budget book" && timeout 600 python3 verify_couple.py`
Expected: `통과: 부부 확장 27개 항목 일치`

- [ ] **Step 4: Commit**

```bash
cd "/mnt/d/budget book" && git add verify_asset_status.py && git commit -m "test: 자산현황 통합 시험 — 대출 상환·저축률·목표·기한 지남

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: 운영 적용과 눈으로 확인

**Files:** 없음 (운영 시트·Apps Script 배포)

- [ ] **Step 1: 전체 시험**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q 2>&1 | tail -1 && node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: pytest 전부 통과, node fail 0

- [ ] **Step 2: 운영 계획 미리 보기(쓰기 없음)** — 스크래치 스크립트

```python
import sys; sys.path.insert(0, "/mnt/d/budget book")
from auth import get_credentials
from googleapiclient.discovery import build
import migrate_couple as mc
s = build("sheets", "v4", credentials=get_credentials()).spreadsheets()
st = mc._state(s, mc.ID_FILE.read_text().strip())
print("dash_head", mc._dash_head(st.pie), "dash_base", st.dash_base, "trend_head", st.trend_head)
structure, values, visual = mc.plan(st)
print("addSheet", [r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r])
print("입력칸 쓰기?", [e["range"] for e in values if e["range"].startswith(("설정!J8", "설정!J9", "설정!J10"))])
print("addChart", [r["addChart"]["chart"]["spec"]["title"] for r in visual if "addChart" in r])
```

Expected: `dash_head 19 dash_base 46 trend_head 14`, addSheet `['자산현황']`, 입력칸 쓰기 `[]`, addChart `['월별 저축률', '자산 분포']`.

- [ ] **Step 3: 백업 후 적용**

```python
# 스크래치: 드라이브 사본
import sys, datetime as dt; sys.path.insert(0, "/mnt/d/budget book")
from auth import get_credentials
from googleapiclient.discovery import build
import migrate_couple as mc
c = get_credentials()
print(build("drive", "v3", credentials=c).files().copy(fileId=mc.ID_FILE.read_text().strip(),
      body={"name": f"우리집 가계부 백업 ({dt.date.today()} 시골쥐 재구성 적용 전)"}).execute()["id"])
```

Run: `cd "/mnt/d/budget book" && python3 migrate_couple.py && python3 deploy_script.py`
Expected: `적용: 구조 …개, 값 …개 범위, 서식 …개 요청` / 스크립트 업로드 성공 메시지

- [ ] **Step 4: 운영 확인**
  - 모든 탭 오류 칸 0 (batchGet `'{탭}'!A1:Z300`, `#REF/#N/A/#VALUE/#DIV/#ERROR` 개수)
  - 내역·반복·자산·설정 값이 보관본(`~/.config/budget-book/snapshot-2026-10-14.json` FORMATTED_VALUE)과 같은지: 내역 A1:M20, 반복 A1:I54, 자산 A1:I15, 설정 A1:M22 비교 → 차이 0
  - 대시보드·자산현황 PDF(`export?format=pdf&gid=400`, `gid=2100`, `range=A1:N60`로 쪽 수 줄이기)를 읽어 바탕 회청·머리글 남색·입력 분홍·업데이트일 확인
  - 대시보드 M6, 자산현황 A5(= 대시보드 J6 순자산) 값 확인

- [ ] **Step 5: 메모리 갱신·보고**
  `~/.claude/projects/-home-jack/memory/project_budget_book.md`에 한 줄: 시골쥐 재구성 적용(테마 토큰 styling·theme.py, 자산현황 탭 sheetId 2100, 대출 = 자산 종류 '대출', 목표 = 설정 J8:J10). 사용자에게 결론 먼저 한국어 보고(백업 ID, 시험 수, 확인한 화면, 남은 일: 목표 3칸·대출 입력은 사용자 몫, 다음 묶음 2·3).
