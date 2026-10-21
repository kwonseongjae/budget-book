"""[빠른입력] 탭: 폰에서 [내역] 맨 아래 줄을 찾지 않고 값만 고르고 '추가'를 체크 (2026-10-16 사용성 점검 B1).

세로 폼(왼쪽 이름, 오른쪽 입력칸)이라 폰 화면에 한 줄씩 들어간다. 체크하면 스크립트(addQuick)가 내역에 한 줄을 넣고
날짜·카테고리·금액·통화·입금자산·메모는 비우며, 사용자·구분·결제수단은 다음 입력을 위해 남긴다 → 그 칸은 값으로 쓰지 않는다.
카테고리 목록은 고른 구분에 따라 숨은 D열에 만들어 드롭다운이 읽는다(스크립트 없이 바로 바뀜).
"""
from layout import (ASSET_LIST, CURRENCIES, PAY_LIST, QUICK as S, TYPES, USERS, a1_to_grid, number_format, v)

TITLE = f"{S}!A1"
FIELDS = ["날짜 (비우면 오늘)", "사용자", "구분", "카테고리", "금액", "통화 (비우면 원화)", "결제수단", "입금자산 (이체만)", "메모", "추가"]  # 4~13행
CAT_FIRST, CAT_LAST = 5, 60   # 숨은 D열: 고른 구분의 카테고리 목록

SECTIONS = [f"{S}!A16", f"{S}!A20"]
HEADS: list = []
TOTALS: list = []
SUBTOTALS: list = []
BODIES = [f"{S}!A4:B14", f"{S}!A17:B18", f"{S}!A21:B25"]
INPUTS = [f"{S}!B4:B13"]
RUNS = [("A", 4, 14, "LC"), ("A", 17, 18, "LR"), ("A", 21, 25, "L")]
WIDTHS = [190, 270, 20, 150]
HIDDEN = [3]


def _recent() -> str:
    """최근 입력 5건: 날짜 · 카테고리 · 원화금액 · 메모 (가장 최근 줄부터). 줄 번호 열은 SEQUENCE(ROWS(..))로 — 시트가 5000행보다 짧아도
    범위와 크기가 같다(ROW(범위)나 고정 4999는 #N/A)."""
    cols = ",".join(f"내역!${c}$2:${c}$5000" for c in "ABDJK")
    return (f'=IFERROR(LET(r,FILTER(HSTACK(SEQUENCE(ROWS(내역!$A$2:$A$5000),1,2),{cols}),내역!$A$2:$A$5000<>""),'
            f'x,ARRAY_CONSTRAIN(SORT(r,1,FALSE),5,6),'
            f'ARRAYFORMULA(TEXT(INDEX(x,,2),"m/d")&" · "&INDEX(x,,4)&" · "&TEXT(INDEX(x,,6),"#,##0")&"원 · "&INDEX(x,,5)'
            f'&" ("&INDEX(x,,3)&")")),"")')  # x 열: 1 줄번호 2 날짜 3 사용자 4 카테고리 5 메모 6 원화금액


def values() -> list[dict]:
    out = [v(TITLE, [["빠른 입력"]]),
           v(f"{S}!A2", [["값을 고르고 맨 아래 '추가'를 체크하면 내역에 들어갑니다. 사용자·구분·결제수단은 남아 다음 입력이 빨라요."]])]
    out += [v(f"{S}!A{r}", [[label]]) for r, label in enumerate(FIELDS, 4)]
    out += [v(f"{S}!A14", [["결과"]]),
            v(f"{S}!A16", [["오늘 · 이번 달"]]),
            v(f"{S}!A17:B17", [["오늘 지출", '=SUMIFS(내역!$K$2:$K$5000,내역!$A$2:$A$5000,TODAY(),내역!$C$2:$C$5000,"지출")']]),
            v(f"{S}!A18:B18", [["이번 달 지출", '=SUMIFS(내역!$K$2:$K$5000,내역!$L$2:$L$5000,계산!$C$2,내역!$C$2:$C$5000,"지출")']]),
            v(f"{S}!A20", [["최근 입력 5건"]]),
            v(f"{S}!A21", [[_recent()]]),
            v(f"{S}!D4", [["카테고리 목록"]]),
            v(f"{S}!D{CAT_FIRST}", [[f'=IFERROR(FILTER(설정!$A$2:$A$60,설정!$B$2:$B$60=IF($B$6="","지출",$B$6)),"")']])]
    return out


def _rule(a1: str, ctype: str, *values: str) -> dict:
    cond = {"type": ctype, **({"values": [{"userEnteredValue": x} for x in values]} if values else {})}
    return {"setDataValidation": {"range": a1_to_grid(f"{S}!{a1}"), "rule": {"condition": cond, "strict": False, "showCustomUi": True}}}


def formats() -> list[dict]:
    """번호 서식 + 드롭다운 (검증은 추가형 아님 — 같은 규칙 덮어쓰기라 반복 안전하지만 탭을 만들 때 한 번만 쓴다)."""
    return ([number_format(f"{S}!B4", "DATE", "yyyy-mm-dd"), number_format(f"{S}!B8", "NUMBER", "#,##0"),
             number_format(f"{S}!B17:B18", "NUMBER", "#,##0")]
            + [_rule("B4", "DATE_IS_VALID"), _rule("B5", "ONE_OF_RANGE", USERS), _rule("B6", "ONE_OF_RANGE", TYPES),
               _rule("B7", "ONE_OF_RANGE", f"=$D${CAT_FIRST}:$D${CAT_LAST}"), _rule("B9", "ONE_OF_RANGE", CURRENCIES),
               _rule("B10", "ONE_OF_RANGE", PAY_LIST), _rule("B11", "ONE_OF_RANGE", ASSET_LIST), _rule("B13", "BOOLEAN")])


def chart_requests() -> list[dict]:
    return []
