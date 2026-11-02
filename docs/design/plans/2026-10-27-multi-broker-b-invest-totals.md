# 다증권사 B단계: 투자 합산·투자기록에 붙여넣기 계좌 자동 포함 Implementation Plan

**Goal:** `증권계좌`에 붙여넣기 계좌를 적고 종목을 반영하면, `투자` 탭 합산(평가·원금·손익·수익률·KPI)과 `투자기록`(매일 06시 기록)에 그 계좌가 **자동으로 포함**되고, 계좌별 기록도 쌓인다.

**Architecture:** 기존 `투자` 탭의 4개 고정 계좌 행과 `투자기록` 12열 기록은 **건드리지 않고**, (1) `증권계좌`에 계좌별 평가·원금·손익 열을 수식으로 더하고, (2) `투자` 13행(비어 있던 줄)에 "기타 증권사(붙여넣기)" 합계 한 줄을 넣어 KPI에 포함하고, (3) `투자기록`에 `기타 평가·기타 원금` 두 열(M·N)을 더하며 합계(J·K)에는 포함하고, (4) 숨김 탭 `투자기록_계좌`(날짜|계좌|평가|원금)에 붙여넣기 계좌별 기록을 쌓는다.

**Tech Stack:** Python 3 + pytest(시트 생성기), Apps Script(V8) + `node --test`(가짜 시트), Sheets API.

**Spec:** `docs/design/specs/2026-10-21-multi-broker-design.md` (§3.3 투자기록·§7 투자 화면). **설계와 다른 점(아래 Ruling)**: 설계는 `투자기록` 전체를 "날짜|계좌|평가|원금" 한 줄씩으로 변환하라고 했으나, 운영 기록 변환의 위험(과거 추이 손상)을 피하려고 기존 12열 기록은 그대로 두고 **기타 합계 2열 + 계좌별 기록 새 탭**을 더하는 방식으로 같은 목표(자동 포함·계좌별 기록)를 이룬다. 기존 4계좌의 이전·어댑터·`주식투자` 소스 전환은 C단계 별도 계획.

## Global Constraints

- 코드·문서·테스트에는 실제 이름 금지, 사람은 **신랑 / 신부**만 쓴다 (`names.py`, `conftest.py`).
- 조회 전용(주문·환전 없음), 키·계좌번호는 코드·git·시트에 두지 않는다.
- 사용자 입력 칸과 스크립트가 쓰는 칸은 `values()`로 덮어쓰지 않는다 (`증권계좌` A5:E14, F5:F14, `투자기록` 데이터 행, `투자기록_계좌` 데이터 행).
- 커밋은 파일 경로를 지정한다 (`git add -A` 금지). 커밋 메시지 끝: ``.
- 붙여넣기 계좌가 하나도 없으면 `투자`·`투자기록`의 기존 값은 **한 글자도 달라지지 않는다** (회귀 금지).
- 기존 테스트(pytest 409, node 173)는 계속 통과해야 한다. 열 수·행 수·KPI 수식을 세는 기존 테스트의 기대값 갱신은 해당 Task에서 한다.
- 투자 화면 색 관례: 수익 빨강, 손실 파랑.

## Review Focus

1. 붙여넣기 계좌가 없는 날의 기록·합산이 이전과 같다 (Task 1 `withExtras` 빈 목록, Task 4 수식이 `""`).
2. 평가가 숫자가 아닌 계좌(붙여넣기 전)는 기타 합계에서 빠진다 (Task 1 `extraAccounts`).
3. 일부 계좌의 원금이 비어 있어도 손익 분모가 부풀지 않는다 (Task 4 `paired` 수식).
4. 같은 날 두 번 기록·계좌 이름 변경 뒤에도 `투자기록_계좌`에 줄이 쌓이지 않는다 (Task 1 `upsertAccountLog`, Task 2 글루).
5. 붙여넣기 계좌가 처음 생긴 날 `전일 대비`가 계좌 평가액만큼 뛴다 — 오해하지 않게 사용법에 적는다 (Task 5).

---

## File Structure

| 파일 | 역할 | 신규/수정 |
|---|---|---|
| `apps-script/positions.gs` | (Task 0) 손익 비움 조건이 수량(D)이 아닌 매입금액(E) 열을 보도록 수정 | 수정 |
| `apps-script/invest_logic.gs` | `extraAccounts`·`withExtras`·`accountLogRows`·`upsertAccountLog`, `shouldRecordInvest` 갱신, 열 수 14 | 수정 |
| `apps-script/triggers.gs` | `recordInvest`가 기타 계좌를 읽어 14열 기록 + 계좌별 기록 | 수정 |
| `layout.py` | `투자기록` 14열, 새 숨김 탭 `투자기록_계좌`, `증권계좌` 12열 | 수정 |
| `invest.py` | `투자` 13행 기타 합계, KPI 포함, 서식, `LOG_HEAD` 14열 | 수정 |
| `broker_accounts.py` | `증권계좌` H:L 계좌별 평가·원금·손익·수익률 수식 | 수정 |
| `migrate_couple.py` | 열 늘리기 일반화, 숨김 탭 등록, 13행 서식 매번 | 수정 |
| `guide.py`, `docs/USAGE.md` | 사용법 | 수정 |
| `tests/invest.test.js`, `tests/invest_record.test.js` | 순수 로직·글루 | 수정/신규 |
| `tests/test_invest_extra.py` | 시트 구성 | 신규 |

주소 상수: `증권계좌` 목록 `A5:A14`, 총평가 `J5:J14`, 원금 `I5:I14`, 예수금 `E5:E14`, 상태 `G5:G14`, 갱신일 `F5:F14`. 투자 기타 합계 행 `13`.

---

### Task 0: 계좌 탭 손익 비움 조건의 열 버그 수정

리뷰 반영 때 넣은 "매입금액이 빈 종목이 있으면 손익을 비운다"가 매입금액(E)이 아니라 **수량(D)** 열을 보고 있다. (정규 표 열: A 계좌 · B 코드 · C 종목명 · D 수량 · E 매입금액 · F 평가금액 · G 통화)

