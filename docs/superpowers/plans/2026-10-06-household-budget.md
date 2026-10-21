# 부부 가계부 (Google Sheets) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Python 스크립트 한 번 실행으로 부부 공유 가계부 구글 시트(탭·드롭다운·수식·차트·보호)를 만들고, 시트에 연결된 Apps Script로 이름 자동 변경·즐겨찾기·반복·문자입력·예산 알림을 붙인다.

**Architecture:** `layout.py`(탭/검증/서식/보호) · `formulas.py`(핵심 수식) · `views.py`(추이/달력/검색 수식) · `charts.py`(차트/조건부서식)는 Sheets API 요청 JSON을 만드는 순수 함수이고, `build_budget.py`가 이를 조립해 한 번 호출한다. Apps Script는 `logic.gs`(순수 로직, node로 테스트)와 `triggers.gs`(시트 연결부)로 나누고 `deploy_script.py`가 Apps Script API로 업로드한다. 모든 데이터는 `내역` 탭 하나에 쌓이고 나머지 탭은 수식으로 읽기만 한다.

**Tech Stack:** Python 3.12, google-api-python-client, google-auth-oauthlib, pytest 8 / Google Apps Script V8 / Node 22 (`node --test`)

**Spec:** `docs/superpowers/specs/2026-10-06-household-budget-design.md`

## Global Constraints

- 작업 폴더: `/mnt/d/budget book` (Windows `D:\budget book`). 모든 명령은 이 폴더에서 실행.
- 비밀값 하드코딩 금지: `BUDGET_CLIENT_SECRET`(client_secret.json 경로), `BUDGET_PARTNER_EMAIL`(배우자 이메일)은 환경변수, 없으면 `ValueError("... not set")`.
- `token.json`, `client_secret*.json`, `.env`, `.spreadsheet_id`, `.script_id` 는 커밋 금지(.gitignore).
- 탭 이름은 정확히: `내역, 대시보드, 추이, 달력, 검색, 즐겨찾기, 반복, 문자입력, 자산, 설정, 계산, 알림기록`.
- 스프레드시트 locale `ko_KR`, timeZone `Asia/Seoul`; Apps Script manifest timeZone `Asia/Seoul`, runtime `V8`.
- 월 키는 문자열이 아닌 **숫자 `YYYYMM`**(예: 202610), 표시 서식 `0000"-"00`. 모든 집계는 `내역!K`(원화금액)·`내역!L`(귀속월)을 사용.
- 내역에 행을 추가하는 모든 스크립트 경로는 `appendTxn()` 하나만 사용.
- 모바일 시트 앱에서 커스텀 메뉴·버튼은 동작하지 않으므로, 스크립트 동작은 체크박스(onEdit) 또는 시간 트리거로만 시작.
- 파일 800줄, 함수 50줄 이하.
- 알려진 한계(의도된 단순화): 외화는 입력 시점이 아니라 **현재 환율**(`GOOGLEFINANCE`)로 환산된다.

## Review Focus

1. **월 문자열 자동 날짜 변환** — "2026-10"을 SUMIFS 조건으로 쓰면 시트가 날짜로 해석해 합계가 0이 될 수 있다 → 귀속월을 숫자 202610으로 저장한다 (Task 3 `test_txn_ym_is_numeric_key`).
2. **ARRAYFORMULA가 열 끝까지 차서 appendRow가 5000행 뒤에 붙는 문제** → A열 기준 `nextEmptyRow` (Task 7 테스트).
3. **이름 변경 오작동** — 빈 칸에 새 카테고리 추가, 이름 지우기, 여러 칸 붙여넣기, 헤더 수정 시 과거 내역을 건드리면 안 된다 (Task 7 `routeEdit` 테스트).
4. **31일 반복 항목** — 30일/28일 달에는 말일에 생성되고, 트리거가 하루 빠져도 다음날 따라잡고, 같은 달 중복 생성이 없어야 한다 (Task 8 테스트).
5. **카드 문자 오인식** — 누적금액을 결제금액으로 착각, 승인취소 문자 추가, 1월에 받은 12/31 문자의 연도 → 직전 연도 (Task 9 테스트).

---

### Task 1: 프로젝트 골격 + OAuth

**Files:**
- Create: `requirements.txt`, `auth.py`, `tests/test_auth.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `auth.get_credentials() -> google.oauth2.credentials.Credentials`, `auth.client_secret_path() -> Path`, `auth.SCOPES: list[str]`

- [ ] **Step 1: Write the failing test** — `tests/test_auth.py`

```python
import pytest

import auth


def test_client_secret_env_missing(monkeypatch):
    monkeypatch.delenv("BUDGET_CLIENT_SECRET", raising=False)
    with pytest.raises(ValueError, match="BUDGET_CLIENT_SECRET not set"):
        auth.client_secret_path()


def test_client_secret_file_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("BUDGET_CLIENT_SECRET", str(tmp_path / "nope.json"))
    with pytest.raises(ValueError, match="client_secret 파일 없음"):
        auth.client_secret_path()


def test_scopes_cover_sheets_drive_script():
    assert set(auth.SCOPES) == {
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.file",
        "https://www.googleapis.com/auth/script.projects",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_auth.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'auth'`

- [ ] **Step 3: Write implementation**

`requirements.txt`:
```
google-api-python-client>=2.100
google-auth-oauthlib>=1.0
pytest>=8
```

`.gitignore` (전체 내용):
```
token.json
client_secret*.json
.env
__pycache__/
.spreadsheet_id
.script_id
```

`auth.py`:
```python
"""Google OAuth 토큰 발급/로드 (Sheets 생성 + Drive 공유 + Apps Script 업로드).

사용 (2단계 — `!` 명령은 stdin이 없어 input()을 쓸 수 없음):
  1) python3 auth.py           → 인증 URL 출력
  2) python3 auth.py "<URL>"   → 리다이렉트 URL에서 code 추출 후 token.json 저장
"""
import os
import sys
import urllib.parse
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

ROOT = Path(__file__).parent
TOKEN_FILE = ROOT / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/script.projects",
]
REDIRECT_URI = "http://localhost:8080/"


def client_secret_path() -> Path:
    raw = os.environ.get("BUDGET_CLIENT_SECRET")
    if not raw:
        raise ValueError("BUDGET_CLIENT_SECRET not set")
    path = Path(raw)
    if not path.exists():
        raise ValueError(f"client_secret 파일 없음: {path}")
    return path


def _save(creds: Credentials) -> None:
    TOKEN_FILE.write_text(creds.to_json())
    TOKEN_FILE.chmod(0o600)


def get_credentials() -> Credentials:
    if not TOKEN_FILE.exists():
        raise FileNotFoundError("token.json 없음. 먼저 python3 auth.py 실행")
    creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save(creds)
    return creds


def main(argv: list[str]) -> None:
    # 두 프로세스에 걸친 흐름이라 PKCE verifier를 공유할 수 없음 → 비활성화
    flow = Flow.from_client_secrets_file(
        str(client_secret_path()), SCOPES, redirect_uri=REDIRECT_URI,
        autogenerate_code_verifier=False,
    )
    if len(argv) < 2:
        url, _ = flow.authorization_url(access_type="offline", prompt="consent")
        print(url)
        print('브라우저에서 허용 후, 주소창 URL을 복사해: python3 auth.py "<URL>"')
        return
    query = urllib.parse.urlparse(argv[1].strip()).query
    code = urllib.parse.parse_qs(query).get("code", [""])[0]
    if not code:
        raise ValueError("URL에 code 파라미터가 없습니다")
    flow.fetch_token(code=code)
    _save(flow.credentials)
    print(f"저장됨: {TOKEN_FILE}")


if __name__ == "__main__":
    main(sys.argv)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_auth.py -q`
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .gitignore auth.py tests/test_auth.py
git commit -m "feat: OAuth 토큰 발급/로드 (env 기반 client_secret)"
```

---

### Task 2: layout.py — 탭, 초기 데이터, 검증, 서식, 보호

**Files:**
- Create: `layout.py`, `tests/test_layout.py`

**Interfaces:**
- Produces:
  - 탭 이름 상수 `TXN, SETTINGS, ASSETS, DASH, TREND, CAL, SEARCH, RECUR, FAV, SMS, CALC, STATE`
  - `SHEETS: list[tuple[str, int, int, int, bool]]`, `SHEET_ID: dict[str, int]`
  - `TXN_HEADERS: list[str]` (10개)
  - `col_index(letters: str) -> int` (0-based), `a1_to_grid(a1: str) -> dict` (닫힌 범위만)
  - `v(a1: str, rows: list[list]) -> dict` (`{"range","values"}`)
  - `number_format(a1: str, kind: str, pattern: str) -> dict` (repeatCell 요청)
  - `create_body(title: str) -> dict`, `seed_values(partner_email: str) -> list[dict]`
  - `validation_requests() / format_requests() / protection_requests() -> list[dict]`

- [ ] **Step 1: Write the failing test** — `tests/test_layout.py`

```python
import pytest

import layout


def test_a1_to_grid_range():
    assert layout.a1_to_grid("내역!B2:D10") == {
        "sheetId": 100, "startRowIndex": 1, "endRowIndex": 10,
        "startColumnIndex": 1, "endColumnIndex": 4,
    }


def test_a1_to_grid_single_cell_and_double_letters():
    g = layout.a1_to_grid("추이!AA3")
    assert (g["startRowIndex"], g["endRowIndex"]) == (2, 3)
    assert (g["startColumnIndex"], g["endColumnIndex"]) == (26, 27)


def test_a1_to_grid_rejects_open_range():
    with pytest.raises(ValueError):
        layout.a1_to_grid("내역!A2:A")


def test_create_body_tabs_locale_and_unique_ids():
    body = layout.create_body("테스트")
    assert body["properties"]["locale"] == "ko_KR"
    assert body["properties"]["timeZone"] == "Asia/Seoul"
    props = [s["properties"] for s in body["sheets"]]
    assert [p["title"] for p in props][:2] == ["내역", "대시보드"]
    assert len({p["sheetId"] for p in props}) == len(props)
    hidden = {p["title"] for p in props if p["hidden"]}
    assert hidden == {"계산", "알림기록"}


def test_seed_settings_has_partner_email_and_start_day():
    seeds = {s["range"]: s["values"] for s in layout.seed_values("a@b.com")}
    assert seeds["설정!I1:J4"][1] == ["월 시작일", 1]
    assert seeds["설정!I1:J4"][3][1] == "a@b.com"
    assert ["공동"] in seeds["설정!E1:E4"]


def test_category_dropdown_uses_open_settings_range():
    reqs = layout.validation_requests()
    txn_d = [r["setDataValidation"] for r in reqs
             if r["setDataValidation"]["range"] == layout.a1_to_grid("내역!D2:D5000")][0]
    assert txn_d["rule"]["condition"] == {
        "type": "ONE_OF_RANGE", "values": [{"userEnteredValue": "=설정!$A$2:$A"}]}
    assert txn_d["rule"]["strict"] is False  # 이름 변경 직후/미분류 행이 거부되지 않도록


def test_view_tabs_protected_except_selector():
    reqs = [r["addProtectedRange"]["protectedRange"] for r in layout.protection_requests()]
    dash = [p for p in reqs if p["range"] == {"sheetId": 400}][0]
    assert dash["warningOnly"] is True
    assert dash["unprotectedRanges"] == [layout.a1_to_grid("대시보드!B1")]


def test_month_key_columns_use_month_format():
    reqs = layout.format_requests()
    l_col = [r for r in reqs if r.get("repeatCell", {}).get("range") == layout.a1_to_grid("내역!L2:L5000")][0]
    assert l_col["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]["pattern"] == '0000"-"00'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_layout.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'layout'`

