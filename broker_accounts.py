"""[증권계좌] 탭: 증권사와 상관없이 계좌를 적는 목록 (다증권사 A단계).

이름을 적으면 스크립트(positions.gs syncAccountTab)가 '계좌_이름' 탭을 자동으로 만든다. 종목은 [증권종목]에 붙여넣는다.
F(마지막 붙여넣기)는 스크립트가 쓰는 칸이라 값으로 쓰지 않고, G(상태)는 수식이다.
"""
from layout import ACCT_NAMES, BROKER_ACCTS as S, USERS, a1_to_grid, number_format, v

TITLE = f"{S}!A1"
HEAD = 4
FIRST, LAST = 5, 14
HEADERS = ["이름", "소유자", "증권사", "방식", "예수금", "마지막 붙여넣기", "상태"]

SECTIONS: list = []
HEADS = [f"{S}!A{HEAD}:G{HEAD}"]
TOTALS: list = []
SUBTOTALS: list = []
BODIES = [f"{S}!A{FIRST}:G{LAST}"]
INPUTS = [f"{S}!A{FIRST}:E{LAST}"]
RUNS = [("A", FIRST, LAST, "LCLCRCC")]
WIDTHS = [180, 90, 110, 90, 110, 130, 110]
HIDDEN: list = []

# 탭 이름이 되므로 금지 문자 [ ] * ? : / \ 와 중복·90자 초과를 입력 단계에서 막는다 (apps-script validAccountName과 같은 규칙)
NAME_RULE = (f'=OR(A{FIRST}="",AND(COUNTIF($A${FIRST}:$A${LAST},A{FIRST})=1,LEN(A{FIRST})<=90,'
             f'NOT(REGEXMATCH(A{FIRST},"[\\[\\]*?:/\\\\]"))))')


def values() -> list[dict]:
    status = (f'=ARRAYFORMULA(IF(A{FIRST}:A{LAST}="","",IF(F{FIRST}:F{LAST}="","붙여넣기 전",'
              f'IF(TODAY()-F{FIRST}:F{LAST}>14,"오래됨","정상"))))')
    return [v(TITLE, [["증권 계좌"]]),
            v(f"{S}!A2", [["증권사 이름과 상관없이 계좌를 적으세요. 이름을 적으면 '계좌_이름' 탭이 자동으로 만들어집니다. 종목은 [증권종목]에 붙여넣으세요."]]),
            v(f"{S}!A{HEAD}:G{HEAD}", [HEADERS]),
            v(f"{S}!G{FIRST}", [[status]]),
            v(f"{S}!A{LAST + 2}", [["방식은 지금 '붙여넣기'만 쓸 수 있습니다. 예수금은 증권사 앱의 현금(예수금)을 직접 적으세요."]])]


def _rule(a1: str, ctype: str, *values: str, strict: bool = False) -> dict:
    cond = {"type": ctype, **({"values": [{"userEnteredValue": x} for x in values]} if values else {})}
    return {"setDataValidation": {"range": a1_to_grid(f"{S}!{a1}"), "rule": {"condition": cond, "strict": strict, "showCustomUi": True}}}


def formats() -> list[dict]:
    return [number_format(f"{S}!E{FIRST}:E{LAST}", "NUMBER", "#,##0"), number_format(f"{S}!F{FIRST}:F{LAST}", "DATE", "yyyy-mm-dd"),
            _rule(ACCT_NAMES, "CUSTOM_FORMULA", NAME_RULE, strict=True),
            _rule(f"B{FIRST}:B{LAST}", "ONE_OF_RANGE", USERS), _rule(f"D{FIRST}:D{LAST}", "ONE_OF_LIST", "붙여넣기", strict=True),
            _rule(f"E{FIRST}:E{LAST}", "NUMBER_GREATER_THAN_EQ", "0")]


def chart_requests() -> list[dict]:
    return []