**Files:**
- Modify: `apps-script/positions.gs` (`buildAccountTab_`)
- Test: `tests/account_tab.test.js`

**Interfaces:**
- Consumes: 없음
- Produces: 계좌 탭 `B7`이 `COUNTIFS(증권종목표!$A$2:$A$1001,$B$1,증권종목표!$E$2:$E$1001,"")`를 쓴다.

- [ ] **Step 1: Write the failing test** — `tests/account_tab.test.js`의 `손익·수익률은 모든 종목에 매입금액이 있을 때만` 테스트에서 정규식의 `\$D\$2:\$D\$1001`을 `\$E\$2:\$E\$1001`로 바꾼다:

```js
  assert.match(sh.get(7, 2), /^=IF\(COUNTIFS\(증권종목표!\$A\$2:\$A\$1001,\$B\$1,증권종목표!\$E\$2:\$E\$1001,""\)>0,"",B3-B4\)$/);
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/account_tab.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: FAIL — `# fail 1`

- [ ] **Step 3: Write minimal implementation** — `apps-script/positions.gs`의 `buildAccountTab_`에서 `T + '!$D$2:$D$1001,""'`를 `T + '!$E$2:$E$1001,""'`로 바꾼다.

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: `# fail 0`

- [ ] **Step 5: Commit**

```bash
git add apps-script/positions.gs tests/account_tab.test.js
git commit -m "fix: 계좌 탭 손익 비움 조건이 수량이 아닌 매입금액 열을 보도록

"
```

---

### Task 1: 기록 순수 로직 (기타 계좌 합산·계좌별 기록)

**Files:**
- Modify: `apps-script/invest_logic.gs`
- Test: `tests/invest.test.js`

**Interfaces:**
- Consumes: 기존 `investLogRow(date, pairs) -> 12열 배열`, `isNum`, `dayStart`, 전역 `isBlank`
- Produces:
  - `var INVEST_LOG_COLS = 14`, `var INVEST_LOG_MISSING = 11`
  - `extraAccounts(rows) -> [{name, value, principal}]` (rows = `증권계좌!A5:K14` 값, 이름 A=0, 원금 I=8, 총평가 J=9)
  - `withExtras(row12, extras) -> 14열` (J·K에 기타 합계를 더하고 M·N에 기타 합계를 따로 둔다; extras가 비면 M·N은 `''`)
  - `accountLogRows(date, extras) -> [[date,name,value,principal]]`
  - `upsertAccountLog(existing, rows) -> rows` (같은 날짜+이름은 새 값으로 교체)
  - `shouldRecordInvest(row)`가 14열 줄도 처리

- [ ] **Step 1: Write the failing test** — `tests/invest.test.js` 끝에 추가:

```js
test('extraAccounts: 총평가가 숫자인 계좌만, 원금이 숫자가 아니면 빈칸', () => {
  const rows = [['신랑 키움', '', '', '', '', '', '', '', 1000, 1100], ['신부 삼성', '', '', '', '', '', '', '', '', 500],
    ['붙여넣기 전', '', '', '', '', '', '', '', '', ''], ['', '', '', '', '', '', '', '', 1, 2]];
  assert.deepEqual(plain(ctx.extraAccounts(rows)), [{ name: '신랑 키움', value: 1100, principal: 1000 }, { name: '신부 삼성', value: 500, principal: '' }]);
});

test('withExtras: 기타 계좌가 없으면 기존 12열 값은 그대로이고 M·N만 빈칸 (회귀 없음)', () => {
  const base = ctx.investLogRow(new Date(2026, 9, 12), [[1000, 900], ['', ''], [500, ''], ['키없음', 3]]);
  const out = ctx.withExtras(base, []);
  assert.equal(out.length, 14);
  assert.deepEqual(plain(out.slice(0, 12)), plain(base));
  assert.deepEqual(plain(out.slice(12)), ['', '']);
});

test('withExtras: 기타 평가·원금을 합계(J·K)에 더하고 M·N에 따로 남긴다, 원금이 하나도 없으면 N은 빈칸', () => {
  const base = ctx.investLogRow(new Date(2026, 9, 12), [[1000, 900], ['', ''], ['', ''], ['', '']]);
  const out = plain(ctx.withExtras(base, [{ name: 'a', value: 100, principal: 80 }, { name: 'b', value: 50, principal: '' }]));
  assert.deepEqual(out.slice(9), [1150, 980, 3, 150, 80]);
  const noP = plain(ctx.withExtras(base, [{ name: 'b', value: 50, principal: '' }]));
  assert.deepEqual(noP.slice(9), [1050, 900, 3, 50, '']);
});

test('shouldRecordInvest: 4계좌가 모두 비어도 기타 계좌가 있으면 기록한다, 둘 다 없으면 기록하지 않는다', () => {
  const d = new Date(2026, 9, 12);
  const empty = ctx.investLogRow(d, [['', ''], ['', ''], ['', ''], ['', '']]);
  assert.equal(ctx.shouldRecordInvest(ctx.withExtras(empty, [])), false);
  assert.equal(ctx.shouldRecordInvest(ctx.withExtras(empty, [{ name: 'a', value: 5, principal: '' }])), true);
  assert.equal(ctx.shouldRecordInvest(ctx.withExtras(ctx.investLogRow(d, [[1, 1], ['', ''], ['', ''], ['', '']]), [])), true);
});

test('upsertAccountLog: 같은 날짜+계좌는 교체, 다른 날짜·계좌는 유지, 날짜가 아닌 줄은 버림', () => {
  const d1 = new Date(2026, 9, 11), d2 = new Date(2026, 9, 12, 6, 3);
  const existing = [[d1, 'a', 1, 1], [new Date(2026, 9, 12), 'a', 2, 2], [new Date(2026, 9, 12), 'b', 3, 3], ['', '', '', '']];
  const out = ctx.upsertAccountLog(existing, ctx.accountLogRows(d2, [{ name: 'a', value: 9, principal: 8 }]));
  assert.deepEqual(plain(out).map((r) => [r[1], r[2]]), [['a', 1], ['b', 3], ['a', 9]]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/invest.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: FAIL — `ctx.extraAccounts is not a function` (새 5개 실패)

- [ ] **Step 3: Write minimal implementation** — `apps-script/invest_logic.gs` 수정:

`var INVEST_LOG_COLS = 12;`를 아래로 바꾼다:
```js
var INVEST_LOG_COLS = 14;      // A 날짜 · B~I 4계좌(평가,원금) · J 합계 평가 · K 합계 원금 · L 빠진 계좌 수 · M 기타 평가 · N 기타 원금
var INVEST_LOG_MISSING = 11;   // L열(0부터 11)
```
`shouldRecordInvest`를 아래로 교체한다:
```js
// 4계좌가 모두 빈 날(키 넣기 전 등)은 기록하지 않는다 — 0원 줄이 추이 그래프와 전일 대비를 망친다. 기타(붙여넣기) 계좌가 있으면 기록한다.
function shouldRecordInvest(row) {
  return row[INVEST_LOG_MISSING] < INVEST_ACCOUNT_ROWS.length || (row.length > 12 && isNum(row[12]));
}
```
파일 끝에 추가한다:
```js
// 증권계좌 A5:K14 줄 → 총평가(J)가 숫자인 계좌 [{name, value, principal}] (원금 I가 숫자가 아니면 '')
function extraAccounts(rows) {
  var out = [];
  rows.forEach(function (r) {
    var name = isBlank(r[0]) ? '' : String(r[0]).trim();
    if (name && isNum(r[9])) out.push({ name: name, value: r[9], principal: isNum(r[8]) ? r[8] : '' });
  });
  return out;
}

