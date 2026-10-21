"""시트에 연결된 Apps Script 프로젝트를 만들거나(최초) 코드를 갱신한다.

사전 조건: https://script.google.com/home/usersettings 에서 "Google Apps Script API" 켜기.
사용: python3 deploy_script.py
"""
import json
from pathlib import Path

from googleapiclient.discovery import build

from auth import get_credentials
from names import localize

ROOT = Path(__file__).parent
SCRIPT_DIR = ROOT / "apps-script"
SPREADSHEET_ID_FILE = ROOT / ".spreadsheet_id"
SCRIPT_ID_FILE = ROOT / ".script_id"
MANIFEST = {"timeZone": "Asia/Seoul", "exceptionLogging": "STACKDRIVER", "runtimeVersion": "V8"}
SOURCES = ["logic", "triggers", "meritz_logic", "meritz", "kis_logic", "kis", "invest_logic"]


def script_files() -> list[dict]:
    files = [{"name": "appsscript", "type": "JSON", "source": json.dumps(MANIFEST)}]
    return files + [{"name": n, "type": "SERVER_JS",
                     "source": localize((SCRIPT_DIR / f"{n}.gs").read_text(encoding="utf-8"))} for n in SOURCES]


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