- [ ] **Step 3: Write implementation** — `layout.py`

```python
"""시트 구성: 탭 정의, 생성 본문, 초기 데이터, 검증, 서식, 보호."""
import re

TXN, SETTINGS, ASSETS, DASH, TREND, CAL = "내역", "설정", "자산", "대시보드", "추이", "달력"
SEARCH, RECUR, FAV, SMS, CALC, STATE = "검색", "반복", "즐겨찾기", "문자입력", "계산", "알림기록"

# (제목, sheetId, 행, 열, 숨김) — 이 순서대로 탭이 생긴다
SHEETS = [
    (TXN, 100, 5000, 12, False),
    (DASH, 400, 100, 14, False),
    (TREND, 500, 80, 26, False),
    (CAL, 600, 20, 7, False),
    (SEARCH, 700, 1000, 10, False),
    (FAV, 900, 50, 7, False),
    (RECUR, 800, 50, 9, False),
    (SMS, 1000, 500, 3, False),
    (ASSETS, 300, 50, 5, False),
    (SETTINGS, 200, 60, 10, False),
    (CALC, 1100, 200, 3, True),
    (STATE, 1200, 500, 2, True),
]
SHEET_ID = {title: sid for title, sid, *_ in SHEETS}

TXN_HEADERS = ["날짜", "사용자", "구분", "카테고리", "소분류", "결제수단", "입금자산", "금액", "통화", "메모"]
RECUR_HEADERS = ["사용", "매월 일자", "사용자", "구분", "카테고리", "결제수단", "금액", "메모", "마지막 생성 월"]
FAV_HEADERS = ["추가", "사용자", "구분", "카테고리", "결제수단", "금액", "메모"]
EXPENSE_CATS = ["식비", "카페·간식", "생활용품", "주거·관리비", "통신", "교통", "의료", "쇼핑", "문화·여가", "경조사", "기타"]
INCOME_CATS = ["월급", "부수입", "기타수입"]
RENAME_NOTE = ("카테고리·사용자 이름을 한 칸씩 고치면 과거 내역·반복·즐겨찾기도 자동으로 바뀝니다. "
               "여러 칸을 한꺼번에 붙여넣으면 자동 변경되지 않습니다. "
               "카테고리 행을 지우면 그 카테고리의 과거 지출은 대시보드에서 '미분류'로 집계됩니다.")

USERS, CATS, ASSET_LIST, CURRENCIES = "=설정!$E$2:$E", "=설정!$A$2:$A", "=자산!$A$2:$A", "=설정!$G$2:$G"
MONTHS, YEARS = "=계산!$A$2:$A", "=계산!$B$2:$B"
MONTH_FMT = '0000"-"00'


def col_index(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def a1_to_grid(a1: str) -> dict:
    """'내역!A2:J5000' → GridRange. 끝이 열린 범위(A2:A)는 지원하지 않는다."""
    title, ref = a1.split("!")
    m = re.fullmatch(r"([A-Z]+)(\d+)(?::([A-Z]+)(\d+))?", ref)
    if not m:
        raise ValueError(f"지원하지 않는 범위: {a1}")
    c0, r0 = m.group(1), int(m.group(2))
    c1, r1 = m.group(3) or c0, int(m.group(4) or r0)
    return {"sheetId": SHEET_ID[title], "startRowIndex": r0 - 1, "endRowIndex": r1,
            "startColumnIndex": col_index(c0), "endColumnIndex": col_index(c1) + 1}


def v(a1: str, rows: list[list]) -> dict:
    return {"range": a1, "values": rows}


def number_format(a1: str, kind: str, pattern: str) -> dict:
    return {"repeatCell": {"range": a1_to_grid(a1),
                           "cell": {"userEnteredFormat": {"numberFormat": {"type": kind, "pattern": pattern}}},
                           "fields": "userEnteredFormat.numberFormat"}}


def create_body(title: str) -> dict:
    return {
        "properties": {"title": title, "locale": "ko_KR", "timeZone": "Asia/Seoul"},
        "sheets": [
            {"properties": {"sheetId": sid, "title": t, "hidden": hidden,
                            "gridProperties": {"rowCount": rows, "columnCount": cols, "frozenRowCount": 1}}}
            for t, sid, rows, cols, hidden in SHEETS
        ],
    }


def seed_values(partner_email: str) -> list[dict]:
    cats = [[c, "지출", ""] for c in EXPENSE_CATS] + [[c, "수입", ""] for c in INCOME_CATS]
    return [
        v(f"{TXN}!A1:J1", [TXN_HEADERS]),
        v(f"{SETTINGS}!A1:C1", [["카테고리", "구분", "월 예산"]]),
        v(f"{SETTINGS}!A2:C{1 + len(cats)}", cats),
        v(f"{SETTINGS}!E1:E4", [["사용자"], ["사용자1"], ["사용자2"], ["공동"]]),
        v(f"{SETTINGS}!G1:G5", [["통화"], ["KRW"], ["USD"], ["JPY"], ["EUR"]]),
        v(f"{SETTINGS}!I1:J4", [["항목", "값"], ["월 시작일", 1], ["예산 알림", True],
                                ["알림 받을 이메일(쉼표 구분)", partner_email]]),
        v(f"{SETTINGS}!I6", [[RENAME_NOTE]]),
        v(f"{ASSETS}!A1:D4", [["자산명", "종류", "초기 잔액", "월 실적 목표"], ["현금", "현금", 0, ""],
                              ["주거래통장", "통장", 0, ""], ["신용카드1", "카드", 0, ""]]),
        v(f"{RECUR}!A1:I1", [RECUR_HEADERS]),
        v(f"{FAV}!A1:G2", [FAV_HEADERS, [False, "공동", "지출", "카페·간식", "신용카드1", 4500, "커피"]]),
        v(f"{SMS}!A1:C1", [["↓ A2부터 카드 문자 붙여넣기", False, "← 체크하면 내역에 추가"]]),
        v(f"{STATE}!A1:B1", [["발송 키", "발송 시각"]]),
    ]


def _rule(ctype: str, *values, strict: bool = False) -> dict:
    cond = {"type": ctype}
    if values:
        cond["values"] = [{"userEnteredValue": str(x)} for x in values]
    return {"condition": cond, "strict": strict, "showCustomUi": True}


def validation_requests() -> list[dict]:
    rules = [
        (f"{TXN}!A2:A5000", _rule("DATE_IS_VALID")),
        (f"{TXN}!B2:B5000", _rule("ONE_OF_RANGE", USERS)),
        (f"{TXN}!C2:C5000", _rule("ONE_OF_LIST", "수입", "지출", "이체")),
        (f"{TXN}!D2:D5000", _rule("ONE_OF_RANGE", CATS)),
        (f"{TXN}!F2:G5000", _rule("ONE_OF_RANGE", ASSET_LIST)),
        (f"{TXN}!H2:H5000", _rule("NUMBER_GREATER", 0)),
        (f"{TXN}!I2:I5000", _rule("ONE_OF_RANGE", CURRENCIES)),
        (f"{SETTINGS}!B2:B60", _rule("ONE_OF_LIST", "수입", "지출")),
        (f"{SETTINGS}!J2", _rule("NUMBER_BETWEEN", 1, 28, strict=True)),
        (f"{SETTINGS}!J3", _rule("BOOLEAN")),
        (f"{ASSETS}!B2:B50", _rule("ONE_OF_LIST", "통장", "카드", "현금")),
        (f"{RECUR}!A2:A50", _rule("BOOLEAN")),
        (f"{RECUR}!B2:B50", _rule("NUMBER_BETWEEN", 1, 31, strict=True)),
        (f"{RECUR}!C2:C50", _rule("ONE_OF_RANGE", USERS)),
        (f"{RECUR}!D2:D50", _rule("ONE_OF_LIST", "수입", "지출")),
        (f"{RECUR}!E2:E50", _rule("ONE_OF_RANGE", CATS)),
        (f"{RECUR}!F2:F50", _rule("ONE_OF_RANGE", ASSET_LIST)),
        (f"{RECUR}!G2:G50", _rule("NUMBER_GREATER", 0)),
        (f"{FAV}!A2:A50", _rule("BOOLEAN")),
        (f"{FAV}!B2:B50", _rule("ONE_OF_RANGE", USERS)),
        (f"{FAV}!C2:C50", _rule("ONE_OF_LIST", "수입", "지출")),
        (f"{FAV}!D2:D50", _rule("ONE_OF_RANGE", CATS)),
        (f"{FAV}!E2:E50", _rule("ONE_OF_RANGE", ASSET_LIST)),
        (f"{FAV}!F2:F50", _rule("NUMBER_GREATER", 0)),
        (f"{SMS}!B1", _rule("BOOLEAN")),
        (f"{DASH}!B1", _rule("ONE_OF_RANGE", MONTHS)),
        (f"{CAL}!B1", _rule("ONE_OF_RANGE", MONTHS)),
        (f"{TREND}!B1", _rule("ONE_OF_RANGE", YEARS)),
        (f"{SEARCH}!B2:B3", _rule("DATE_IS_VALID")),
        (f"{SEARCH}!B4", _rule("ONE_OF_RANGE", USERS)),
    ]
    return [{"setDataValidation": {"range": a1_to_grid(a1), "rule": rule}} for a1, rule in rules]


def format_requests() -> list[dict]:
    fmts = [
        (f"{TXN}!A2:A5000", "DATE", "yyyy-mm-dd"),
        (f"{TXN}!H2:H5000", "NUMBER", "#,##0.##"),
        (f"{TXN}!K2:K5000", "NUMBER", "#,##0"),
        (f"{TXN}!L2:L5000", "NUMBER", MONTH_FMT),
        (f"{SETTINGS}!C2:C60", "NUMBER", "#,##0"),
        (f"{SETTINGS}!H2:H20", "NUMBER", "#,##0.00"),
        (f"{ASSETS}!C2:E50", "NUMBER", "#,##0"),
        (f"{RECUR}!G2:G50", "NUMBER", "#,##0"),
        (f"{RECUR}!I2:I50", "NUMBER", MONTH_FMT),
        (f"{FAV}!F2:F50", "NUMBER", "#,##0"),
        (f"{CALC}!A2:A200", "NUMBER", MONTH_FMT),
    ]
    bold = [{"repeatCell": {"range": {"sheetId": sid, "startRowIndex": 0, "endRowIndex": 1,
                                      "startColumnIndex": 0, "endColumnIndex": cols},
                            "cell": {"userEnteredFormat": {"textFormat": {"bold": True}}},
                            "fields": "userEnteredFormat.textFormat.bold"}}
            for _, sid, _, cols, _ in SHEETS]
    return [number_format(a1, kind, pattern) for a1, kind, pattern in fmts] + bold


def _protect(grid: dict, unprotected: list[dict]) -> dict:
    pr = {"range": grid, "warningOnly": True, "description": "수식 영역 — 직접 수정하지 마세요"}
    if unprotected:
        pr["unprotectedRanges"] = unprotected
    return {"addProtectedRange": {"protectedRange": pr}}


def protection_requests() -> list[dict]:
    whole = [(DASH, ["B1"]), (TREND, ["B1"]), (CAL, ["B1"]), (CALC, [])]
    parts = [f"{TXN}!K1:L5000", f"{SETTINGS}!H1:H20", f"{ASSETS}!E1:E50",
             f"{SEARCH}!A6:J1000", f"{SEARCH}!E1:E2"]
    reqs = [_protect({"sheetId": SHEET_ID[t]}, [a1_to_grid(f"{t}!{c}") for c in free]) for t, free in whole]
    return reqs + [_protect(a1_to_grid(a1), []) for a1 in parts]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_layout.py -q`
