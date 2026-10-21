"""[시작하기] 탭: 처음 쓸 때 해야 할 일을 ✓/✗로 한눈에 (2026-10-16 사용성 점검 B2).

항목마다 시트 값으로 상태를 계산한다 — 필수는 ✗가 없어질 때까지, 선택은 필요할 때. 바로가기는 그 탭으로 이동.
숫자 세는 식은 대시보드 '확인 필요' 줄과 같은 formulas 함수를 쓴다(두 곳이 어긋나지 않게).
"""
from formulas import bad_rows_expr, blank_recurring_expr, missing_payments_count_expr, negative_accounts_expr
from layout import ASSET_STATUS, CHECKLIST as S, SHEET_ID, a1_to_grid, v

TITLE = f"{S}!A1"
HEAD = 4
FIRST = 5

_N = negative_accounts_expr()
_B = bad_rows_expr()
_R = blank_recurring_expr()
_M = missing_payments_count_expr()
_kind = lambda *ks: "+".join(f'COUNTIF(자산!$B$2:$B$50,"{k}")' for k in ks)
_owner_blank = 'SUMPRODUCT((자산!$A$2:$A$50<>"")*(자산!$I$2:$I$50=""))'
_mail = '설정!$J$4'

# (항목, 구분, 완료 조건, 지금 상태, 하는 법, 바로가기 탭)
ITEMS = [
    ("두 사람 이름", "필수", 'COUNTA(설정!$E$2:$E$3)=2', '설정!$E$2&" · "&설정!$E$3',
     "[설정] E열에 두 사람 이름을 적으세요. E4 '공동'은 그대로 둡니다.", "설정"),
    ("통장·카드 등록", "필수", f'AND({_kind("계좌", "통장")}>0,{_kind("카드")}>0)',
     f'"통장·계좌 "&({_kind("계좌", "통장")})&"개 · 카드 "&({_kind("카드")})&"개"',
     "[자산]에 쓰는 통장·카드를 적고 종류를 고르세요. 카드 이름에 카드사 이름을 넣으면 문자 입력이 연결됩니다.", "자산"),
    ("자산 소유자 지정", "필수", f'{_owner_blank}=0', f'"소유자가 빈 자산 "&{_owner_blank}&"개"',
     "[자산] I열에서 누구 것인지 고르세요(함께 쓰면 '공동'). 공동 지출 정산이 이 칸으로 계산됩니다.", "자산"),
    ("통장 초기 잔액", "필수", f'{_N}=0', f'"잔액이 음수인 통장·현금 "&{_N}&"개"',
     "[자산] 초기 잔액에 지금 통장·현금 잔액을 넣으세요. 안 넣으면 순자산이 실제보다 작게 나옵니다.", "자산"),
    ("결제수단 이름 일치", "필수", f'{_M}=0', f'"[자산]에 없는 결제수단 "&{_M}&"개"',
     "[내역]·[반복]·[즐겨찾기]에 쓴 결제수단이 [자산] 이름과 같아야 잔액에 반영됩니다. 빨간 칸을 확인하세요.", "자산"),
    ("이번 달 내역 입력", "필수", 'COUNTIF(내역!$L$2:$L$5000,계산!$C$2)>0', '"이번 달 "&COUNTIF(내역!$L$2:$L$5000,계산!$C$2)&"건"',
     "[내역]에 적거나 [문자입력]에 카드 문자를 붙여넣으세요.", "내역"),
    ("입력 오류 없음", "필수", f'{_B}=0', f'"빨간 줄 "&{_B}&"건"',
     "[내역]의 빨간 줄(날짜·금액 형식, 사용자 빈칸)을 고치세요. 고치기 전에는 대시보드 합계에서 빠집니다.", "내역"),
    ("자동 갱신 켜짐", "필수", 'IFERROR(TODAY()-계산!$C$5<=1,FALSE)',
     'IF(ISNUMBER(계산!$C$5),"마지막 자동 갱신 "&TEXT(계산!$C$5,"yyyy-mm-dd"),"기록 없음")',
     "매일 아침 6시에 반복 입력·환율·카드 대금·순자산·투자 기록이 자동으로 돕니다. 어제보다 오래됐으면 자동 실행이 멈춘 것이니 알려 주세요.", "자산기록"),
    ("고정 지출 반복 등록", "선택", 'COUNTIF(반복!$A$2:$A$50,TRUE)>=1', '"사용 중 "&COUNTIF(반복!$A$2:$A$50,TRUE)&"개"',
     "[반복]에 월급·월세·보험을 한 번 등록하면 매달 자동 입력됩니다.", "반복"),
    ("반복 금액 채우기", "필수", f'{_R}=0', f'"금액이 빈 반복 "&{_R}&"개"',
     "[반복]의 빨간 금액 칸에 금액을 적으세요. 금액이 없으면 자동으로 만들 수 없습니다(관리비처럼 달마다 다르면 그 달에 직접 입력).", "반복"),
    ("카드 결제일·계좌", "선택", 'COUNTIFS(카드!$I$5:$I$40,">0",카드!$J$5:$J$40,"<>")>=1',
     f'COUNTIFS(카드!$I$5:$I$40,">0",카드!$J$5:$J$40,"<>")&" / 카드 "&({_kind("카드")})&"개"',
     "[카드]에서 카드마다 결제일(날짜 숫자)과 결제 계좌를 적으면 결제일 아침에 카드 대금 이체가 자동으로 들어갑니다.", "카드"),
    ("목표 입력", "선택", 'COUNTA(설정!$J$8:$J$10)=3', 'COUNTA(설정!$J$8:$J$10)&" / 3 입력"',
     "[설정] J8~J10에 목표 순자산·기한·올해 저축 목표를 적으면 [자산현황]에 달성률이 나옵니다.", "설정"),
    ("사람별 예산", "선택", 'COUNTIF(설정!$C$2:$C$60,">0")>=3', '"예산 있는 카테고리 "&COUNTIF(설정!$C$2:$C$60,">0")&"개"',
     "[설정] K~M열에 월 예산을 적으면 사용률이 나옵니다(J12 체크 = 지난 3개월 평균으로 빈 칸 채우기).", "설정"),
    ("알림 메일", "선택", f'LEN(TRIM({_mail}))>0',
     f'IF(LEN(TRIM({_mail}))=0,"없음",(LEN({_mail})-LEN(SUBSTITUTE({_mail},",",""))+1)&"명")',
     "[설정] J4에 예산 알림·월간 결산을 받을 메일을 적으세요(쉼표로 여러 명).", "설정"),
    ("증권 계좌 자동 연동", "선택", 'COUNTIF(투자!$G$7:$G$11,"자동")>=1', '"자동 연동 "&COUNTIF(투자!$G$7:$G$11,"자동")&"개 계좌"',
     "각자 PC에서 메뉴 '증권 연동' > 키 입력 후 '자동 갱신 켜기'를 누르세요(조회 전용).", "투자"),
]
LAST = FIRST + len(ITEMS) - 1

