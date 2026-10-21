"""코드·문서에는 실제 이름 대신 신랑·신부 (names.py)."""
import subprocess
from pathlib import Path

import deploy_script
import names

ROOT = Path(__file__).parent.parent


def test_default_names_are_identity():
    assert (names.GROOM, names.BRIDE) == names.DEFAULT
    assert names.localize("주식_신랑 · 신부") == "주식_신랑 · 신부"


def test_localize_swaps_both_roles(monkeypatch):
    monkeypatch.setattr(names, "GROOM", "가")
    monkeypatch.setattr(names, "BRIDE", "나")
    assert names.localize("메리츠_신랑 / 한투ISA_신부") == "메리츠_가 / 한투ISA_나"


def test_deploy_uses_localize_on_script_sources(monkeypatch):
    monkeypatch.setattr(deploy_script, "localize", lambda t: t.replace("신랑", "가").replace("신부", "나"))
    src = {f["name"]: f["source"] for f in deploy_script.script_files()}
    assert "주식_가" in src["meritz_logic"] and "신랑" not in "".join(src.values())


def test_env_overrides_file(tmp_path, monkeypatch):
    monkeypatch.setenv("BUDGET_NAMES", "철수, 영희")
    assert names._load() == ("철수", "영희")
    monkeypatch.setenv("BUDGET_NAMES", "한명만")
    assert names._load() == names.DEFAULT


def test_tracked_files_hold_no_real_names():
    banned = [p for p in (ROOT / ".names").read_text(encoding="utf-8").split() if p] if (ROOT / ".names").exists() else []
    if not banned:
        return  # 로컬 .names가 없는 환경(CI·공개 사본)에서는 건너뜀
    files = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.split("\n")
    hits = [f for f in files if f and (ROOT / f).is_file() and any(b in (ROOT / f).read_text(encoding="utf-8", errors="ignore") for b in banned)]
    assert not hits, hits