Expected: `8 passed`

- [ ] **Step 5: Commit**

```bash
git add layout.py tests/test_layout.py
git commit -m "feat: 탭 구성·초기값·드롭다운 검증·서식·보호 요청 빌더"
```

---

### Task 3: formulas.py — 내역 계산열, 환율, 계산, 자산 잔액, 대시보드

**Files:**
- Create: `formulas.py`, `tests/test_formulas.py`

**Interfaces:**
- Consumes: `layout.v`, `layout.number_format`, 탭 상수, `layout.MONTH_FMT`
- Produces:
  - 상수 `START="설정!$J$2"`, `AMT, YM, TYPE, CAT, USER, ASSET, TO_ASSET, DATE_COL`, `INC='"수입"'`, `EXP='"지출"'`, `TRF='"이체"'`
  - 대시보드 행 상수 `TABLE_HEAD=60, UNCAT_ROW=61, CAT_FIRST=62, CAT_LAST=91, SIDE_FIRST=61, SIDE_LAST=76`
  - `sumifs(*conds: tuple[str, str]) -> str`, `ym_of(expr: str) -> str`
  - `core_values() -> list[dict]`, `core_formats() -> list[dict]`

- [ ] **Step 1: Write the failing test** — `tests/test_formulas.py`

```python
import formulas


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_sumifs_builder():
    assert formulas.sumifs(("내역!$L:$L", "$B$2"), ("내역!$C:$C", '"지출"')) == \
        'SUMIFS(내역!$K:$K,내역!$L:$L,$B$2,내역!$C:$C,"지출")'


def test_txn_ym_is_numeric_key():
    l1 = _by_range(formulas.core_values())["내역!L1"][0][0]
    assert "*100+MONTH(" in l1          # 202610 같은 숫자 키 — 문자열 "2026-10" 금지
    assert "TEXT(" not in l1
    assert "설정!$J$2" in l1             # 월 시작일 반영


def test_krw_amount_uses_rate_table():
    k1 = _by_range(formulas.core_values())["내역!K1"][0][0]
    assert k1.startswith("=ARRAYFORMULA(")
    assert "VLOOKUP(I:I,설정!$G:$H,2,FALSE)" in k1


def test_dashboard_prev_month_wraps_year():
    kpi = _by_range(formulas.core_values())["대시보드!A5:F6"][1]
    assert "-89" in kpi[3]               # 202601 → 202512


def test_uncategorized_is_total_minus_listed():
    row = _by_range(formulas.core_values())["대시보드!A61:B61"][0]
    assert row == ["미분류", "=B6-SUM(B62:B91)"]


def test_asset_balance_includes_transfers_both_ways():
    e2 = _by_range(formulas.core_values())["자산!E1:E2"][1][0]
    assert e2.count('"이체"') == 2
    assert "내역!$G:$G" in e2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_formulas.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'formulas'`

- [ ] **Step 3: Write implementation** — `formulas.py`

```python
"""핵심 수식: 내역 계산열, 환율, 계산, 자산 잔액, 대시보드."""
from layout import ASSETS, CALC, DASH, MONTH_FMT, SETTINGS, TXN, number_format, v

START = "설정!$J$2"
AMT, YM, TYPE, CAT = "내역!$K:$K", "내역!$L:$L", "내역!$C:$C", "내역!$D:$D"
USER, ASSET, TO_ASSET, DATE_COL = "내역!$B:$B", "내역!$F:$F", "내역!$G:$G", "내역!$A:$A"
INC, EXP, TRF = '"수입"', '"지출"', '"이체"'

TABLE_HEAD, UNCAT_ROW, CAT_FIRST, CAT_LAST = 60, 61, 62, 91
SIDE_FIRST, SIDE_LAST = 61, 76  # 사용자·카드 표


def sumifs(*conds: tuple[str, str]) -> str:
    """원화금액 합계. conds = (범위, 조건) 쌍."""
    return "SUMIFS(" + ",".join([AMT] + [f"{rng},{crit}" for rng, crit in conds]) + ")"


def ym_of(expr: str) -> str:
    """날짜 → 월 시작일 기준 귀속월 숫자 키(YYYYMM)."""
    first = f"DATE(YEAR({expr}),MONTH({expr})-(DAY({expr})<{START}),1)"
    return f"YEAR({first})*100+MONTH({first})"


def txn_values() -> list[dict]:
    krw = 'H:H*IF(I:I="",1,IFERROR(VLOOKUP(I:I,설정!$G:$H,2,FALSE),1))'
    return [
        v(f"{TXN}!K1", [[f'=ARRAYFORMULA(IF(ROW(H:H)=1,"원화금액",IF(H:H="","",{krw})))']]),
        v(f"{TXN}!L1", [[f'=ARRAYFORMULA(IF(ROW(A:A)=1,"귀속월",IF(A:A="","",{ym_of("A:A")})))']]),
    ]


def settings_values() -> list[dict]:
    rate = '=IF(G{r}="","",IF(G{r}="KRW",1,GOOGLEFINANCE("CURRENCY:"&G{r}&"KRW")))'
    return [v(f"{SETTINGS}!H1:H20", [["환율(원)"]] + [[rate.format(r=r)] for r in range(2, 21)])]


def calc_values() -> list[dict]:
    months = '=IFERROR(SORT(UNIQUE(FILTER(내역!L2:L,내역!L2:L<>"")),1,FALSE),"")'
    years = '=IFERROR(SORT(UNIQUE(FILTER(INT(내역!L2:L/100),내역!L2:L<>"")),1,FALSE),"")'
    return [v(f"{CALC}!A1:C2", [["월목록", "연도목록", "현재월"], [months, years, f"={ym_of('TODAY()')}"]])]


def asset_values() -> list[dict]:
    a = "A2:A"
    bal = (f"C2:C+{sumifs((ASSET, a), (TYPE, INC))}-{sumifs((ASSET, a), (TYPE, EXP))}"
           f"-{sumifs((ASSET, a), (TYPE, TRF))}+{sumifs((TO_ASSET, a), (TYPE, TRF))}")
    return [v(f"{ASSETS}!E1:E2", [["현재 잔액"], [f'=ARRAYFORMULA(IF(A2:A="","",{bal}))']])]


def dashboard_values() -> list[dict]:
    m, cats, users, cards = "$B$2", "A62:A91", "F61:F76", "I61:I76"
    prev = f"IF(MOD({m},100)=1,{m}-89,{m}-1)"
    top = [["조회 월", "", "← 비우면 이번 달"],
           ["적용 월", f'=IF(B1="",{CALC}!$C$2,B1)', ""],
           ["기간", f"=DATE(INT({m}/100),MOD({m},100),{START})", "=EDATE(B3,1)-1"]]
    kpi = [["수입", "지출", "잔액", "전월 대비 지출", "일평균 지출", "월말 예상 지출"],
           [f"={sumifs((YM, m), (TYPE, INC))}", f"={sumifs((YM, m), (TYPE, EXP))}", "=A6-B6",
            f'=IFERROR(B6/{sumifs((YM, prev), (TYPE, EXP))}-1,"")',
            "=B6/MAX(1,MIN(TODAY(),$C$3)-$B$3+1)", "=E6*($C$3-$B$3+1)"]]
    head = [["카테고리", "지출", "예산", "사용률", "", "사용자", "지출", "", "카드", "사용액", "실적 목표", "달성률"]]
    cat_row = [f'=IFERROR(FILTER({SETTINGS}!$A$2:$A,{SETTINGS}!$B$2:$B="지출"),"")',
               f'=ARRAYFORMULA(IF({cats}="","",{sumifs((YM, m), (TYPE, EXP), (CAT, cats))}))',
               f'=ARRAYFORMULA(IF({cats}="","",IFERROR(VLOOKUP({cats},{SETTINGS}!$A:$C,3,FALSE),"")))',
               '=ARRAYFORMULA(IF(A62:A91="","",IF((C62:C91="")+(C62:C91=0),"",B62:B91/C62:C91)))']
    side_row = [f'=IFERROR(FILTER({SETTINGS}!$E$2:$E,{SETTINGS}!$E$2:$E<>""),"")',
                f'=ARRAYFORMULA(IF({users}="","",{sumifs((YM, m), (TYPE, EXP), (USER, users))}))',
                "",
                f'=IFERROR(FILTER({ASSETS}!$A$2:$A,{ASSETS}!$B$2:$B="카드"),"")',
                f'=ARRAYFORMULA(IF({cards}="","",{sumifs((YM, m), (TYPE, EXP), (ASSET, cards))}))',
                f'=ARRAYFORMULA(IF({cards}="","",IFERROR(VLOOKUP({cards},{ASSETS}!$A:$D,4,FALSE),"")))',
                '=ARRAYFORMULA(IF(I61:I76="","",IF((K61:K76="")+(K61:K76=0),"",J61:J76/K61:K76)))']
    return [v(f"{DASH}!A1:C3", top), v(f"{DASH}!A5:F6", kpi), v(f"{DASH}!A60:L60", head),
            v(f"{DASH}!A61:B61", [["미분류", "=B6-SUM(B62:B91)"]]),
            v(f"{DASH}!A62:D62", [cat_row]), v(f"{DASH}!F61:L61", [side_row])]


def core_values() -> list[dict]:
    return txn_values() + settings_values() + calc_values() + asset_values() + dashboard_values()


def core_formats() -> list[dict]:
    fmts = [
        (f"{DASH}!B1:B2", "NUMBER", MONTH_FMT), (f"{DASH}!B3:C3", "DATE", "yyyy-mm-dd"),
        (f"{DASH}!A6:C6", "NUMBER", "#,##0"), (f"{DASH}!D6", "PERCENT", "0.0%"),
        (f"{DASH}!E6:F6", "NUMBER", "#,##0"), (f"{DASH}!B61:C91", "NUMBER", "#,##0"),
        (f"{DASH}!D62:D91", "PERCENT", "0%"), (f"{DASH}!G61:G76", "NUMBER", "#,##0"),
        (f"{DASH}!J61:K76", "NUMBER", "#,##0"), (f"{DASH}!L61:L76", "PERCENT", "0%"),
    ]
    return [number_format(a1, kind, pattern) for a1, kind, pattern in fmts]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_formulas.py -q`
Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add formulas.py tests/test_formulas.py
git commit -m "feat: 원화환산·귀속월·자산잔액·대시보드 수식"
```

---

### Task 4: views.py — 추이, 달력, 검색

**Files:**
- Create: `views.py`, `tests/test_views.py`

**Interfaces:**
- Consumes: `formulas.sumifs, START, YM, TYPE, CAT, DATE_COL, INC, EXP`, `layout.v, number_format, TXN_HEADERS, MONTH_FMT`, 탭 상수
- Produces: 추이 행 상수 `TR_HEAD=38, TR_FIRST=39, HEAT_LAST=68, YEAR_LAST=58`; `view_values() -> list[dict]`, `view_formats() -> list[dict]`, `search_cond() -> str`

- [ ] **Step 1: Write the failing test** — `tests/test_views.py`

```python
import views


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_heatmap_cell_uses_month_offset_and_row_category():
    cells = _by_range(views.view_values())["추이!G39:R68"]
    assert len(cells) == 30 and all(len(r) == 12 for r in cells)
    assert "$B$2*100+1," in cells[0][0] and "$F39" in cells[0][0]
    assert "$B$2*100+12," in cells[29][11] and "$F68" in cells[29][11]


