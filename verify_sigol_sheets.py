"""시골쥐 기능 시트 통합 시험 — 임시 시트에 반복·카드·주식·연금·내역 표본을 넣고 계산값을 확인한 뒤 휴지통으로.

사용: python3 verify_sigol_sheets.py  (종료코드 0 = 통과). 운영 시트는 건드리지 않음.
"""
import os

os.environ["BUDGET_NAMES"] = "신랑,신부"  # 통합 시험은 로컬 .names와 무관하게 기본 이름으로
import datetime as dt
import sys
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

import build_budget
import category_bars
import layout
from auth import get_credentials
from breakdown import BASE
from verify_meritz import _same


def sample(day: str, ym: str) -> list[dict]:
    t = lambda typ, cat, pay, amt, who="공동": [day, who, typ, cat, "", pay, "", amt, "KRW", "검증"]
    v = layout.v
    return [v("자산!A5:I9", [["하나카드", "카드", 0, 200000, "", "", "", "", "신부"],
                            ["연금저축", "연금", 1100000, "", "", "", "", "", "신랑"],
                            ["금통장", "기타", 600000, "", "", "", "", "", "공동"],
                            ["ISA", "주식", 1000000, "", "", "", "", "", "신부"],
                            ["정기적금", "계좌", 2400000, "", "", "", "", "", "신랑"]]),
            v("자산!A10:K11", [["달러통장", "계좌", 0, "", "", "", "", "", "신랑", "USD", 1000],
                              ["하나카드", "카드", 0, 50000, "", "", "", "", "신랑", "", ""]]),  # 같은 이름 카드 (소유자만 다름)
            v("반복!A2:M4", [[True, 25, "신랑", "지출", "주거·관리비", "주거래통장", 300000, "관리비", "", "", "", "", ""],
                            [True, 10, "공동", "지출", "통신", "신용카드1", 50000, "휴대폰", "", "", "", "", ""],
                            [True, 5, "신랑", "수입", "월급", "주거래통장", 3000000, "급여", "", "", "", "", ""]]),
            v("내역!A2:J6", [t("수입", "월급", "주거래통장", 3000000), t("지출", "식비", "하나카드", 80000, "신부"),
                            t("지출", "교통", "하나카드", 20000, "신부"), t("저축", "기타", "주거래통장", 400000),
                            t("지출", "식비", "하나카드", 30000, "신랑")]),
            v("주식_신랑!A9:C9", [["USD", 100, 1400]]),
            v("주식_신랑!A16:H17", [["해외", "TSLA", "테슬라", 10, 500000, 550000, 5000000, 5500000],
                                    ["국내", "005930", "삼성전자", 10, 70000, 60000, 700000, 600000]]),
            v("주식투자!K38:L39", [["TSLA", "전기차·2차전지"], ["005930", "반도체"]]),
            v("카드!A5", [["하나카드 (신부)"]]), v("카드!C5:J5", [["하나", "교통 10%", 15000, "교통", 3000000, ym, 14, "주거래통장"]]),
            v("저축·연금!A5", [["정기적금"]]), v("저축·연금!D5:G5", [["우리", "예적금", 200000, 0.035]]),
            v("저축·연금!A29", [["연금저축"]]), v("저축·연금!E29", [[1000000]]),
            v("저축·연금!A44", [["금통장"]]), v("저축·연금!C44", [[500000]])]


def checks(month: int) -> dict:
    r = category_bars.rows(BASE)
    return {"고정지출!A5": "통신", "고정지출!E5": 50000, "고정지출!L5": "주거·관리비",  # 목록=납입일 순, 요약=금액 큰 순
             "고정지출!M20": 350000, "고정지출!N20": 1,
            "카드!B5": "신부", "카드!K5": 100000, "카드!M5": 0.5, "카드!O5": "신용카드1",
            "주식투자!L33": 7100000, "주식투자!K19": "전기차·2차전지", "주식투자!M19": 5500000 / 7100000,
            "주식투자!H1": 1400, "주식투자!K94": "테슬라", "주식투자!L105": 7100000,
            # 둘째 줄 비율: LET 안 나눗셈은 ARRAYFORMULA 없이 첫 줄만 계산된다 (2026-10-14 운영에서 발견)
            "고정지출!N6": 50000 / 350000, "주식투자!M95": 1000000 / 7100000, "주식투자!M20": 1000000 / 7100000,
            "저축·연금!B5": "계좌", "저축·연금!H5": 2400000, "저축·연금!H21": 2400000, "저축·연금!F24": 200000,
            "저축·연금!G29": 0.1, "저축·연금!E44": 0.2,
            "자산현황!B31": 1700000, f"자산현황!B{50 + (month - 1) // 3}": 3000000, "자산현황!B54": 3000000,
            "자산!H10": "USD 환율 자동", "자산!E5": -100000, "자산!E11": -30000,  # 하나카드 두 장이 각자 것만
            "카드!L5": 200000, f"자산현황!{chr(ord('B') + month - 1)}68": 3000000, "자산현황!A71": "저축률",
            "자산현황!C61": 1100000, "자산현황!D61": 0.1, "자산현황!M48": 300000,
            f"대시보드!A{r['first']}": "월급", f"대시보드!E{r['first']}": "식비", f"대시보드!F{r['first']}": 110000,  # 지출 표 E·F열
            f"대시보드!J{r['first']}": 400000,
            f"대시보드!A{r['save']}": 400000}


def run(sheets, vals, drive) -> list[str]:
    sid = sheets.create(body=layout.create_body("시골쥐 시트 시험 (자동 삭제)"), fields="spreadsheetId").execute()["spreadsheetId"]
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
        # 달러통장: 1,000달러 × 실시간 환율 (900~2,000원 사이면 정상), 결제수단 목록엔 연금·기타 없음
        fx = vals.batchGet(spreadsheetId=sid, ranges=["자산!E10", "자산!L2:L20"], valueRenderOption="UNFORMATTED_VALUE").execute()["valueRanges"]
        usd = (fx[0].get("values") or [[None]])[0][0]
        if not (isinstance(usd, (int, float)) and 900000 < usd < 2000000):
            errors.append(f"자산!E10 달러통장 원화 환산 기대 90만~200만, 실제 {usd!r}")
        pay = [r[0] for r in fx[1].get("values", []) if r]
        if {"연금저축", "금통장"} & set(pay) or "달러통장" not in pay:
            errors.append(f"결제수단 목록 {pay}")
        tabs = ["고정지출", "카드", "주식투자", "저축·연금", "자산현황", "대시보드"]
        full = vals.batchGet(spreadsheetId=sid, ranges=[f"{t}!A1:T200" for t in tabs]).execute()["valueRanges"]
        for t, r in zip(tabs, full):
            bad = [c for row in r.get("values", []) for c in row if str(c).startswith(("#REF", "#N/A", "#VALUE", "#DIV", "#ERROR", "#NAME", "#NUM"))]
            if bad:
                errors.append(f"{t} 오류 칸 {bad[:5]}")
        return errors
    finally:
        drive.files().update(fileId=sid, body={"trashed": True}).execute()


def main() -> int:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    errors = run(sheets, sheets.values(), build("drive", "v3", credentials=creds))
    print("\n".join(errors) if errors else f"통과: 시골쥐 시트 {len(checks(1))}개 항목 + 오류 칸 0 (임시 시트는 휴지통으로)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
