"""가계부 스프레드시트를 새로 만들고 배우자에게 편집 권한으로 공유한다.

사용: BUDGET_CLIENT_SECRET=... BUDGET_PARTNER_EMAIL=... python3 build_budget.py ["시트 제목"]
"""
import os
import re
import sys
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

import align
import asset_status
import breakdown
import category_bars
import charts
import couple
import formulas
import guide
import invest
import meritz_sheet
import meritz_style
import readability
import sigol_tabs
import layout
import styling
import theme
import views
import chart_fit
import fit_dims
from auth import get_credentials

ROOT = Path(__file__).parent
ID_FILE = ROOT / ".spreadsheet_id"
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def partner_email() -> str:
    email = os.environ.get("BUDGET_PARTNER_EMAIL")
    if email is None:
        raise ValueError("BUDGET_PARTNER_EMAIL not set")
    email = email.strip()
    if not EMAIL_RE.fullmatch(email):
        raise ValueError(f"이메일 형식 오류: {email!r}")
    return email


def structure_requests() -> list[dict]:
    return (layout.validation_requests() + layout.format_requests() + formulas.core_formats()
            + views.view_formats() + meritz_style.structure_requests() + couple.couple_formats()
            + invest.structure_requests() + asset_status.formats() + sigol_tabs.formats() + layout.protection_requests()
            + sigol_tabs.protection())


def value_data(email: str) -> list[dict]:
    return (layout.seed_values(email) + formulas.core_values() + views.view_values()
            + guide.guide_values() + styling.title_values() + breakdown.breakdown_values() + meritz_sheet.all_values() + couple.couple_values()
            + invest.invest_values() + theme.badge_values()
            + asset_status.values() + asset_status.settings_labels() + asset_status.dashboard_kpi() + sigol_tabs.values()
            + category_bars.values(breakdown.BASE))


def visual_requests() -> list[dict]:
    # 운영 migrate와 같은 순서: styling(글꼴·제목·체크박스 색) 뒤에 theme(바탕·흰 표·남색·분홍)
    return ([theme.spreadsheet_theme()] + styling.style_requests() + theme.requests() + guide.guide_requests()
            + charts.chart_requests() + charts.conditional_requests() + meritz_style.visual_requests() + meritz_style.hide_requests()
            + couple.visual_requests() + invest.visual_requests()
            + breakdown.style_requests() + breakdown.chart_requests() + readability.requests(60) + align.requests() + asset_status.chart_requests()
            + sigol_tabs.widths() + sigol_tabs.chart_requests()
            + category_bars.style_requests(breakdown.BASE) + category_bars.chart_requests(breakdown.BASE))


def share(drive, sid: str, email: str) -> bool:
    try:
        drive.permissions().create(
            fileId=sid, body={"type": "user", "role": "writer", "emailAddress": email},
            sendNotificationEmail=True).execute()
        return True
    except HttpError as e:
        print(f"공유 실패({email}): {e}. 시트 공유 메뉴에서 직접 추가하세요.")
        return False


def build_sheet(title: str, email: str) -> str:
    if ID_FILE.exists():
        raise FileExistsError(f"이미 생성된 시트가 있습니다 ({ID_FILE.read_text().strip()}). 새로 만들려면 {ID_FILE.name} 삭제 후 실행")
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    created = sheets.create(body=layout.create_body(title), fields="spreadsheetId,spreadsheetUrl").execute()
    sid = created["spreadsheetId"]
    ID_FILE.write_text(sid)  # 이후 단계가 실패해도 어떤 시트인지 남긴다
    sheets.batchUpdate(spreadsheetId=sid, body={"requests": structure_requests()}).execute()
    sheets.values().batchUpdate(spreadsheetId=sid, body={
        "valueInputOption": "USER_ENTERED", "data": value_data(email)}).execute()
    sheets.batchUpdate(spreadsheetId=sid, body={"requests": visual_requests()}).execute()
    fit_dims.fit(sheets, sid)
    chart_fit.fit(sheets, sid)
    share(build("drive", "v3", credentials=creds), sid, email)
    return created["spreadsheetUrl"]


if __name__ == "__main__":
    print(build_sheet(sys.argv[1] if len(sys.argv) > 1 else "우리집 가계부", partner_email()))
