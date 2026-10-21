"""운영 시트에 부부 확장(사람별 예산·부부·자산기록·메리츠 계좌 2개)을 제자리 적용한다. 두 번 실행해도 안전.

첫 실행 때만: 시트 사본(백업) 생성, 기존 월 예산(C열)을 사람별 칸(K:M)으로 이전.
사용: python3 migrate_couple.py   (대상: .spreadsheet_id)
"""
import datetime as dt
import sys
from pathlib import Path
from typing import NamedTuple

from googleapiclient.discovery import build

import align
import chart_fit
import fit_dims
import asset_status
import breakdown
import budget_reco
import cards
import category_bars
import charts
import couple
import formulas
import guide
import invest
import layout
import meritz_sheet
import meritz_style
import readability
import sigol_tabs
import stock_sectors
import styling
import theme
import views
from auth import get_credentials
from layout import (ASSET_STATUS, ASSETS, COUPLE, DASH, GUIDE, INVEST, INVEST_LOG, KIS_RAW, MERITZ, MERITZ_SLOTS, NETWORTH, RAW2, SETTINGS, SHEET_ID, SHEETS, STOCK,
                    STOCK2, MERITZ2, v)

NEW_TABS = (COUPLE, NETWORTH, STOCK2, MERITZ2, RAW2)
INVEST_TABS = (INVEST, KIS_RAW, INVEST_LOG)
HOLD_TABS = (layout.KIS_HOLD,)
STATUS_TABS = (ASSET_STATUS,)
SIGOL_TABS = tuple(sigol_tabs.NAMES)
RENAMES = {"주식": STOCK, "메리츠": MERITZ}
COLS = {SETTINGS: 13, ASSETS: 12, layout.RECUR: 14, layout.TXN: 14}
BUDGET_OWNER = {"월급1": 0, "월급2": 1}  # 나머지 기존 예산은 공동(2)으로
ID_FILE = Path(__file__).parent / ".spreadsheet_id"


class State(NamedTuple):
    titles: set
    settings_cols: int
    asset_cols: int
    networth_charts: int
    settings: list        # 설정 A2:C60 (카테고리, 구분, 월 예산)
    budgets_empty: bool   # 설정 K2:M60이 모두 비었나 (= 아직 이전 전)
    pie: dict = None      # 대시보드 '카테고리별 지출' 차트 (운영은 표 위치가 코드와 다름)
    invest_charts: int = 0  # [투자] 탭 차트 수 (있으면 투자 보기 서식이 이미 적용된 것)
    networth_chart: dict = None   # [자산기록] '월별 순자산' 차트 {chartId, spec} — 가로축 고치기용
    dash_rows: int = 0            # 대시보드 행 수 (0 = 모름 → 늘리지 않음)
    dash_chart_titles: frozenset = None  # 대시보드 차트 제목들 (None = 모름 → 추가 안 함) — 고정비·변동비 그래프 한 번만
    dash_base: int = breakdown.BASE      # 고정비·변동비 구역 시작 행 (사용자가 위로 옮기면 그 자리)
    dash_charts: tuple = ()              # 대시보드 차트 [{chartId, spec}] — 행 삭제로 어긋난 그래프 범위 고치기용
    type_rules: tuple = ()               # 구분 색 조건부 서식 [(sheetId, index, rule)] — 수입 빨강·지출 파랑으로 바꾸기용
    trend_head: int = 38                 # 추이 월별 표 머리글 행 (운영 14)
    charts: tuple = ()                   # 모든 탭 차트 [{chartId, title, sheetId, row, col}] — 제자리로 옮기기용
    status_cols: int = 0                 # 자산현황 열 수 (0 = 모름/없음 → 늘리지 않음)
    status_rows: int = 0                 # 자산현황 행 수 (0 = 모름 → 늘리지 않음)
    recur_cols: int = 14                 # 반복 열 수 (14 미만이면 J:N 고정지출 상세·통화 열 추가)
    txn_cols: int = 14                   # 내역 열 수 (14 미만이면 N 적용 환율 열 추가)
    card_col_a: tuple = ()               # [카드] A열 — 사용자가 줄을 지워 표 자리가 바뀌었는지 (cards.find_layout)
    grid: dict = None                    # {sheetId: (행 수, 열 수)} — 넘는 서식·값은 잘라 보낸다 (None = 모름)
    stock_kl: tuple = ()                 # [주식투자] K:L 값 — 섹터 지정 표가 옛 자리인지 (stock_sectors.relocate)
    stock_protect: tuple = ()            # [주식투자] 보호 범위 id들 (옮길 때 새 입력칸으로 다시 만든다)
    txn_currency_hidden: bool = False    # [내역] I열(통화)이 숨겨져 있는지 — 통화표를 처음 채울 때 한 번만 보이게 한다
    settings_fx: tuple = ()              # [설정] G3:G20 통화표에 사용자가 적은 통화 (비었으면 USD·JPY·EUR·CNY를 채운다)
    rules_seen: frozenset = frozenset()  # {(sheetId, 조건부 서식 수식)} — 입력 확인 규칙을 한 번만 추가 (추가형이라)


def _sheet_ids(req: dict) -> set[int]:
    """요청이 건드리는 sheetId 모음 (범위가 여러 개인 조건부 서식 포함)."""
    found, stack = set(), [next(iter(req.values()))]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            if isinstance(cur.get("sheetId"), int):
                found.add(cur["sheetId"])
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)
    return found


def _only(reqs: list[dict], ids: set[int]) -> list[dict]:
    return [r for r in reqs if _sheet_ids(r) and _sheet_ids(r) <= ids]


