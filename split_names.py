"""같은 이름 자산을 '이름_소유자'로 나누는 한 번짜리 정리 (2026-10-14 하나카드 신랑·신부).

이름이 같으면 사용자가 '공동'인 지출이 어느 카드인지 알 수 없어 정산·결산 메일·잔액이 틀어진다.
[자산] 이름을 바꾸고, 이미 적힌 내역(결제수단·입금자산)·반복·즐겨찾기·카드 탭 값을 그 줄의 사용자에 맞춰 고친다.
사용자가 소유자가 아닌 줄(공동 등)은 고치지 않고 목록으로 알려 사람이 고르게 한다.

사용: python3 split_names.py           → 바꿀 목록만 보여 줌 (운영 시트 그대로)
      python3 split_names.py --apply   → 드라이브 백업 사본을 만든 뒤 적용
"""
import socket
import sys
from collections import Counter
from typing import NamedTuple

from googleapiclient.discovery import build

import cards

# (데이터 키, 탭, 첫 행, [(이름 열 index, 열 문자)], 사용자 열 index)
TABLES = [("txn", "내역", 2, [(5, "F"), (6, "G")], 1),
          ("recur", "반복", 2, [(5, "F")], 2),
          ("fav", "즐겨찾기", 2, [(4, "E")], 1)]


class Change(NamedTuple):
    range: str
    old: str
    new: str


def _cell(row: list, i: int) -> str:
    return str(row[i]).strip() if i < len(row) and row[i] is not None else ""


def plan(data: dict) -> tuple[list, list]:
    """data = {assets: 자산 A:I 줄(2행부터), txn, recur, fav: 각 탭 줄(2행부터), cards: 카드 탭 A열(5행부터)}."""
    names = [_cell(r, 0) for r in data["assets"]]
    dup = {n for n, k in Counter(names).items() if n and k > 1}
    if not dup:
        return [], []
    changes, unresolved = [], []
    for i, r in enumerate(data["assets"]):
        n, owner = _cell(r, 0), _cell(r, 8)
        if n in dup:
            if owner:
                changes.append(Change(f"자산!A{i + 2}", n, f"{n}_{owner}"))
            else:
                unresolved.append(f"자산!A{i + 2} ({n}, 소유자 없음)")
    owners = {n: {_cell(r, 8) for r in data["assets"] if _cell(r, 0) == n} for n in dup}
    for key, tab, first, cols, user_i in TABLES:
        for i, r in enumerate(data[key]):
            user = _cell(r, user_i)
            for ci, letter in cols:
                n = _cell(r, ci)
                if n not in dup:
                    continue
                a1 = f"{tab}!{letter}{i + first}"
                if user in owners[n]:
                    changes.append(Change(a1, n, f"{n}_{user}"))
                else:
                    unresolved.append(f"{a1} ({user or '사용자 없음'}, {n})")
    for i, r in enumerate(data["cards"]):  # 카드 탭: '하나카드 (신랑)' 표시 이름 → '하나카드_신랑'
        label = _cell(r, 0)
        base, _, rest = label.partition(" (")
        a1 = f"카드!A{i + cards.DEFAULT.first}"
        if base in dup and rest.endswith(")") and rest[:-1] in owners[base]:
            changes.append(Change(a1, label, f"{base}_{rest[:-1]}"))
        elif label in dup:
            unresolved.append(f"{a1} ({label})")
    return changes, unresolved


def _read(sheets, sid: str) -> dict:
    r = sheets.values().batchGet(spreadsheetId=sid, valueRenderOption="UNFORMATTED_VALUE",
                                 ranges=["자산!A2:I50", "내역!A2:J5000", "반복!A2:H50", "즐겨찾기!A2:G50", "카드!A5:A40"]).execute()["valueRanges"]
    keys = ["assets", "txn", "recur", "fav", "cards"]
    return {k: x.get("values", []) for k, x in zip(keys, r)}


def main() -> int:
    from auth import get_credentials
    from migrate_couple import ID_FILE
    socket.setdefaulttimeout(300)
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    sid = ID_FILE.read_text().strip()
    changes, unresolved = plan(_read(sheets, sid))
    for c in changes:
        print(f"{c.range}: {c.old} → {c.new}")
    for u in unresolved:
        print(f"직접 골라야 함: {u}")
    if not changes:
        print("같은 이름 자산 없음 — 할 일 없음")
        return 0
    if "--apply" not in sys.argv:
        print(f"(미리 보기) {len(changes)}칸. 적용하려면 --apply")
        return 0
    backup = build("drive", "v3", credentials=creds).files().copy(
        fileId=sid, body={"name": "우리집 가계부 백업 (같은 이름 자산 나누기 전)"}).execute()["id"]
    print("백업:", backup)
    sheets.values().batchUpdate(spreadsheetId=sid, body={"valueInputOption": "RAW",
                                                         "data": [{"range": c.range, "values": [[c.new]]} for c in changes]}).execute()
    print(f"적용: {len(changes)}칸")
    return 0


if __name__ == "__main__":
    sys.exit(main())