SECTIONS: list = []  # A3 안내 문장은 본문 글씨 그대로
HEADS = [f"{S}!A{HEAD}:F{HEAD}"]
TOTALS: list = []
SUBTOTALS: list = []
BODIES = [f"{S}!A{FIRST}:F{LAST}"]
INPUTS: list = []
RUNS = [("A", FIRST, LAST, "LCCLLC")]
WIDTHS = [190, 60, 90, 250, 480, 130]
HIDDEN: list = []


def _status(n: int, ok: str) -> str:
    return f'=IF({ok},"✓ 완료",IF(B{n}="필수","✗ 할 일","△ 선택"))'


def values() -> list[dict]:
    p = (f'="필수 "&COUNTIFS(B{FIRST}:B{LAST},"필수",C{FIRST}:C{LAST},"✓*")&" / "&COUNTIF(B{FIRST}:B{LAST},"필수")'
         f'&" 완료  ·  선택 "&COUNTIFS(B{FIRST}:B{LAST},"선택",C{FIRST}:C{LAST},"✓*")&" / "&COUNTIF(B{FIRST}:B{LAST},"선택")')
    out = [v(TITLE, [["시작하기 — 처음 쓸 때 할 일"]]), v(f"{S}!A2", [[p]]),
           v(f"{S}!A3", [["필수는 ✗가 없어질 때까지, 선택은 필요할 때. 상태는 시트 값으로 자동 계산됩니다."]]),
           v(f"{S}!A{HEAD}:F{HEAD}", [["항목", "구분", "상태", "지금", "하는 법", "바로가기"]])]
    for n, (label, kind, ok, now, how, tab) in enumerate(ITEMS, FIRST):
        link = f'=HYPERLINK("#gid={SHEET_ID[tab]}","{tab} 열기")'
        out.append(v(f"{S}!A{n}:F{n}", [[label, kind, _status(n, ok), f"={now}", how, link]]))
    return out


def formats() -> list[dict]:
    """상태 색: ✓ 초록 · ✗ 빨강 · △ 주황 (조건부 서식은 추가형이라 탭을 만들 때 한 번만)."""
    colors = {"✓": ({"red": 0.85, "green": 0.94, "blue": 0.85}, {"red": 0.1, "green": 0.45, "blue": 0.15}),
              "✗": ({"red": 0.96, "green": 0.8, "blue": 0.8}, {"red": 0.7, "green": 0.0, "blue": 0.0}),
              "△": ({"red": 1.0, "green": 0.9, "blue": 0.7}, {"red": 0.6, "green": 0.4, "blue": 0.0})}
    rules = [{"addConditionalFormatRule": {"index": 0, "rule": {"ranges": [a1_to_grid(f"{S}!C{FIRST}:C{LAST}")], "booleanRule": {
        "condition": {"type": "TEXT_STARTS_WITH", "values": [{"userEnteredValue": sym}]},
        "format": {"backgroundColor": bg, "textFormat": {"bold": True, "foregroundColor": fg}}}}}}
        for sym, (bg, fg) in colors.items()]
    return rules + wrap_requests()


def wrap_requests() -> list[dict]:
    """'하는 법' 열(E)은 긴 문장이라 줄바꿈 — 열 너비는 fit_dims가 건드리지 않게 고정(PINNED)."""
    return [{"repeatCell": {"range": a1_to_grid(f"{S}!E{FIRST}:E{LAST}"), "cell": {"userEnteredFormat": {"wrapStrategy": "WRAP"}},
                            "fields": "userEnteredFormat.wrapStrategy"}}]


def chart_requests() -> list[dict]:
    return []
