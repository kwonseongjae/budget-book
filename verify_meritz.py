"""메리츠 화면 통합 시험 — 임시 시트를 새로 만들어 샘플 원본을 넣고 화면 값을 확인한 뒤 휴지통으로 보낸다.

운영 시트에는 손대지 않는다. 공유하지 않는다. 사용: python3 verify_meritz.py  (종료코드 0 = 통과)
"""
import os

os.environ["BUDGET_NAMES"] = "신랑,신부"  # 통합 시험은 로컬 .names와 무관하게 기본 이름으로
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

import build_budget
import layout
from auth import get_credentials

FIX = Path(__file__).parent / "tests" / "fixtures" / "meritz_expected.json"


def serial(t: dt.datetime) -> float:
    """시트 날짜 일련번호 (1899-12-30 기준, 시트 시간대 Asia/Seoul의 벽시계 시각)."""
    base = dt.datetime(1899, 12, 30)
    return (t.replace(tzinfo=None) - base).total_seconds() / 86400


def raw_data(expected: dict, now_serial: float) -> list[dict]:
    rows = expected["holdings"]
    status = [["성공", "5766", "", now_serial]] * 4
    return [layout.v("메리츠원본!H1:H8", [[x] for x in expected["summary"]] + [[now_serial]]),
            layout.v("메리츠원본!B2:E5", status),
            layout.v("메리츠원본!J2:N2", expected["fx"]),
            layout.v(f"메리츠원본!A11:N{10 + len(rows)}", rows),
            layout.v("자산!A5:D5", [["메리츠증권", "통장", 0, ""]]),
            layout.v("자산!G5", [[layout.MERITZ_SLOTS[0].sync]])]


def checks(expected: dict) -> dict:
    rows = expected["holdings"]
    krw = [r for r in rows if r[5] != ""]
    profit = sum(r[7] for r in krw)
    cost = sum(r[5] for r in krw)
    wins, losses = sum(r[7] > 0 for r in krw), sum(r[7] < 0 for r in krw)
    return {f"{layout.STOCK}!A6": expected["summary"][6], f"{layout.STOCK}!E6": profit, f"{layout.STOCK}!F6": profit / cost,
            f"{layout.MERITZ}!B3": "정상", f"{layout.MERITZ}!D6": f"{len(rows)}개 ({wins} / {losses})",
            "자산!E5": expected["summary"][6]}


def _same(got, want) -> bool:
    if isinstance(want, float):
        return isinstance(got, (int, float)) and abs(got - want) < 1e-9
    return got == want


def _read(vals, sid: str, a1: str):
    got = vals.get(spreadsheetId=sid, range=a1, valueRenderOption="UNFORMATTED_VALUE").execute().get("values")
    return got[0][0] if got else None


def run(sheets, vals, drive) -> list[str]:
    expected = json.loads(FIX.read_text(encoding="utf-8"))
    sid = sheets.create(body=layout.create_body("메리츠 시험 (자동 삭제)"), fields="spreadsheetId").execute()["spreadsheetId"]
    try:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.structure_requests()}).execute()
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": build_budget.value_data("nobody@example.com")}).execute()
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.visual_requests()}).execute()
        now = serial(dt.datetime.now(ZoneInfo("Asia/Seoul")))
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "RAW", "data": raw_data(expected, now)}).execute()
        errors = [f"{a1}: 기대 {want!r}, 실제 {_read(vals, sid, a1)!r}"
                  for a1, want in checks(expected).items() if not _same(_read(vals, sid, a1), want)]
        fresh = _read(vals, sid, "자산!H5")
        if not str(fresh).startswith("연동 "):
            errors.append(f"자산!H5: '연동 …' 기대, 실제 {fresh!r}")
        vals.update(spreadsheetId=sid, range="메리츠원본!H8", valueInputOption="RAW", body={"values": [[now - 5]]}).execute()
        stale = _read(vals, sid, "자산!H5")
        if not str(stale).startswith("오래됨"):
            errors.append(f"자산!H5(5일 전): '오래됨' 기대, 실제 {stale!r}")
        return errors
    finally:
        drive.files().update(fileId=sid, body={"trashed": True}).execute()


def main() -> int:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    errors = run(sheets, sheets.values(), build("drive", "v3", credentials=creds))
    print("\n".join(errors) if errors else "통과: 메리츠 화면 8개 항목 일치 (임시 시트는 휴지통으로)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