def test_calendar_grid_has_date_and_amount_rows():
    grid = _by_range(views.view_values())["달력!A5:G16"]
    assert len(grid) == 12
    assert grid[0][0] == '=IF(AND($E$2+0>=$C$2,$E$2+0<=$D$2),$E$2+0,"")'
    assert grid[11][6].startswith('=IF(G15="","",SUMIFS(')


def test_search_blank_inputs_mean_no_filter():
    c = views.search_cond()
    for cell in ("$B$1", "$B$2", "$B$3", "$B$4"):
        assert f'(({cell}="")+' in c


def test_yearly_uses_range_not_text_match():
    yearly = _by_range(views.view_values())["추이!T39:W39"][0]
    assert '">="&T39:T58*100' in yearly[1] and '"<"&(T39:T58+1)*100' in yearly[1]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_views.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'views'`

- [ ] **Step 3: Write implementation** — `views.py`

```python
"""보기 탭 수식: 추이(월별·카테고리×월·연도별), 달력, 검색."""
from formulas import CAT, DATE_COL, EXP, INC, START, TYPE, YM, sumifs
from layout import CAL, CALC, MONTH_FMT, SEARCH, TREND, TXN_HEADERS, number_format, v

TR_HEAD, TR_FIRST, HEAT_LAST, YEAR_LAST = 38, 39, 68, 58


def _trend_monthly(y: str) -> list[dict]:
    months = f"{y}*100+SEQUENCE(12)"
    row = ['=ARRAYFORMULA(SEQUENCE(12)&"월")',
           f"=ARRAYFORMULA({sumifs((YM, months), (TYPE, INC))})",
           f"=ARRAYFORMULA({sumifs((YM, months), (TYPE, EXP))})",
           "=ARRAYFORMULA(B39:B50-C39:C50)"]
    return [v(f"{TREND}!A39:D39", [row])]


def _trend_heatmap(y: str) -> list[dict]:
    cats = '=IFERROR(FILTER(설정!$A$2:$A,설정!$B$2:$B="지출"),"")'
    cells = []
    for r in range(TR_FIRST, HEAT_LAST + 1):
        cells.append([f'=IF($F{r}="","",{sumifs((YM, f"{y}*100+{i}"), (TYPE, EXP), (CAT, f"$F{r}"))})'
                      for i in range(1, 13)])
    return [v(f"{TREND}!F39", [[cats]]), v(f"{TREND}!G39:R68", cells)]


def _trend_yearly() -> list[dict]:
    years = "T39:T58"
    ge, lt = f'">="&{years}*100', f'"<"&({years}+1)*100'
    inc, exp = sumifs((YM, ge), (YM, lt), (TYPE, INC)), sumifs((YM, ge), (YM, lt), (TYPE, EXP))
    row = ['=IFERROR(ARRAYFORMULA(TO_TEXT(SORT(UNIQUE(FILTER(INT(내역!L2:L/100),내역!L2:L<>""))))),"")',
           f'=ARRAYFORMULA(IF({years}="","",{inc}))',
           f'=ARRAYFORMULA(IF({years}="","",{exp}))',
           f'=ARRAYFORMULA(IF({years}="","",U39:U58-V39:V58))']
    return [v(f"{TREND}!T39:W39", [row])]


def trend_values() -> list[dict]:
    y = "$B$2"
    top = [["연도", "", "← 비우면 올해"], ["적용 연도", f'=IF(B1="",INT({CALC}!$C$2/100),B1)', ""]]
    head = [["월", "수입", "지출", "잔액", "", "카테고리"] + [f"{i}월" for i in range(1, 13)]
            + ["", "연도", "수입", "지출", "잔액"]]
    return ([v(f"{TREND}!A1:C2", top), v(f"{TREND}!A38:W38", head)]
            + _trend_monthly(y) + _trend_heatmap(y) + _trend_yearly())


def calendar_values() -> list[dict]:
    top = [["조회 월", "", "기간 시작", "기간 끝", "그리드 시작"],
           ["적용 월", f'=IF(B1="",{CALC}!$C$2,B1)', f"=DATE(INT(B2/100),MOD(B2,100),{START})",
            "=EDATE(C2,1)-1", "=C2-WEEKDAY(C2)+1"]]
    grid = []
    for w in range(6):
        date_row = 5 + 2 * w
        grid.append([f'=IF(AND($E$2+{w * 7 + c}>=$C$2,$E$2+{w * 7 + c}<=$D$2),$E$2+{w * 7 + c},"")'
                     for c in range(7)])
        grid.append([f'=IF({col}{date_row}="","",{sumifs((DATE_COL, f"{col}{date_row}"), (TYPE, EXP))})'
                     for col in "ABCDEFG"])
    week = [["일", "월", "화", "수", "목", "금", "토"]]
    return [v(f"{CAL}!A1:E2", top), v(f"{CAL}!A4:G4", week), v(f"{CAL}!A5:G16", grid)]


def search_cond() -> str:
    """빈 입력칸은 조건 없음으로 취급하는 FILTER 조건(숫자 배열)."""
    return ('(내역!A2:A<>"")'
            '*((($B$1="")+ISNUMBER(SEARCH($B$1,내역!D2:D&" "&내역!E2:E&" "&내역!J2:J)))>0)'
            '*((($B$2="")+(내역!A2:A>=$B$2))>0)'
            '*((($B$3="")+(내역!A2:A<=$B$3))>0)'
            '*((($B$4="")+(내역!B2:B=$B$4))>0)')


def search_values() -> list[dict]:
    c = search_cond()
    totals = [["지출 합계", f'=IFERROR(SUM(FILTER(내역!K2:K,{c}*(내역!C2:C="지출"))),0)'],
              ["수입 합계", f'=IFERROR(SUM(FILTER(내역!K2:K,{c}*(내역!C2:C="수입"))),0)']]
    return [v(f"{SEARCH}!A1:A4", [["키워드"], ["시작일"], ["종료일"], ["사용자"]]),
            v(f"{SEARCH}!D1:E2", totals),
            v(f"{SEARCH}!A6:J6", [TXN_HEADERS]),
            v(f"{SEARCH}!A7", [[f'=IFERROR(FILTER(내역!A2:J,{c}),"결과 없음")']])]


def view_values() -> list[dict]:
    return trend_values() + calendar_values() + search_values()


def view_formats() -> list[dict]:
    fmts = [(f"{TREND}!B39:D50", "NUMBER", "#,##0"), (f"{TREND}!G39:R68", "NUMBER", "#,##0"),
            (f"{TREND}!U39:W58", "NUMBER", "#,##0"),
            (f"{CAL}!B2", "NUMBER", MONTH_FMT), (f"{CAL}!C2:E2", "DATE", "yyyy-mm-dd"),
            (f"{SEARCH}!E1:E2", "NUMBER", "#,##0"), (f"{SEARCH}!A7:A1000", "DATE", "yyyy-mm-dd"),
            (f"{SEARCH}!H7:H1000", "NUMBER", "#,##0")]
    for w in range(6):
        fmts.append((f"{CAL}!A{5 + 2 * w}:G{5 + 2 * w}", "DATE", "m/d"))
        fmts.append((f"{CAL}!A{6 + 2 * w}:G{6 + 2 * w}", "NUMBER", "#,##0;-#,##0;"))
    return [number_format(a1, kind, pattern) for a1, kind, pattern in fmts]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_views.py -q`
Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add views.py tests/test_views.py
git commit -m "feat: 추이·달력·검색 탭 수식"
```

---

### Task 5: charts.py — 차트 5개 + 조건부 서식

**Files:**
- Create: `charts.py`, `tests/test_charts.py`

**Interfaces:**
- Consumes: `layout.a1_to_grid, SHEET_ID, DASH, TREND, CAL`
- Produces: `chart_requests() -> list[dict]` (5개), `conditional_requests() -> list[dict]`

- [ ] **Step 1: Write the failing test** — `tests/test_charts.py`

```python
import charts


def _specs():
    return [r["addChart"]["chart"]["spec"] for r in charts.chart_requests()]


def test_five_charts_with_expected_titles():
    assert [s["title"] for s in _specs()] == [
        "카테고리별 지출", "예산 대비 지출", "사용자별 지출", "월별 수입·지출·잔액", "연도별 수입·지출·잔액"]


def test_donut_has_hole():
    assert _specs()[0]["pieChart"]["pieHole"] == 0.5


def test_series_type_only_on_combo():
    combo = _specs()[3]["basicChart"]
    assert combo["chartType"] == "COMBO"
    assert [s["type"] for s in combo["series"]] == ["COLUMN", "COLUMN", "LINE"]
    column = _specs()[1]["basicChart"]
    assert all("type" not in s for s in column["series"])


def test_charts_stacked_vertically_for_phone():
    anchors = [r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]
               for r in charts.chart_requests()]
    assert all(a["columnIndex"] == 0 for a in anchors)


def test_budget_over_100_is_red_and_first():
    rules = [r["addConditionalFormatRule"] for r in charts.conditional_requests()]
    first = rules[0]
    assert first["index"] == 0
    assert first["rule"]["booleanRule"]["condition"]["values"] == [{"userEnteredValue": "1"}]
    assert first["rule"]["booleanRule"]["format"]["backgroundColor"] == charts.RED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_charts.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'charts'`

- [ ] **Step 3: Write implementation** — `charts.py`