// 4계좌 기록 줄(12열)에 기타 증권사 계좌를 더해 14열로: 합계(J·K)에 포함하고 M·N에 기타 합계를 따로 남긴다. 기타가 없으면 M·N은 빈칸.
function withExtras(row, extras) {
  var out = row.slice(0, 12);
  if (!extras.length) return out.concat(['', '']);
  var v = 0, p = 0, hasP = false;
  extras.forEach(function (e) {
    v += e.value;
    if (e.principal !== '') { p += e.principal; hasP = true; }
  });
  out[9] += v;
  out[10] += p;
  return out.concat([v, hasP ? p : '']);
}

function accountLogRows(date, extras) {
  return extras.map(function (e) { return [date, e.name, e.value, e.principal]; });
}

// 투자기록_계좌(날짜|계좌|평가|원금): 같은 날짜+계좌는 새 값으로 교체하고 나머지는 유지한다. 날짜가 아닌 줄(빈 줄)은 버린다.
function upsertAccountLog(existing, rows) {
  var key = function (d, n) { return dayStart(d).getTime() + '|' + n; };
  var fresh = {};
  rows.forEach(function (r) { fresh[key(r[0], r[1])] = true; });
  var kept = existing.filter(function (r) {
    return Object.prototype.toString.call(r[0]) === '[object Date]' && !fresh[key(r[0], r[1])];
  });
  return kept.concat(rows);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)|^not ok"`
Expected: 전부 통과 (`# fail 0`). 기존 `investLogRow`/`shouldRecordInvest` 테스트도 12열 줄로 그대로 통과한다.

- [ ] **Step 5: Commit**

```bash
git add apps-script/invest_logic.gs tests/invest.test.js
git commit -m "feat: 투자기록 순수 로직 — 기타(붙여넣기) 계좌 합산·계좌별 기록

"
```

---

### Task 2: `recordInvest` 글루 + 시트 구성(기록 14열·새 숨김 탭)

**Files:**
- Modify: `apps-script/triggers.gs` (`recordInvest`), `layout.py`, `migrate_couple.py`, `invest.py` (`LOG_HEAD`)
- Test: `tests/invest_record.test.js` (신규), `tests/test_invest_extra.py` (신규)

**Interfaces:**
- Consumes: Task 1의 `extraAccounts`·`withExtras`·`accountLogRows`·`upsertAccountLog`, `FakeSpreadsheet`
- Produces:
  - `recordInvest(ss)`가 `투자기록` 14열 줄과 `투자기록_계좌` 줄을 쓴다
  - `layout.INVEST_LOG_DETAIL == "투자기록_계좌"` (sheetId 2830, 5000행, 4열, 숨김)
  - `layout.SHEETS`의 `투자기록`이 14열, `증권계좌`가 12열
  - `migrate_couple.GROW_COLS` (열 늘리기 일반화)

- [ ] **Step 1: Write the failing tests**

