"""시트 구성: 탭 정의, 생성 본문, 초기 데이터, 검증, 서식, 보호."""
import re
from typing import NamedTuple

from names import BRIDE, GROOM, localize as nm

TXN, SETTINGS, ASSETS, DASH, TREND, CAL = "내역", "설정", "자산", "대시보드", "추이", "달력"
SEARCH, RECUR, FAV, SMS, CALC, STATE = "검색", "반복", "즐겨찾기", "문자입력", "계산", "알림기록"
GUIDE = "사용법"
RAW, STOCK, MERITZ = "메리츠원본", nm("주식_신랑"), nm("메리츠_신랑")
RAW2, STOCK2, MERITZ2 = "메리츠원본2", nm("주식_신부"), nm("메리츠_신부")
INVEST, KIS_RAW, INVEST_LOG = "투자", "한투원본", "투자기록"
KIS_HOLD = "한투종목"  # 한투 ISA 종목 목록: 신랑 A:E, 신부 G:K (apps-script/kis.gs KIS_HOLD_COL)
COUPLE, NETWORTH = "부부", "자산기록"
ASSET_STATUS = "자산현황"
FIXED, CARDS, STOCKS, SAVINGS = "고정지출", "카드", "주식투자", "저축·연금"  # 시골쥐 기능 시트
CHECKLIST = "시작하기"  # 처음 쓸 때 할 일 ✓/✗ (사용성 점검 B2)
QUICK = "빠른입력"  # 폰 빠른 입력 폼 (사용성 점검 B1)


class Slot(NamedTuple):
    """메리츠 계좌 슬롯: 앱 Key가 곧 계좌. 0 = 시트 소유자, 1 = 배우자 (apps-script/meritz_logic.gs MERITZ_SLOTS와 같은 순서)."""
    raw: str
    stock: str
    meritz: str
    owner: str

    @property
    def sync(self) -> str:  # 자산 G열 '연동' 값
        return f"메리츠_{self.owner}"


MERITZ_SLOTS = [Slot(RAW, STOCK, MERITZ, GROOM), Slot(RAW2, STOCK2, MERITZ2, BRIDE)]

# (제목, sheetId, 행, 열, 숨김) — 이 순서대로 탭이 생긴다
SHEETS = [
    (GUIDE, 1300, 120, 2, False),
    (CHECKLIST, 2600, 40, 6, False),
    (QUICK, 2700, 40, 4, False),
    (TXN, 100, 5000, 14, False),  # N 적용 환율(입력 시점 환율, 스크립트가 채움)
    (DASH, 400, 190, 14, False),  # 고정비·변동비(95~145) + 분류별 막대그래프(147~)
    (ASSET_STATUS, 2100, 90, 16, False),  # 81~85행 월별 저축률 가로형 표  # K열: 부채 표 대출명 선택지(숨은 보조 열)
    (FIXED, 2200, 60, 16, False),
    (CARDS, 2300, 60, 16, False),
    (STOCKS, 2400, 150, 28, False),
    (SAVINGS, 2500, 60, 16, False),
    (COUPLE, 1700, 60, 11, False),
    (TREND, 500, 80, 26, False),
    (NETWORTH, 1800, 200, 12, False),  # 차트를 F열에 두므로 12열
    (INVEST, 1900, 100, 10, False),
    (CAL, 600, 20, 7, False),
    (SEARCH, 700, 1000, 10, False),
    (STOCK, 1500, 120, 16, False),
    (MERITZ, 1600, 100, 8, False),
    (STOCK2, 1550, 120, 16, False),
    (MERITZ2, 1650, 100, 8, False),
    (FAV, 900, 50, 7, False),
    (RECUR, 800, 50, 14, False),  # J:M 고정지출 상세(전체 금액·금리·만기·비고), N 통화
    (SMS, 1000, 500, 3, False),
    (ASSETS, 300, 50, 12, False),  # J 통화·K 외화 잔액(달러통장 등), L 결제수단 목록(숨은 보조 열)
    (SETTINGS, 200, 60, 13, False),
    (CALC, 1100, 200, 16, True),
    (STATE, 1200, 500, 2, True),
    (RAW, 1400, 110, 14, True),
    (RAW2, 1450, 110, 14, True),
    (KIS_RAW, 1950, 3, 7, True),
    (INVEST_LOG, 2000, 1000, 12, True),
    (KIS_HOLD, 1960, 101, 11, True),
]
SHEET_ID = {title: sid for title, sid, *_ in SHEETS}
# 자주 안 쓰는 보기 탭: 처음엔 숨겨 두고 PC 메뉴 '가계부'로 꺼낸다 (SHEETS의 hidden은 사람이 안 보는 내부 탭)
TUCKED = {TREND, CAL, SEARCH, STOCK, MERITZ, STOCK2, MERITZ2}
# [자산] G열 연동 값 → [투자] 탭 그 계좌의 행 (평가 B열, 마지막 갱신 F열)
INVEST_ACCOUNTS = [(nm("메리츠_신랑"), 7), (nm("한투ISA_신랑"), 8), (nm("메리츠_신부"), 10), (nm("한투ISA_신부"), 11)]