```python
"""차트(폰에서 보기 좋게 세로로 쌓음)와 조건부 서식."""
from layout import CAL, DASH, SHEET_ID, TREND, a1_to_grid

RED = {"red": 0.96, "green": 0.8, "blue": 0.8}
ORANGE = {"red": 1.0, "green": 0.9, "blue": 0.7}
GREEN = {"red": 0.8, "green": 0.94, "blue": 0.8}
WHITE = {"red": 1.0, "green": 1.0, "blue": 1.0}
HEAT = {"red": 0.9, "green": 0.4, "blue": 0.4}


def _src(a1: str) -> dict:
    return {"sourceRange": {"sources": [a1_to_grid(a1)]}}


def _chart(spec: dict, sheet: str, row: int) -> dict:
    anchor = {"sheetId": SHEET_ID[sheet], "rowIndex": row, "columnIndex": 0}
    return {"addChart": {"chart": {"spec": spec, "position": {"overlayPosition": {
        "anchorCell": anchor, "widthPixels": 600, "heightPixels": 320}}}}}


def _basic(title: str, kind: str, domain: str, series: list[tuple[str, str]]) -> dict:
    out = []
    for a1, stype in series:
        s = {"series": _src(a1), "targetAxis": "LEFT_AXIS"}
        if kind == "COMBO":
            s["type"] = stype
        out.append(s)
    return {"title": title, "basicChart": {"chartType": kind, "legendPosition": "BOTTOM_LEGEND",
                                           "headerCount": 1, "domains": [{"domain": _src(domain)}],
                                           "series": out}}


def chart_requests() -> list[dict]:
    d, t = DASH, TREND
    pie = {"title": "카테고리별 지출", "pieChart": {"legendPosition": "RIGHT_LEGEND", "pieHole": 0.5,
                                              "domain": _src(f"{d}!A61:A91"), "series": _src(f"{d}!B61:B91")}}
    return [
        _chart(pie, d, 7),
        _chart(_basic("예산 대비 지출", "COLUMN", f"{d}!A60:A91",
                      [(f"{d}!B60:B91", "COLUMN"), (f"{d}!C60:C91", "COLUMN")]), d, 24),
        _chart(_basic("사용자별 지출", "COLUMN", f"{d}!F60:F76", [(f"{d}!G60:G76", "COLUMN")]), d, 41),
        _chart(_basic("월별 수입·지출·잔액", "COMBO", f"{t}!A38:A50",
                      [(f"{t}!B38:B50", "COLUMN"), (f"{t}!C38:C50", "COLUMN"), (f"{t}!D38:D50", "LINE")]), t, 3),
        _chart(_basic("연도별 수입·지출·잔액", "COLUMN", f"{t}!T38:T58",
                      [(f"{t}!U38:U58", "COLUMN"), (f"{t}!V38:V58", "COLUMN"), (f"{t}!W38:W58", "COLUMN")]), t, 20),
    ]


def _bool_rule(a1: str, value: float, color: dict, index: int) -> dict:
    cond = {"type": "NUMBER_GREATER_THAN_EQ", "values": [{"userEnteredValue": str(value)}]}
    return {"addConditionalFormatRule": {"index": index, "rule": {
        "ranges": [a1_to_grid(a1)], "booleanRule": {"condition": cond, "format": {"backgroundColor": color}}}}}


def _gradient(ranges: list[str]) -> dict:
    return {"addConditionalFormatRule": {"index": 0, "rule": {
        "ranges": [a1_to_grid(a) for a in ranges],
        "gradientRule": {"minpoint": {"type": "MIN", "color": WHITE}, "maxpoint": {"type": "MAX", "color": HEAT}}}}}


def conditional_requests() -> list[dict]:
    budget = f"{DASH}!D62:D91"
    return [
        _bool_rule(budget, 1, RED, 0),
        _bool_rule(budget, 0.8, ORANGE, 1),
        _bool_rule(f"{DASH}!L61:L76", 1, GREEN, 2),
        _gradient([f"{TREND}!G39:R68"]),
        _gradient([f"{CAL}!A{r}:G{r}" for r in range(6, 17, 2)]),
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_charts.py -q`
Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add charts.py tests/test_charts.py
git commit -m "feat: 도넛·예산·사용자·월별·연도별 차트와 조건부 서식"
```

---

### Task 6: build_budget.py — 조립·생성·공유 + 전체 정합성 테스트

**Files:**
- Create: `build_budget.py`, `tests/test_build.py`

**Interfaces:**
- Consumes: Tasks 1–5 의 모든 공개 함수
- Produces: `partner_email() -> str`, `structure_requests() / visual_requests() -> list[dict]`, `value_data(email: str) -> list[dict]`, `build_sheet(title: str, email: str) -> str`(URL); 파일 `.spreadsheet_id`

- [ ] **Step 1: Write the failing test** — `tests/test_build.py`

```python
import re

import pytest

import build_budget
import layout


def _cells(entry):
    title, ref = entry["range"].split("!")
    m = re.fullmatch(r"([A-Z]+)(\d+)(?::[A-Z]+\d+)?", ref)
    c0, r0 = layout.col_index(m.group(1)), int(m.group(2))
    return {(title, r0 + i, c0 + j) for i, row in enumerate(entry["values"]) for j in range(len(row))}


def test_value_shapes_match_declared_ranges():
    for e in build_budget.value_data("a@b.com"):
        g = layout.a1_to_grid(e["range"])
        assert len(e["values"]) == g["endRowIndex"] - g["startRowIndex"], e["range"]
        for row in e["values"]:
            assert len(row) == g["endColumnIndex"] - g["startColumnIndex"], e["range"]


def test_no_two_writes_hit_same_cell():
    seen = set()
    for e in build_budget.value_data("a@b.com"):
        cells = _cells(e)
        assert not (seen & cells), e["range"]
        seen |= cells


def test_formula_parentheses_balanced():
    for e in build_budget.value_data("a@b.com"):
        for row in e["values"]:
            for cell in row:
                if isinstance(cell, str) and cell.startswith("="):
                    depth = 0
                    for ch in re.sub(r'"[^"]*"', "", cell):
                        depth += {"(": 1, ")": -1}.get(ch, 0)
                        assert depth >= 0, cell
                    assert depth == 0, cell


def test_every_request_is_single_op():
    for r in build_budget.structure_requests() + build_budget.visual_requests():
        assert len(r) == 1


@pytest.mark.parametrize("bad", ["", "nope", "a@b", "a b@c.com"])
def test_partner_email_validated(monkeypatch, bad):
    monkeypatch.setenv("BUDGET_PARTNER_EMAIL", bad)
    with pytest.raises(ValueError):
        build_budget.partner_email()


def test_partner_email_missing(monkeypatch):
    monkeypatch.delenv("BUDGET_PARTNER_EMAIL", raising=False)
    with pytest.raises(ValueError, match="BUDGET_PARTNER_EMAIL not set"):
        build_budget.partner_email()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_build.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'build_budget'`

- [ ] **Step 3: Write implementation** — `build_budget.py`

```python
"""가계부 스프레드시트를 새로 만들고 배우자에게 편집 권한으로 공유한다.

사용: BUDGET_CLIENT_SECRET=... BUDGET_PARTNER_EMAIL=... python3 build_budget.py ["시트 제목"]
"""
import os
import re
import sys
from pathlib import Path

from googleapiclient.discovery import build

import charts
import formulas
import layout
import views
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
            + views.view_formats() + layout.protection_requests())


def value_data(email: str) -> list[dict]:
    return layout.seed_values(email) + formulas.core_values() + views.view_values()


def visual_requests() -> list[dict]:
    return charts.chart_requests() + charts.conditional_requests()


def build_sheet(title: str, email: str) -> str:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    created = sheets.create(body=layout.create_body(title), fields="spreadsheetId,spreadsheetUrl").execute()
    sid = created["spreadsheetId"]
    ID_FILE.write_text(sid)  # 이후 단계가 실패해도 어떤 시트인지 남긴다
    sheets.batchUpdate(spreadsheetId=sid, body={"requests": structure_requests()}).execute()
    sheets.values().batchUpdate(spreadsheetId=sid, body={
        "valueInputOption": "USER_ENTERED", "data": value_data(email)}).execute()
    sheets.batchUpdate(spreadsheetId=sid, body={"requests": visual_requests()}).execute()
    build("drive", "v3", credentials=creds).permissions().create(
        fileId=sid, body={"type": "user", "role": "writer", "emailAddress": email},
        sendNotificationEmail=True).execute()
    return created["spreadsheetUrl"]


if __name__ == "__main__":
    print(build_sheet(sys.argv[1] if len(sys.argv) > 1 else "우리집 가계부", partner_email()))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q`
Expected: 모든 테스트 통과 (`test_build.py` 9개 포함, 합계 35 passed). 실패하면 해당 range의 shape/겹침/괄호를 Task 2–4 코드에서 고친다.

- [ ] **Step 5: Commit**

```bash
git add build_budget.py tests/test_build.py
git commit -m "feat: 시트 생성·공유 진입점과 전체 정합성 테스트"
```

---

### Task 7: logic.gs — 다음 빈 행, 이름 치환, onEdit 라우팅

**Files:**
- Create: `apps-script/logic.gs`, `tests/logic.test.js`

**Interfaces:**
- Produces (Apps Script 전역 함수):
  - `TXN_COLS = 10`, `RENAME_TARGETS`
  - `nextEmptyRow(colAValues: any[][]) -> number` (1-based)
  - `replaceExact(values: any[][], from: string, to: string) -> {values: any[][], changed: number}`
  - `routeEdit(ev: {sheet,row,col,numRows,numCols,oldValue,value}) -> null | {type:'rename',from,to,targets:[[sheet,col]...]} | {type:'favorite',row} | {type:'sms'}`

- [ ] **Step 1: Write the failing test** — `tests/logic.test.js`

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', 'logic.gs'), 'utf8'), ctx);
const plain = (x) => JSON.parse(JSON.stringify(x)); // vm 렐름 객체 비교용

const ev = (o) => Object.assign({ numRows: 1, numCols: 1 }, o);

test('nextEmptyRow: 마지막 값 다음 행 (중간 공백 무시)', () => {
  assert.equal(ctx.nextEmptyRow([['날짜'], ['2026-10-01'], [''], ['x'], [''], ['']]), 5);
  assert.equal(ctx.nextEmptyRow([['날짜'], [''], ['']]), 2);
  assert.equal(ctx.nextEmptyRow([['날짜'], [new Date(2026, 9, 1)], [null]]), 3);
});

test('replaceExact: 정확히 일치하는 값만 바꾸고 원본은 그대로', () => {
  const orig = [['식비'], ['식비2'], ['식비']];
  const res = ctx.replaceExact(orig, '식비', '외식');
  assert.deepEqual(plain(res), { values: [['외식'], ['식비2'], ['외식']], changed: 2 });
  assert.deepEqual(orig, [['식비'], ['식비2'], ['식비']]);
});

test('routeEdit: 설정 카테고리 이름 변경 → 내역·반복·즐겨찾기', () => {
  const a = ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 1, oldValue: '식비', value: '외식' }));
  assert.deepEqual(plain(a), { type: 'rename', from: '식비', to: '외식',
    targets: [['내역', 4], ['반복', 5], ['즐겨찾기', 4]] });
});

test('routeEdit: 사용자·자산 이름 변경 대상 열', () => {
  const u = ctx.routeEdit(ev({ sheet: '설정', row: 2, col: 5, oldValue: '사용자1', value: '성재' }));
  assert.deepEqual(plain(u.targets), [['내역', 2], ['반복', 3], ['즐겨찾기', 2]]);
  const a = ctx.routeEdit(ev({ sheet: '자산', row: 4, col: 1, oldValue: '신용카드1', value: '신한카드' }));
  assert.deepEqual(plain(a.targets), [['내역', 6], ['내역', 7], ['반복', 6], ['즐겨찾기', 5]]);
});

test('routeEdit: 새로 추가/지우기/여러 칸/헤더/같은 값은 무시', () => {
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 20, col: 1, oldValue: undefined, value: '반려동물' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 1, oldValue: '식비', value: undefined })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 1, numRows: 3, oldValue: '식비', value: '외식' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 1, col: 1, oldValue: '카테고리', value: '분류' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 1, oldValue: '식비', value: ' 식비 ' })), null);
  assert.equal(ctx.routeEdit(ev({ sheet: '설정', row: 3, col: 3, oldValue: '1', value: '2' })), null);
});

test('routeEdit: 즐겨찾기 체크 / 문자입력 체크', () => {
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '즐겨찾기', row: 2, col: 1, value: 'TRUE' }))),
    { type: 'favorite', row: 2 });
  assert.equal(ctx.routeEdit(ev({ sheet: '즐겨찾기', row: 2, col: 1, value: 'FALSE' })), null);
  assert.deepEqual(plain(ctx.routeEdit(ev({ sheet: '문자입력', row: 1, col: 2, value: 'TRUE' }))), { type: 'sms' });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/logic.test.js`
Expected: FAIL — `ENOENT: no such file or directory ... apps-script/logic.gs`

- [ ] **Step 3: Write implementation** — `apps-script/logic.gs`