`tests/invest_record.test.js`:
```js
// recordInvest 글루: 4계좌 + 기타(붙여넣기) 계좌 → 투자기록 14열, 투자기록_계좌 줄.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet, FakeSpreadsheet } = require('./fake_sheets');

function setup(accountRows) {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'meritz_logic.gs', 'invest_logic.gs', 'triggers.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.todayDate = () => new Date(2026, 9, 22);                       // 어제 = 10-21
  const tab = new FakeSheet(Array.from({ length: 12 }, () => ['', '', '']));
  [[7, 1000, 900], [10, 500, 400]].forEach(([r, v, p]) => { tab.set(r, 2, v); tab.set(r, 3, p); });
  const list = new FakeSheet([[], [], [], [], ...accountRows]);
  const log = new FakeSheet([['날짜']]);
  const detail = new FakeSheet([['날짜']]);
  const ss = new FakeSpreadsheet({ '투자': tab, '투자기록': log, '증권계좌': list, '투자기록_계좌': detail });
  return { ctx, ss, log, detail, list };
}
const acct = (name, principal, value) => [name, '', '', '', '', '', '', '', principal, value, '', ''];
const plain = (x) => JSON.parse(JSON.stringify(x));

test('recordInvest: 기타 계좌가 합계(J·K)에 들어가고 M·N에 따로, 계좌별 줄도 쌓인다', () => {
  const t = setup([acct('신랑 키움', 800, 900), acct('신부 삼성', '', 100)]);
  t.ctx.recordInvest(t.ss);
  const row = plain(t.log.getRange('A2:N2').getValues()[0]);
  assert.deepEqual(row.slice(1), [1000, 900, '', '', 500, 400, '', '', 2500, 2100, 2, 1000, 800]);
  assert.deepEqual(plain(t.detail.getRange('B2:D3').getValues()), [['신랑 키움', 900, 800], ['신부 삼성', 100, '']]);
});

test('recordInvest: 기타 계좌가 없으면 기존과 똑같은 합계, M·N 빈칸, 계좌별 탭은 그대로', () => {
  const t = setup([]);
  t.ctx.recordInvest(t.ss);
  assert.deepEqual(plain(t.log.getRange('J2:N2').getValues()[0]), [1500, 1300, 2, '', '']);
  assert.equal(t.detail.get(2, 1), '');
});

test('recordInvest: 같은 날 두 번 돌려도 계좌별 줄은 늘지 않고 값만 바뀐다', () => {
  const t = setup([acct('신랑 키움', 800, 900)]);
  t.ctx.recordInvest(t.ss);
  t.list.set(5, 10, 950);
  t.ctx.recordInvest(t.ss);
  assert.deepEqual(plain(t.detail.getRange('B2:D3').getValues()), [['신랑 키움', 950, 800], ['', '', '']]);
  assert.equal(t.log.get(3, 1), '');
});

test('recordInvest: 4계좌가 모두 비어도 기타 계좌만 있으면 기록, 아무것도 없으면 기록하지 않는다', () => {
  const t = setup([acct('신랑 키움', 800, 900)]);
  [[7], [10]].forEach(([r]) => { t.ss.getSheetByName('투자').set(r, 2, ''); t.ss.getSheetByName('투자').set(r, 3, ''); });
  t.ctx.recordInvest(t.ss);
  assert.deepEqual(plain(t.log.getRange('J2:L2').getValues()[0]), [900, 800, 4]);
  const none = setup([]);
  [[7], [10]].forEach(([r]) => { none.ss.getSheetByName('투자').set(r, 2, ''); none.ss.getSheetByName('투자').set(r, 3, ''); });
  none.ctx.recordInvest(none.ss);
  assert.equal(none.log.get(2, 1), '');
});
```

`tests/test_invest_extra.py`:
```python
"""투자기록 14열·계좌별 기록 탭 (다증권사 B단계)."""
import layout
import migrate_couple as mc

ALL = {t for t, *_ in layout.SHEETS}


def _state(titles=ALL, grid=None):
    return mc.State(titles=set(titles), settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                    invest_charts=2, dash_rows=200, dash_base=46, grid=grid or {})


def test_log_has_14_columns_and_detail_tab_is_hidden_internal():
    props = {t: (sid, rows, cols, hidden) for t, sid, rows, cols, hidden in layout.SHEETS}
    assert props[layout.INVEST_LOG][2] == 14 and props[layout.BROKER_ACCTS][2] == 12
    assert props[layout.INVEST_LOG_DETAIL] == (2830, 5000, 4, True)


def test_headers_for_new_log_columns_and_detail_tab():
    import invest
    assert invest.LOG_HEAD[-2:] == ["기타 평가", "기타 원금"] and len(invest.LOG_HEAD) == 14
    ranges = {e["range"]: e["values"] for e in mc.plan(_state())[1]}
    assert ranges["투자기록_계좌!A1:D1"] == [["날짜", "계좌", "평가", "원금"]]
    assert ranges[f"{layout.INVEST_LOG}!A1:N1"][0][-2:] == ["기타 평가", "기타 원금"]


def test_live_tabs_grow_to_new_widths_once_and_detail_tab_is_added():
    grid = {layout.SHEET_ID[layout.INVEST_LOG]: (1000, 12), layout.SHEET_ID[layout.BROKER_ACCTS]: (40, 9)}
    st = _state(ALL - {layout.INVEST_LOG_DETAIL}, grid)
    structure = mc.plan(st)[0]
    grow = {r["appendDimension"]["sheetId"]: r["appendDimension"]["length"] for r in structure if "appendDimension" in r}
    assert grow[layout.SHEET_ID[layout.INVEST_LOG]] == 2 and grow[layout.SHEET_ID[layout.BROKER_ACCTS]] == 3
    assert layout.INVEST_LOG_DETAIL in {r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r}
    done = {layout.SHEET_ID[layout.INVEST_LOG]: (1000, 14), layout.SHEET_ID[layout.BROKER_ACCTS]: (40, 12)}
    again = {r["appendDimension"]["sheetId"] for r in mc.plan(_state(grid=done))[0] if "appendDimension" in r}
    assert layout.SHEET_ID[layout.INVEST_LOG] not in again and layout.SHEET_ID[layout.BROKER_ACCTS] not in again
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/invest_record.test.js 2>&1 | grep -E "^# (pass|fail)"; python3 -m pytest -q tests/test_invest_extra.py 2>&1 | tail -3`
Expected: node 4개 실패, pytest `AttributeError: module 'layout' has no attribute 'INVEST_LOG_DETAIL'`

- [ ] **Step 3: Write minimal implementation**

`apps-script/triggers.gs`의 `recordInvest`를 아래로 교체한다 (`if (!shouldRecordInvest(row)) return;` 줄은 그대로 유지 — `tests/test_deploy.py`가 찾는다):
```js
function recordInvest(ss) {
  var tab = ss.getSheetByName('투자');
  var log = ss.getSheetByName('투자기록');
  if (!tab || !log) return;
  var vals = tab.getRange(1, 2, 12, 2).getValues(); // B1:C12 — 계좌 행의 평가·원금
  var pairs = INVEST_ACCOUNT_ROWS.map(function (r) { return vals[r - 1]; });
  var list = ss.getSheetByName('증권계좌');
  var extras = list ? extraAccounts(list.getRange('A5:K14').getValues()) : [];   // 붙여넣기 계좌 (총평가가 숫자인 것만)
  var date = yesterday(todayDate());
  var row = withExtras(investLogRow(date, pairs), extras);
  if (!shouldRecordInvest(row)) return;
  var at = dateRowIndex(log.getRange(1, 1, log.getMaxRows(), 1).getValues(), date);
  if (at > log.getMaxRows()) log.insertRowsAfter(log.getMaxRows(), 365);
  log.getRange(at, 1, 1, INVEST_LOG_COLS).setValues([row]);
  var detail = ss.getSheetByName('투자기록_계좌');
  if (detail && extras.length) {
    var last = nextEmptyRow(detail.getRange(1, 1, detail.getMaxRows(), 1).getValues()) - 1;
    var existing = last >= 2 ? detail.getRange(2, 1, last - 1, 4).getValues() : [];
    var rows = upsertAccountLog(existing, accountLogRows(date, extras));
    if (rows.length + 1 > detail.getMaxRows()) detail.insertRowsAfter(detail.getMaxRows(), 1000);
    detail.getRange(2, 1, rows.length, 4).setValues(rows);
  }
}
```

