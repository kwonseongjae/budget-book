"""[증권종목] 탭: 증권사 앱의 보유종목 표를 붙여넣어 계좌별 종목을 반영 (다증권사 A단계).

B2 계좌 선택, B3 체크(반영), C3 결과(스크립트), A6:T205 붙여넣기 칸(넓은 표도 받도록 20열).
반영된 종목의 정규 표는 숨김 탭 [증권종목표]에 스크립트가 쓴다 — 붙여넣기 칸 옆에 두면 열이 많은 표가 덮어쓰기 때문.
사용자 칸과 스크립트가 쓰는 칸은 values()로 쓰지 않는다.
"""
from layout import BROKER_POS as S, POS_PASTE, POS_TABLE_TAB, a1_to_grid, number_format, v

TITLE = f"{S}!A1"
MODES = ["추가·갱신 (기본)", "전체 교체"]   # 비워 두면 추가·갱신 (apps-script importPositions)
HEADERS = ["계좌", "코드", "종목명", "수량", "매입금액", "평가금액", "통화"]

SECTIONS: list = []
HEADS: list = []
TOTALS: list = []
SUBTOTALS: list = []
BODIES = [f"{S}!A2:B4"]
INPUTS = [f"{S}!B2:B4", f"{S}!{POS_PASTE}"]
RUNS = [("A", 2, 4, "LC")]
WIDTHS = [190, 270, 110, 110, 110, 110] + [90] * 14
HIDDEN: list = []


def values() -> list[dict]:
    return [v(TITLE, [["증권 종목 붙여넣기"]]),
            v(f"{S}!A2:A4", [["계좌"], ["반영 (체크)"], ["반영 방식"]]),
            v(f"{S}!A5", [["↓ 아래 A6부터 증권사 앱·홈페이지의 보유종목 표를 머리글부터 붙여넣고, 위 B3을 체크하세요. 금액은 원화로. 방식(B4): 기본은 기존 종목에 더하고 같은 종목은 갱신, 전체 교체는 이 계좌를 붙여넣은 표로 바꿉니다."]]),
            v(f"{S}!H4:N5", [[""] * 7, [""] * 7]),            # 예전에 여기 있던 정규 표 머리글 정리 (이제 [증권종목표]에 있다)
            v(f"{POS_TABLE_TAB}!A1:G1", [HEADERS])]


def _rule(a1: str, ctype: str, *values: str) -> dict:
    cond = {"type": ctype, **({"values": [{"userEnteredValue": x} for x in values]} if values else {})}
    return {"setDataValidation": {"range": a1_to_grid(f"{S}!{a1}"), "rule": {"condition": cond, "strict": False, "showCustomUi": True}}}


def formats() -> list[dict]:
    return [number_format(f"{POS_TABLE_TAB}!D2:D1001", "NUMBER", "#,##0.####"), number_format(f"{POS_TABLE_TAB}!E2:F1001", "NUMBER", "#,##0"),
            _rule("B2", "ONE_OF_RANGE", "=증권계좌!$A$5:$A$14"), _rule("B3", "BOOLEAN"),
            _rule("B4", "ONE_OF_LIST", *MODES)]


def chart_requests() -> list[dict]:
    return []
