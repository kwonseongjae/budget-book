import json
import re

import deploy_script


def test_script_files_manifest_and_sources():
    files = {f["name"]: f for f in deploy_script.script_files()}
    assert set(files) == {"appsscript", "logic", "triggers", "meritz_logic", "meritz", "kis_logic", "kis", "invest_logic"}
    manifest = json.loads(files["appsscript"]["source"])
    assert manifest["timeZone"] == "Asia/Seoul"
    assert manifest["runtimeVersion"] == "V8"
    assert "function routeEdit" in files["logic"]["source"]
    assert "function onEdit" in files["triggers"]["source"]
    assert files["logic"]["type"] == files["triggers"]["type"] == "SERVER_JS"


def test_meritz_script_has_no_trading_paths_and_owner_guard():
    files = {f["name"]: f["source"] for f in deploy_script.script_files()}
    src = files["meritz"] + files["meritz_logic"]
    assert "/trading/" not in src and "/forex/" not in src and "tr_cont:" not in src
    assert "getUserProperties" in src and "getScriptProperties" not in src
    assert "function onEditMeritz" in files["meritz"] and "function onEdit(" not in files["meritz"]
    assert "'onEditMeritz'" in files["meritz"] and "'refreshMeritz'" in files["meritz"]
    assert "setupMeritzTriggers();" in _fn(files["triggers"], "setupTriggers")


def _fn(src, name):
    return re.search(r"function " + name + r"\([^)]*\) \{(.*?)\n\}", src, re.S).group(1)


def test_owner_guards_and_token_renewal_rule():
    files = {f["name"]: f["source"] for f in deploy_script.script_files()}
    assert "isOwner_()" in _fn(files["triggers"], "setupTriggers")
    # 키는 각자 자기 사용자 속성에 — 갱신이 각자 권한으로 돌기 때문에 소유자 전용 제한 없음, 대신 슬롯으로 원본 탭을 고른다
    assert "isOwner_()" not in _fn(files["meritz"], "clearMeritzKeys")
    assert "MERITZ_SLOTS[isOwner_() ? 0 : 1]" in _fn(files["meritz"], "slot_")
    assert "getUserLock()" in _fn(files["meritz"], "refreshMeritz")
    assert "slot_().stock" in _fn(files["meritz"], "onEditMeritz")
    assert "if (!sh) return;" in _fn(files["meritz"], "writeAllStatus_")
    assert "r.code !== 'EGW00200' && r.code !== '5766' && !renewed" in files["meritz"]
    assert ".slice(0, 100)" in _fn(files["meritz"], "refreshMeritz")


def test_view_menu_opens_and_retucks_hidden_tabs():
    files = {f["name"]: f["source"] for f in deploy_script.script_files()}
    src = "\n".join(files.values())
    assert "createMenu('가계부')" in src
    for fn in ("openTrend", "openCalendar", "openSearch", "openMyMeritz", "openMyStock", "tuckViews"):
        assert f"function {fn}(" in src, fn
    assert "showSheet()" in _fn(src, "showTab_") and "hideSheet()" in _fn(src, "tuckViews")
    assert "showTab_('투자')" in _fn(files["meritz"], "setMeritzKeys")  # 키 넣으면 투자 탭이 보이게


def test_kis_script_reads_only_and_keeps_keys_in_user_properties():
    files = {f["name"]: f["source"] for f in deploy_script.script_files()}
    src = files["kis"] + files["kis_logic"]
    assert "order" not in src.lower()
    assert "getUserProperties" in src and "getScriptProperties" not in src
    refresh = _fn(files["kis"], "refreshKis_")
    assert "r.kind === 'expired'" in refresh and "getKisToken_(p, key, secret, true)" in refresh  # 만료면 한 번만 재발급
    assert "catch (err)" in refresh  # 예외를 밖으로 던지지 않는다


def test_securities_menu_refresh_and_daily_invest_record():
    files = {f["name"]: f["source"] for f in deploy_script.script_files()}
    assert "createMenu('증권 연동')" in files["meritz"]
    assert "'setKisKeys'" in files["meritz"]
    assert "refreshKis_(ss);" in _fn(files["meritz"], "refreshMeritz")
    assert "clearKisKeys_();" in _fn(files["meritz"], "clearMeritzKeys")
    assert "'투자'" in _fn(files["meritz"], "onEditMeritz")
    assert "principalOf" not in files["meritz"] + files["meritz_logic"]  # 원금은 시트 수식이 종목 블록에서
    assert "if (!shouldRecordInvest(row)) return;" in _fn(files["triggers"], "recordInvest")
    assert "recordInvest(ss);" in _fn(files["triggers"], "dailyJob")
    assert "'주식_신랑'" in files["triggers"] and "'주식_신부'" in files["triggers"]  # 상세 탭은 다시 숨기기 대상
    assert [f["name"] for f in deploy_script.script_files()][1:] == [
        "logic", "triggers", "meritz_logic", "meritz", "kis_logic", "kis", "invest_logic"]


def test_diagnose_menu_reports_each_step_without_revealing_keys():
    files = {f["name"]: f["source"] for f in deploy_script.script_files()}
    m = files["meritz"]
    assert "'diagnoseMeritz'" in m and "연동 점검 (내 계좌)" in m
    body = _fn(m, "diagnoseMeritz")
    for label in ("내 계정", "시트 소유자", "내 칸", "메리츠 키", "내 자동 갱신 트리거", "지금 조회"):
        assert f"'{label}'" in body, label
    assert "catch (e)" in body  # 단계마다 오류를 잡아 메시지로 보여 줌
    assert "? '있음' : '없음'" in body  # 키 값은 절대 표시하지 않고 있음/없음만
    assert "getProperty(PROP.key) +" not in body and "getProperty(PROP.secret) +" not in body