`layout.py`: 상수 `INVEST_LOG_DETAIL = "투자기록_계좌"` (다른 탭 이름 상수 옆), `SHEETS`에서
`(INVEST_LOG, 2000, 1000, 12, True),` → `(INVEST_LOG, 2000, 1000, 14, True),`
`(BROKER_ACCTS, 2800, 40, 9, False),` → `(BROKER_ACCTS, 2800, 40, 12, False),`
그리고 내부용 숨김 탭 끝(`POS_TABLE_TAB` 줄 뒤)에 `(INVEST_LOG_DETAIL, 2830, 5000, 4, True),` 추가.

`invest.py`: `LOG_HEAD` 끝에 `"기타 평가", "기타 원금"` 추가 (14열). `from layout import ...`에 `INVEST_LOG_DETAIL` 추가하고 `invest_values()`의 마지막 `v(f"{L}!A1:L1", [LOG_HEAD])`를 `v(f"{L}!A1:N1", [LOG_HEAD])`로 바꾸고, 같은 목록에 `v(f"{INVEST_LOG_DETAIL}!A1:D1", [["날짜", "계좌", "평가", "원금"]])`를 더한다. `structure_requests()`의 서식 목록에 `(f"{INVEST_LOG_DETAIL}!A2:A5000", "DATE", "yyyy-mm-dd")`, `(f"{INVEST_LOG_DETAIL}!C2:D5000", "NUMBER", "#,##0")`, `(f"{L}!M2:N1000", "NUMBER", "#,##0")`를 더한다.

`migrate_couple.py`:
- `HOLD_TABS = (layout.KIS_HOLD, layout.POS_TABLE_TAB, layout.INVEST_LOG_DETAIL)`
- 클래스 상단 상수 근처에 `GROW_COLS = (layout.BROKER_POS, layout.BROKER_ACCTS, layout.INVEST_LOG)  # 열이 늘어난 기존 탭`
- `_structure`의 `pos_cols = ... appendDimension` 블록(BROKER_POS 전용)을 아래 반복문으로 교체:
```python
    for tab in GROW_COLS:  # 처음 만들 때보다 열이 늘어난 기존 탭 (붙여넣기 칸 A:T, 증권계좌 H:L, 투자기록 M:N)
        want = next(c for t, _s, _r, c, _h in SHEETS if t == tab)
        have = (s.grid or {}).get(SHEET_ID[tab], (0, want))[1]
        if tab in s.titles and have < want:
            reqs.append({"appendDimension": {"sheetId": SHEET_ID[tab], "dimension": "COLUMNS", "length": want - have}})
```
- `_grown`의 반복 대상 `(layout.STOCKS, layout.BROKER_POS)`를 `(layout.STOCKS, *GROW_COLS)`로 바꾼다.

- [ ] **Step 4: Run tests to verify they pass, then fix count-based expectations**

Run: `node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)"; python3 -m pytest -q 2>&1 | tail -12`
Expected: 새 테스트 통과. 기존 테스트 중 **`투자기록` 열 수(12)·탭 목록/숨김 목록·`LOG_HEAD` 길이·`INVEST_LOG` 범위 문자열**을 세는 것이 실패할 수 있다 (예: `tests/test_invest.py`, `tests/test_layout.py`, `tests/test_couple.py`, `tests/test_migrate_couple.py`의 숨김 탭 집합에 `투자기록_계좌` 추가, `props["투자기록"] == (2000, 1000, 12, True)` → 14). 실패 각각을 읽고 새 값만 반영한다 (동작은 바꾸지 않는다). 최종 `# fail 0` / `failed 0`.

- [ ] **Step 5: Commit**

```bash
git add apps-script/triggers.gs layout.py invest.py migrate_couple.py tests/invest_record.test.js tests/test_invest_extra.py tests/test_invest.py tests/test_layout.py tests/test_couple.py tests/test_migrate_couple.py
git commit -m "feat: recordInvest가 기타(붙여넣기) 계좌를 투자기록 합계·계좌별 기록에 포함

"
```
(다른 테스트 파일의 기대값을 고쳤다면 그 경로도 `git add`에 지정한다.)

---

### Task 3: `증권계좌` 계좌별 평가·원금·손익 열

**Files:**
- Modify: `broker_accounts.py`
- Test: `tests/test_invest_extra.py`

**Interfaces:**
- Consumes: Task 2의 `증권계좌` 12열, 정규 표(`증권종목표` A 계좌·D 수량·E 매입금액·F 평가금액)
- Produces: `증권계좌` H 종목평가 · I 원금(매입금액 합, 빈 매입금액이 있으면 빈칸) · J 평가금액(총, 종목평가+예수금, 종목이 없으면 빈칸) · K 손익(종목 기준) · L 수익률 — 5~14행 각 행 수식. `Task 1`의 `extraAccounts`가 I(원금)·J(총평가)를 읽는다.

- [ ] **Step 1: Write the failing test** — `tests/test_invest_extra.py`에 추가:

