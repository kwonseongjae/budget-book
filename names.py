"""사람 이름 설정: 코드·문서·배포 파일에는 '신랑'·'신부'만 쓰고, 실제 이름은 이 저장소 밖(로컬)에서만 정한다.

실제 이름 지정 (둘 중 하나, 환경 변수가 우선):
  - 환경 변수 BUDGET_NAMES="이름1,이름2"
  - 저장소 폴더의 .names 파일 (두 줄: 신랑 이름 / 신부 이름) — .gitignore 대상이라 git에 올라가지 않는다.
없으면 기본값 신랑·신부. 시트의 탭 이름(주식_신랑 등)·사용자 칸·설명 문구가 이 이름으로 만들어지고,
Apps Script는 deploy_script.py가 올릴 때 같은 규칙으로 바꾼다. 이미 만든 시트에서 사용자 이름만 바꾸려면 [설정]의 사용자 칸을 고치면 된다.
"""
import os
from pathlib import Path

DEFAULT = ("신랑", "신부")
FILE = Path(__file__).parent / ".names"


def _load() -> tuple[str, str]:
    env = os.environ.get("BUDGET_NAMES")
    if env is not None:
        parts = [p.strip() for p in env.split(",")]
    elif FILE.exists():
        parts = [p.strip() for p in FILE.read_text(encoding="utf-8").splitlines() if p.strip()]
    else:
        parts = []
    return (parts[0], parts[1]) if len(parts) == 2 and all(parts) else DEFAULT


GROOM, BRIDE = _load()


def localize(text: str) -> str:
    """소스에 적힌 기본 이름(신랑·신부)을 설정한 이름으로 바꾼다. 기본값이면 그대로."""
    return text.replace(DEFAULT[0], GROOM).replace(DEFAULT[1], BRIDE)
