import re
import charts
import layout
import migrate_couple as mc

# 운영 시트의 10-08 상태: 메리츠 탭은 옛 이름, 새 탭 없음, 설정 10열·자산 8열
LIVE_TITLES = {"사용법", "내역", "대시보드", "추이", "달력", "검색", "즐겨찾기", "반복", "자산", "설정", "문자입력",
               "계산", "알림기록", "주식", "메리츠", "메리츠원본"}
SETTINGS = [["식비", "지출", 600000], ["용돈", "지출", 600000], ["월급1", "수입", 2700000],
            ["월급2", "수입", 2800000], ["부수입", "수입", ""]]
LIVE = mc.State(titles=LIVE_TITLES, settings_cols=10, asset_cols=8, networth_charts=0,
                settings=SETTINGS, budgets_empty=True)
DONE = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                settings=[["식비", "지출", 600000]], budgets_empty=False, invest_charts=2)


def _kinds(reqs):
    return [next(iter(r)) for r in reqs]


def _values(values):
    return {v["range"]: v["values"] for v in values}


def test_live_sheet_renames_adds_tabs_and_columns():
    structure, _v, visual = mc.plan(LIVE)
    renames = {r["updateSheetProperties"]["properties"].get("title") for r in structure if "updateSheetProperties" in r}
    assert {"주식_신랑", "메리츠_신랑"} <= renames
    added = sorted(r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r)
    assert added == sorted(["부부", "자산기록", "주식_신부", "메리츠_신부", "메리츠원본2", "투자", "한투원본", "투자기록", "자산현황", "고정지출", "카드", "주식투자", "저축·연금", "한투종목", "시작하기", "빠른입력"])
    assert {"appendDimension": {"sheetId": 200, "dimension": "COLUMNS", "length": 3}} in structure
    assert {"appendDimension": {"sheetId": 300, "dimension": "COLUMNS", "length": 4}} in structure
    assert "addProtectedRange" in _kinds(structure) and "setDataValidation" in _kinds(structure)
    assert {"addChart", "addConditionalFormatRule"} <= set(_kinds(visual))


def test_renames_come_before_anything_that_uses_new_names():
    structure, _v, _vi = mc.plan(LIVE)
    kinds = _kinds(structure)
    first_other = next(i for i, k in enumerate(kinds) if k != "updateSheetProperties")
    renamed = [i for i, r in enumerate(structure)
               if "updateSheetProperties" in r and "title" in r["updateSheetProperties"]["properties"]]
    assert max(renamed) < first_other


def test_tabs_reordered_like_sheets_list():
    structure, _v, _vi = mc.plan(DONE)
    idx = {r["updateSheetProperties"]["properties"]["sheetId"]: r["updateSheetProperties"]["properties"]["index"]
           for r in structure if "index" in r.get("updateSheetProperties", {}).get("properties", {})}
    assert [sid for sid, _ in sorted(idx.items(), key=lambda x: x[1])] == [s[1] for s in layout.SHEETS]


def test_existing_budgets_move_to_person_columns_once():
    _s, values, _vi = mc.plan(LIVE)
    vals = _values(values)
    km = vals["설정!K2:M6"]
    assert km[0] == ["", "", 600000] and km[1] == ["", "", 600000]   # 지출 → 공동
    assert km[2] == [2700000, "", ""] and km[3] == ["", 2800000, ""]  # 월급1 → 신랑, 월급2 → 신부
    assert km[4] == ["", "", ""]
    assert vals["설정!C2:C60"] == [[""]] * 59  # 합계 수식이 펼쳐질 자리 비우기
    assert "설정!C1" in vals