```python
def test_account_list_has_per_account_value_columns_with_blank_safe_formulas():
    import broker_accounts
    vals = {e["range"]: e["values"] for e in broker_accounts.values()}
    assert vals["증권계좌!A4:L4"][0][7:] == ["종목평가", "원금(매입)", "평가금액(총)", "손익", "수익률"]
    row5 = vals["증권계좌!H5:L14"][0]
    h, i, j, k, l = row5
    assert 'SUMIFS(증권종목표!$F$2:$F$1001,증권종목표!$A$2:$A$1001,$A5)' in h
    assert 'COUNTIFS(증권종목표!$A$2:$A$1001,$A5,증권종목표!$E$2:$E$1001,"")>0' in i       # 매입금액이 빈 종목이 있으면 원금은 비움
    assert 'COUNTIF(증권종목표!$A$2:$A$1001,$A5)=0' in j and 'N(E5)' in j                     # 종목이 없으면(붙여넣기 전) 총평가도 빈칸
    assert k == '=IF(OR(J5="",I5=""),"",H5-I5)' and l == '=IF(OR(K5="",N(I5)=0),"",K5/I5)'
    assert len(vals["증권계좌!H5:L14"]) == 10
    assert not any(a in vals for a in ("증권계좌!A5", "증권계좌!E5", "증권계좌!F5"))          # 입력·스크립트 칸은 값으로 쓰지 않는다
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_invest_extra.py::test_account_list_has_per_account_value_columns_with_blank_safe_formulas`
Expected: FAIL — `KeyError: '증권계좌!A4:L4'`

- [ ] **Step 3: Write minimal implementation** — `broker_accounts.py` 수정:

`HEADERS`를 `["이름", "소유자", "증권사", "방식", "예수금", "마지막 붙여넣기", "상태", "종목평가", "원금(매입)", "평가금액(총)", "손익", "수익률"]`로, `HEADS = [f"{S}!A{HEAD}:L{HEAD}"]`, `BODIES = [f"{S}!A{FIRST}:L{LAST}"]`, `RUNS = [("A", FIRST, LAST, "LCLCRCCRRRRR")]`, `WIDTHS = [180, 90, 110, 90, 110, 130, 110, 110, 110, 120, 100, 80]`.

파일 상단 근처에 행 수식 함수를 추가한다:
```python
T = "증권종목표"


def _value_formulas(r: int) -> list[str]:
    """H 종목평가 · I 원금(매입금액 합, 빈 매입금액이 있으면 빈칸) · J 평가금액(총) · K 손익 · L 수익률. 종목이 없으면(붙여넣기 전) 빈칸."""
    a = f"{T}!$A$2:$A$1001"
    return [f'=IF($A{r}="","",SUMIFS({T}!$F$2:$F$1001,{a},$A{r}))',
            f'=IF($A{r}="","",IF(COUNTIFS({a},$A{r},{T}!$E$2:$E$1001,"")>0,"",SUMIFS({T}!$E$2:$E$1001,{a},$A{r})))',
            f'=IF($A{r}="","",IF(COUNTIF({a},$A{r})=0,"",H{r}+N(E{r})))',
            f'=IF(OR(J{r}="",I{r}=""),"",H{r}-I{r})',
            f'=IF(OR(K{r}="",N(I{r})=0),"",K{r}/I{r})']
```
`values()`의 헤더 줄을 `v(f"{S}!A{HEAD}:L{HEAD}", [HEADERS])`로 바꾸고, 목록 끝에 `v(f"{S}!H{FIRST}:L{LAST}", [_value_formulas(r) for r in range(FIRST, LAST + 1)])`를 더한다. `formats()`에 `number_format(f"{S}!H{FIRST}:K{LAST}", "NUMBER", "#,##0")`, `number_format(f"{S}!L{FIRST}:L{LAST}", "PERCENT", "0.0%")`를 더한다.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q 2>&1 | tail -4`
Expected: 통과. `tests/test_broker_tabs.py::test_account_list_headers_input_cells_and_status_formula`가 `증권계좌!A4:G4`를 찾으므로 `증권계좌!A4:L4`로 기대값을 바꾸고 첫 7열이 같은지만 확인한다.

- [ ] **Step 5: Commit**

```bash
git add broker_accounts.py tests/test_invest_extra.py tests/test_broker_tabs.py
git commit -m "feat: 증권계좌에 계좌별 종목평가·원금·총평가·손익·수익률 열

"
```

---

### Task 4: `투자` 탭 13행 "기타 증권사" 합계와 KPI 포함

**Files:**
- Modify: `invest.py`, `migrate_couple.py`
- Test: `tests/test_invest_extra.py`

**Interfaces:**
- Consumes: Task 3의 `증권계좌` I·J·K·E·F·G 열
- Produces: `투자!A13:G13`·`J13` 수식. KPI(`A4:F4`)가 13행을 포함. 13행 서식이 마이그레이션마다 적용.

- [ ] **Step 1: Write the failing test** — `tests/test_invest_extra.py`에 추가:

```python
def test_invest_row13_sums_pasted_accounts_and_kpis_include_it():
    import invest
    vals = {e["range"]: e["values"] for e in invest.invest_values()}
    a, b, c, d, e, f, g = vals["투자!A13:G13"][0]
    assert a == "기타 증권사 (붙여넣기)"
    assert b == '=IF(COUNT(증권계좌!$J$5:$J$14)=0,"",SUM(증권계좌!$J$5:$J$14))'
    assert 'SUM(FILTER(증권계좌!$I$5:$I$14,ISNUMBER(증권계좌!$J$5:$J$14)))' in c           # 평가가 있는 계좌의 원금만
    assert d == '=IF(COUNT(증권계좌!$K$5:$K$14)=0,"",SUM(증권계좌!$K$5:$K$14))'
    assert 'SUM(FILTER(증권계좌!$I$5:$I$14,ISNUMBER(증권계좌!$K$5:$K$14)))' in e            # 손익이 있는 계좌의 원금이 분모
    assert '오래됨' in g and '붙여넣기 전' in g
    assert vals["투자!J13"][0][0].startswith('=IF(COUNT(증권계좌!$J$5:$J$14)=0,"",')
    k = vals["투자!A4:F4"][0]
    assert "B7,B8,B10,B11,B13" in k[0] and "C13" in k[1] and "D13" in k[2] and "IF(ISNUMBER(D13),C13,0)" in k[3]