def _in(reqs: list[dict], a1s: list[str], key: str) -> list[dict]:
    """요청 중 범위가 a1s 중 하나와 정확히 같은 것 (setDataValidation·repeatCell·addProtectedRange)."""
    grids = [layout.a1_to_grid(a) for a in a1s]
    def rng(r):
        body = r[key]
        return body.get("range") or body.get("protectedRange", {}).get("range")
    return [r for r in reqs if key in r and rng(r) in grids]


def _add_sheet(title: str) -> dict:
    _t, sid, rows, cols, hidden = [s for s in SHEETS if s[0] == title][0]
    return {"addSheet": {"properties": {"sheetId": sid, "title": title, "hidden": hidden,
                                        "gridProperties": {"rowCount": rows, "columnCount": cols, "frozenRowCount": 1}}}}


def _prop(props: dict, fields: str) -> dict:
    return {"updateSheetProperties": {"properties": props, "fields": fields}}


def _new_tab_structure(new_ids: set[int]) -> list[dict]:
    """새 탭 + 기존 탭의 새 칸(설정 C·K:M, 자산 G·I, 부부 B1)에 검증·서식·보호. 한 번만(새 탭이 생기는 묶음)."""
    valid = _in(layout.validation_requests(), [f"{ASSETS}!G2:G50", f"{ASSETS}!I2:I50", f"{SETTINGS}!K2:M60",
                                               f"{COUPLE}!B1"], "setDataValidation")
    fmts = _in(layout.format_requests(), [f"{SETTINGS}!K2:M60", f"{NETWORTH}!A2:A200", f"{NETWORTH}!B2:D200"],
               "repeatCell")
    protect = (_only(layout.protection_requests(), new_ids)
               + _in(layout.protection_requests(), [f"{SETTINGS}!C1:C60", f"{SETTINGS}!K1:M1"], "addProtectedRange"))
    return valid + fmts + couple.couple_formats() + meritz_style.structure_requests([MERITZ_SLOTS[1]]) + protect


def _invest_structure(new_ids: set[int]) -> list[dict]:
    """투자 탭 묶음: 검증·서식·보호(새 탭만) + 자산 G 연동 선택지 4계좌로 갱신. 한 번만."""
    valid = _in(layout.validation_requests(), [f"{ASSETS}!G2:G50"], "setDataValidation")
    return valid + invest.structure_requests() + _only(layout.protection_requests(), new_ids)