TXN_HEADERS = ["날짜", "사용자", "구분", "카테고리", "소분류", "결제수단", "입금자산", "금액", "통화", "메모"]
RECUR_HEADERS = ["사용", "매월 일자", "사용자", "구분", "카테고리", "결제수단", "금액", "메모", "마지막 생성 월",
                 "전체 금액", "금리", "만기", "비고", "통화"]
FAV_HEADERS = ["추가", "사용자", "구분", "카테고리", "결제수단", "금액", "메모"]
EXPENSE_CATS = ["식비", "카페·간식", "생활용품", "주거·관리비", "통신", "교통", "의료", "쇼핑", "문화·여가", "경조사", "기타"]
INCOME_CATS = ["월급", "부수입", "기타수입"]
FIXED_CATS = {"주거·관리비", "통신"}  # 대분류 기본값: 나머지 지출은 변동비
MAJORS = ["고정비", "변동비"]
RENAME_NOTE = ("카테고리·사용자 이름을 한 칸씩 고치면 과거 내역·반복·즐겨찾기도 자동으로 바뀝니다. "
               "여러 칸을 한꺼번에 붙여넣으면 자동 변경되지 않습니다. "
               "카테고리 행을 지우면 그 카테고리의 과거 지출은 대시보드에서 '미분류'로 집계됩니다.")

USERS, CATS, ASSET_LIST, CURRENCIES = "=설정!$E$2:$E", "=설정!$A$2:$A", "=자산!$A$2:$A", "=설정!$G$2:$G"
PAY_LIST = "=자산!$L$2:$L$50"  # 결제수단 = 자산 중 대출·연금·기타를 뺀 것 (입금자산은 대출 상환 때문에 전부)
FX_CHOICES = ["USD", "JPY", "EUR", "CNY"]
MONTHS, YEARS = "=계산!$A$2:$A", "=계산!$B$2:$B"
# 대시보드·부부 C1 월 이동 드롭다운 — 문구는 apps-script/logic.gs(MONTH_MOVE_HINT·MONTH_MOVES)와 같아야 한다
MONTH_MOVE_HINT = "◀ 월 이동 ▶"
MONTH_MOVES = ["◀ 이전 달", "다음 달 ▶", "이번 달"]
# 추이 C1 연도 이동 드롭다운 — 문구는 apps-script/logic.gs(YEAR_MOVE_HINT·YEAR_MOVES)와 같아야 한다
YEAR_MOVE_HINT = "◀ 연도 이동 ▶"
YEAR_MOVES = ["◀ 이전 해", "다음 해 ▶", "올해"]
TYPES, TYPES_NO_TRF = "=계산!$D$2:$D", "=계산!$E$2:$E"  # 구분 목록: 설정 B열에 새로 적으면 자동 추가
MONTH_FMT = '0000"-"00'


def col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def a1_to_grid(a1: str) -> dict:
    """'내역!A2:J5000' → GridRange. 끝이 열린 범위(A2:A)는 지원하지 않는다."""
    title, ref = a1.split("!")
    m = re.fullmatch(r"([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?", ref)
    if not m:
        raise ValueError(f"지원하지 않는 범위: {a1}")
    c0, r0 = m.group(1), int(m.group(2))
    c1, r1 = m.group(3) or c0, int(m.group(4) or r0)
    return {"sheetId": SHEET_ID[title], "startRowIndex": r0 - 1, "endRowIndex": r1,
            "startColumnIndex": col_index(c0), "endColumnIndex": col_index(c1) + 1}