```js
/* 순수 로직 — SpreadsheetApp 등 Apps Script 전역에 의존하지 않는다 (node --test 대상). */

var TXN_COLS = 10; // 내역 A:J (K:L은 수식 열)

// 시트 이름 → 편집된 열(1-based) → 이름을 바꿔야 할 [시트, 열] 목록
var RENAME_TARGETS = {
  '설정': {
    1: [['내역', 4], ['반복', 5], ['즐겨찾기', 4]], // A열 카테고리
    5: [['내역', 2], ['반복', 3], ['즐겨찾기', 2]]  // E열 사용자
  },
  '자산': {
    1: [['내역', 6], ['내역', 7], ['반복', 6], ['즐겨찾기', 5]] // A열 자산명
  }
};

function isBlank(x) {
  return x === '' || x === null || x === undefined;
}

// ARRAYFORMULA 열 때문에 getLastRow()/appendRow()는 시트 끝을 가리키므로 A열로 판단한다.
function nextEmptyRow(colAValues) {
  for (var i = colAValues.length - 1; i >= 1; i--) {
    if (!isBlank(colAValues[i][0])) return i + 2;
  }
  return 2;
}

function replaceExact(values, from, to) {
  var changed = 0;
  var out = values.map(function (row) {
    if (row[0] === from) {
      changed++;
      return [to];
    }
    return [row[0]];
  });
  return { values: out, changed: changed };
}

function routeEdit(ev) {
  if (ev.numRows !== 1 || ev.numCols !== 1) return null;
  if (ev.sheet === '문자입력' && ev.row === 1 && ev.col === 2) {
    return ev.value === 'TRUE' ? { type: 'sms' } : null;
  }
  if (ev.row < 2) return null;
  if (ev.sheet === '즐겨찾기' && ev.col === 1) {
    return ev.value === 'TRUE' ? { type: 'favorite', row: ev.row } : null;
  }
  var targets = (RENAME_TARGETS[ev.sheet] || {})[ev.col];
  if (!targets) return null;
  var from = isBlank(ev.oldValue) ? '' : String(ev.oldValue).trim();
  var to = isBlank(ev.value) ? '' : String(ev.value).trim();
  if (!from || !to || from === to) return null; // 새 항목 추가·삭제는 과거 내역을 건드리지 않는다
  return { type: 'rename', from: from, to: to, targets: targets };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/logic.test.js`
Expected: `# pass 6`, `# fail 0`

- [ ] **Step 5: Commit**

```bash
git add apps-script/logic.gs tests/logic.test.js
git commit -m "feat: onEdit 라우팅·이름 치환·다음 빈 행 순수 로직"
```

---

### Task 8: logic.gs — 귀속월·반복 일정

**Files:**
- Modify: `apps-script/logic.gs` (끝에 추가), `tests/logic.test.js` (끝에 추가)

**Interfaces:**
- Produces: `ymKey(date: Date, startDay: number) -> number`, `calendarYm(date: Date) -> number`, `lastDayOfMonth(date: Date) -> number`, `isRecurringDue(day: number, lastYm: any, today: Date) -> boolean`, `dueDate(day: number, today: Date) -> Date`

- [ ] **Step 1: Write the failing test** — `tests/logic.test.js` 끝에 추가

```js
test('ymKey: 월 시작일 기준 귀속월', () => {
  assert.equal(ctx.ymKey(new Date(2026, 9, 5), 1), 202610);
  assert.equal(ctx.ymKey(new Date(2026, 9, 5), 10), 202609);
  assert.equal(ctx.ymKey(new Date(2026, 0, 5), 10), 202512);
  assert.equal(ctx.ymKey(new Date(2026, 9, 10), 10), 202610);
});

test('isRecurringDue: 31일 항목은 짧은 달 말일에 생성', () => {
  assert.equal(ctx.isRecurringDue(31, '', new Date(2027, 1, 28)), true);
  assert.equal(ctx.isRecurringDue(31, '', new Date(2027, 1, 27)), false);
  assert.equal(ctx.isRecurringDue(31, 202609, new Date(2026, 8, 30)), false); // 이미 생성
});

test('isRecurringDue: 트리거가 하루 빠져도 다음날 생성, 같은 달 중복 없음', () => {
  assert.equal(ctx.isRecurringDue(5, 202609, new Date(2026, 9, 7)), true);
  assert.equal(ctx.isRecurringDue(5, 202610, new Date(2026, 9, 7)), false);
  assert.equal(ctx.isRecurringDue(5, '202610', new Date(2026, 9, 7)), false); // 시트 값이 문자열이어도
});

test('dueDate: 말일 보정', () => {
  const d = ctx.dueDate(31, new Date(2027, 1, 28));
  assert.deepEqual([d.getFullYear(), d.getMonth(), d.getDate()], [2027, 1, 28]);
  assert.equal(ctx.calendarYm(new Date(2026, 9, 6)), 202610);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/logic.test.js`
Expected: FAIL — `TypeError: ctx.ymKey is not a function`

- [ ] **Step 3: Write implementation** — `apps-script/logic.gs` 끝에 추가

```js
function ymKey(date, startDay) {
  var back = date.getDate() < startDay ? 1 : 0;
  var first = new Date(date.getFullYear(), date.getMonth() - back, 1);
  return first.getFullYear() * 100 + first.getMonth() + 1;
}

function calendarYm(date) {
  return date.getFullYear() * 100 + date.getMonth() + 1;
}

function lastDayOfMonth(date) {
  return new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate();
}

// 반복 항목은 달력 월 기준. 오늘이 (보정된) 일자 이후이고 이번 달에 아직 안 만들었으면 생성.
function isRecurringDue(day, lastYm, today) {
  if (Number(lastYm) === calendarYm(today)) return false;
  return today.getDate() >= Math.min(day, lastDayOfMonth(today));
}

function dueDate(day, today) {
  return new Date(today.getFullYear(), today.getMonth(), Math.min(day, lastDayOfMonth(today)));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/logic.test.js`
Expected: `# pass 10`, `# fail 0`

- [ ] **Step 5: Commit**

```bash
git add apps-script/logic.gs tests/logic.test.js
git commit -m "feat: 귀속월·반복 일정 계산"
```

---

### Task 9: logic.gs — 카드 문자 파싱

**Files:**
- Modify: `apps-script/logic.gs` (끝에 추가), `tests/logic.test.js` (끝에 추가)

**Interfaces:**
- Produces: `splitMessages(lines: any[]) -> [{startRow: number, text: string}]` (startRow는 lines의 0-based 인덱스), `parseCardSms(text: string, today: Date) -> {status:'ok', date:'YYYY-MM-DD', amount:number, card:string, merchant:string} | {status:'cancel'} | {status:'fail'}`, `cardName(text: string) -> string`, `matchAsset(card: string, assetNames: string[]) -> string`

- [ ] **Step 1: Write the failing test** — `tests/logic.test.js` 끝에 추가

```js
const SHINHAN = '신한카드(1234)승인 홍*동 12,000원(일시불)10/05 12:30 스타벅스 누적1,234,567원';
const KB = ['[Web발신]', 'KB국민카드1*2*승인', '홍*동님', '45,000원 일시불', '10/04 19:10', '이마트', '누적987,000원'];
const TODAY = new Date(2026, 9, 6);

test('parseCardSms: 신한 한 줄 형식', () => {
  assert.deepEqual(plain(ctx.parseCardSms(SHINHAN, TODAY)),
    { status: 'ok', date: '2026-10-05', amount: 12000, card: '신한', merchant: '스타벅스' });
});

test('parseCardSms: KB 여러 줄 형식, 누적금액을 결제금액으로 착각하지 않음', () => {
  const p = ctx.parseCardSms(KB.join('\n'), TODAY);
  assert.deepEqual(plain(p), { status: 'ok', date: '2026-10-04', amount: 45000, card: '국민', merchant: '이마트' });
});

test('parseCardSms: 취소·인식 불가', () => {
  assert.equal(ctx.parseCardSms('[Web발신]\n삼성1234승인취소 12,000원 10/05 12:30 스타벅스', TODAY).status, 'cancel');
  assert.equal(ctx.parseCardSms('안녕하세요 광고입니다', TODAY).status, 'fail');
  assert.equal(ctx.parseCardSms('현대카드 승인 12,000원 13/45 12:30 가게', TODAY).status, 'fail');
});

test('parseCardSms: 1월에 받은 12/31 문자는 작년', () => {
  const p = ctx.parseCardSms('현대카드 승인 홍*동 8,000원 일시불 12/31 23:50 편의점', new Date(2027, 0, 2));
  assert.equal(p.date, '2026-12-31');
});

test('splitMessages: 여러 문자를 행 단위로 붙여넣어도 나눈다', () => {
  const lines = [SHINHAN, ''].concat(KB, ['']);
  const msgs = plain(ctx.splitMessages(lines));
  assert.equal(msgs.length, 2);
  assert.equal(msgs[0].startRow, 0);
  assert.equal(msgs[1].startRow, 2);
  assert.ok(msgs[1].text.startsWith('[Web발신]\nKB국민카드'));
});

test('cardName / matchAsset', () => {
  assert.equal(ctx.cardName('NH농협카드 승인'), '농협');
  assert.equal(ctx.cardName('알 수 없음'), '');
  assert.equal(ctx.matchAsset('신한', ['현금', '신한카드', '국민카드']), '신한카드');
  assert.equal(ctx.matchAsset('삼성', ['현금']), '');
  assert.equal(ctx.matchAsset('', ['현금']), '');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/logic.test.js`
Expected: FAIL — `TypeError: ctx.parseCardSms is not a function`

- [ ] **Step 3: Write implementation** — `apps-script/logic.gs` 끝에 추가

```js
// 카드사마다 문자 형식이 달라 휴리스틱으로 파싱한다. 실패한 문자는 '인식 실패'로 남겨 사람이 처리.
var CARD_RE = /KB국민|NH농협|국민|신한|삼성|현대|롯데|우리|하나|BC|농협/;
var CARD_ALIAS = { 'KB국민': '국민', 'NH농협': '농협' };

function cardName(text) {
  var m = String(text).match(CARD_RE);
  if (!m) return '';
  return CARD_ALIAS[m[0]] || m[0];
}

function matchAsset(card, assetNames) {
  if (!card) return '';
  for (var i = 0; i < assetNames.length; i++) {
    if (String(assetNames[i]).indexOf(card) !== -1) return assetNames[i];
  }
  return '';
}

function pad2(n) {
  return (n < 10 ? '0' : '') + n;
}

function isComplete(text) {
  return /[\d,]+\s*원/.test(text) && /\d{1,2}\/\d{1,2}/.test(text);
}

function splitMessages(lines) {
  var msgs = [];
  var cur = null;
  lines.forEach(function (raw, i) {
    var line = isBlank(raw) ? '' : String(raw).trim();
    if (!line) return;
    var startsNew = /\[Web발신\]/.test(line) ||
      (cur && isComplete(cur.text) && /승인|취소/.test(line) && cardName(line));
    if (!cur || startsNew) {
      cur = { startRow: i, text: '' };
      msgs.push(cur);
    }
    cur.text += (cur.text ? '\n' : '') + line;
  });
  return msgs;
}

function merchantAfter(body, dateMatch) {
  var rest = body.slice(dateMatch.index + dateMatch[0].length);
  var lines = rest.split('\n').map(function (s) { return s.trim(); }).filter(Boolean);
  return lines.length ? lines[0] : '';
}

function parseCardSms(text, today) {
  if (/취소/.test(text)) return { status: 'cancel' };
  var body = text.replace(/(누적|잔액)\s*[\d,]+\s*원/g, '');
  var amt = body.match(/([\d,]+)\s*원/);
  var dm = body.match(/(\d{1,2})\/(\d{1,2})(?:\s+\d{1,2}:\d{2})?/);
  if (!amt || !dm) return { status: 'fail' };
  var amount = Number(amt[1].replace(/,/g, ''));
  var month = Number(dm[1]);
  var day = Number(dm[2]);
  if (!amount || month < 1 || month > 12 || day < 1 || day > 31) return { status: 'fail' };
  var year = today.getFullYear();
  if (new Date(year, month - 1, day) > today) year -= 1; // 연말 문자를 연초에 처리
  return {
    status: 'ok', date: year + '-' + pad2(month) + '-' + pad2(day),
    amount: amount, card: cardName(text), merchant: merchantAfter(body, dm)
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/logic.test.js`
Expected: `# pass 16`, `# fail 0`