def _structure(s: State) -> list[dict]:
    reqs = [_prop({"sheetId": SHEET_ID[new], "title": new}, "title") for old, new in RENAMES.items() if old in s.titles]
    new = [t for t in NEW_TABS if t not in s.titles]
    new_invest = [t for t in INVEST_TABS if t not in s.titles]
    new_status = [t for t in STATUS_TABS if t not in s.titles]
    new_sigol = [t for t in SIGOL_TABS if t not in s.titles]
    new_hold = [t for t in HOLD_TABS if t not in s.titles]
    reqs += [_add_sheet(t) for t in new + new_invest + new_status + new_sigol + new_hold]
    reqs += _only(layout.protection_requests(), {SHEET_ID[t] for t in new_hold})
    for title, have in ((SETTINGS, s.settings_cols), (ASSETS, s.asset_cols), (layout.RECUR, s.recur_cols), (layout.TXN, s.txn_cols)):
        if have < COLS[title]:
            reqs.append({"appendDimension": {"sheetId": SHEET_ID[title], "dimension": "COLUMNS",
                                             "length": COLS[title] - have}})
    status_need = next(c for t, _s, _r, c, _h in SHEETS if t == ASSET_STATUS)
    if 0 < s.status_cols < status_need:  # 그래프 자리(L열~)
        reqs.append({"appendDimension": {"sheetId": SHEET_ID[ASSET_STATUS], "dimension": "COLUMNS",
                                         "length": status_need - s.status_cols}})
    status_rows = next(r for t, _s, r, _c, _h in SHEETS if t == ASSET_STATUS)
    if 0 < s.status_rows < status_rows:  # 맨 아래 가로형 월별 표 자리
        reqs.append({"appendDimension": {"sheetId": SHEET_ID[ASSET_STATUS], "dimension": "ROWS",
                                         "length": status_rows - s.status_rows}})
    stock_rows, stock_cols = next((r, c) for t, _s, r, c, _h in SHEETS if t == layout.STOCKS)
    have_rows, have_stock = (s.grid or {}).get(SHEET_ID[layout.STOCKS], (stock_rows, stock_cols))
    sid_ = SHEET_ID[layout.STOCKS]
    if layout.STOCKS in s.titles and have_rows < stock_rows:  # 섹터 지정·합산 상위 10 표가 내려간 자리
        reqs.append({"appendDimension": {"sheetId": sid_, "dimension": "ROWS", "length": stock_rows - have_rows}})
    if layout.STOCKS in s.titles and have_stock < stock_cols:  # 사람별 그래프 원본(숨김 U~AB) 자리
        reqs.append({"appendDimension": {"sheetId": sid_, "dimension": "COLUMNS", "length": stock_cols - have_stock}})
        reqs.append({"updateDimensionProperties": {"range": {"sheetId": sid_, "dimension": "COLUMNS",
                                                             "startIndex": stock_sectors.HELPER_COLS[0], "endIndex": stock_cols},
                                                   "properties": {"hiddenByUser": True}, "fields": "hiddenByUser"}})
    dash_need = s.dash_base + 95  # 고정비·변동비 구역 + 분류별 막대그래프 구역
    if 0 < s.dash_rows < dash_need:  # 고정비·변동비 구역(시작 행부터 50줄)이 들어갈 만큼만
        reqs.append({"appendDimension": {"sheetId": SHEET_ID[DASH], "dimension": "ROWS", "length": dash_need - s.dash_rows}})
    if s.txn_currency_hidden and not s.settings_fx:  # 외화 입력(환율 자동)용 — 처음 한 번만, 이후 사용자가 숨기면 그대로
        reqs.append(styling._dim(SHEET_ID[layout.TXN], "COLUMNS", 8, 9, {"hiddenByUser": False}, "hiddenByUser"))
    reqs += [_prop({"sheetId": sid, "index": i}, "index") for i, (_t, sid, *_r) in enumerate(SHEETS)]
    reqs += [_prop({"sheetId": SHEET_ID[t], "hidden": True}, "hidden") for t in sorted(layout.TUCKED)]
    reqs.append({"unmergeCells": {"range": GUIDE_ALL}})  # 병합 칸 밑으로 쓴 값은 버려지므로 값 쓰기 전에 푼다
    if new:  # 한 batchUpdate는 원자적: 새 탭이 이미 있으면 이 묶음 전체가 이미 적용된 것
        reqs += _new_tab_structure({SHEET_ID[t] for t in new})
    if new_invest:
        reqs += _invest_structure({SHEET_ID[t] for t in new_invest})
    if new_status:  # 탭이 생기는 묶음에서만: 기본 글씨·행 높이·열 너비·눈금선, 서식·검증·보호
        ids = {SHEET_ID[t] for t in new_status}
        reqs += (_only(styling.base_requests() + styling.layout_requests(), ids) + asset_status.formats()
                 + _only(layout.protection_requests(), ids))
    if new_sigol:  # 시골쥐 기능 시트: 기본 서식·열 너비·드롭다운·조건부 서식·보호 (탭이 생길 때 한 번)
        ids = {SHEET_ID[t] for t in new_sigol}
        reqs += (_only(styling.base_requests() + styling.layout_requests(), ids) + sigol_tabs.widths(new_sigol)
                 + sigol_tabs.formats(new_sigol) + sigol_tabs.protection(new_sigol))
    if s.asset_cols < COLS[ASSETS]:  # 자산 J 통화·K 외화 잔액·L 결제수단 목록 — 열을 추가하는 묶음에서 한 번
        cols = [f"{ASSETS}!J2:J50", f"{ASSETS}!K2:K50"]
        reqs += (_in(layout.validation_requests(), cols, "setDataValidation")
                 + _in(layout.format_requests(), [f"{ASSETS}!K2:K50"], "repeatCell")
                 + [r for r in styling.layout_requests() if r.get("updateDimensionProperties", {}).get("range", {}).get("sheetId") == SHEET_ID[ASSETS]]
                 + _in(layout.protection_requests(), [f"{ASSETS}!L1:L50"], "addProtectedRange"))
    if s.recur_cols < COLS[layout.RECUR]:  # 반복 J:N (전체 금액·금리·만기·통화) 검증·서식 — 열을 추가하는 묶음에서 한 번
        cols = [f"{layout.RECUR}!J2:J50", f"{layout.RECUR}!K2:K50", f"{layout.RECUR}!N2:N50"]
        reqs += (_in(layout.validation_requests(), cols, "setDataValidation")
                 + _in(layout.format_requests(), cols[:2] + [f"{layout.RECUR}!L2:L50"], "repeatCell"))
    if s.recur_cols < COLS[layout.RECUR] or s.txn_cols < COLS[layout.TXN]:  # 새 열 머리글 모양·너비 (반복 N 통화, 내역 N 적용 환율)
        two = {SHEET_ID[layout.RECUR], SHEET_ID[layout.TXN]}
        reqs += (_in(styling.header_requests(), [f"{layout.TXN}!A1:N1", f"{layout.RECUR}!A1:N1"], "repeatCell")
                 + _in(layout.format_requests(), [f"{layout.TXN}!N2:N5000"], "repeatCell")
                 + [r for r in styling.layout_requests() if r.get("updateDimensionProperties", {}).get("range", {}).get("sheetId") in two
                    and r["updateDimensionProperties"]["range"].get("startIndex") == 13])
    return reqs


def budgets_empty(km: list) -> bool:
    """설정 K:M에 사람별 예산 숫자가 하나도 없나. 열 추가 때 J열 체크박스가 복사돼 FALSE가 들어올 수 있어 숫자만 센다."""
    return not any(isinstance(c, (int, float)) and not isinstance(c, bool) and c for r in km for c in r)


def budget_move(settings: list) -> list[dict]:
    """기존 월 예산(C) → 사람별 칸(K:M). 합계 수식(C1)이 펼쳐지도록 C2:C60은 비운다."""
    rows = []
    for r in settings:
        name, amount = (r + ["", "", ""])[0], (r + ["", "", ""])[2]
        row = ["", "", ""]
        if amount not in ("", None):
            row[BUDGET_OWNER.get(name, 2)] = amount
        rows.append(row)
    out = [v(f"{SETTINGS}!C2:C60", [[""]] * 59)]
    if rows:
        out.insert(0, v(f"{SETTINGS}!K2:M{1 + len(rows)}", rows))
    return out


