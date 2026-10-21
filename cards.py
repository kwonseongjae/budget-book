"""[카드] 탭 "카드 및 포인트": 보유 카드(혜택·연회비·실적·용도·한도·유효기간·결제일)와 포인트·마일리지 (시골쥐 '카드 및 포인트').

카드 표 첫 열은 [자산]의 카드 중에서 고르는 드롭다운 → 소유자·이번 달 사용액·실적 목표는 이름으로 찾아 채운다
(자동 목록 옆에 수동 칸을 두면 원천 순서가 바뀔 때 줄이 어긋나므로). 포인트 표는 모두 직접 입력.
"""
from typing import NamedTuple

from formulas import CARD_LABELS, OUTFLOW, card_owner, card_target, card_usage
from layout import CALC, CARDS as S, PAY_LIST, a1_to_grid, number_format, v
from styling import RED_TEXT

HELPER = "P"                 # 숨은 보조 열: [자산] 카드 이름 목록
TITLE = f"{S}!A1"
BADGE = ("M1", "M2")
P_TITLE_TEXT = "포인트·마일리지"


class Layout(NamedTuple):
    """카드 표 첫·끝 줄, 포인트 표 머리글·첫·끝 줄 (합계 = 끝 + 1)."""
    first: int
    last: int
    p_head: int
    p_first: int
    p_last: int


DEFAULT = Layout(5, 24, 31, 32, 46)  # 새로 만들 때: 카드 20줄, 포인트 15줄


def find_layout(col_a) -> Layout:
    """운영 [카드] A열에서 '포인트·마일리지' 제목과 그 아래 '합계'를 찾아 표 자리를 정한다.
    사용자가 빈 줄을 지워 표를 줄여도 그 자리에 쓴다 (2026-10-14 실제로 줄임). 못 찾으면 기본 자리."""
    col = [str(r[0]) if r else "" for r in col_a]
    if P_TITLE_TEXT not in col:
        return DEFAULT
    t = col.index(P_TITLE_TEXT) + 1                       # 제목 행 (1부터)
    total = next((i + 1 for i in range(t, len(col)) if col[i] == "합계"), t + 17)
    return Layout(5, t - 2, t + 1, t + 2, total - 1)


def use(layout: Layout) -> None:
    """이 모듈의 표 자리(머리글·몸통·입력칸·정렬)를 layout으로 다시 계산한다. migrate가 운영 자리로 바꿨다가 되돌린다."""
    global FIRST, LAST, P_HEAD, P_FIRST, P_LAST, SECTIONS, HEADS, TOTALS, SUBTOTALS, BODIES, INPUTS, RUNS
    FIRST, LAST, P_HEAD, P_FIRST, P_LAST = layout
    SECTIONS = [f"{S}!A3", f"{S}!O3", f"{S}!A{P_HEAD - 1}"]
    HEADS = [f"{S}!A4:M4", f"{S}!O4", f"{S}!A{P_HEAD}:G{P_HEAD}"]
    TOTALS = [f"{S}!A{P_LAST + 1}:G{P_LAST + 1}"]
    SUBTOTALS = []
    BODIES = [f"{S}!A{FIRST}:M{LAST}", f"{S}!O{FIRST}:O{LAST}", f"{S}!A{P_FIRST}:G{P_LAST}"]
    INPUTS = [f"{S}!A{FIRST}:A{LAST}", f"{S}!C{FIRST}:J{LAST}", f"{S}!A{P_FIRST}:G{P_LAST}"]
    RUNS = [("A", FIRST, LAST, "CCCLRCRCCCRRR"), ("O", FIRST, LAST, "C"), ("A", P_FIRST, P_LAST, "CLLRCCL")]


use(DEFAULT)


