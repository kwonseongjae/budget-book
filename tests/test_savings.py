import formulas
import invest
import layout
import migrate_couple as mc


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_saving_link_counts_only_owner_rows_for_personal_accounts():
    # 실사용 버그: 신부의 주택청약 납입이 신랑 청약통장 잔액에 더해졌다 (적립이 카테고리만 봄)
    e2 = _by_range(formulas.asset_values())["자산!E1:E2"][1][0]
    assert e2.startswith("=MAP(A2:A,C2:C,F2:F,G2:G,I2:I,J2:J,K2:K,LAMBDA(x,init,link,sync,own,cur,fx,")
    everyone = 'SUMIFS(내역!$K:$K,내역!$D:$D,link,내역!$C:$C,"<>",내역!$C:$C,"<>수입",내역!$C:$C,"<>이체")'
    mine = everyone[:-1] + ",내역!$B:$B,own)"
    assert f'IF(link="",0,IF(OR(own="",own=설정!$E$4),{everyone},{mine}))' in e2


def test_asset_kind_choices_include_saving_and_stock():
    rules = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]
             for r in layout.validation_requests()}
    b = rules[tuple(sorted(layout.a1_to_grid("자산!B2:B50").items()))]
    assert [x["userEnteredValue"] for x in b["condition"]["values"]] == ["통장", "계좌", "카드", "현금", "청약", "주식", "대출", "연금", "기타"]


def test_overview_table_per_person_and_total():
    vals = _by_range(invest.invest_values())
    assert vals["투자!A15:D15"] == [["구분", "=설정!E2", "=설정!E3", "부부 합계"]]
    rows = vals["투자!A16:D20"]
    assert [r[0] for r in rows] == ["주식 (메리츠)", "주식 (ISA·한투)", "청약", "합계", "이번 달 청약 납입"]
    assert rows[0][1:3] == ["=N(B7)", "=N(B10)"] and rows[1][1:3] == ["=N(B8)", "=N(B11)"]
    assert rows[2][1] == '=SUMIFS(자산!$E$2:$E$50,자산!$B$2:$B$50,"청약",자산!$I$2:$I$50,설정!$E$2)'
    assert rows[3][1] == "=SUM(B16:B18)" and rows[0][3] == "=B16+C16"
    assert "설정!$E$3" in rows[4][2] and '자산!$B$2:$B$50="청약"' in rows[4][2] and "계산!$C$2" in rows[4][2]


def test_saving_account_details_listed_next_to_table():
    vals = _by_range(invest.invest_values())
    assert vals["투자!G15:I15"] == [["청약 계좌", "소유자", "잔액"]]  # 넓은 상태 열(G)부터
    assert vals["투자!G16"][0][0] == '=IFERROR(FILTER({자산!A2:A50,자산!I2:I50,자산!E2:E50},자산!B2:B50="청약"),"")'


def test_charts_moved_below_overview():
    anchors = [r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["rowIndex"]
               for r in invest.visual_requests() if "addChart" in r]
    cols = [r["addChart"]["chart"]["position"]["overlayPosition"]["anchorCell"]["columnIndex"]
            for r in invest.visual_requests() if "addChart" in r]
    assert anchors == [21, 21] and cols == [0, 4]  # 나란히: 40행 추이 표를 덮지 않게


LIVE_CHARTS = ({"chartId": 11, "title": "월별 투자 추이 (월말)", "sheetId": 1900, "row": 13, "col": 0},
               {"chartId": 12, "title": "최근 30일 합산 평가금액", "sheetId": 1900, "row": 30, "col": 0})


def test_migration_moves_existing_charts_once_and_refreshes_kind_choices():
    moves = mc.chart_moves(LIVE_CHARTS)
    cell = lambda m: m["updateEmbeddedObjectPosition"]["newPosition"]["overlayPosition"]["anchorCell"]
    assert [(m["updateEmbeddedObjectPosition"]["objectId"], cell(m)["rowIndex"], cell(m)["columnIndex"]) for m in moves] == [
        (11, 21, 0), (12, 21, 4)]
    done = [{**c, "row": 21, "col": col} for c, col in zip(LIVE_CHARTS, (0, 4))]
    assert mc.chart_moves(done) == []
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                     settings=[], budgets_empty=False, invest_charts=2, charts=LIVE_CHARTS)
    structure, values, _vi = mc.plan(state)
    assert any("updateEmbeddedObjectPosition" in r for r in structure)
    assert any(r.get("setDataValidation", {}).get("range") == layout.a1_to_grid("자산!B2:B50") for r in structure)
    assert "투자!A16:D20" in _by_range(values)


def test_dashboard_shows_asset_status_next_to_monthly_kpis():
    vals = _by_range(formulas.dashboard_values())
    assert vals["대시보드!J5:L6"] == [["순자산", "주식 합계", "청약 합계"],
                                    ["=SUM(자산!E2:E50)", "=N(투자!A4)",
                                     '=SUMIFS(자산!E2:E50,자산!B2:B50,"청약")']]
    state = mc.State(titles={t for t, *_ in layout.SHEETS}, settings_cols=13, asset_cols=12, networth_charts=1,
                     settings=[], budgets_empty=False, invest_charts=2)
    _s, values, _vi = mc.plan(state)
    assert "대시보드!J5:L6" in _by_range(values)  # 운영 대시보드도 5·6행 J~L은 비어 있음