def v(a1: str, rows: list[list]) -> dict:
    return {"range": a1, "values": rows}


def number_format(a1: str, kind: str, pattern: str) -> dict:
    return {"repeatCell": {"range": a1_to_grid(a1),
                           "cell": {"userEnteredFormat": {"numberFormat": {"type": kind, "pattern": pattern}}},
                           "fields": "userEnteredFormat.numberFormat"}}


def create_body(title: str) -> dict:
    return {
        "properties": {"title": title, "locale": "ko_KR", "timeZone": "Asia/Seoul"},
        "sheets": [
            {"properties": {"sheetId": sid, "title": t, "hidden": hidden or t in TUCKED,
                            "gridProperties": {"rowCount": rows, "columnCount": cols, "frozenRowCount": 1}}}
            for t, sid, rows, cols, hidden in SHEETS
        ],
    }


def seed_values(partner_email: str) -> list[dict]:
    cats = ([[c, "지출", "", "고정비" if c in FIXED_CATS else "변동비"] for c in EXPENSE_CATS]
            + [[c, "수입", "", ""] for c in INCOME_CATS])
    return [
        v(f"{TXN}!A1:J1", [TXN_HEADERS]),
        v(f"{SETTINGS}!A1:B1", [["카테고리(중분류)", "구분"]]),  # C1 = 사람별 예산 합계 수식 (formulas)
        v(f"{SETTINGS}!D1", [["대분류"]]),
        v(f"{SETTINGS}!K1:M1", [[f'={SETTINGS}!E{r}&" 예산"' for r in (2, 3, 4)]]),
        v(f"{SETTINGS}!A2:D{1 + len(cats)}", cats),
        v(f"{SETTINGS}!E1:E4", [["사용자"], [GROOM], [BRIDE], ["공동"]]),
        v(f"{SETTINGS}!G1:G{2 + len(FX_CHOICES)}", [["통화"], ["KRW"], *[[c] for c in FX_CHOICES]]),  # 환율은 H열이 자동
        v(f"{SETTINGS}!I1:J4", [["항목", "값"], ["월 시작일", 1], ["예산 알림", True],
                                ["알림 받을 이메일(쉼표 구분)", partner_email]]),
        v(f"{SETTINGS}!I6", [[RENAME_NOTE]]),
        v(f"{ASSETS}!A1:D4", [["자산명", "종류", "초기 잔액", "월 실적 목표"], ["현금", "현금", 0, ""],
                              ["주거래통장", "통장", 0, ""], ["신용카드1", "카드", 0, ""]]),
        v(f"{ASSETS}!F1", [["적립 카테고리"]]),
        v(f"{ASSETS}!G1", [["연동"]]),
        v(f"{ASSETS}!I1", [["소유자"]]),
        v(f"{ASSETS}!J1:K1", [["통화", "외화 잔액"]]),
        v(f"{RECUR}!A1:N1", [RECUR_HEADERS]),
        v(f"{TXN}!N1", [["적용 환율"]]),
        v(f"{FAV}!A1:G2", [FAV_HEADERS, [False, "공동", "지출", "카페·간식", "신용카드1", 4500, "커피"]]),
        v(f"{SMS}!A1:C1", [["↓ A2부터 카드 문자 붙여넣기", False, "← 체크하면 내역에 추가"]]),
        v(f"{STATE}!A1:B1", [["발송 키", "발송 시각"]]),
    ]


def _rule(ctype: str, *values, strict: bool = False) -> dict:
    cond = {"type": ctype}
    if values:
        cond["values"] = [{"userEnteredValue": str(x)} for x in values]
    return {"condition": cond, "strict": strict, "showCustomUi": True}


