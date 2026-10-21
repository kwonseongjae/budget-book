"""설정 카테고리 줄을 대분류 순(고정비 → 변동비 → 빈칸, 수입은 맨 아래)으로 한 번 정렬한다.

한 줄로 묶인 칸(A 이름·B 구분·D 대분류·K~M 사람별 예산)만 함께 옮기고, 같은 행의 다른 목록(E 사용자, G:H 환율, I:J 항목)은
그대로 둔다. C는 합계 수식(C1)이 펼쳐지는 자리라 비운다. 같은 대분류 안은 지금 순서 유지. 두 번 실행해도 같음.
사용: python3 sort_settings.py   (대상: .spreadsheet_id, 실행 전 백업 사본 생성)
"""
import datetime as dt
import sys
from pathlib import Path

from googleapiclient.discovery import build

from auth import get_credentials
from layout import SETTINGS, v

LAST = 60
MAJOR_ORDER = {"고정비": 0, "변동비": 1}


def _pad(r: list, n: int) -> list:
    return (list(r) + [""] * n)[:n]


def sorted_rows(ad: list, km: list) -> tuple[list, list]:
    """ad = A:D 행들, km = K:M 행들 (같은 순서). 빈 이름 줄은 맨 뒤로 빼서 지운다."""
    rows = [(_pad(a, 4), _pad(k, 3)) for a, k in zip(ad + [[]] * (len(km) - len(ad)), km + [[]] * (len(ad) - len(km)))]
    named = [r for r in rows if r[0][0] != ""]
    key = lambda ir: (ir[1][0][1] == "수입", MAJOR_ORDER.get(ir[1][0][3], 2), ir[0])
    out = [r for _i, r in sorted(enumerate(named), key=key)]
    return [[a[0], a[1], "", a[3]] for a, _k in out], [k for _a, k in out]


def main() -> int:
    sid = (Path(__file__).parent / ".spreadsheet_id").read_text().strip()
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    got = sheets.values().batchGet(spreadsheetId=sid, valueRenderOption="UNFORMATTED_VALUE",
                                   ranges=[f"{SETTINGS}!A2:D{LAST}", f"{SETTINGS}!K2:M{LAST}"]).execute()["valueRanges"]
    ad, km = got[0].get("values", []), got[1].get("values", [])
    new_ad, new_km = sorted_rows(ad, km)
    if [_pad(r, 4)[:2] + [_pad(r, 4)[3]] for r in ad if _pad(r, 4)[0]] == [[r[0], r[1], r[3]] for r in new_ad]:
        print("이미 정렬됨")
        return 0
    name = f"우리집 가계부 백업 ({dt.date.today().isoformat()} 설정 정렬 전)"
    print("백업:", build("drive", "v3", credentials=creds).files().copy(fileId=sid, body={"name": name}).execute()["id"])
    blank = LAST - 1 - len(new_ad)
    data = [v(f"{SETTINGS}!A2:B{LAST}", [r[:2] for r in new_ad] + [["", ""]] * blank),
            v(f"{SETTINGS}!D2:D{LAST}", [[r[3]] for r in new_ad] + [[""]] * blank),
            v(f"{SETTINGS}!K2:M{LAST}", new_km + [["", "", ""]] * blank)]
    sheets.values().batchUpdate(spreadsheetId=sid, body={"valueInputOption": "RAW", "data": data}).execute()
    print(f"정렬: 카테고리 {len(new_ad)}줄")
    return 0


if __name__ == "__main__":
    sys.exit(main())