def test_second_run_adds_nothing_duplicable_and_keeps_budgets():
    seen = frozenset(mc._rule_key(r) for r in charts.data_check_rules())  # 첫 적용 뒤 운영 시트에 이미 있는 입력 확인 규칙
    structure, values, visual = mc.plan(DONE._replace(rules_seen=seen))
    assert not {"addSheet", "addProtectedRange", "appendDimension"} & set(_kinds(structure))
    # 검증은 자산 종류 선택지만 매번 다시 씀 (같은 규칙 덮어쓰기라 반복 안전)
    # 매번 다시 거는 것: 자산 종류 선택지 + 결제수단(대출·연금·기타 제외)·입금자산 선택지 + 월 이동 드롭다운(대시보드·부부 C1), 추천 예산 체크박스(설정 J12)
    assert [r["setDataValidation"]["range"] for r in structure if "setDataValidation" in r] == [
        layout.a1_to_grid(a1) for a1 in ("내역!B2:B5000", "내역!C2:C5000", "내역!F2:F5000", "내역!G2:G5000", "내역!I2:I5000", "자산!A2:A50", "자산!B2:B50", "반복!F2:F50", "즐겨찾기!E2:E50", "대시보드!C1", "부부!C1", "추이!C1", "카드!J5:J24", "설정!J12")]
    assert not {"addChart", "addConditionalFormatRule"} & set(_kinds(visual))  # 사용법 서식만 다시
    ranges = set(_values(values))
    assert not any(r.startswith("설정!K2") or r == "설정!C2:C60" for r in ranges)
    assert {"부부!A16:K16", "자산!E1:E2", "대시보드!F6", "주식_신부!A16:P16"} <= ranges


def test_dashboard_only_projection_cell():
    # 운영 대시보드는 생성 뒤 표·차트 위치를 옮겨 코드 배치(60행)와 다르다 → 바뀐 F6 한 칸만 쓴다
    for state in (LIVE, DONE):
        _s, values, _vi = mc.plan(state)
        dash = [r for r in _values(values) if r.startswith("대시보드!")]
        row = lambda r: int(re.match(r"대시보드![A-Z]+(\d+)", r).group(1))
        # 월말 예상 + 자산 현황(5·6행 J~L 빈자리) + 업데이트일(L1:L2, 운영에서 빈 칸 확인 2026-10-14)
        top = {"대시보드!F6", "대시보드!J5:L6", "대시보드!L1", "대시보드!L2", "대시보드!M5:M6", "대시보드!C1", "대시보드!D1", "대시보드!D2"}  # M5:M6 목표 달성률, C1 안내 문구(분홍), D1 제목(이모지 뺀 글자), D2 확인 필요 한 줄
        assert {r for r in dash if row(r) < 95} == top
        assert all(row(r) >= 95 for r in dash if r not in top)  # 그 밖엔 운영 표(19~50행) 아래 빈 구역(고정비·변동비)만


def test_never_writes_user_data_ranges():
    for state in (LIVE, DONE):
        _s, values, _vi = mc.plan(state)
        for r in _values(values):
            sheet, ref = r.split("!")
            if r in ("반복!J1:N1", "내역!K1", "내역!N1"):  # 새 열 머리글 줄 / 내역 원화금액 수식 열(K1 한 칸, 사람이 입력하는 칸이 아님)
                continue
            assert sheet not in ("내역", "반복", "즐겨찾기", "문자입력", "알림기록"), r
            if sheet == "자산":
                assert ref[0] in "EGHIJL" and not ref.startswith(("G2", "J2", "K2")), r  # 머리글·수식 열만 (J1:K1 머리글, L 결제수단 목록)


def test_budgets_empty_ignores_checkbox_values_copied_by_column_append():
    # 열 추가 때 J3(예산 알림 체크박스)가 K3:M3로 복사돼 FALSE가 들어온 실제 사례
    assert mc.budgets_empty([[], [False, False, False], ["", ""]]) is True
    assert mc.budgets_empty([[0, "", ""]]) is True
    assert mc.budgets_empty([["", 300000]]) is False


LIVE_PIE = {"chartId": 7, "spec": {"title": "카테고리별 지출", "pieChart": {
    "legendPosition": "RIGHT_LEGEND", "pieHole": 0.5,
    "domain": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 50,
                                            "startColumnIndex": 0, "endColumnIndex": 1}]}},
    "series": {"sourceRange": {"sources": [{"sheetId": 400, "startRowIndex": 19, "endRowIndex": 50,
                                            "startColumnIndex": 1, "endColumnIndex": 2}]}}}}}


