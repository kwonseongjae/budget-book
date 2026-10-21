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
LEGACY_TOKEN = ROOT / "token.json"  # D 드라이브(drvfs)는 chmod가 안 먹어 누구나 읽을 수 있음 → 옮긴다
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


def token_path() -> Path:
    raw = os.environ.get("BUDGET_TOKEN_FILE")
    return Path(raw) if raw else Path.home() / ".config" / "budget-book" / "token.json"


def _write_private(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    path.touch(mode=0o600, exist_ok=True)
    path.chmod(0o600)
    path.write_text(text)


def migrate_legacy_token() -> Path:
    """예전 위치(프로젝트 폴더)의 token.json을 권한 600 위치로 옮긴다. 이미 옮겼으면 그대로."""
    path = token_path()
    if not path.exists() and LEGACY_TOKEN.exists():
        _write_private(path, LEGACY_TOKEN.read_text())
        LEGACY_TOKEN.unlink()
    return path


def _save(creds: Credentials) -> None:
    _write_private(token_path(), creds.to_json())


def get_credentials() -> Credentials:
    path = migrate_legacy_token()
    if not path.exists():
        raise FileNotFoundError(f"{path} 없음. 먼저 python3 auth.py 실행")
    creds = Credentials.from_authorized_user_file(str(path), SCOPES)
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
    print(f"저장됨: {token_path()}")


if __name__ == "__main__":
    main(sys.argv)
