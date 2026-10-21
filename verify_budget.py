"""실제 시트에 샘플 3건을 넣어 집계를 확인한 뒤 지운다. 내역이 비어 있을 때만 실행.

사용: python3 verify_budget.py   (종료코드 0 = 통과)
"""
import os

os.environ["BUDGET_NAMES"] = "신랑,신부"  # 통합 시험은 로컬 .names와 무관하게 기본 이름으로
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from auth import get_credentials

ID_FILE = Path(__file__).parent / ".spreadsheet_id"


def sample(day: str) -> list[list]:
    return [[day, "신랑", "수입", "월급", "", "주거래통장", "", 3000000, "KRW", "검증"],
            [day, "신부", "지출", "식비", "", "신용카드1", "", 12000, "KRW", "검증"],
            [day, "공동", "이체", "", "", "주거래통장", "현금", 50000, "KRW", "검증"]]


def expected(today: dt.date) -> dict:
    return {"대시보드!A6:C6": [[3000000, 12000, 2988000]],
            "대시보드!B62": [[12000]],
            "대시보드!G62": [[12000]],
            "대시보드!J61": [[12000]],
            "자산!E2:E4": [[50000], [2950000], [-12000]],
            f"추이!C{38 + today.month}": [[12000]],
            "검색!E1": [[12000]]}


def main() -> int:
    sid = ID_FILE.read_text().strip()
    vals = build("sheets", "v4", credentials=get_credentials()).spreadsheets().values()
    if vals.get(spreadsheetId=sid, range="내역!A2:A2").execute().get("values"):
        print("내역이 비어 있지 않아 중단 (실데이터 보호)")
        return 2
    today = dt.datetime.now(ZoneInfo("Asia/Seoul")).date()
    vals.update(spreadsheetId=sid, range="내역!A2:J4", valueInputOption="USER_ENTERED",
                body={"values": sample(today.isoformat())}).execute()
    try:
        errors = []
        for rng, want in expected(today).items():
            got = vals.get(spreadsheetId=sid, range=rng, valueRenderOption="UNFORMATTED_VALUE").execute().get("values")
            if got != want:
                errors.append(f"{rng}: 기대 {want}, 실제 {got}")
    finally:
        vals.clear(spreadsheetId=sid, range="내역!A2:J4").execute()
    print("\n".join(errors) if errors else f"통과: {len(expected(today))}개 범위 일치")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
