"""부부 확장 통합 시험 — 임시 시트를 새로 만들어 샘플 내역을 넣고 부부·설정·대시보드·자산 값을 확인한 뒤 휴지통으로.

운영 시트에는 손대지 않는다. 공유하지 않는다. 사용: python3 verify_couple.py  (종료코드 0 = 통과)
"""
import os

os.environ["BUDGET_NAMES"] = "신랑,신부"  # 통합 시험은 로컬 .names와 무관하게 기본 이름으로
import calendar
import datetime as dt
import sys
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

import build_budget
import layout
from auth import get_credentials
from verify_meritz import _read, _same, serial


def sample(day: str) -> list[dict]:
    t = lambda user, typ, cat, pay, amt: [day, user, typ, cat, "", pay, "", amt, "KRW", "검증"]
    return [layout.v("자산!I2:I4", [[""], ["공동"], ["신랑"]]),
            layout.v("자산!A5:I6", [["하나카드", "카드", 0, "", "", "", "", "", "신부"],
                                    ["메리츠한", "통장", 0, "", "", "", "메리츠_신부", "", "신부"]]),
            layout.v("설정!K2:M2", [[300000, "", 600000]]),
            layout.v("반복!A2:I2", [[True, 28, "공동", "지출", "식비", "주거래통장", 100000, "검증", ""]]),
            layout.v("내역!A2:J7", [t("신랑", "수입", "월급", "주거래통장", 3000000),
                                    t("신랑", "지출", "식비", "신용카드1", 350000),
                                    t("공동", "지출", "식비", "신용카드1", 100000),
                                    t("공동", "지출", "식비", "하나카드", 40000),
                                    t("공동", "지출", "식비", "주거래통장", 500000),
                                    t("공동", "지출", "식비", "현금", 7000)])]


def checks(today: dt.date) -> dict:
    spent = 350000 + 647000
    elapsed, days = today.day, calendar.monthrange(today.year, today.month)[1]
    pending = 100000  # 반복 I열(마지막 생성 월)이 비어 있음 = 이번 달 미생성 → 예상에 포함
    return {"설정!C2": 900000,
            "부부!B5": 3000000, "부부!C5": 350000, "부부!E5": 2650000, "부부!C7": 647000,
            "부부!B10": 100000, "부부!B11": 40000, "부부!B12": "신부 → 신랑 30,000원", "부부!B13": 1,
            # 식비는 대분류 순 정렬로 고정비 2개(주거·관리비, 통신) 다음 → 18행
            "부부!C18": 350000, "부부!D18": 300000, "부부!E18": 350000 / 300000, "부부!I18": 647000, "부부!J18": 600000,
            "대시보드!B6": spent, "대시보드!F6": spent + pending + spent / elapsed * (days - elapsed),
            "자산!E6": 1234567, "주식_신부!A6": 1234567,
            # 카테고리 목록은 대분류 순: 기본 고정비(주거·관리비, 통신)가 먼저, 그다음 변동비(식비 …)
            "대시보드!A62": "주거·관리비", "대시보드!A63": "통신", "대시보드!A64": "식비",
            "부부!A16": "주거·관리비", "부부!A18": "식비"}


def fixed_sample(day: str) -> list[dict]:
    """고정비 2건 — 앞 항목 확인을 끝낸 뒤에 넣어 기존 기대값은 그대로 둔다."""
    return [layout.v("내역!A8:J9", [[day, "공동", "지출", "주거·관리비", "", "주거래통장", "", 800000, "KRW", "월세"],
                                    [day, "신랑", "지출", "통신", "", "신용카드1", "", 70000, "KRW", "휴대폰"]])]


BREAKDOWN = {"대시보드!A97:C101": [["고정비", 870000, 870000 / 3000000], ["변동비", 997000, 997000 / 3000000],
                                  ["대분류 없음", 0, 0], ["남은 돈", 1133000, 1133000 / 3000000], ["총수입", 3000000, 1]],
             "대시보드!A106:F107": [["주거·관리비", "월세", "공동", 800000, 800000 / 870000, "주거·관리비·월세 (공동) 92.0%"],
                                   ["통신", "휴대폰", "신랑", 70000, 70000 / 870000, "통신·휴대폰 (신랑) 8.0%"]],
             "대시보드!H106:K107": [["식비", 997000, 1, "식비 100.0%"]]}


def breakdown_errors(vals, sid: str) -> list[str]:
    got = vals.batchGet(spreadsheetId=sid, ranges=list(BREAKDOWN), valueRenderOption="UNFORMATTED_VALUE").execute()
    errors = []
    for (a1, want), vr in zip(BREAKDOWN.items(), got["valueRanges"]):
        rows = vr.get("values", [])
        flat = [(w, rows[i][j] if i < len(rows) and j < len(rows[i]) else None)
                for i, r in enumerate(want) for j, w in enumerate(r)]
        if not all(_same(g, w) for w, g in flat):
            errors.append(f"{a1}: 기대 {want!r}, 실제 {rows!r}")
    return errors


def run(sheets, vals, drive) -> list[str]:
    sid = sheets.create(body=layout.create_body("부부 시험 (자동 삭제)"), fields="spreadsheetId").execute()["spreadsheetId"]
    try:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.structure_requests()}).execute()
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": build_budget.value_data("nobody@example.com")}).execute()
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.visual_requests()}).execute()
        now = dt.datetime.now(ZoneInfo("Asia/Seoul"))
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": sample(now.date().isoformat())}).execute()
        vals.update(spreadsheetId=sid, range="메리츠원본2!H7:H8", valueInputOption="RAW",
                    body={"values": [[1234567], [serial(now)]]}).execute()
        want = checks(now.date())  # 한 번에 읽기 (분당 읽기 한도 60회)
        got = vals.batchGet(spreadsheetId=sid, ranges=list(want), valueRenderOption="UNFORMATTED_VALUE").execute()
        actual = {a1: (r.get("values") or [[None]])[0][0] for a1, r in zip(want, got["valueRanges"])}
        errors = [f"{a1}: 기대 {w!r}, 실제 {actual[a1]!r}" for a1, w in want.items() if not _same(actual[a1], w)]
        status = _read(vals, sid, "자산!H6")
        if not str(status).startswith("연동 "):
            errors.append(f"자산!H6: '연동 …' 기대, 실제 {status!r}")
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": fixed_sample(now.date().isoformat())}).execute()
        return errors + breakdown_errors(vals, sid)
    finally:
        drive.files().update(fileId=sid, body={"trashed": True}).execute()


def main() -> int:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    errors = run(sheets, sheets.values(), build("drive", "v3", credentials=creds))
    print("\n".join(errors) if errors else f"통과: 부부 확장 {len(checks(dt.date.today())) + 1 + len(BREAKDOWN)}개 항목 일치 (임시 시트는 휴지통으로)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