def values() -> list[dict]:
    a = f"A{FIRST}:A{LAST}"
    used = f'=MAP({a},LAMBDA(x,IF(x="","",{card_usage("x", f"{CALC}!$C$2", OUTFLOW)})))'  # 소유자 붙은 카드는 그 사람 것만
    rate = f'=MAP(K{FIRST}:K{LAST},L{FIRST}:L{LAST},LAMBDA(k,l,IF(OR(k="",N(l)=0),"",k/l)))'
    h = f"{HELPER}{FIRST}:{HELPER}{LAST + 10}"
    t = P_LAST + 1
    return [v(TITLE, [["카드 및 포인트"]]),
            v(f"{S}!A3", [["보유 카드 목록 — 카드는 [자산]에서 고르고 분홍 칸을 채우세요"]]),
            v(f"{S}!A4:M4", [["카드", "소유자", "카드사", "혜택", "연회비", "용도", "한도", "유효기간", "결제일",
                              "결제 계좌", "이번 달 사용액", "실적 목표", "실적 달성률"]]),
            v(f"{S}!B{FIRST}", [[f'=MAP({a},LAMBDA(x,IF(x="","",{card_owner("x")})))']]), v(f"{S}!K{FIRST}", [[used]]),
            v(f"{S}!L{FIRST}", [[f'=MAP({a},LAMBDA(x,IF(x="","",{card_target("x")})))']]),
            v(f"{S}!M{FIRST}", [[rate]]),
            v(f"{S}!{HELPER}4", [["카드 목록"]]),
            v(f"{S}!{HELPER}{FIRST}", [[CARD_LABELS]]),
            v(f"{S}!O3", [["표에 없는 카드"]]), v(f"{S}!O4", [["[자산]에만 있는 카드"]]),
            v(f"{S}!O{FIRST}", [[f'=IFERROR(FILTER({h},{h}<>"",ISNA(MATCH({h},{a},0))),"모두 등록됨")']]),
            v(f"{S}!A{P_HEAD - 1}", [[P_TITLE_TEXT]]),
            v(f"{S}!A{P_HEAD}:G{P_HEAD}", [["구분", "이름", "혜택", "잔액", "용도", "유효기간", "비고"]]),
            v(f"{S}!A{t}:D{t}", [["합계", "", "", f"=SUM(D{P_FIRST}:D{P_LAST})"]])]


def _soon(a1: str, col: str, first: int) -> dict:
    """유효기간이 2달 안(또는 지남)이면 빨간 굵은 글씨. 'yyyy-mm' 글자·날짜 모두."""
    d = f'IF(ISTEXT(${col}{first}),DATEVALUE(${col}{first}&"-01"),${col}{first})'
    cond = {"type": "CUSTOM_FORMULA", "values": [{"userEnteredValue": f'=AND(${col}{first}<>"",IFERROR({d}<=EDATE(TODAY(),2),FALSE))'}]}
    return {"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [a1_to_grid(a1)], "booleanRule": {
        "condition": cond, "format": {"textFormat": {"foregroundColor": RED_TEXT, "bold": True}}}}}}


def formats() -> list[dict]:
    t = P_LAST + 1
    fmts = [(f"{S}!E{FIRST}:E{LAST}", "NUMBER", "#,##0"), (f"{S}!G{FIRST}:G{LAST}", "NUMBER", "#,##0"),
            (f"{S}!H{FIRST}:H{LAST}", "DATE", "yyyy-mm"), (f"{S}!I{FIRST}:I{LAST}", "NUMBER", '0"일"'),
            (f"{S}!K{FIRST}:L{LAST}", "NUMBER", "#,##0"), (f"{S}!M{FIRST}:M{LAST}", "PERCENT", "0%"),
            (f"{S}!D{P_FIRST}:D{t}", "NUMBER", "#,##0"), (f"{S}!F{P_FIRST}:F{P_LAST}", "DATE", "yyyy-mm")]
    rule = lambda vals: {"condition": {"type": "ONE_OF_LIST", "values": [{"userEnteredValue": x} for x in vals]},
                         "strict": False, "showCustomUi": True}
    pick = [{"setDataValidation": {"range": a1_to_grid(f"{S}!A{FIRST}:A{LAST}"), "rule": {
                "condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": f"={S}!${HELPER}${FIRST}:${HELPER}${LAST + 10}"}]},
                "strict": False, "showCustomUi": True}}},
            {"setDataValidation": {"range": a1_to_grid(f"{S}!J{FIRST}:J{LAST}"),  # 결제 계좌 = [자산] 이름 (카드 대금 이체가 이 이름으로 들어간다)
                                   "rule": {"condition": {"type": "ONE_OF_RANGE", "values": [{"userEnteredValue": PAY_LIST}]},
                                            "strict": False, "showCustomUi": True}}},
            {"setDataValidation": {"range": a1_to_grid(f"{S}!A{P_FIRST}:A{P_LAST}"),
                                   "rule": rule(["포인트", "마일리지", "페이머니", "기타"])}}]
    wrap = {"repeatCell": {"range": a1_to_grid(f"{S}!D{FIRST}:D{LAST}"), "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                           "fields": "userEnteredFormat.wrapStrategy"}}
    return ([number_format(a1, k, p) for a1, k, p in fmts] + pick + [wrap]
            + [_soon(f"{S}!H{FIRST}:H{LAST}", "H", FIRST), _soon(f"{S}!F{P_FIRST}:F{P_LAST}", "F", P_FIRST)])


def chart_requests() -> list[dict]:
    return []


WIDTHS = [120, 70, 90, 260, 80, 110, 90, 80, 60, 110, 100, 100, 80, 20, 130, 100]
HIDDEN = [15]  # P: 카드 목록 보조 열