def _values(s: State) -> list[dict]:
    # 머리글·수식뿐이고 사람이 입력하는 칸과 겹치지 않으므로 매번 덮어써도 안전
    vals = (budget_move(s.settings) if s.budgets_empty else [])
    seeds = [e for e in layout.seed_values("") if e["range"] in (f"{SETTINGS}!K1:M1", f"{ASSETS}!G1", f"{ASSETS}!I1",
                                                                  f"{ASSETS}!J1:K1")]
    # 운영 대시보드는 생성 뒤 표·차트 위치가 옮겨져 코드 배치와 다르다 → 바뀐 월말 예상(F6) 한 칸만
    dash = ([v(f"{DASH}!F6", [[formulas.projection("$B$2")]]), formulas.asset_status()] + styling.title_values()  # 제목(이모지 없음)
            + formulas.attention_values() + formulas.txn_values()[:1]
            + [e for e in formulas.calc_values() if e["range"] == "계산!C4"])  # 확인 필요 한 줄, 내역 원화금액(금액오류 구분)
    head = _dash_head(s.pie)
    if head is not None:  # 카드 표: 같은 이름 카드는 소유자별로 (운영 표 위치 = 그래프가 읽는 행 기준)
        dash += formulas.dashboard_cards(head)
    fx = [] if s.settings_fx else [v(f"{SETTINGS}!G3:G{2 + len(layout.FX_CHOICES)}", [[c] for c in layout.FX_CHOICES])]  # 환율(H)은 자동
    stale = [v(f"{INVEST}!F15:F16", [[""], [""]])] + fx
    hints = [v(f"{DASH}!C1", [[layout.MONTH_MOVE_HINT]]),  # 월 이동 드롭다운 안내(짧게: 옆 D1 제목에 잘리지 않게)
             v(f"{layout.TREND}!C1", [[layout.YEAR_MOVE_HINT]])]  # 옛 청약 계좌 목록 자리(F) — 남아 있으면 새 G16 펼침과 겹쳐 #REF!
    return (vals + seeds + formulas.settings_values() + formulas.asset_values() + dash + stale + hints
            + couple.couple_values() + meritz_sheet.all_values() + guide.guide_values() + invest.invest_values()
            + breakdown.breakdown_values(s.dash_base) + category_bars.values(s.dash_base) + theme.badge_values()
            + asset_status.values() + asset_status.settings_labels() + asset_status.dashboard_kpi()
            + sigol_tabs.values() + budget_reco.values() + views.search_totals() + [v(f"{layout.RECUR}!J1:N1", [layout.RECUR_HEADERS[9:]]), v(f"{layout.TXN}!N1", [["적용 환율"]])])


GUIDE_ALL = {"sheetId": SHEET_ID[GUIDE], "startRowIndex": 0, "endRowIndex": 120, "startColumnIndex": 0, "endColumnIndex": 2}


def _guide_format() -> list[dict]:
    """사용법은 내용 줄이 바뀌므로 매번 다시 칠한다 (병합 풀기는 값 쓰기 전 구조 단계에서)."""
    plain = {"repeatCell": {"range": GUIDE_ALL, "cell": {"userEnteredFormat": {}},
                            "fields": "userEnteredFormat(backgroundColor,textFormat)"}}
    return [plain] + guide.guide_requests()


def _rule_key(req: dict) -> tuple:
    rule = req["addConditionalFormatRule"]["rule"]
    return rule["ranges"][0]["sheetId"], rule["booleanRule"]["condition"]["values"][0]["userEnteredValue"]


def _visual(s: State) -> list[dict]:
    out = []
    if not s.networth_charts:  # 차트도 같은 원자적 묶음 → 있으면 부부 보기 서식이 이미 적용된 것
        new_ids = {SHEET_ID[t] for t in NEW_TABS}
        touched = new_ids | {SHEET_ID[SETTINGS], SHEET_ID[ASSETS]}
        out += (_only(styling.base_requests(), new_ids)
                + _only(styling.layout_requests() + styling.header_requests(), touched)
                + _only(styling.highlight_requests(), {SHEET_ID[COUPLE]}) + styling.couple_title_requests()
                + couple.visual_requests() + meritz_style.visual_requests([MERITZ_SLOTS[1]])
                + [charts.unregistered_payment_rule()])
    out += [r for r in charts.data_check_rules() if _rule_key(r) not in s.rules_seen]  # 입력 오류 줄·미등록 결제수단 표시
    if not s.invest_charts:
        ids = {SHEET_ID[INVEST]}
        out += (_only(styling.base_requests() + styling.layout_requests() + styling.header_requests(), ids)
                + invest.visual_requests())
    if s.dash_chart_titles is not None and breakdown.CHART_TITLES[0] not in s.dash_chart_titles:
        out += breakdown.chart_requests(s.dash_base)
    if s.dash_chart_titles is not None and category_bars.CHART_TITLES[0] not in s.dash_chart_titles:
        out += category_bars.chart_requests(s.dash_base)
    if ASSET_STATUS not in s.titles:  # 탭을 이번에 만들면 그래프도 이번에 한 번
        out += asset_status.chart_requests()
    out += sigol_tabs.chart_requests([t for t in SIGOL_TABS if t not in s.titles])
    if ASSET_STATUS in s.titles and s.charts:  # 자산현황 보강 그래프: 운영 차트 목록을 알고, 그 제목이 없을 때만
        have = {c["title"] for c in s.charts if c["sheetId"] == SHEET_ID[ASSET_STATUS]}
        out += [r for r in asset_status.extra_chart_requests() if r["addChart"]["chart"]["spec"]["title"] not in have]
    if layout.STOCKS in s.titles and s.charts:  # 주식투자 사람별 원형: 운영에 그 제목이 없을 때만
        have = {c["title"] for c in s.charts if c["sheetId"] == SHEET_ID[layout.STOCKS]}
        out += [r for r in stock_sectors.chart_requests()[2:] if r["addChart"]["chart"]["spec"]["title"] not in have]
    out += chart_spec_fixes(s.charts, s.dash_base)
    return out + breakdown.chart_fixes(s.dash_charts, s.dash_base) + _guide_format()