def test_live_pie_gets_percent_labels_at_its_own_rows():
    values, reqs = mc.pie_fix(LIVE_PIE)
    vals = _values(values)
    assert vals["대시보드!M19:M20"][0] == ["비율 표시"]
    assert "A20:A50" in vals["대시보드!M19:M20"][1][0] and "B20:B50" in vals["대시보드!M19:M20"][1][0]
    spec = reqs[0]["updateChartSpec"]
    assert spec["chartId"] == 7 and spec["spec"]["pieChart"]["legendPosition"] == "LABELED_LEGEND"
    dom = spec["spec"]["pieChart"]["domain"]["sourceRange"]["sources"][0]
    assert (dom["startColumnIndex"], dom["startRowIndex"], dom["endRowIndex"]) == (12, 19, 50)
    assert spec["spec"]["pieChart"]["series"] == LIVE_PIE["spec"]["pieChart"]["series"]
    assert spec["spec"]["pieChart"]["pieHole"] == 0.5 and spec["spec"]["title"] == "카테고리별 지출"


def test_live_pie_fix_runs_once():
    _v, reqs = mc.pie_fix(LIVE_PIE)
    done = {"chartId": 7, "spec": reqs[0]["updateChartSpec"]["spec"]}
    values, again = mc.pie_fix(done)
    assert again == [] and len(values) == 1  # 수식은 다시 써도 안전, 차트는 그대로
    assert mc.pie_fix(None) == ([], [])


def test_tucks_rare_tabs_and_always_reformats_guide():
    structure, _v, visual = mc.plan(DONE)
    hidden = {r["updateSheetProperties"]["properties"]["sheetId"] for r in structure
              if r.get("updateSheetProperties", {}).get("properties", {}).get("hidden") is True}
    assert hidden == {layout.SHEET_ID[t] for t in layout.TUCKED}
    # 병합을 값 쓰기 전에 풀어야 병합 칸 밑으로 들어가는 사용법 B열 값이 버려지지 않는다 (운영에서 실제로 겪음)
    assert "unmergeCells" in _kinds(structure) and "unmergeCells" not in _kinds(visual)
    assert "autoResizeDimensions" in _kinds(visual)
    assert "addChart" not in _kinds(visual)


AFTER_COUPLE = mc.State(titles={t for t, *_ in layout.SHEETS} - {"투자", "한투원본", "투자기록"}, settings_cols=13,
                        asset_cols=12, networth_charts=1, settings=[["식비", "지출", 600000]], budgets_empty=False)


def test_invest_tabs_added_once_without_redoing_couple_structure():
    structure, values, visual = mc.plan(AFTER_COUPLE)
    added = sorted(r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r)
    assert added == ["투자", "투자기록", "한투원본"]
    prot = [r["addProtectedRange"]["protectedRange"]["range"] for r in structure if "addProtectedRange" in r]
    assert prot and all(g.get("sheetId") in (1900, 1950, 2000) for g in prot)  # 설정 C·K:M 보호를 또 만들지 않음
    assert any(r.get("setDataValidation", {}).get("range") == layout.a1_to_grid("자산!G2:G50") for r in structure)
    assert "투자!A7:G7" in _values(values)
    titles = [r["addChart"]["chart"]["spec"]["title"] for r in visual if "addChart" in r]
    assert titles == ["월별 투자 추이 (월말)", "최근 30일 합산 평가금액"]


def test_invest_rerun_adds_nothing():
    structure, _v, visual = mc.plan(DONE)
    assert "addSheet" not in _kinds(structure) and "addChart" not in _kinds(visual)
    hidden = {r["updateSheetProperties"]["properties"]["sheetId"] for r in structure
              if r.get("updateSheetProperties", {}).get("properties", {}).get("hidden") is True}
    assert layout.SHEET_ID["주식_신랑"] in hidden