def validation_requests() -> list[dict]:
    rules = [
        (f"{TXN}!A2:A5000", _rule("DATE_IS_VALID")),
        (f"{TXN}!B2:B5000", _rule("ONE_OF_RANGE", USERS, strict=True)),
        (f"{TXN}!C2:C5000", _rule("ONE_OF_RANGE", TYPES, strict=True)),
        (f"{TXN}!D2:D5000", _rule("ONE_OF_RANGE", CATS)),
        (f"{TXN}!F2:F5000", _rule("ONE_OF_RANGE", PAY_LIST, strict=True)),
        (f"{TXN}!G2:G5000", _rule("ONE_OF_RANGE", ASSET_LIST, strict=True)),
        (f"{TXN}!H2:H5000", _rule("NUMBER_GREATER", 0)),
        (f"{TXN}!I2:I5000", _rule("ONE_OF_RANGE", CURRENCIES, strict=True)),
        (f"{RECUR}!N2:N50", _rule("ONE_OF_RANGE", CURRENCIES)),
        (f"{SETTINGS}!B2:B60", _rule("ONE_OF_RANGE", TYPES_NO_TRF)),
        (f"{SETTINGS}!D2:D60", _rule("ONE_OF_LIST", *MAJORS)),
        (f"{SETTINGS}!J2", _rule("NUMBER_BETWEEN", 1, 28, strict=True)),
        (f"{SETTINGS}!J3", _rule("BOOLEAN")),
        (f"{ASSETS}!A2:A50", {**_rule("CUSTOM_FORMULA", "=COUNTIF($A$2:$A$50,A2)=1"),
                              "inputMessage": nm("자산명은 겹치지 않게 — 같은 카드가 두 장이면 하나카드_신랑처럼 이름_소유자로")}),
        (f"{ASSETS}!B2:B50", _rule("ONE_OF_LIST", "통장", "계좌", "카드", "현금", "청약", "주식", "대출", "연금", "기타")),
        (f"{ASSETS}!F2:F50", _rule("ONE_OF_RANGE", CATS)),
        (f"{ASSETS}!G2:G50", _rule("ONE_OF_LIST", *[n for n, _r in INVEST_ACCOUNTS])),
        (f"{ASSETS}!I2:I50", _rule("ONE_OF_RANGE", USERS)),
        (f"{ASSETS}!J2:J50", _rule("ONE_OF_LIST", *FX_CHOICES)),
        (f"{ASSETS}!K2:K50", _rule("NUMBER_GREATER_THAN_EQ", 0)),
        (f"{SETTINGS}!K2:M60", _rule("NUMBER_GREATER_THAN_EQ", 0)),
        (f"{RECUR}!A2:A50", _rule("BOOLEAN")),
        (f"{RECUR}!B2:B50", _rule("NUMBER_BETWEEN", 1, 31, strict=True)),
        (f"{RECUR}!C2:C50", _rule("ONE_OF_RANGE", USERS)),
        (f"{RECUR}!D2:D50", _rule("ONE_OF_RANGE", TYPES_NO_TRF)),
        (f"{RECUR}!E2:E50", _rule("ONE_OF_RANGE", CATS)),
        (f"{RECUR}!F2:F50", _rule("ONE_OF_RANGE", PAY_LIST)),
        (f"{RECUR}!G2:G50", _rule("NUMBER_GREATER", 0)),
        (f"{RECUR}!J2:J50", _rule("NUMBER_GREATER_THAN_EQ", 0)),
        (f"{RECUR}!K2:K50", _rule("NUMBER_BETWEEN", 0, 1)),  # 금리 3%는 3%·0.03으로 (3이면 300%)
        (f"{FAV}!A2:A50", _rule("BOOLEAN")),
        (f"{FAV}!B2:B50", _rule("ONE_OF_RANGE", USERS)),
        (f"{FAV}!C2:C50", _rule("ONE_OF_RANGE", TYPES_NO_TRF)),
        (f"{FAV}!D2:D50", _rule("ONE_OF_RANGE", CATS)),
        (f"{FAV}!E2:E50", _rule("ONE_OF_RANGE", PAY_LIST)),
        (f"{FAV}!F2:F50", _rule("NUMBER_GREATER", 0)),
        (f"{SMS}!B1", _rule("BOOLEAN")),
        (f"{DASH}!B1", _rule("ONE_OF_RANGE", MONTHS)),
        (f"{DASH}!C1", _rule("ONE_OF_LIST", *MONTH_MOVES)),
        (f"{CAL}!B1", _rule("ONE_OF_RANGE", MONTHS)),
        (f"{COUPLE}!B1", _rule("ONE_OF_RANGE", MONTHS)),
        (f"{COUPLE}!C1", _rule("ONE_OF_LIST", *MONTH_MOVES)),
        (f"{TREND}!B1", _rule("ONE_OF_RANGE", YEARS)),
        (f"{TREND}!C1", _rule("ONE_OF_LIST", *YEAR_MOVES)),
        (f"{SEARCH}!B2:B3", _rule("DATE_IS_VALID")),
        (f"{SEARCH}!B4", _rule("ONE_OF_RANGE", USERS)),
    ]
    return [{"setDataValidation": {"range": a1_to_grid(a1), "rule": rule}} for a1, rule in rules]