def type_rule_fix(rules) -> list[dict]:
    """구분 색 조건부 서식(=$C2="수입" 등)을 지금 색(수입 빨강·지출 파랑)으로. 이미 같으면 아무것도 안 함."""
    want = {word: {"backgroundColor": bg, "textFormat": {"foregroundColor": fg, "bold": True}}
            for word, bg, fg in styling.TYPE_COLORS}
    out = []
    for sid, index, rule in rules:
        cond = rule.get("booleanRule", {}).get("condition", {})
        text = (cond.get("values") or [{}])[0].get("userEnteredValue", "")
        word = next((w for w in want if cond.get("type") == "CUSTOM_FORMULA" and text.endswith(f'="{w}"')), None)
        if word and rule["booleanRule"].get("format") != want[word]:
            new = {**rule, "booleanRule": {**rule["booleanRule"], "format": want[word]}}
            out.append({"updateConditionalFormatRule": {"sheetId": sid, "index": index, "rule": new}})
    return out


def pie_fix(chart):
    """원형 그래프에 비율 표시: 그 차트가 읽는 행에 M열 이름표를 쓰고, 이름표를 조각 옆에 붙인다(한 번만)."""
    if not chart:
        return [], []
    pie = chart["spec"]["pieChart"]
    src = pie["series"]["sourceRange"]["sources"][0]
    values = [charts.pie_labels(src["startRowIndex"] + 1, src["endRowIndex"])]
    dom = {**src, "startColumnIndex": charts.PIE_LABEL_COL, "endColumnIndex": charts.PIE_LABEL_COL + 1}
    if pie["domain"]["sourceRange"]["sources"][0] == dom and pie["legendPosition"] == "LABELED_LEGEND":
        return values, []
    new_pie = {**pie, "legendPosition": "LABELED_LEGEND", "domain": {"sourceRange": {"sources": [dom]}}}
    return values, [{"updateChartSpec": {"chartId": chart["chartId"], "spec": {**chart["spec"], "pieChart": new_pie}}}]


def chart_spots(base: int = breakdown.BASE) -> dict:
    """제목 → (sheetId, 행, 열) 코드가 정한 그래프 자리(0부터). 사람이 배치한 대시보드 위쪽 그래프는 넣지 않는다."""
    spots = {t: (SHEET_ID[DASH], r["overlayPosition"]["anchorCell"]["rowIndex"], r["overlayPosition"]["anchorCell"]["columnIndex"],
                 r["overlayPosition"]["widthPixels"], r["overlayPosition"]["heightPixels"])
             for t, r in zip(breakdown.CHART_TITLES + category_bars.CHART_TITLES,
                             (c["addChart"]["chart"]["position"] for c in breakdown.chart_requests(base) + category_bars.chart_requests(base)))}
    for req in invest.visual_requests()[:2] + [couple.networth_chart()] + asset_status.chart_requests() + sigol_tabs.chart_requests():
        chart = req["addChart"]["chart"]
        o = chart["position"]["overlayPosition"]
        a = o["anchorCell"]
        spots[chart["spec"]["title"]] = (a["sheetId"], a["rowIndex"], a["columnIndex"], o["widthPixels"], o["heightPixels"])
    return spots


def _pie_sources(spec: dict):
    pie = (spec or {}).get("pieChart", {})
    basic = (spec or {}).get("basicChart", {})
    return (pie.get("domain", {}).get("sourceRange"), pie.get("series", {}).get("sourceRange"),
            [d.get("domain", {}).get("sourceRange") for d in basic.get("domains", [])],
            [x.get("series", {}).get("sourceRange") for x in basic.get("series", [])])


def chart_spec_fixes(charts, base: int = breakdown.BASE) -> list[dict]:
    """원형·분류별 막대 그래프가 코드와 다른 범위를 읽으면(표를 옮긴 뒤 등) 코드 범위로. 범위만 비교 — 맞으면 아무것도 안 함."""
    bars = category_bars.chart_requests(base)
    reqs = asset_status.chart_requests() + sigol_tabs.chart_requests() + bars
    want = {(r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["sheetId"], r["addChart"]["chart"]["spec"]["title"]):
            r["addChart"]["chart"]["spec"] for r in reqs if "pieChart" in r["addChart"]["chart"]["spec"] or r in bars}
    out = []
    for c in charts:
        spec = want.get((c["sheetId"], c["title"]))
        if spec and c.get("spec") is not None and _pie_sources(c["spec"]) != _pie_sources(spec):
            out.append({"updateChartSpec": {"chartId": c["chartId"], "spec": spec}})
    return out


def chart_moves(charts, base: int = breakdown.BASE) -> list[dict]:
    """코드 자리와 다른 그래프(행 삽입·삭제로 밀린 것 포함)를 제자리로, 코드 크기보다 크면 코드 크기로.
    이미 그 자리이고 코드 크기 이하면(그래프 맞춤이 줄인 것) 아무것도 안 함."""
    spots = chart_spots(base)
    out = []
    for c in charts:
        spot = spots.get(c["title"])
        if not spot or spot[0] != c["sheetId"]:
            continue
        sid, row, col, w, h = spot
        new_w, new_h = min(c.get("w", w), w), min(c.get("h", h), h)
        if (c["row"], c["col"]) == (row, col) and (new_w, new_h) == (c.get("w", w), c.get("h", h)):
            continue
        out.append({"updateEmbeddedObjectPosition": {"objectId": c["chartId"], "fields": "anchorCell,widthPixels,heightPixels",
                    "newPosition": {"overlayPosition": {"anchorCell": {"sheetId": sid, "rowIndex": row, "columnIndex": col},
                                                        "widthPixels": new_w, "heightPixels": new_h}}}})
    return out


