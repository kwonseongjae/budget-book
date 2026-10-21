"""[증권종목] 탭: 증권사 앱의 보유종목 표를 붙여넣어 계좌별 종목을 반영 (다증권사 A단계).

B2 계좌 선택, B3 체크(반영), C3 결과(스크립트), A6:F205 붙여넣기 칸, H5:N 정규 종목 표(스크립트가 씀).
사용자 칸과 스크립트가 쓰는 칸은 values()로 쓰지 않는다.
"""
from layout import ACCT_NAMES, BROKER_POS as S, POS_PASTE, a1_to_grid, number_format, v

TITLE = f"{S}!A1"
HEADERS = ["계좌", "코드", "종목명", "수량", "매입금액", "평가금액", "통화"]

SECTIONS = [f"{S}!H4"]
HEADS = [f"{S}!H5:N5"]
TOTALS: list = []
SUBTOTALS: list = []
BODIES = [f"{S}!A2:B3", f"{S}!H6:N205"]
INPUTS = [f"{S}!B2:B3", f"{S}!{POS_PASTE}"]
RUNS = [("A", 2, 3, "LC"), ("H", 6, 205, "LLLRRRC")]
WIDTHS = [190, 270, 110, 110, 110, 110, 20, 140, 90, 200, 80, 120, 120, 60]
HIDDEN: list = []


def values() -> list[dict]:
    return [v(TITLE, [["증권 종목 붙여넣기"]]),
            v(f"{S}!A2:A3", [["계좌"], ["반영 (체크)"]]),
            v(f"{S}!A5", [["↓ 아래 A6부터 증권사 앱·홈페이지의 보유종목 표를 머리글부터 붙여넣고, 위 B3을 체크하세요."]]),
            v(f"{S}!H4", [["반영된 종목 (자동)"]]),
            v(f"{S}!H5:N5", [HEADERS])]


def _rule(a1: str, ctype: str, *values: str) -> dict:
    cond = {"type": ctype, **({"values": [{"userEnteredValue": x} for x in values]} if values else {})}
    return {"setDataValidation": {"range": a1_to_grid(f"{S}!{a1}"), "rule": {"condition": cond, "strict": False, "showCustomUi": True}}}


def formats() -> list[dict]:
    return [number_format(f"{S}!K6:K1005", "NUMBER", "#,##0.####"), number_format(f"{S}!L6:M1005", "NUMBER", "#,##0"),
            _rule("B2", "ONE_OF_RANGE", f"=증권계좌!$A$5:$A$14"), _rule("B3", "BOOLEAN")]


def chart_requests() -> list[dict]:
    return []