def test_row13_formats_applied_every_run_with_red_gain_blue_loss_number_format():
    structure = mc.plan(_state())[0]
    fmts = {r["repeatCell"]["range"]["startRowIndex"]: r for r in structure if "repeatCell" in r
            and r["repeatCell"]["range"].get("sheetId") == layout.SHEET_ID[layout.INVEST]}
    patterns = [r["repeatCell"]["cell"]["userEnteredFormat"].get("numberFormat", {}).get("pattern", "") for r in structure
                if "repeatCell" in r and r["repeatCell"]["range"] == layout.a1_to_grid("투자!D13")]
    assert patterns == ["[Red]+#,##0;[Blue]-#,##0;0"]
    pct = [r["repeatCell"]["cell"]["userEnteredFormat"]["numberFormat"]["pattern"] for r in structure
           if "repeatCell" in r and r["repeatCell"]["range"] == layout.a1_to_grid("투자!E13")]
    assert pct == ["[Red]0.0%;[Blue]-0.0%;0.0%"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_invest_extra.py -k "row13"`
Expected: FAIL — `KeyError: '투자!A13:G13'`

- [ ] **Step 3: Write minimal implementation**

`invest.py` — 함수 추가:
```python
EXTRA_ROW = 13
EXTRA_NAME = "기타 증권사 (붙여넣기)"
_LIST = "증권계좌"


def extra_row() -> list[str]:
    """붙여넣기 계좌(증권계좌 5~14행) 합계 한 줄. 평가가 숫자인 계좌만 센다. 갱신은 가장 오래된 붙여넣기 날짜."""
    j, i, k, e, f, g = (f"{_LIST}!${c}$5:${c}$14" for c in "JIKEFG")
    return [EXTRA_NAME,
            f'=IF(COUNT({j})=0,"",SUM({j}))',
            f'=IF(COUNT({j})=0,"",IFERROR(SUM(FILTER({i},ISNUMBER({j}))),0))',
            f'=IF(COUNT({k})=0,"",SUM({k}))',
            f'=IF(COUNT({k})=0,"",IFERROR(D13/SUM(FILTER({i},ISNUMBER({k}))),""))',
            f'=IF(COUNT({j})=0,"",IFERROR(MIN(FILTER({f},ISNUMBER({f}))),""))',
            f'=IF(COUNT({j})=0,"붙여넣기 전",IF(COUNTIF({g},"오래됨")>0,"오래됨 "&COUNTIF({g},"오래됨")&"개","정상"))']
```
`_kpi()`의 `acc`와 합산 식에 13행을 더한다:
```python
    acc = "B7,B8,B10,B11,B13"
    ...
    return [f'=IF(COUNT({acc})=0,"",SUM({acc}))', f'=IF(COUNT(C7,C8,C10,C11,C13)=0,"",SUM(C7,C8,C10,C11,C13))',
            '=IF(COUNT(D7,D8,D10,D11,D13)=0,"",SUM(D7,D8,D10,D11,D13))', f'=IFERROR(C4/({paired_principal((7, 8, 10, 11, 13))}),"")',
            prev_day, prev_month]
```
(주의: 수익률 분모는 `D4/(...)`가 아니라 기존 식 그대로 손익 합 `C4`가 아닌 **D4** 기준인지 확인한다 — 기존 코드가 쓰는 셀(`D4`/`C4`)을 그대로 두고 `paired_principal`의 행 목록만 바꾼다.)

`invest_values()`의 계좌·합계 줄 추가 부분에 아래를 더한다:
```python
    out += [v(f"{INVEST}!A13:G13", [extra_row()]),
            v(f"{INVEST}!J13", [[f'=IF(COUNT({_LIST}!$J$5:$J$14)=0,"",IFERROR(SUM(FILTER({_LIST}!$E$5:$E$14,ISNUMBER({_LIST}!$J$5:$J$14))),""))']])]
```
`structure_requests()`의 서식 목록은 기존 항목을 두고 13행을 추가한다:
`(f"{INVEST}!B13:C13", "NUMBER", "#,##0")`, `(f"{INVEST}!D13", "NUMBER", "[Red]+#,##0;[Blue]-#,##0;0")`, `(f"{INVEST}!E13", "PERCENT", "[Red]0.0%;[Blue]-0.0%;0.0%")`, `(f"{INVEST}!F13", "DATE_TIME", "mm/dd")`, `(f"{INVEST}!J13", "NUMBER", "#,##0")`.

`migrate_couple.py` `_always`의 `fmts = _in(invest.structure_requests(), [...], "repeatCell")` 범위 목록에 `f"{INVEST}!B13:C13", f"{INVEST}!D13", f"{INVEST}!E13", f"{INVEST}!F13", f"{INVEST}!J13"`를 추가해 **운영 시트에도 매번** 적용되게 한다.

- [ ] **Step 4: Run tests to verify they pass, then fix KPI-text expectations**

Run: `python3 -m pytest -q 2>&1 | tail -8`
Expected: 새 테스트 통과. `tests/test_invest.py` 등에서 KPI 수식 문자열(`B7,B8,B10,B11`, `paired_principal` 행 목록)을 비교하는 기존 단언이 실패하면 새 식(13행 포함)으로 기대값만 갱신한다. 최종 `failed 0`.

- [ ] **Step 5: Commit**

```bash
git add invest.py migrate_couple.py tests/test_invest_extra.py tests/test_invest.py
git commit -m "feat: 투자 13행 기타 증권사(붙여넣기) 합계, KPI 포함

"
```

---

### Task 5: 사용법·안내 문서

**Files:**
- Modify: `guide.py`, `docs/USAGE.md`, `README.md`
- Test: `tests/test_invest_extra.py`

**Interfaces:**
- Consumes: `guide.CONTENT`
- Produces: `[투자]` 사용법 행에 기타 증권사 한 줄·전일 대비 점프 안내

- [ ] **Step 1: Write the failing test** — `tests/test_invest_extra.py`에 추가:

```python
def test_guide_explains_extra_row_and_first_day_jump():
    import guide
    text = " ".join(b for _k, a, b in guide.CONTENT if a == "[투자]")
    assert "기타 증권사" in text and "붙여넣기" in text
    assert "처음" in text and "전일 대비" in text            # 붙여넣기 계좌가 생긴 첫날 전일 대비가 뛴다
    assert "투자기록" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_invest_extra.py::test_guide_explains_extra_row_and_first_day_jump`
Expected: FAIL — `assert '기타 증권사' in ...`

- [ ] **Step 3: Write minimal implementation** — `guide.py`의 `("row", "[투자]", "...")` 문장 끝에 아래 문장을 이어 붙인다:

`" [증권계좌]에 적고 [증권종목]에 붙여넣은 다른 증권사 계좌는 13행 '기타 증권사 (붙여넣기)' 한 줄로 합산되어 위 합계·손익·수익률에 들어가고, 매일 아침 [투자기록]에 함께 기록됩니다(계좌별 기록은 숨김 탭에 쌓임). 붙여넣기 값은 직접 갱신해야 하므로 14일이 넘으면 상태가 '오래됨'으로 바뀌고, 붙여넣기 계좌가 처음 생긴 날은 전일 대비가 그 계좌 평가금액만큼 뛰어 보입니다."`

`docs/USAGE.md`의 "### 다른 증권사 (붙여넣기)" 표에 두 줄을 더한다:
```markdown
| `투자` 탭 반영 | 13행 `기타 증권사 (붙여넣기)`에 합산되어 KPI(평가·원금·손익·수익률)에 포함 |
| `투자기록` | 매일 06시에 합계(J·K)에 포함되고 M·N에 기타 합계, 계좌별 값은 숨김 탭 `투자기록_계좌`에 쌓임. 붙여넣기 계좌가 처음 생긴 날은 `전일 대비`가 그 계좌 평가만큼 뛰어 보임 |
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest -q 2>&1 | tail -3; node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: 모두 통과

- [ ] **Step 5: Commit**

```bash
git add guide.py docs/USAGE.md tests/test_invest_extra.py
git commit -m "docs: 투자 합산·투자기록에 기타 증권사 포함 안내

"
```

---

### Task 6: 배포와 운영 시트 적용·검증

**Files:** 코드 변경 없음 (검증 중 발견한 버그만 TDD로 고친다)

- [ ] **Step 1: 전체 테스트**

Run: `python3 -m pytest -q 2>&1 | tail -1; node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: pytest 전부 통과, node `# fail 0`

- [ ] **Step 2: 백업 사본**

`우리집 가계부 백업 (2026-10-27 투자 기타 증권사 전)` 이름으로 Drive 사본을 만든다 (`split_names.py` 98~100행의 `files().copy` 호출 형태). Expected: 사본 id 출력.

- [ ] **Step 3: 배포와 적용**

Run: `python3 deploy_script.py && python3 migrate_couple.py` (사이에 오류가 나면 중단). 그 뒤 약 60초 기다린다.
Expected: `업로드 완료`, `적용: 구조 N개, 값 M개 범위, ...`

- [ ] **Step 4: 읽기 전용 검증 (회귀 없음)**

기존 `post2.py`와 아래를 읽는다.
- 오류 칸 0, 1650px 넘는 탭 없음.
- `투자!A4:F4`·`B7:J12`가 적용 전과 **같다** (붙여넣기 계좌가 없으므로 `B13:G13`은 빈칸/`붙여넣기 전`, `J13` 빈칸).
- `증권계좌!H4:L4` 머리글, `투자기록!M1:N1` 머리글, 숨김 탭 `투자기록_계좌!A1:D1`.
- `투자기록`의 기존 행(10-12~어제)은 변하지 않았다.

- [ ] **Step 5: 실사용 확인 요청 (자동 기록은 06시, 이 환경에서 직접 실행 불가)**

사용자에게 안내한다: ① `증권계좌`에 계좌를 적고 종목을 반영한 뒤 `투자` 13행·KPI에 포함되는지, ② 다음 날 06시 이후 `투자기록` 어제 줄의 M·N열과 숨김 탭 `투자기록_계좌`에 줄이 생겼는지(테스트 계좌는 확인 후 지울 것). 다음 날 아침 읽기 전용 점검을 예약한다.

- [ ] **Step 6: 병합·push는 요청할 때만**

---

## Self-Review

1. **Spec coverage**: §3.3 "계좌가 목록에 생기면 다음 기록부터 자동 포함" → Task 1·2(`recordInvest`) / "계좌별 기록" → `투자기록_계좌`(Task 2) / §7 "투자 표가 목록 길이만큼" → 13행 한 줄 합계로 단순화(Ruling, 같은 효과: 합산·KPI 포함) / 평가가 숫자가 아닌 계좌는 기록하지 않음 → `extraAccounts` / §8 마이그레이션 백업·대조 → 기존 기록을 바꾸지 않으므로 변환 대신 Task 6의 "기존 값 동일" 검증. **C단계로 미룬 것**: 기존 4계좌의 목록 이전, 어댑터(`x_fetch`), `주식투자` 소스 전환, 투자 탭 소유자별 합계에 기타 포함.
2. **Placeholder scan**: Task 2/4 Step 4의 "기대값 갱신"은 실패한 테스트를 열어 새 값만 반영하는 구체 지시다. Task 4 `_kpi` 안내 괄호는 기존 셀 참조를 유지하라는 지시이며 실제 코드를 제시했다. TBD 없음.
3. **Type consistency**: `extraAccounts` 반환 `{name,value,principal}` ↔ `withExtras`/`accountLogRows` 사용 일치. `증권계좌` 열(I 원금·J 총평가·K 손익·E 예수금·F 갱신·G 상태)이 Task 1 `A5:K14` 인덱스(원금 8·총평가 9)·Task 4 수식 열과 일치. 기록 열 수 14, 빠진 계좌 수 인덱스 11, 기타 평가 12 ↔ `shouldRecordInvest`.
4. **Review Focus 매핑**: 1 → Task 1 `withExtras` 빈 목록·Task 2 `기타 계좌가 없으면`, 2 → Task 1 `extraAccounts`, 3 → Task 4 `paired`(분모 FILTER), 4 → Task 1 `upsertAccountLog`·Task 2 `같은 날 두 번`, 5 → Task 5.