- [ ] **Step 5: Commit**

```bash
git add apps-script/logic.gs tests/logic.test.js
git commit -m "feat: 카드 승인 문자 분리·파싱"
```

---

### Task 10: logic.gs — 예산 알림 판정

**Files:**
- Modify: `apps-script/logic.gs` (끝에 추가), `tests/logic.test.js` (끝에 추가)

**Interfaces:**
- Produces: `spendByCategory(rows: any[][], ym: number) -> {[cat]: number}` (rows = 내역 A:L 값), `newAlerts(rows: [{category, spent, budget}], sent: {[key]: true}, ym: number) -> [{category, level: 80|100, spent, budget, key}]`, `formatAlerts(alerts) -> string`, `comma(n: number) -> string`

- [ ] **Step 1: Write the failing test** — `tests/logic.test.js` 끝에 추가

```js
test('spendByCategory: 해당 귀속월 지출만 원화금액(K)으로 합산', () => {
  const row = (type, cat, krw, ym) => ['', '', type, cat, '', '', '', 0, 'KRW', '', krw, ym];
  const out = ctx.spendByCategory([
    row('지출', '식비', 10000, 202610), row('지출', '식비', 5000, 202610),
    row('수입', '월급', 3000000, 202610), row('지출', '식비', 99999, 202609)], 202610);
  assert.deepEqual(plain(out), { '식비': 15000 });
});

test('newAlerts: 80%·100% 각 1회, 예산 없으면 제외', () => {
  const rows = [{ category: '식비', spent: 85, budget: 100 }, { category: '쇼핑', spent: 120, budget: 100 },
    { category: '교통', spent: 50, budget: 100 }, { category: '기타', spent: 500, budget: 0 }];
  const first = plain(ctx.newAlerts(rows, {}, 202610));
  assert.deepEqual(first.map((a) => [a.category, a.level]), [['식비', 80], ['쇼핑', 100]]);
  const sent = { '202610|식비|80': true, '202610|쇼핑|100': true };
  assert.deepEqual(plain(ctx.newAlerts(rows, sent, 202610)), []);
});

test('formatAlerts: 사람이 읽는 문장', () => {
  const text = ctx.formatAlerts([{ category: '쇼핑', level: 100, spent: 312000.4, budget: 300000 }]);
  assert.equal(text, '쇼핑: 312,000 / 300,000원 (104%) — 예산 초과');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/logic.test.js`
Expected: FAIL — `TypeError: ctx.spendByCategory is not a function`

- [ ] **Step 3: Write implementation** — `apps-script/logic.gs` 끝에 추가

```js
// 내역 A:L 한 행: [날짜, 사용자, 구분, 카테고리, 소분류, 결제수단, 입금자산, 금액, 통화, 메모, 원화금액, 귀속월]
function spendByCategory(rows, ym) {
  var out = {};
  rows.forEach(function (r) {
    if (r[2] !== '지출' || Number(r[11]) !== ym) return;
    out[r[3]] = (out[r[3]] || 0) + (Number(r[10]) || 0);
  });
  return out;
}

function newAlerts(rows, sent, ym) {
  var out = [];
  rows.forEach(function (r) {
    if (!(r.budget > 0)) return;
    var ratio = r.spent / r.budget;
    var level = ratio >= 1 ? 100 : ratio >= 0.8 ? 80 : 0;
    if (!level) return;
    var key = ym + '|' + r.category + '|' + level;
    if (sent[key]) return;
    out.push({ category: r.category, level: level, spent: r.spent, budget: r.budget, key: key });
  });
  return out;
}

function comma(n) {
  return String(Math.round(n)).replace(/\B(?=(\d{3})+(?!\d))/g, ',');
}

function formatAlerts(alerts) {
  return alerts.map(function (a) {
    var pct = Math.round(a.spent / a.budget * 100);
    var label = a.level === 100 ? '예산 초과' : '80% 도달';
    return a.category + ': ' + comma(a.spent) + ' / ' + comma(a.budget) + '원 (' + pct + '%) — ' + label;
  }).join('\n');
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/logic.test.js`
Expected: `# pass 19`, `# fail 0`

- [ ] **Step 5: Commit**

```bash
git add apps-script/logic.gs tests/logic.test.js
git commit -m "feat: 예산 알림 판정·문구"
```

---

### Task 11: triggers.gs + deploy_script.py

**Files:**
- Create: `apps-script/triggers.gs`, `deploy_script.py`, `tests/test_deploy.py`

**Interfaces:**
- Consumes: logic.gs 전체 (Tasks 7–10), `auth.get_credentials`, 파일 `.spreadsheet_id`
- Produces: Apps Script 전역 `onEdit(e)`, `appendTxn(ss, txn10)`, `dailyJob()`, `setupTriggers()`; Python `deploy_script.script_files() -> list[dict]`, `deploy_script.deploy() -> str`(scriptId); 파일 `.script_id`

triggers.gs는 SpreadsheetApp 등에 묶인 얇은 연결부라 단위 테스트 대신 Task 12의 실제 시트 수동 점검으로 검증한다(판단 로직은 모두 logic.gs에서 테스트됨). Python 배포 쪽만 TDD.

- [ ] **Step 1: Write the failing test** — `tests/test_deploy.py`

```python
import json

import deploy_script


def test_script_files_manifest_and_sources():
    files = {f["name"]: f for f in deploy_script.script_files()}
    assert set(files) == {"appsscript", "logic", "triggers"}
    manifest = json.loads(files["appsscript"]["source"])
    assert manifest["timeZone"] == "Asia/Seoul"
    assert manifest["runtimeVersion"] == "V8"
    assert "function routeEdit" in files["logic"]["source"]
    assert "function onEdit" in files["triggers"]["source"]
    assert files["logic"]["type"] == files["triggers"]["type"] == "SERVER_JS"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_deploy.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'deploy_script'`

- [ ] **Step 3: Write implementation**

`apps-script/triggers.gs`:
```js
/* 시트 연결부 — 판단 로직은 logic.gs. 모바일에서도 동작하도록 체크박스(onEdit)와 시간 트리거만 사용. */

function onEdit(e) {
  var range = e.range;
  var action = routeEdit({
    sheet: range.getSheet().getName(), row: range.getRow(), col: range.getColumn(),
    numRows: range.getNumRows(), numCols: range.getNumColumns(),
    oldValue: e.oldValue, value: e.value
  });
  if (!action) return;
  if (action.type === 'rename') applyRename(e.source, action);
  if (action.type === 'favorite') addFavorite(e.source, action.row, range);
  if (action.type === 'sms') importSms(e.source, range);
}

function applyRename(ss, action) {
  action.targets.forEach(function (t) {
    var sh = ss.getSheetByName(t[0]);
    var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
    if (last < 2) return;
    var rng = sh.getRange(2, t[1], last - 1, 1);
    var res = replaceExact(rng.getValues(), action.from, action.to);
    if (res.changed) rng.setValues(res.values);
  });
}

function todayDate() {
  var d = new Date();
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

// 모든 입력 경로의 유일한 내역 추가 함수. txn = TXN_COLS(10)칸 배열.
function appendTxn(ss, txn) {
  var lock = LockService.getDocumentLock();
  lock.waitLock(10000);
  try {
    var sh = ss.getSheetByName('내역');
    var row = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues());
    if (row > sh.getMaxRows()) sh.insertRowsAfter(sh.getMaxRows(), 500);
    sh.getRange(row, 1, 1, TXN_COLS).setValues([txn]);
  } finally {
    lock.releaseLock();
  }
}

function addFavorite(ss, row, checkbox) {
  // 즐겨찾기: 추가, 사용자, 구분, 카테고리, 결제수단, 금액, 메모
  var f = ss.getSheetByName('즐겨찾기').getRange(row, 1, 1, 7).getValues()[0];
  checkbox.setValue(false);
  if (!(Number(f[5]) > 0)) {
    checkbox.setNote('금액이 없어 추가하지 않았습니다');
    return;
  }
  checkbox.clearNote();
  appendTxn(ss, [todayDate(), f[1], f[2], f[3], '', f[4], '', Number(f[5]), 'KRW', f[6]]);
}

function assetNames(ss) {
  return ss.getSheetByName('자산').getRange('A2:A50').getValues()
    .map(function (r) { return r[0]; }).filter(function (x) { return !isBlank(x); });
}

function importSms(ss, checkbox) {
  checkbox.setValue(false);
  var sh = ss.getSheetByName('문자입력');
  var last = nextEmptyRow(sh.getRange(1, 1, sh.getMaxRows(), 1).getValues()) - 1;
  if (last < 2) return;
  var lines = sh.getRange(2, 1, last - 1, 1).getValues().map(function (r) { return r[0]; });
  var assets = assetNames(ss);
  var failed = [];
  var added = 0;
  splitMessages(lines).forEach(function (m) {
    var p = parseCardSms(m.text, todayDate());
    if (p.status === 'cancel') return;
    if (p.status !== 'ok') { failed.push(m.text); return; }
    var d = p.date.split('-');
    var date = new Date(Number(d[0]), Number(d[1]) - 1, Number(d[2]));
    appendTxn(ss, [date, '공동', '지출', '', '', matchAsset(p.card, assets), '', p.amount, 'KRW', p.merchant]);
    added++;
  });
  sh.getRange(2, 1, last - 1, 3).clearContent(); // 같은 문자를 두 번 추가하지 않도록 비운다
  if (failed.length) {
    sh.getRange(2, 1, failed.length, 3).setValues(failed.map(function (t) { return [t, '', '인식 실패']; }));
  }
  sh.getRange(1, 3).setValue(added + '건 추가 / 실패 ' + failed.length + '건 (카테고리를 채워주세요)');
}

function dailyJob() {
  var ss = SpreadsheetApp.getActive();
  runRecurring(ss);
  runAlerts(ss);
}

function runRecurring(ss) {
  var sh = ss.getSheetByName('반복');
  var rows = sh.getRange(2, 1, 49, 9).getValues();
  var now = todayDate();
  rows.forEach(function (r, i) {
    // 사용, 일자, 사용자, 구분, 카테고리, 결제수단, 금액, 메모, 마지막 생성 월
    if (r[0] !== true || !(Number(r[6]) > 0) || !(Number(r[1]) >= 1)) return;
    if (!isRecurringDue(Number(r[1]), r[8], now)) return;
    appendTxn(ss, [dueDate(Number(r[1]), now), r[2], r[3], r[4], '', r[5], '', Number(r[6]), 'KRW', r[7]]);
    sh.getRange(i + 2, 9).setValue(calendarYm(now));
  });
}

function runAlerts(ss) {
  var settings = ss.getSheetByName('설정');
  if (settings.getRange('J3').getValue() !== true) return;
  var ym = ymKey(todayDate(), Number(settings.getRange('J2').getValue()) || 1);
  var txn = ss.getSheetByName('내역');
  var last = nextEmptyRow(txn.getRange(1, 1, txn.getMaxRows(), 1).getValues()) - 1;
  if (last < 2) return;
  var spent = spendByCategory(txn.getRange(2, 1, last - 1, 12).getValues(), ym);
  var rows = settings.getRange('A2:C60').getValues()
    .filter(function (r) { return r[0] && r[1] === '지출'; })
    .map(function (r) { return { category: r[0], spent: spent[r[0]] || 0, budget: Number(r[2]) || 0 }; });
  var state = ss.getSheetByName('알림기록');
  var sent = {};
  state.getDataRange().getValues().forEach(function (r) { if (r[0]) sent[r[0]] = true; });
  var alerts = newAlerts(rows, sent, ym);
  if (!alerts.length) return;
  MailApp.sendEmail(recipients(settings), '[가계부] 예산 알림 ' + alerts.length + '건', formatAlerts(alerts));
  state.getRange(state.getLastRow() + 1, 1, alerts.length, 2)
    .setValues(alerts.map(function (a) { return [a.key, new Date()]; }));
}

function recipients(settings) {
  var extra = String(settings.getRange('J4').getValue()).split(',')
    .map(function (s) { return s.trim(); }).filter(function (s) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(s); });
  return [Session.getEffectiveUser().getEmail()].concat(extra).join(',');
}

// 시트에서 1회 직접 실행: 확장 프로그램 > Apps Script > setupTriggers ▶ 실행 → 권한 허용
function setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(function (t) { ScriptApp.deleteTrigger(t); });
  ScriptApp.newTrigger('dailyJob').timeBased().everyDays(1).atHour(6).create();
}
```

