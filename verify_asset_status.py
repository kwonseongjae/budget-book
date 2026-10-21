"""자산현황 통합 시험 — 임시 시트에 대출·내역·목표를 넣고 자산현황 값을 확인한 뒤 휴지통으로. 운영 시트는 건드리지 않음.

사용: python3 verify_asset_status.py  (종료코드 0 = 통과)
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
from verify_meritz import _same


def sample(day: str, ym: str) -> list[dict]:
    t = lambda typ, cat, pay, to, amt: [day, "공동", typ, cat, "", pay, to, amt, "KRW", "검증"]
    return [layout.v("자산!A5:I5", [["전세대출", "대출", -50000000, "", "", "", "", "", "공동"]]),
            layout.v("설정!A15:D15", [["적금", "저축", "", "고정비"]]),
            layout.v("내역!A2:J5", [t("수입", "월급", "주거래통장", "", 3000000),
                                    t("지출", "식비", "신용카드1", "", 1000000),
                                    t("저축", "적금", "주거래통장", "", 500000),
                                    t("이체", "", "주거래통장", "전세대출", 1000000)]),
            layout.v("자산현황!A36", [["전세대출"]]),
            layout.v("자산현황!D36:G36", [[0.035, 1000000, 25, ym]])]


def checks(month: int) -> dict:
    r = 12 + month
    # 부채 묶음 = 대출 −49,000,000 + 시험 카드(신용카드1) 식비 −1,000,000
    return {"자산!E5": -49000000, "자산현황!C36": -49000000, "자산현황!B36": "공동",
            f"자산현황!B{r}": 3000000, f"자산현황!C{r}": 1000000, f"자산현황!D{r}": 2000000, f"자산현황!E{r}": 2 / 3,
            "자산현황!A9": 2000000, "자산현황!B32": -50000000, "자산현황!H36": 0,
            "자산현황!B5": "", "자산현황!C5": "", "자산현황!E5": "", "대시보드!M6": ""}


def run(sheets, vals, drive) -> list[str]:
    sid = sheets.create(body=layout.create_body("자산현황 시험 (자동 삭제)"), fields="spreadsheetId").execute()["spreadsheetId"]
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
        # 목표를 넣으면 달성률·필요 월 저축이 나온다 (기한 = 이번 달 → 기한 지남)
        vals.update(spreadsheetId=sid, range="설정!J8:J10", valueInputOption="USER_ENTERED",
                    body={"values": [[100000000], [now.strftime("%Y-%m")], [30000000]]}).execute()
        g = vals.batchGet(spreadsheetId=sid, ranges=["자산현황!C5:E5", "자산현황!C9", "대시보드!M6", "자산현황!A1:K46"],
                          valueRenderOption="UNFORMATTED_VALUE").execute()["valueRanges"]
        c5, d5, e5 = ((g[0].get("values") or [[]])[0] + ["", "", ""])[:3]
        if not (isinstance(c5, (int, float)) and d5 == 0 and e5 == "기한 지남"):
            errors.append(f"목표 입력 뒤 자산현황 C5:E5 기대 (숫자, 0, '기한 지남'), 실제 {(c5, d5, e5)!r}")
        if not _same((g[1].get("values") or [[None]])[0][0], 2000000 / 30000000):
            errors.append(f"자산현황!C9 기대 {2000000 / 30000000}, 실제 {g[1].get('values')!r}")
        if not _same((g[2].get("values") or [[None]])[0][0], c5):
            errors.append(f"대시보드!M6 기대 자산현황 C5와 같음 {c5!r}, 실제 {g[2].get('values')!r}")
        errs = [c for row in g[3].get("values", []) for c in row if str(c)[:2] in ("#R", "#N", "#V", "#D", "#E")]
        return errors + ([f"자산현황 오류 칸 {errs}"] if errs else [])
    finally:
        drive.files().update(fileId=sid, body={"trashed": True}).execute()


def main() -> int:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    errors = run(sheets, sheets.values(), build("drive", "v3", credentials=creds))
    print("\n".join(errors) if errors else f"통과: 자산현황 {len(checks(1)) + 4}개 항목 일치 (임시 시트는 휴지통으로)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
