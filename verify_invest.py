"""투자 탭 통합 시험 — 임시 시트에 가짜 원본·투자기록을 넣고 합산·증감·월말 표·직접입력·자산 연동을 확인한 뒤 휴지통으로.

운영 시트에는 손대지 않는다. 사용: python3 verify_invest.py  (종료코드 0 = 통과)
"""
import os

os.environ["BUDGET_NAMES"] = "신랑,신부"  # 통합 시험은 로컬 .names와 무관하게 기본 이름으로
import datetime as dt
import sys
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

import build_budget
import layout
from auth import get_credentials
from verify_meritz import _same, serial


def log_rows() -> list[list]:
    d = lambda m, day: serial(dt.datetime(2026, m, day))
    row = lambda date, total, principal: [date, total, principal, "", "", "", "", "", "", total, principal, 3]
    return [row(d(9, 29), 3000000, 2700000), row(d(9, 30), 3100000, 2700000),
            row(d(10, 7), 3400000, 3000000), row(d(10, 8), 3500000, 3100000)]


def sample(now: float) -> list[dict]:
    return [layout.v("메리츠원본!B2", [["성공"]]), layout.v("메리츠원본!H7:H8", [[1000000], [now]]),
            layout.v("메리츠원본!H2", [[100000]]), layout.v("메리츠원본!F11", [[800000]]),  # 원금 = 매입 800,000 + 현금 100,000
            layout.v("한투원본!B2:G2", [["성공", "0", "", now, 2000000, 1800000]]),
            layout.v("투자!H10:I10", [[500000, 400000]]), layout.v("투자!H11", [[100000]]),
            layout.v("자산!A5:D5", [["ISA권", "통장", 0, ""]]),  # E열은 잔액 수식이 펼쳐지는 자리라 쓰지 않는다
            layout.v("자산!G5", [["한투ISA_신랑"]]),
            layout.v("투자기록!A2:L5", log_rows())]


def saving_sample(today: str) -> list[dict]:
    """청약통장 2개(사람별) + 두 사람이 같은 '주택청약' 카테고리로 각 100,000 납입 — 각자 통장에만 쌓여야 함."""
    paid = lambda who: [today, who, "저축", "주택청약", "", "현금", "", 100000, "KRW", "검증"]
    return [layout.v("자산!A6:D7", [["청약_권", "청약", 5800000, ""], ["청약_한", "청약", 1000000, ""]]),
            layout.v("자산!F6:F7", [["주택청약"], ["주택청약"]]), layout.v("자산!I6:I7", [["신랑"], ["신부"]]),
            layout.v("내역!A2:J3", [paid("신랑"), paid("신부")])]


def checks() -> dict:
    return {"투자!B7": 1000000, "투자!C7": 900000, "투자!G7": "자동", "투자!G8": "자동", "투자!G10": "직접입력",
            "투자!B11": 100000, "투자!C11": "", "투자!B9": 3000000, "투자!B12": 600000,
            "투자!A4": 3600000, "투자!B4": 3100000, "투자!C4": 400000,  # 손익은 원금 있는 계좌만 (신부 ISA 제외)
            "투자!E4": 100000, "투자!F4": 400000,
            "투자!B41": 3100000, "투자!B42": 3500000, "투자!C42": 3100000,
            "자산!E5": 2000000,
            "자산!E6": 5900000, "자산!E7": 1100000,  # 사람별 적립 (예전엔 둘 다 합쳐 6,000,000·1,200,000)
            "투자!B18": 5900000, "투자!C18": 1100000, "투자!D18": 7000000,
            "투자!B19": 8900000, "투자!C19": 1700000, "투자!D19": 10600000,
            "투자!B20": 100000, "투자!C20": 100000, "투자!G16": "청약_권",
            # 대시보드 자산 현황: 순자산 = 현금 −200,000(청약 납입) + ISA권 2,000,000 + 청약 5,900,000 + 1,100,000
            "대시보드!J6": 8800000, "대시보드!K6": 3600000, "대시보드!L6": 7000000}


STALE = {"투자!B8": "", "투자!C8": "", "투자!B7": ""}  # 키 삭제(한투) · 4일 전 마지막 성공(메리츠) → 옛 값 빠짐


def stale_errors(vals, sid: str, now: float) -> list[str]:
    vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "RAW", "data": [
        layout.v("한투원본!B2", [["키없음"]]), layout.v("메리츠원본!B2", [["오류"]]), layout.v("메리츠원본!H8", [[now - 4]])]}).execute()
    got = vals.batchGet(spreadsheetId=sid, ranges=list(STALE), valueRenderOption="UNFORMATTED_VALUE").execute()
    actual = [(r.get("values") or [[""]])[0][0] for r in got["valueRanges"]]
    return [f"{a1}: 기대 {w!r}, 실제 {g!r}" for (a1, w), g in zip(STALE.items(), actual) if g != w]


def run(sheets, vals, drive) -> list[str]:
    sid = sheets.create(body=layout.create_body("투자 시험 (자동 삭제)"), fields="spreadsheetId").execute()["spreadsheetId"]
    try:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.structure_requests()}).execute()
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": build_budget.value_data("nobody@example.com")}).execute()
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.visual_requests()}).execute()
        now = serial(dt.datetime.now(ZoneInfo("Asia/Seoul")))
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "RAW", "data": sample(now)}).execute()
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": saving_sample(dt.datetime.now(ZoneInfo("Asia/Seoul")).date().isoformat())}).execute()
        want = checks()
        got = vals.batchGet(spreadsheetId=sid, ranges=list(want), valueRenderOption="UNFORMATTED_VALUE").execute()
        cell = lambda r: (r.get("values") or [[""]])[0][0]  # 한 번에 읽기 (분당 읽기 한도 60회)
        actual = {a1: cell(r) for a1, r in zip(want, got["valueRanges"])}
        errors = [f"{a1}: 기대 {w!r}, 실제 {actual[a1]!r}" for a1, w in want.items() if not _same(actual[a1], w)]
        return errors + stale_errors(vals, sid, now)
    finally:
        drive.files().update(fileId=sid, body={"trashed": True}).execute()


def main() -> int:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    errors = run(sheets, sheets.values(), build("drive", "v3", credentials=creds))
    print("\n".join(errors) if errors else f"통과: 투자 탭 {len(checks()) + len(STALE)}개 항목 일치 (임시 시트는 휴지통으로)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