def networth_axis_fix(chart) -> list[dict]:
    """자산기록 그래프 가로축을 글자 월(E열)로. 숫자 월(A열)이면 축이 0000-00 눈금이 된다. 이미 E면 아무것도 안 함."""
    if not chart:
        return []
    basic = chart["spec"]["basicChart"]
    src = basic["domains"][0]["domain"]["sourceRange"]["sources"][0]
    if src["startColumnIndex"] == 4:
        return []
    dom = [{**basic["domains"][0], "domain": {"sourceRange": {"sources": [{**src, "startColumnIndex": 4, "endColumnIndex": 5}]}}}]
    return [{"updateChartSpec": {"chartId": chart["chartId"],
                                 "spec": {**chart["spec"], "basicChart": {**basic, "domains": dom}}}}]


def _widths() -> list[dict]:
    """열 너비: 투자·부부·자산기록 전체, 대시보드는 자산 현황 J~L만 (운영 대시보드 배치는 코드와 다름)."""
    tabs = {SHEET_ID[INVEST], SHEET_ID[COUPLE], SHEET_ID[NETWORTH], SHEET_ID[ASSET_STATUS]}
    reqs = [r for r in styling.layout_requests() if "updateDimensionProperties" in r]
    rng = lambda r: r["updateDimensionProperties"]["range"]
    return [r for r in reqs if rng(r)["sheetId"] in tabs and "pixelSize" in r["updateDimensionProperties"]["properties"]
            or (rng(r)["sheetId"] == SHEET_ID[DASH] and rng(r)["startIndex"] in (9, 10, 11))]


def _dash_head(pie):
    return pie["spec"]["pieChart"]["series"]["sourceRange"]["sources"][0]["startRowIndex"] if pie else None


def _readability(s: State) -> list[dict]:
    """운영 대시보드 표 머리글 행 = '카테고리별 지출' 그래프가 읽는 첫 행 바로 위. 그래프를 못 찾으면 대시보드 표는 건너뜀."""
    reqs = readability.couple_tab() + readability.trend_tab(s.trend_head) + readability.assets_tabs()
    head = _dash_head(s.pie)
    return reqs if head is None else readability.dashboard(head, s.dash_base) + reqs


def _theme(s: State) -> list[dict]:
    """시골쥐 화면(바탕·흰 표·남색 머리글·분홍 입력·업데이트일). 대시보드 위치를 모르면 대시보드는 건너뜀."""
    head = _dash_head(s.pie)
    reqs = theme.requests(head if head is not None else 60, s.dash_base, s.trend_head)
    if head is None:
        reqs = [r for r in reqs if _sheet_ids(r) != {SHEET_ID[DASH]}]
    return reqs


def _align_and_labels(s: State) -> list[dict]:
    """정렬 + 구분 색 규칙 고치기. 대시보드 표 위치를 모르면 대시보드 정렬은 건너뜀."""
    head = _dash_head(s.pie)
    reqs = align.requests(head if head is not None else 60, s.dash_base, s.trend_head)
    if head is None:
        reqs = [r for r in reqs if r["repeatCell"]["range"]["sheetId"] != SHEET_ID[DASH]]
    return reqs + type_rule_fix(s.type_rules)


def _always(s: State) -> list[dict]:
    """반복해도 같은 결과인 갱신: 시골쥐 모양(글꼴·크기·행 높이·제목), 자산 종류 선택지, 한눈에 표 서식, 그래프 위치.

    순서 = 나중 것이 이긴다: 글꼴·행 높이 → 제목·숫자 카드 → 바탕·흰 표·남색 머리글(theme) → 탭별 세부 서식.
    사용법 탭은 내용 줄마다 크기가 달라 _guide_format이 따로 칠한다(여기서 덮으면 안 됨).
    """
    kinds = _in(layout.validation_requests(), [f"{ASSETS}!A2:A50", f"{ASSETS}!B2:B50", f"{layout.TXN}!F2:F5000", f"{layout.TXN}!G2:G5000",
                                               f"{layout.TXN}!B2:B5000", f"{layout.TXN}!C2:C5000", f"{layout.TXN}!I2:I5000",
                                               f"{layout.RECUR}!F2:F50", f"{layout.FAV}!E2:E50", f"{DASH}!C1", f"{COUPLE}!C1", f"{layout.TREND}!C1"], "setDataValidation")
    fmts = _in(invest.structure_requests(), [f"{INVEST}!B16:D20", f"{INVEST}!I16:I19"], "repeatCell")
    dash = _in(formulas.core_formats(), [f"{DASH}!J6:L6"], "repeatCell") + styling.asset_status_style()
    base = [r for r in styling.base_requests() if _sheet_ids(r) != {SHEET_ID[GUIDE]}]
    look = ([theme.spreadsheet_theme()] + base + styling.dashboard_requests() + styling.highlight_requests()
            + styling.calendar_requests() + meritz_style.style_requests() + meritz_style.hide_requests()
            + [r for r in meritz_style.structure_requests() if "repeatCell" in r])  # 숫자·시각 서식은 매번
    pay_col = layout.a1_to_grid(f"{layout.CARDS}!J{cards.FIRST}:J{cards.LAST}")  # 카드 결제 계좌 드롭다운 (운영 카드 표 자리 기준, 매번 같은 규칙)
    card_pay = [r for r in cards.formats() if "setDataValidation" in r and r["setDataValidation"]["range"] == pay_col]
    return (look + _theme(s) + kinds + card_pay + budget_reco.validation_requests() + fmts + dash + chart_moves(s.charts, s.dash_base) + invest.polish_requests()
            + _widths() + styling.asset_align_requests() + networth_axis_fix(s.networth_chart)
            + [r for r in asset_status.formats() + sigol_tabs.formats() if "repeatCell" in r]  # 숫자 서식은 매번(자리 옮김 반영)
            + breakdown.style_requests(s.dash_base) + category_bars.style_requests(s.dash_base) + _readability(s)
            + _align_and_labels(s))