`deploy_script.py`:
```python
"""시트에 연결된 Apps Script 프로젝트를 만들거나(최초) 코드를 갱신한다.

사전 조건: https://script.google.com/home/usersettings 에서 "Google Apps Script API" 켜기.
사용: python3 deploy_script.py
"""
import json
from pathlib import Path

from googleapiclient.discovery import build

from auth import get_credentials

ROOT = Path(__file__).parent
SCRIPT_DIR = ROOT / "apps-script"
SPREADSHEET_ID_FILE = ROOT / ".spreadsheet_id"
SCRIPT_ID_FILE = ROOT / ".script_id"
MANIFEST = {"timeZone": "Asia/Seoul", "exceptionLogging": "STACKDRIVER", "runtimeVersion": "V8"}
SOURCES = ["logic", "triggers"]


def script_files() -> list[dict]:
    files = [{"name": "appsscript", "type": "JSON", "source": json.dumps(MANIFEST)}]
    return files + [{"name": n, "type": "SERVER_JS",
                     "source": (SCRIPT_DIR / f"{n}.gs").read_text(encoding="utf-8")} for n in SOURCES]


def deploy() -> str:
    projects = build("script", "v1", credentials=get_credentials()).projects()
    if SCRIPT_ID_FILE.exists():
        script_id = SCRIPT_ID_FILE.read_text().strip()
    else:
        if not SPREADSHEET_ID_FILE.exists():
            raise FileNotFoundError(".spreadsheet_id 없음. 먼저 python3 build_budget.py 실행")
        parent = SPREADSHEET_ID_FILE.read_text().strip()
        script_id = projects.create(body={"title": "가계부 스크립트", "parentId": parent}).execute()["scriptId"]
        SCRIPT_ID_FILE.write_text(script_id)
    projects.updateContent(scriptId=script_id, body={"files": script_files()}).execute()
    return script_id


if __name__ == "__main__":
    print(f"업로드 완료: scriptId={deploy()}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q && node --test tests/logic.test.js && node -e "new Function(require('fs').readFileSync('apps-script/triggers.gs','utf8'))" && echo SYNTAX_OK`
Expected: pytest `36 passed`, node `# pass 19`, 마지막 줄 `SYNTAX_OK`

- [ ] **Step 5: Commit**

```bash
git add apps-script/triggers.gs deploy_script.py tests/test_deploy.py
git commit -m "feat: 시트 연결 트리거(이름변경·즐겨찾기·문자·반복·알림)와 스크립트 배포"
```

---

### Task 12: 실제 생성·배포·통합 검증 + README

**Files:**
- Create: `verify_budget.py`, `README.md`

**Interfaces:**
- Consumes: `.spreadsheet_id`, `auth.get_credentials`, 시트 셀 주소(대시보드 A6:C6, 자산 E2:E4, 추이 C39:C50, 검색 E1)

- [ ] **Step 1: Write the integration check** — `verify_budget.py`

```python
"""실제 시트에 샘플 3건을 넣어 집계를 확인한 뒤 지운다. 내역이 비어 있을 때만 실행.

사용: python3 verify_budget.py   (종료코드 0 = 통과)
"""
import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

from auth import get_credentials

ID_FILE = Path(__file__).parent / ".spreadsheet_id"


def sample(day: str) -> list[list]:
    return [[day, "사용자1", "수입", "월급", "", "주거래통장", "", 3000000, "KRW", "검증"],
            [day, "사용자2", "지출", "식비", "", "신용카드1", "", 12000, "KRW", "검증"],
            [day, "공동", "이체", "", "", "주거래통장", "현금", 50000, "KRW", "검증"]]


def expected(today: dt.date) -> dict:
    return {"대시보드!A6:C6": [[3000000, 12000, 2988000]],
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
```

- [ ] **Step 2: 사용자 작업 — OAuth 토큰 발급** (브라우저 필요, 사용자가 `!` 로 실행)

```bash
export BUDGET_CLIENT_SECRET=/home/jack/blog-automation/client_secret.json
cd "/mnt/d/budget book" && python3 auth.py
# 출력 URL을 브라우저에서 열고 허용 → 주소창 URL 복사
python3 auth.py "<복사한 URL>"
```
사전 확인: GCP 프로젝트(`blog-automation-497807`)에서 **Google Sheets API, Google Drive API, Apps Script API** 사용 설정, https://script.google.com/home/usersettings 에서 Apps Script API 켜기.
Expected: `저장됨: .../token.json`

- [ ] **Step 3: 시트 생성 + 스크립트 배포 + 통합 검증**

Run:
```bash
cd "/mnt/d/budget book"
export BUDGET_CLIENT_SECRET=/home/jack/blog-automation/client_secret.json BUDGET_PARTNER_EMAIL=<배우자 이메일>
python3 build_budget.py "우리집 가계부" && python3 deploy_script.py && python3 verify_budget.py; echo "exit=$?"
```
Expected: 시트 URL 출력, `업로드 완료: scriptId=...`, `통과: 4개 범위 일치`, `exit=0`.
실패하면 해당 셀 수식을 시트에서 열어 오류 메시지(#REF!/#VALUE!/#N/A)를 확인하고 Task 3·4 코드를 고친 뒤, **새 시트로 다시 생성**(`.spreadsheet_id`, `.script_id` 삭제 후 재실행; 이전 테스트 시트는 사용자에게 드라이브에서 지워 달라고 요청).

- [ ] **Step 4: Write README** — `README.md`

```markdown
# 우리집 가계부 (Google Sheets)

## 처음 한 번
1. GCP에서 Sheets·Drive·Apps Script API 사용 설정, https://script.google.com/home/usersettings 에서 Apps Script API 켜기
2. `export BUDGET_CLIENT_SECRET=<client_secret.json 경로> BUDGET_PARTNER_EMAIL=<배우자 이메일>`
3. `python3 auth.py` → 브라우저 허용 → `python3 auth.py "<주소창 URL>"`
4. `python3 build_budget.py "우리집 가계부"` → 출력된 URL 열기 (배우자에게 편집 권한 메일 발송됨)
5. `python3 deploy_script.py`
6. 시트에서 **확장 프로그램 > Apps Script** → 함수 `setupTriggers` 선택 → ▶ 실행 → 권한 허용 (반복 입력·예산 알림용, 1회)
7. 폰: 구글 시트 앱 설치 → 가계부 열기 → 공유 메뉴의 "홈 화면에 추가"(안드로이드) / 즐겨찾기(iOS)

## 사용법
- **입력**: `내역` 탭 맨 아래 빈 행에 날짜(달력)·사용자·구분·카테고리 선택, 금액 입력. 행 삭제·수정 자유.
- **카테고리/사용자 추가·이름 변경**: `설정` 탭. 한 칸씩 고치면 과거 내역도 자동 변경.
- **카드·통장**: `자산` 탭에 카드사 이름이 들어가게 등록(예: `신한카드`) → 문자 입력 시 자동 매칭.
- **즐겨찾기**: `즐겨찾기` 탭 A열 체크 → 오늘 날짜로 내역 추가.
- **고정지출**: `반복` 탭에 등록하고 '사용' 체크 → 매일 06시에 해당 일자 항목 자동 추가.
- **카드 문자**: `문자입력` A2부터 문자 여러 건 붙여넣기 → B1 체크 → 추가 후 카테고리만 채우기.
- **보기**: `대시보드`(월), `추이`(연), `달력`, `검색`. B1 드롭다운으로 기간 선택, 비우면 이번 달/올해.
- **백업/내보내기**: 파일 > 버전 기록, 파일 > 다운로드(xlsx/csv).

## 개발
- 테스트: `python3 -m pytest -q` / `node --test tests/logic.test.js`
- 스크립트 수정 후 반영: `python3 deploy_script.py`
- 통합 검증(빈 시트에서만): `python3 verify_budget.py`

## 알려진 한계
- 외화는 현재 환율로 환산(입력 시점 환율 아님).
- 이름 변경 자동 반영은 한 칸씩 수정할 때만 동작.
- 문자 파싱은 카드사 형식에 따라 실패할 수 있음 → '인식 실패'로 남음.
- 은행/카드 자동 연동, 위젯은 불가.
```

- [ ] **Step 5: 폰 수동 점검 (사용자와 함께, 결과를 체크)**

- [ ] 폰 시트 앱: 내역 행 추가(달력·드롭다운 동작) → 대시보드 숫자·도넛 갱신
- [ ] 내역 행 수정·삭제 → 대시보드 반영
- [ ] 설정에 카테고리 `반려동물` 추가 → 내역 드롭다운에 표시
- [ ] 설정 `식비` → `외식` 수정 → 내역·즐겨찾기의 `식비`가 `외식`으로 변경
- [ ] 즐겨찾기 A2 체크 → 내역에 오늘 날짜 4,500원 추가, 체크 해제됨
- [ ] 문자입력에 Task 9의 신한 예시 붙여넣기 → B1 체크 → 내역 추가, C1에 `1건 추가`
- [ ] `setupTriggers` 실행 후 Apps Script 트리거 목록에 `dailyJob` 1개
- [ ] 반복에 오늘 일자 항목 등록 후 Apps Script에서 `dailyJob` 수동 실행 → 내역 추가, I열에 이번 달
- [ ] 식비 예산 1000 설정 후 `dailyJob` 실행 → 이메일 수신, 다시 실행 시 재발송 없음
- [ ] 점검용으로 넣은 행 삭제

- [ ] **Step 6: Commit**

```bash
git add verify_budget.py README.md
git commit -m "docs: 설치·사용 README와 실제 시트 통합 검증 스크립트"
```

---

## 스펙 대비 커버리지

| 스펙 항목 | Task |
|---|---|
| 내역 탭·드롭다운·계산열 | 2, 3 |
| 설정(카테고리·예산·사용자·통화·월 시작일·알림) | 2, 3 |
| 이름 변경 자동 반영 | 7, 11 |
| 자산·이체·카드 실적 | 2, 3 |
| 대시보드 KPI·도넛·예산·사용자·카드 | 3, 5 |
| 추이 월별·히트맵·연도별 | 4, 5 |
| 달력 / 검색 | 4 |
| 반복 / 즐겨찾기 | 8, 11 |
| 문자입력 | 9, 11 |
| 예산 알림 | 10, 11 |
| 다중 통화 | 3 |
| 공유·보호 | 2, 6 |
| 시트 기본 기능(백업·내보내기·음성·영수증) | 12 README |
| 통합/수동 검증 | 12 |

스펙의 "구현 순서"(1~4단계)는 기능 우선순위다. 이 계획은 같은 결과물을 컴포넌트 단위(Python 시트 생성 → Apps Script)로 나눠 만들고 Task 12에서 한 번에 실제 시트로 검증한다.