def format_requests() -> list[dict]:
    fmts = [
        (f"{TXN}!A2:A5000", "DATE", "yyyy-mm-dd"),
        (f"{TXN}!H2:H5000", "NUMBER", "#,##0"),
        (f"{TXN}!K2:K5000", "NUMBER", "#,##0"),
        (f"{TXN}!L2:L5000", "NUMBER", MONTH_FMT),
        (f"{TXN}!N2:N5000", "NUMBER", "#,##0.00"),
        (f"{SETTINGS}!C2:C60", "NUMBER", "#,##0"),
        (f"{SETTINGS}!K2:M60", "NUMBER", "#,##0"),
        (f"{NETWORTH}!A2:A200", "NUMBER", MONTH_FMT),
        (f"{NETWORTH}!B2:D200", "NUMBER", "#,##0"),
        (f"{SETTINGS}!H2:H20", "NUMBER", "#,##0.00"),
        (f"{ASSETS}!C2:E50", "NUMBER", "#,##0"),
        (f"{ASSETS}!K2:K50", "NUMBER", "#,##0.00"),
        (f"{RECUR}!G2:G50", "NUMBER", "#,##0"),
        (f"{RECUR}!I2:I50", "NUMBER", MONTH_FMT),
        (f"{RECUR}!J2:J50", "NUMBER", "#,##0"),
        (f"{RECUR}!K2:K50", "PERCENT", "0.00%"),
        (f"{RECUR}!L2:L50", "DATE", "yyyy-mm"),
        (f"{FAV}!F2:F50", "NUMBER", "#,##0"),
        (f"{CALC}!A2:A200", "NUMBER", MONTH_FMT),
    ]
    bold = [{"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                                      "startColumnIndex": 0, "endColumnIndex": cols},
                            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                            "fields": "userEnteredFormat.textFormat.bold"}}
            for _, sid, _, cols, _ in SHEETS]
    return [number_format(a1, kind, pattern) for a1, kind, pattern in fmts] + bold


def _protect(grid: dict, unprotected: list[dict]) -> dict:
    pr = {"range": grid, "warningOnly": True, "description": "수식 영역 — 직접 수정하지 마세요"}
    if unprotected:
        pr["unprotectedRanges"] = unprotected
    return {"addProtectedRange": {"protectedRange": pr}}


def protection_requests() -> list[dict]:
    whole = [(DASH, ["B1"]), (TREND, ["B1"]), (CAL, ["B1"]), (CALC, []), (COUPLE, ["B1"]), (NETWORTH, []),
             (INVEST, ["H1", "H7:I8", "H10:I11"]), (KIS_RAW, []), (INVEST_LOG, []), (KIS_HOLD, []),
             (ASSET_STATUS, ["A36:A45", "D36:G45", "I36:I45"])]
    whole += [(t, free) for s in MERITZ_SLOTS for t, free in ((s.stock, ["H1"]), (s.meritz, []), (s.raw, []))]
    parts = [f"{TXN}!K1:M5000", f"{SETTINGS}!H1:H20", f"{SETTINGS}!C1:C60", f"{SETTINGS}!K1:M1",
             f"{ASSETS}!E1:E50", f"{ASSETS}!H1:H50", f"{ASSETS}!L1:L50",
             f"{SEARCH}!A6:J1000", f"{SEARCH}!E1:E2"]
    reqs = [_protect({"sheetId": SHEET_ID[t]}, [a1_to_grid(f"{t}!{c}") for c in free]) for t, free in whole]
    return reqs + [_protect(a1_to_grid(a1), []) for a1 in parts]