def dash_list(pie) -> list[dict]:
    """운영 대시보드 카테고리 목록 칸(미분류 다음 줄)을 대분류 순 정렬 수식으로. 그래프를 못 찾으면 건너뜀."""
    if not pie:
        return []
    head = pie["spec"]["pieChart"]["series"]["sourceRange"]["sources"][0]["startRowIndex"]
    return [v(f"{DASH}!A{head + 2}", [[f"={formulas.by_major()}"]])]


def _clip(reqs: list, values: list, grid) -> tuple[list, list]:
    """운영 탭 크기를 넘는 서식 범위·값 줄은 잘라 낸다 — 사용자가 줄을 지운 탭 하나 때문에 전체가 실패하지 않게."""
    if not grid:
        return reqs, values
    out = []
    for r in reqs:
        kind = next(iter(r))
        g = r[kind].get("range") if kind in ("repeatCell", "updateBorders", "setDataValidation") else None
        if g and g.get("sheetId") in grid and "endRowIndex" in g:
            rows, cols = grid[g["sheetId"]]
            g = {**g, "endRowIndex": min(g["endRowIndex"], rows), "endColumnIndex": min(g.get("endColumnIndex", cols), cols)}
            if g["startRowIndex"] >= g["endRowIndex"] or g.get("startColumnIndex", 0) >= g["endColumnIndex"]:
                continue
            r = {kind: {**r[kind], "range": g}}
        out.append(r)
    vals = []
    for e in values:
        try:
            g = layout.a1_to_grid(e["range"])
        except (ValueError, KeyError):
            vals.append(e)
            continue
        rows = grid.get(g["sheetId"], (10 ** 9, 0))[0]
        keep = rows - g["startRowIndex"]
        if keep <= 0:
            continue
        vals.append(e if len(e["values"]) <= keep else {**e, "values": e["values"][:keep]})
    return out, vals


def _grown(grid):
    """이번 묶음이 늘리는 탭 크기(_structure의 appendDimension)를 반영한 크기 — 늘린 줄에 쓰는 값이 잘리지 않게."""
    if not grid or SHEET_ID[layout.STOCKS] not in grid:
        return grid
    rows, cols = next((r, c) for t, _s, r, c, _h in SHEETS if t == layout.STOCKS)
    have = grid[SHEET_ID[layout.STOCKS]]
    return {**grid, SHEET_ID[layout.STOCKS]: (max(have[0], rows), max(have[1], cols))}


def plan(s: State):
    cards.use(cards.find_layout(s.card_col_a))  # [카드] 표는 운영 자리(사용자가 줄 지움)로 — 끝나면 기본으로 되돌림
    try:
        pie_values, pie_reqs = pie_fix(s.pie)
        move_reqs, move_values = stock_sectors.relocate(s.stock_kl, s.stock_protect)  # 옮기는 한 번: 비우고 입력값을 새 자리로
        grid = _grown(s.grid)
        structure, values = _clip(_structure(s) + move_reqs + pie_reqs + _always(s),
                                  move_values + _values(s) + pie_values + dash_list(s.pie), grid)
        return structure, values, _clip(_visual(s), [], grid)[0]
    finally:
        cards.use(cards.DEFAULT)


def _state(sheets, sid: str) -> State:
    meta = sheets.get(spreadsheetId=sid, fields="sheets(properties(sheetId,title,gridProperties(columnCount,rowCount)),charts(chartId,spec,position),conditionalFormats,protectedRanges(protectedRangeId))").execute()
    props = {s["properties"]["sheetId"]: s for s in meta["sheets"]}
    cols = lambda title: props[SHEET_ID[title]]["properties"]["gridProperties"]["columnCount"]
    charts_n = len(props.get(SHEET_ID[NETWORTH], {}).get("charts", []))
    invest_charts = props.get(SHEET_ID[INVEST], {}).get("charts", [])
    invest_n = len(invest_charts)
    every = tuple({"chartId": c["chartId"], "title": c["spec"].get("title", ""), "sheetId": sid, "spec": c["spec"],
                   "row": c.get("position", {}).get("overlayPosition", {}).get("anchorCell", {}).get("rowIndex", 0),
                   "col": c.get("position", {}).get("overlayPosition", {}).get("anchorCell", {}).get("columnIndex", 0),
                   "w": c.get("position", {}).get("overlayPosition", {}).get("widthPixels", 600),
                   "h": c.get("position", {}).get("overlayPosition", {}).get("heightPixels", 371)}
                  for sid, sh in props.items() for c in sh.get("charts", []))
    has_cards = SHEET_ID[layout.CARDS] in props
    has_stocks = SHEET_ID[layout.STOCKS] in props
    txn_meta = sheets.get(spreadsheetId=sid, ranges=[f"{layout.TXN}!I1"], fields="sheets(data(columnMetadata(hiddenByUser)))").execute()
    hidden_txn_i = bool(txn_meta["sheets"][0]["data"][0].get("columnMetadata", [{}])[0].get("hiddenByUser"))
    got = sheets.values().batchGet(spreadsheetId=sid, valueRenderOption="UNFORMATTED_VALUE",
                                   ranges=[f"{SETTINGS}!A2:C60", f"{SETTINGS}!K2:M60" if cols(SETTINGS) >= 13
                                           else f"{SETTINGS}!A1:A1", f"{DASH}!A1:A200", f"{layout.TREND}!A1:A60",
                                           f"{layout.CARDS}!A1:A80" if has_cards else f"{SETTINGS}!A1:A1",
                                           f"{layout.STOCKS}!K1:L150" if has_stocks else f"{SETTINGS}!A1:A1",
                                           f"{SETTINGS}!G3:G20"]).execute()["valueRanges"]
    settings = got[0].get("values", [])
    empty = cols(SETTINGS) < 13 or budgets_empty(got[1].get("values", []))
    pies = [c for c in props[SHEET_ID[DASH]].get("charts", []) if "pieChart" in c["spec"]]
    nets = [c for c in props.get(SHEET_ID[NETWORTH], {}).get("charts", []) if "basicChart" in c["spec"]]
    rowc = lambda title: props[SHEET_ID[title]]["properties"]["gridProperties"]["rowCount"]
    has_status = SHEET_ID[ASSET_STATUS] in props
    dash_charts = props[SHEET_ID[DASH]].get("charts", [])
    # 키워드로 넣는다 — 같은 int 칸(행·열 수)을 순서로 넣다가 서로 바뀌어 자산현황 행이 매번 늘어난 적이 있다
    return State(
        titles={s["properties"]["title"] for s in meta["sheets"]}, settings_cols=cols(SETTINGS), asset_cols=cols(ASSETS),
        networth_charts=charts_n, settings=settings, budgets_empty=empty, pie=pies[0] if pies else None, invest_charts=invest_n,
        networth_chart=nets[0] if nets else None, dash_rows=rowc(DASH),
        dash_chart_titles=frozenset(c["spec"].get("title", "") for c in dash_charts),
        dash_base=breakdown.find_base(got[2].get("values", [])),
        dash_charts=tuple({"chartId": c["chartId"], "spec": c["spec"]} for c in dash_charts),
        type_rules=_type_rules(props), trend_head=_trend_head(got[3].get("values", [])), charts=every,
        status_cols=cols(ASSET_STATUS) if has_status else 0, status_rows=rowc(ASSET_STATUS) if has_status else 0,
        recur_cols=cols(layout.RECUR), txn_cols=cols(layout.TXN),
        card_col_a=tuple(map(tuple, got[4].get("values", []))) if has_cards else (),
        grid={sid_: (p["properties"]["gridProperties"]["rowCount"], p["properties"]["gridProperties"]["columnCount"])
              for sid_, p in props.items()},
        stock_kl=tuple(map(tuple, got[5].get("values", []))) if has_stocks else (),
        stock_protect=tuple(p["protectedRangeId"] for p in props.get(SHEET_ID[layout.STOCKS], {}).get("protectedRanges", [])),
        txn_currency_hidden=hidden_txn_i,
        settings_fx=tuple(r[0] for r in got[6].get("values", []) if r and str(r[0]).strip()),
        rules_seen=frozenset((sid_, v_["condition"]["values"][0].get("userEnteredValue", ""))
                             for sid_, sh in props.items() for cf in sh.get("conditionalFormats", [])
                             for v_ in [cf.get("booleanRule", {})] if v_.get("condition", {}).get("values")))


def _type_rules(props) -> tuple:
    ids = {layout.a1_to_grid(a1)["sheetId"] for a1, _ref in styling.TYPE_RANGES}
    return tuple((sid, i, rule) for sid in sorted(ids)
                 for i, rule in enumerate(props.get(sid, {}).get("conditionalFormats", [])))


def _trend_head(col_a: list) -> int:
    """추이 A열에서 월별 표 머리글('월') 행. 없으면 코드 위치 38."""
    return next((n for n, row in enumerate(col_a, 1) if row and row[0] == "월"), 38)


def backup(creds, sid: str) -> str:
    name = f"우리집 가계부 백업 ({dt.date.today().isoformat()} 부부 확장 적용 전)"
    return build("drive", "v3", credentials=creds).files().copy(fileId=sid, body={"name": name}).execute()["id"]


def main() -> int:
    sid = ID_FILE.read_text().strip()
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    state = _state(sheets, sid)
    if COUPLE not in state.titles:
        print(f"백업 사본: {backup(creds, sid)}")
    structure, values, visual = plan(state)
    sheets.batchUpdate(spreadsheetId=sid, body={"requests": structure}).execute()
    sheets.values().batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED", "data": values}).execute()
    if visual:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": visual}).execute()
    fit_dims.fit(sheets, sid)   # 행·열을 데이터 크기에 맞춘 뒤
    chart_fit.fit(sheets, sid)  # 실제 행 높이·열 너비로: 그래프가 표를 덮지 않게
    print(f"적용: 구조 {len(structure)}개, 값 {len(values)}개 범위, 서식 {len(visual)}개 요청"
          f"{', 예산 이전' if state.budgets_empty else ''}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
