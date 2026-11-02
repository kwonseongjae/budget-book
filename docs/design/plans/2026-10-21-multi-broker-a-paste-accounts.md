# 다증권사 계좌 (A단계: 계좌 목록 · 붙여넣기 · 계좌 탭 자동 생성) Implementation Plan

**Goal:** 메리츠·한투 외 증권사 계좌를 `증권계좌` 목록에 적고, 증권사 앱의 보유종목 표를 `증권종목`에 붙여넣으면 종목이 반영되며, 계좌를 적는 즉시 그 계좌의 상세 탭 `계좌_<이름>`이 자동으로 만들어진다.

**Architecture:** 순수 로직(`positions_logic.gs`: 표 해석·행 교체·이름 검증)과 시트 연결(`positions.gs`: 붙여넣기 반영·탭 동기화)을 나누고, onEdit 라우팅(`logic.gs routeEdit` → `triggers.gs onEdit`)으로 호출한다. 시트 쪽은 새 탭 두 개(`broker_accounts.py`, `broker_positions.py`)를 기존 `sigol_tabs.MODULES` 경로로 만들고 `migrate_couple.py`가 운영 시트에 한 번만 추가한다. **기존 `투자`·`투자기록`·`주식투자`는 이 단계에서 건드리지 않는다** (B단계 별도 계획).

**Tech Stack:** Python 3 + pytest(시트 생성기), Google Apps Script(V8) + `node --test`(가짜 시트 `tests/fake_sheets.js`), Sheets API.

**Spec:** `docs/design/specs/2026-10-21-multi-broker-design.md` (§2 범위의 `증권계좌`·`증권종목`·붙여넣기·§6 계좌 탭 자동 생성·§5 파서. §3.3 투자기록 변환·§7 투자/주식투자 전환·§4 어댑터·§8 마이그레이션은 B단계)

## Global Constraints

- 코드·문서·테스트에는 실제 이름 금지, 사람은 **신랑 / 신부**만 쓴다 (`names.py`, `conftest.py`가 테스트를 기본 이름으로 고정).
- 조회 전용: 주문·환전 경로 없음. 앱 키·계좌번호는 코드·git·시트에 두지 않는다 (이 단계는 키가 필요 없다).
- 시트 사용자 문구는 한국어, 응답·보고도 한국어.
- 커밋은 파일 경로를 지정해서 한다 (`git add -A` 금지). 커밋 메시지 끝에 ``.
- 사용자가 직접 입력하는 칸(`INPUTS`)은 `values()`가 쓰지 않는다. 스크립트가 쓰는 칸(결과 메시지, 마지막 붙여넣기 날짜, 정규 종목 표)도 `values()`로 덮어쓰지 않는다.
- 계좌는 최대 10개 (`증권계좌!A5:A14`), 붙여넣기 표는 최대 200줄 (`A6:F205`), 정규 종목 표는 최대 1000줄 (`H6:N1005`).
- 기존 테스트(pytest 395, node 134)는 모두 계속 통과해야 한다. 탭 목록·검증 목록을 세는 기존 테스트의 기대값 갱신은 해당 Task에서 한다.

## Review Focus

1. 머리글을 못 찾은 붙여넣기 → 기존 종목을 지우지 않고 안내만 한다 (Task 1·3 테스트).
2. 같은 계좌를 두 번 붙여넣기 → 교체되며 줄이 쌓이지 않는다. 다른 계좌 줄은 그대로 (Task 1·3).
3. 합계 줄·빈 줄·음수(괄호)·`원`/`%`/쉼표가 섞인 숫자·CSV 따옴표 쉼표 (`"A, Inc"`) (Task 1).
4. 계좌 이름에 금지 문자(`[ ] * ? : / \`)·중복·너무 긴 이름 → 탭을 만들지 않고 알린다 (Task 4).
5. 계좌 이름을 바꾸면 탭 이름과 `증권종목`의 계좌명이 함께 바뀐다. 이름을 지우면 탭은 삭제하지 않고 숨긴다 (Task 4).

---

## File Structure

| 파일 | 역할 | 신규/수정 |
|---|---|---|
| `apps-script/positions_logic.gs` | 표 해석 `parsePositions`, 행 교체 `replaceAccountRows`, 이름 바꾸기 `renameAccountRows`, 이름 검증 `validAccountName` (순수) | 신규 |
| `apps-script/positions.gs` | `importPositions`, `syncAccountTab`, `buildAccountTab` (시트 연결) | 신규 |
| `apps-script/logic.gs` | `routeEdit`에 `positions`·`brokerTab` 경로 추가 | 수정 |
| `apps-script/triggers.gs` | `onEdit`가 두 경로를 호출 | 수정 |
| `tests/fake_sheets.js` | `FakeSpreadsheet`, 시트 이름·숨김·수식 지원 | 수정 |
| `tests/positions.test.js` | 파서·행 교체·이름 검증 | 신규 |
| `tests/positions_import.test.js` | `importPositions` 글루 | 신규 |
| `tests/account_tab.test.js` | `syncAccountTab`·라우팅 | 신규 |
| `layout.py` | 탭 이름·sheetId·주소 상수, `SHEETS` 두 줄 | 수정 |
| `broker_accounts.py` | `증권계좌` 탭 모듈 | 신규 |
| `broker_positions.py` | `증권종목` 탭 모듈 | 신규 |
| `sigol_tabs.py` | `MODULES`에 두 모듈 | 수정 |
| `styling.py` | `TAB_COLORS`에 두 탭 | 수정 |
| `deploy_script.py` | `SOURCES`에 두 `.gs` | 수정 |
| `guide.py` | `[증권계좌]`·`[증권종목]` 사용법 | 수정 |
| `docs/USAGE.md`, `README.md` | 사용법 안내 | 수정 |
| `tests/test_broker_tabs.py` | 탭 구성·주소 일치·마이그레이션 | 신규 |

주소 상수(Python `layout.py` ↔ `positions.gs`, 테스트가 대조):
`POS_ACCOUNT='B2'` `POS_CHECK='B3'` `POS_RESULT='C3'` `POS_PASTE='A6:F205'` `POS_TABLE='H6:N1005'` `ACCT_NAMES='A5:A14'` `ACCT_PASTED='F5:F14'` `ACCOUNT_TAB_PREFIX='계좌_'`.

---

### Task 1: 붙여넣기 표 해석 (순수 로직)

**Files:**
- Create: `apps-script/positions_logic.gs`
- Test: `tests/positions.test.js`

**Interfaces:**
- Consumes: 전역 `isBlank(x)` (`logic.gs`)
- Produces:
  - `posNum(x) -> number|NaN`
  - `parsePositions(cells: any[][]) -> {error:string} | {positions:[{code,name,qty,cost,value,currency}], failed:string[]}`
  - `replaceAccountRows(table: any[][], account: string, positions) -> any[][]` (행 = `[계좌,코드,종목명,수량,매입금액,평가금액,통화]`)
  - `renameAccountRows(table, from, to) -> any[][]`
  - `validAccountName(name: string) -> string` (문제가 없으면 `''`, 있으면 사용자에게 보일 문장)

- [ ] **Step 1: Write the failing test** — `tests/positions.test.js`

```js
// 붙여넣은 보유종목 표 해석: 머리글 이름으로 열을 찾고, 숫자 표기·합계 줄·CSV를 견딘다.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function load() {
  const ctx = vm.createContext({});
  for (const f of ['logic.gs', 'positions_logic.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  return ctx;
}
const plain = (x) => JSON.parse(JSON.stringify(x));

test('posNum: 쉼표·원·%·플러스·괄호 음수, 못 읽으면 NaN', () => {
  const c = load();
  assert.equal(c.posNum('1,234원'), 1234);
  assert.equal(c.posNum('+5.2%'), 5.2);
  assert.equal(c.posNum('(1,234)'), -1234);
  assert.equal(c.posNum(7), 7);
  assert.ok(Number.isNaN(c.posNum('-')));
  assert.ok(Number.isNaN(c.posNum('abc')));
});

test('parsePositions: 칸 단위 표 — 수량×단가로 계산, 합계 줄은 건너뜀', () => {
  const c = load();
  const r = plain(c.parsePositions([['종목명', '보유수량', '평균단가', '현재가', '평가금액(원)'],
    ['삼성전자', 10, '70,000', '75,000', '750,000'], ['합계', '', '', '', '750,000'], ['', '', '', '', '']]));
  assert.deepEqual(r.positions, [{ code: '', name: '삼성전자', qty: 10, cost: 700000, value: 750000, currency: 'KRW' }]);
  assert.deepEqual(r.failed, []);
});

test('parsePositions: 평가금액이 없으면 수량×현재가, 코드·통화 열은 있으면 읽음', () => {
  const c = load();
  const r = plain(c.parsePositions([['종목코드', '종목명', '수량', '매입금액', '현재가', '통화'], ['AAPL', 'Apple', 2, '300,000', '200,000', 'usd']]));
  assert.deepEqual(r.positions[0], { code: 'AAPL', name: 'Apple', qty: 2, cost: 300000, value: 400000, currency: 'USD' });
});

test('parsePositions: 첫 열에 한 줄씩 들어온 CSV(따옴표 안 쉼표)와 탭 구분', () => {
  const c = load();
  const csv = plain(c.parsePositions([['종목명,수량,매입금액,평가금액'], ['"A, Inc",3,"300,000","330,000"'], ['bad,x,y,z']]));
  assert.equal(csv.positions[0].name, 'A, Inc');
  assert.equal(csv.positions[0].value, 330000);
  assert.deepEqual(csv.failed, ['bad x y z']);
  const tab = plain(c.parsePositions([['종목명\t수량\t평균단가\t현재가'], ['TIGER\t5\t10,000\t11,000']]));
  assert.equal(tab.positions[0].value, 55000);
});

test('parsePositions: 머리글을 못 찾으면 error만 돌려준다', () => {
  const c = load();
  const r = plain(c.parsePositions([['foo', 'bar'], ['1', '2']]));
  assert.match(r.error, /머리글/);
  assert.equal(r.positions, undefined);
});

test('parsePositions: 음수 평가(괄호)와 종목명이 빈 줄은 실패로', () => {
  const c = load();
  const r = plain(c.parsePositions([['종목명', '평가금액'], ['환헤지', '(5,000)'], ['', '1,000']]));
  assert.equal(r.positions[0].value, -5000);
  assert.deepEqual(r.failed, ['1,000']);
});

test('replaceAccountRows: 그 계좌만 교체하고 다른 계좌 줄은 그대로, 두 번 해도 쌓이지 않는다', () => {
  const c = load();
  const table = [['a', '1', 'x', 1, 2, 3, 'KRW'], ['b', '2', 'y', 1, 2, 3, 'KRW'], ['', '', '', '', '', '', '']];
  const p = [{ code: '9', name: 'n', qty: 1, cost: 2, value: 3, currency: 'KRW' }];
  const once = plain(c.replaceAccountRows(table, 'a', p));
  assert.deepEqual(once, [['b', '2', 'y', 1, 2, 3, 'KRW'], ['a', '9', 'n', 1, 2, 3, 'KRW']]);
  assert.deepEqual(plain(c.replaceAccountRows(once, 'a', p)), once);
});

test('renameAccountRows: 계좌명만 바꾼다', () => {
  const c = load();
  const out = plain(c.renameAccountRows([['a', '1', 'x', 1, 2, 3, 'KRW'], ['b', '2', 'y', 1, 2, 3, 'KRW']], 'a', 'z'));
  assert.deepEqual(out.map((r) => r[0]), ['z', 'b']);
});

test('validAccountName: 금지 문자·빈 이름·너무 긴 이름은 문장으로, 정상은 빈 문자열', () => {
  const c = load();
  assert.equal(c.validAccountName('신랑 키움'), '');
  for (const bad of ['a/b', 'a[1]', 'a*', 'a?', 'a:b', 'a\\b']) assert.match(c.validAccountName(bad), /사용할 수 없는 문자/, bad);
  assert.match(c.validAccountName(''), /이름/);
  assert.match(c.validAccountName('가'.repeat(91)), /90자/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/positions.test.js`
Expected: FAIL — `ENOENT ... positions_logic.gs` (파일 없음)

- [ ] **Step 3: Write minimal implementation** — `apps-script/positions_logic.gs`

```js
/* 붙여넣은 보유종목 표 해석 (순수 로직, node --test 대상). isBlank는 logic.gs(같은 전역)의 것을 쓴다. */

var POS_ALIASES = {
  name: ['종목명', '종목', '상품명', '종목이름'],
  code: ['종목코드', '코드', '티커', '심볼'],
  qty: ['보유수량', '잔고수량', '수량', '보유량'],
  cost: ['매입금액', '매입가액', '투자원금', '매입원금', '취득금액'],
  unit: ['평균단가', '매입단가', '평단가', '매입가', '평균매입가'],
  value: ['평가금액', '평가액', '평가금'],
  price: ['현재가', '시세'],
  currency: ['통화', '통화코드']
};
var POS_SUMMARY = /합계|총계|소계|^total$/i;

// '1,234원' '+5.2%' '(1,234)' → 숫자. 못 읽으면 NaN.
function posNum(x) {
  if (typeof x === 'number') return x;
  if (x === null || x === undefined) return NaN;
  var s = String(x).trim();
  if (!s || /^[-–—]+$/.test(s)) return NaN;
  var neg = /^\(.*\)$/.test(s);
  s = s.replace(/[()원%,\s+]/g, '');
  if (!/^-?\d+(\.\d+)?$/.test(s)) return NaN;
  return neg ? -Number(s) : Number(s);
}

function posHeadKey(cell) {
  var h = String(isBlank(cell) ? '' : cell).replace(/\([^)]*\)/g, '').replace(/\s+/g, '');
  for (var k in POS_ALIASES) if (POS_ALIASES[k].indexOf(h) !== -1) return k;
  return '';
}

// 쉼표(따옴표 지원)·탭으로 나눈다. 탭이 있으면 탭 우선.
function posSplit(line) {
  if (line.indexOf('\t') !== -1) return line.split('\t');
  var out = [], cur = '', q = false;
  for (var i = 0; i < line.length; i++) {
    var c = line.charAt(i);
    if (c === '"') {
      if (q && line.charAt(i + 1) === '"') { cur += '"'; i++; } else q = !q;
    } else if (c === ',' && !q) { out.push(cur); cur = ''; }
    else cur += c;
  }
  out.push(cur);
  return out;
}

// 칸 단위 표(스프레드시트 붙여넣기) 또는 첫 열에 한 줄씩 들어온 CSV/탭 글을 같은 모양의 칸 표로.
function posRows(cells) {
  var rows = cells.map(function (r) { return r.slice(); });
  var oneCol = rows.every(function (r) { return r.slice(1).every(isBlank); });
  var hasSep = rows.some(function (r) { return typeof r[0] === 'string' && /[\t,]/.test(r[0]); });
  return oneCol && hasSep ? rows.map(function (r) { return isBlank(r[0]) ? [] : posSplit(String(r[0])); }) : rows;
}

// cells: 붙여넣기 칸 값(2차원). 돌려주는 값: {error} 또는 {positions:[{code,name,qty,cost,value,currency}], failed:[줄 글자]}
function parsePositions(cells) {
  var rows = posRows(cells);
  var head = -1, idx = {};
  for (var i = 0; i < Math.min(rows.length, 8) && head < 0; i++) {
    var m = {};
    rows[i].forEach(function (c, j) { var k = posHeadKey(c); if (k && m[k] === undefined) m[k] = j; });
    if (m.name !== undefined && (m.value !== undefined || m.cost !== undefined ||
        (m.qty !== undefined && (m.price !== undefined || m.unit !== undefined)))) {
      head = i; idx = m;
    }
  }
  if (head < 0) return { error: '머리글(종목명·평가금액 등)을 찾지 못했습니다. 표의 첫 줄(머리글)부터 붙여넣어 주세요.' };
  var positions = [], failed = [];
  rows.slice(head + 1).forEach(function (r) {
    var cell = function (k) { return idx[k] === undefined ? '' : r[idx[k]]; };
    var text = r.filter(function (c) { return !isBlank(c); }).join(' ');
    if (!text) return;
    var name = isBlank(cell('name')) ? '' : String(cell('name')).trim();
    if (!name) { failed.push(text); return; }
    if (POS_SUMMARY.test(name)) return;
    var qty = posNum(cell('qty'));
    var value = posNum(cell('value'));
    if (isNaN(value) && !isNaN(qty)) value = qty * posNum(cell('price'));
    var cost = posNum(cell('cost'));
    if (isNaN(cost) && !isNaN(qty)) cost = qty * posNum(cell('unit'));
    if (isNaN(value)) { failed.push(text); return; }
    var cur = isBlank(cell('currency')) ? 'KRW' : String(cell('currency')).trim().toUpperCase();
    positions.push({ code: isBlank(cell('code')) ? '' : String(cell('code')).trim(), name: name,
      qty: isNaN(qty) ? '' : qty, cost: isNaN(cost) ? '' : cost, value: value, currency: cur });
  });
  return { positions: positions, failed: failed };
}

// 증권종목 정규 표(계좌|코드|종목명|수량|매입금액|평가금액|통화)에서 그 계좌 줄을 새 줄로 바꾼다. 다른 계좌 줄은 그대로, 빈 줄은 버린다.
function replaceAccountRows(table, account, positions) {
  var kept = table.filter(function (r) { return !isBlank(r[0]) && r[0] !== account; });
  return kept.concat(positions.map(function (p) { return [account, p.code, p.name, p.qty, p.cost, p.value, p.currency]; }));
}

function renameAccountRows(table, from, to) {
  return table.map(function (r) { return r[0] === from ? [to].concat(r.slice(1)) : r; });
}

// 계좌 이름 → 탭 이름('계좌_' + 이름)이 되므로 시트 탭에 쓸 수 없는 문자와 길이를 막는다. 정상이면 ''.
// 금지 문자는 broker_accounts.py의 입력 검사와 같아야 한다: [ ] * ? : / \
function validAccountName(name) {
  var n = isBlank(name) ? '' : String(name).trim();
  if (!n) return '계좌 이름을 적어 주세요.';
  if (n.length > 90) return '계좌 이름은 90자 이하로 적어 주세요.';
  if (/[\[\]*?:\/\\]/.test(n)) return '계좌 이름에 사용할 수 없는 문자가 있습니다: [ ] * ? : / \\';
  return '';
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/positions.test.js`
Expected: PASS — `# pass 9`, `# fail 0`

- [ ] **Step 5: Commit**

```bash
git add apps-script/positions_logic.gs tests/positions.test.js
git commit -m "feat: 붙여넣은 보유종목 표 해석(parsePositions) 순수 로직

"
```

---

### Task 2: 가짜 시트 확장 + 붙여넣기 반영 글루 (`importPositions`)

**Files:**
- Modify: `tests/fake_sheets.js`
- Create: `apps-script/positions.gs`
- Test: `tests/positions_import.test.js`

**Interfaces:**
- Consumes: Task 1의 `parsePositions`·`replaceAccountRows`, 전역 `todayDate()`·`safeText()`·`isBlank()`
- Produces:
  - `importPositions(ss, checkbox)` — 체크박스를 풀고 `증권종목`의 붙여넣기 칸을 반영
  - `var POS_*`, `ACCT_*` 주소 상수 (Task 5의 Python 테스트가 대조)
  - `FakeSpreadsheet(sheetsByName)` (`getSheetByName`·`insertSheet`), `FakeSheet#setFormulas/setFormula/setNote/setName/getName/hideSheet/showSheet/isSheetHidden`

- [ ] **Step 1: Write the failing test** — `tests/positions_import.test.js`

```js
// importPositions 글루: 붙여넣기 칸 → 정규 종목 표, 계좌 목록의 마지막 붙여넣기 날짜, 결과 메시지.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet, FakeSpreadsheet } = require('./fake_sheets');

function setup() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs', 'positions_logic.gs', 'positions.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  ctx.todayDate = () => new Date(2026, 9, 21);
  const pos = new FakeSheet([[], [], [], [], []]);
  const acct = new FakeSheet([[], [], [], [], ['신랑 키움'], ['신부 삼성']]);
  const ss = new FakeSpreadsheet({ '증권종목': pos, '증권계좌': acct });
  const paste = (account, rows) => {
    pos.set(2, 2, account);
    rows.forEach((r, i) => r.forEach((v, j) => pos.set(6 + i, 1 + j, v)));
    let checkbox = null;
    ctx.importPositions(ss, { setValue(v) { checkbox = v; } });
    return checkbox;
  };
  const table = () => pos.getRange('H6:N1005').getValues().filter((r) => r[0] !== '');
  return { ctx, pos, acct, paste, table, result: () => pos.get(3, 3) };
}

const HEAD = ['종목명', '수량', '매입금액', '평가금액'];

test('importPositions: 종목이 정규 표에 들어가고, 붙여넣기 칸은 비워지고, 마지막 붙여넣기 날짜가 기록된다', () => {
  const t = setup();
  assert.equal(t.paste('신랑 키움', [HEAD, ['삼성전자', 10, '700,000', '750,000'], ['SK하이닉스', 2, '400,000', '380,000']]), false);
  assert.deepEqual(t.table().map((r) => [r[0], r[2], r[5]]), [['신랑 키움', '삼성전자', 750000], ['신랑 키움', 'SK하이닉스', 380000]]);
  assert.equal(t.pos.get(6, 1), '');                                   // 붙여넣기 칸 비움
  assert.equal(t.acct.get(5, 6).getTime(), new Date(2026, 9, 21).getTime());
  assert.match(t.result(), /^✓ 2종목 반영/);
});

test('importPositions: 같은 계좌를 다시 붙여넣으면 교체되고 다른 계좌 줄은 그대로', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  t.paste('신부 삼성', [HEAD, ['B', 1, 200, 210]]);
  t.paste('신랑 키움', [HEAD, ['C', 2, 300, 330]]);
  assert.deepEqual(t.table().map((r) => [r[0], r[2]]), [['신부 삼성', 'B'], ['신랑 키움', 'C']]);
});

test('importPositions: 머리글을 못 찾으면 기존 종목을 그대로 두고 안내만 한다', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110]]);
  t.paste('신랑 키움', [['foo', 'bar'], ['1', '2']]);
  assert.deepEqual(t.table().map((r) => r[2]), ['A']);
  assert.match(t.result(), /^✗ .*머리글/);
  assert.equal(t.pos.get(6, 1), 'foo');                                // 못 읽은 표는 지우지 않는다
});

test('importPositions: 계좌를 안 골랐거나 붙여넣기가 비면 안내만', () => {
  const t = setup();
  t.paste('', [HEAD, ['A', 1, 100, 110]]);
  assert.match(t.result(), /계좌를 먼저/);
  const t2 = setup();
  t2.paste('신랑 키움', []);
  assert.match(t2.result(), /붙여넣어/);
});

test('importPositions: 일부 줄이 실패하면 나머지는 반영하고 실패 줄을 표시한다', () => {
  const t = setup();
  t.paste('신랑 키움', [HEAD, ['A', 1, 100, 110], ['', 1, 5, '??']]);
  assert.equal(t.table().length, 1);
  assert.match(t.result(), /실패 1줄/);
  assert.equal(t.pos.get(6, 6), '인식 실패');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/positions_import.test.js`
Expected: FAIL — `FakeSpreadsheet is not a constructor` (또는 `positions.gs` 없음)

- [ ] **Step 3: Write minimal implementation**

`tests/fake_sheets.js` 수정 — 세 곳:

(1) `getRange(...)`가 돌려주는 객체(`return { getValue: ..., setNumberFormat: ..., ... }`)에 세 줄을 더한다:
```js
      setFormulas: (vals) => vals.forEach((row, i) => row.forEach((v, j) => sh.set(r + i, col + j, v))),
      setFormula: (f) => sh.set(r, col, f),
      setNote: () => {},
```
(2) `class FakeSheet` 안, `getMaxRows() {...}` 아래에 메서드를 더한다:
```js
  getName() { return this.name; }
  setName(n) { if (this.owner) { delete this.owner.sheets[this.name]; this.owner.sheets[n] = this; } this.name = n; return this; }
  hideSheet() { this.hidden = true; return this; }
  showSheet() { this.hidden = false; return this; }
  isSheetHidden() { return !!this.hidden; }
```
(3) 파일 끝의 `module.exports = { FakeSheet };`를 아래로 바꾼다:
```js
class FakeSpreadsheet {
  constructor(sheets) {            // { 이름: FakeSheet }
    this.sheets = sheets;
    Object.keys(sheets).forEach((n) => { sheets[n].name = n; sheets[n].owner = this; });
  }
  getSheetByName(n) { return this.sheets[n] || null; }
  insertSheet(n) { const s = new FakeSheet([[]]); s.name = n; s.owner = this; this.sheets[n] = s; return s; }
}

module.exports = { FakeSheet, FakeSpreadsheet };
```

`apps-script/positions.gs`:

```js
/* 증권 계좌 목록·붙여넣기·계좌 탭 (시트 연결). 순수 로직은 positions_logic.gs. 조회 전용 — 주문 경로 없음. */

var POS_TAB = '증권종목';
var ACCT_TAB = '증권계좌';
var POS_ACCOUNT = 'B2';
var POS_CHECK = 'B3';
var POS_RESULT = 'C3';
var POS_PASTE = 'A6:F205';
var POS_TABLE = 'H6:N1005';
var ACCT_NAMES = 'A5:A14';
var ACCT_PASTED = 'F5:F14';
var ACCOUNT_TAB_PREFIX = '계좌_';

function blankRows_(n, m) {
  var out = [];
  for (var i = 0; i < n; i++) out.push(new Array(m).fill(''));
  return out;
}

// 증권종목 B3 체크: 붙여넣기 칸(A6:F205)을 해석해 고른 계좌(B2)의 종목을 정규 표(H6:N1005)에 교체해 넣는다.
function importPositions(ss, checkbox) {
  checkbox.setValue(false);
  var sh = ss.getSheetByName(POS_TAB);
  var out = sh.getRange(POS_RESULT);
  var account = String(sh.getRange(POS_ACCOUNT).getValue() || '').trim();
  if (!account) { out.setValue('✗ 계좌를 먼저 고르세요 (B2).'); return; }
  var cells = sh.getRange(POS_PASTE).getValues();
  while (cells.length && cells[cells.length - 1].every(isBlank)) cells.pop();
  if (!cells.length) { out.setValue('✗ A6부터 증권사 보유종목 표를 붙여넣어 주세요.'); return; }
  var r = parsePositions(cells);
  if (r.error) { out.setValue('✗ ' + r.error); return; }       // 못 읽으면 기존 종목과 붙여넣은 표를 그대로 둔다
  var rows = replaceAccountRows(sh.getRange(POS_TABLE).getValues(), account, r.positions);
  if (rows.length > 1000) { out.setValue('✗ 종목이 너무 많습니다 (전체 1000줄까지).'); return; }
  sh.getRange(POS_TABLE).setValues(rows.concat(blankRows_(1000 - rows.length, 7)));
  var names = ss.getSheetByName(ACCT_TAB).getRange(ACCT_NAMES).getValues();
  for (var i = 0; i < names.length; i++) {
    if (String(names[i][0]).trim() === account) { ss.getSheetByName(ACCT_TAB).getRange(5 + i, 6).setValue(todayDate()); break; }
  }
  sh.getRange(POS_PASTE).clearContent();
  if (r.failed.length) {
    sh.getRange(6, 1, r.failed.length, 6).setValues(r.failed.map(function (t) { return [safeText(t), '', '', '', '', '인식 실패']; }));
  }
  out.setValue('✓ ' + r.positions.length + '종목 반영' + (r.failed.length ? ' / 실패 ' + r.failed.length + '줄' : ''));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/positions_import.test.js && node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: PASS — 새 5개 통과, 전체 `# fail 0`

- [ ] **Step 5: Commit**

```bash
git add tests/fake_sheets.js apps-script/positions.gs tests/positions_import.test.js
git commit -m "feat: 붙여넣기 반영(importPositions)과 가짜 스프레드시트

"
```

---

### Task 3: 계좌 탭 자동 생성·이름 변경·숨김 + onEdit 라우팅

**Files:**
- Modify: `apps-script/positions.gs`, `apps-script/logic.gs` (`routeEdit`), `apps-script/triggers.gs` (`onEdit`)
- Test: `tests/account_tab.test.js`

**Interfaces:**
- Consumes: Task 1의 `validAccountName`·`renameAccountRows`, Task 2의 `POS_*` 상수·`FakeSpreadsheet`
- Produces:
  - `syncAccountTab(ss, from, to) -> 'created'|'shown'|'renamed'|'hidden'|'exists'|'none'|'invalid'`
  - `buildAccountTab_(sh, name)` — 요약 수식과 종목 표 수식을 쓴다
  - `routeEdit` 새 반환값: `{type:'positions'}` · `{type:'brokerTab', from, to}`

- [ ] **Step 1: Write the failing test** — `tests/account_tab.test.js`

```js
// 증권계좌 A열에 이름을 적으면 '계좌_이름' 탭이 자동으로 만들어지고, 바꾸면 따라 바뀌고, 지우면 숨긴다.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { FakeSheet, FakeSpreadsheet } = require('./fake_sheets');

function setup() {
  const ctx = vm.createContext({ LockService: { getDocumentLock: () => ({ waitLock() {}, releaseLock() {} }) } });
  for (const f of ['logic.gs', 'triggers.gs', 'positions_logic.gs', 'positions.gs']) vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
  const pos = new FakeSheet([[], [], [], [], []]);
  const ss = new FakeSpreadsheet({ '증권종목': pos, '증권계좌': new FakeSheet([[]]) });
  return { ctx, ss, pos, tab: (n) => ss.getSheetByName('계좌_' + n) };
}

test('새 이름 → 계좌 탭 생성(이름 칸·요약·종목 표 수식), 같은 이름을 또 적으면 다시 만들지 않음', () => {
  const t = setup();
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움'), 'created');
  const sh = t.tab('신랑 키움');
  assert.ok(sh);
  assert.equal(sh.get(1, 2), '신랑 키움');
  assert.match(sh.get(3, 2), /^=SUMIFS\(증권종목!\$M\$6:\$M\$1005,증권종목!\$H\$6:\$H\$1005,\$B\$1\)$/);
  assert.match(sh.get(12, 1), /^=IFERROR\(FILTER\(증권종목!\$I\$6:\$N\$1005/);
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움'), 'shown');
  assert.equal(Object.keys(t.ss.sheets).filter((n) => n.startsWith('계좌_')).length, 1);
});

test('이름 바꾸기 → 탭 이름·B1·증권종목의 계좌명이 함께 바뀐다', () => {
  const t = setup();
  t.ctx.syncAccountTab(t.ss, '', '신랑 키움');
  t.pos.getRange('H6:N7').setValues([['신랑 키움', '1', 'A', 1, 2, 3, 'KRW'], ['신부 삼성', '2', 'B', 1, 2, 3, 'KRW']]);
  assert.equal(t.ctx.syncAccountTab(t.ss, '신랑 키움', '신랑 키움증권'), 'renamed');
  assert.ok(!t.tab('신랑 키움') && t.tab('신랑 키움증권'));
  assert.equal(t.tab('신랑 키움증권').get(1, 2), '신랑 키움증권');
  assert.deepEqual([t.pos.get(6, 8), t.pos.get(7, 8)], ['신랑 키움증권', '신부 삼성']);
});

test('이름 지우기 → 탭은 삭제하지 않고 숨긴다, 다시 적으면 보인다', () => {
  const t = setup();
  t.ctx.syncAccountTab(t.ss, '', '신랑 키움');
  assert.equal(t.ctx.syncAccountTab(t.ss, '신랑 키움', ''), 'hidden');
  assert.equal(t.tab('신랑 키움').isSheetHidden(), true);
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '신랑 키움'), 'shown');
  assert.equal(t.tab('신랑 키움').isSheetHidden(), false);
});

test('금지 문자·너무 긴 이름은 탭을 만들지 않는다', () => {
  const t = setup();
  assert.equal(t.ctx.syncAccountTab(t.ss, '', 'a/b'), 'invalid');
  assert.equal(t.ctx.syncAccountTab(t.ss, '', '가'.repeat(91)), 'invalid');
  assert.equal(Object.keys(t.ss.sheets).filter((n) => n.startsWith('계좌_')).length, 0);
});

test('바꾸려는 이름의 탭이 이미 있으면 건드리지 않고 exists', () => {
  const t = setup();
  t.ctx.syncAccountTab(t.ss, '', 'A');
  t.ctx.syncAccountTab(t.ss, '', 'B');
  assert.equal(t.ctx.syncAccountTab(t.ss, 'A', 'B'), 'exists');
  assert.ok(t.tab('A') && t.tab('B'));
});

test('이전 탭이 없는 이름 바꾸기(사용자가 탭을 지운 경우)는 새 탭을 만든다', () => {
  const t = setup();
  assert.equal(t.ctx.syncAccountTab(t.ss, 'X', 'Y'), 'created');
  assert.ok(t.tab('Y'));
});

test('routeEdit: 증권종목 B3 체크는 positions, 증권계좌 A5:A14 편집은 brokerTab(이전·새 이름)', () => {
  const c = setup().ctx;
  const ev = (o) => Object.assign({ sheet: '증권종목', row: 3, col: 2, numRows: 1, numCols: 1, value: 'TRUE' }, o);
  const plain = (x) => JSON.parse(JSON.stringify(x));
  assert.deepEqual(plain(c.routeEdit(ev({}))), { type: 'positions' });
  assert.equal(c.routeEdit(ev({ value: 'FALSE' })), null);
  const acct = (o) => Object.assign({ sheet: '증권계좌', row: 5, col: 1, numRows: 1, numCols: 1, value: '신랑 키움', oldValue: undefined }, o);
  assert.deepEqual(plain(c.routeEdit(acct({}))), { type: 'brokerTab', from: '', to: '신랑 키움' });
  assert.deepEqual(plain(c.routeEdit(acct({ value: undefined, oldValue: '신랑 키움' }))), { type: 'brokerTab', from: '신랑 키움', to: '' });
  assert.equal(c.routeEdit(acct({ row: 15 })), null);       // 목록 밖
  assert.equal(c.routeEdit(acct({ col: 2 })), null);        // 이름 칸이 아님
  assert.equal(c.routeEdit(acct({ value: 'a', oldValue: 'a' })), null);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/account_tab.test.js`
Expected: FAIL — `t.ctx.syncAccountTab is not a function`

- [ ] **Step 3: Write minimal implementation**

`apps-script/positions.gs`에 추가:

```js
// 증권계좌 A5:A14 편집 → 그 계좌의 탭을 만들거나(없으면) 보이게/이름 바꾸기/숨기기. 반환값은 처리 결과(테스트·토스트용).
function syncAccountTab(ss, from, to) {
  var problem = to ? validAccountName(to) : '';
  if (problem) { if (ss.toast) ss.toast(problem, '증권계좌', 8); return 'invalid'; }
  if (!to) {
    var old = from ? ss.getSheetByName(ACCOUNT_TAB_PREFIX + from) : null;
    if (!old) return 'none';
    old.hideSheet();                       // 기록 보존을 위해 삭제하지 않는다
    return 'hidden';
  }
  var target = ss.getSheetByName(ACCOUNT_TAB_PREFIX + to);
  if (!from) {
    if (target) { target.showSheet(); return 'shown'; }
    buildAccountTab_(ss.insertSheet(ACCOUNT_TAB_PREFIX + to), to);
    return 'created';
  }
  var oldTab = ss.getSheetByName(ACCOUNT_TAB_PREFIX + from);
  if (!oldTab) {
    if (target) { target.showSheet(); return 'shown'; }
    buildAccountTab_(ss.insertSheet(ACCOUNT_TAB_PREFIX + to), to);
    return 'created';
  }
  if (target) { if (ss.toast) ss.toast('같은 이름의 계좌 탭이 이미 있습니다.', '증권계좌', 8); return 'exists'; }
  oldTab.setName(ACCOUNT_TAB_PREFIX + to);
  oldTab.getRange('B1').setValue(to);
  var pos = ss.getSheetByName(POS_TAB);
  if (pos) pos.getRange(POS_TABLE).setValues(renameAccountRows(pos.getRange(POS_TABLE).getValues(), from, to));
  return 'renamed';
}

// 계좌 탭: B1 = 계좌 이름(수식이 이 칸을 읽는다), 요약 B2:B9, 종목 표 A11:F(필터), 오른쪽에 종목 비중 원형 그래프.
function buildAccountTab_(sh, name) {
  var T = '증권종목', L = '증권계좌';
  var find = function (col) { return 'IFERROR(INDEX(' + L + '!$' + col + '$5:$' + col + '$14,MATCH($B$1,' + L + '!$A$5:$A$14,0)),"")'; };
  var sum = function (col) { return '=SUMIFS(' + T + '!$' + col + '$6:$' + col + '$1005,' + T + '!$H$6:$H$1005,$B$1)'; };
  sh.getRange('A1:B1').setValues([['계좌', name]]);
  sh.getRange('A2:A9').setValues([['소유자 · 증권사'], ['종목 평가'], ['원금 (매입금액)'], ['예수금'], ['평가금액 (총)'], ['손익 (종목 기준)'], ['수익률'], ['마지막 붙여넣기']]);
  sh.getRange('B2:B9').setFormulas([
    ['=' + find('B') + '&" · "&' + find('C')], [sum('M')], [sum('L')], ['=N(' + find('E') + ')'], ['=B3+B5'],
    ['=B3-B4'], ['=IF(B4>0,B7/B4,"")'], ['=' + find('F')]]);
  sh.getRange('A11:F11').setValues([['코드', '종목명', '수량', '매입금액', '평가금액', '통화']]);
  sh.getRange('A12').setFormula('=IFERROR(FILTER(' + T + '!$I$6:$N$1005,' + T + '!$H$6:$H$1005=$B$1),"")');
  sh.getRange('B3:B7').setNumberFormat('#,##0');
  sh.getRange('B9').setNumberFormat('yyyy-mm-dd');
  sh.getRange('B8').setNumberFormat('0.0%');
  sh.getRange('D12:E61').setNumberFormat('#,##0');
  if (typeof sh.newChart === 'function' && typeof Charts !== 'undefined') {
    sh.insertChart(sh.newChart().setChartType(Charts.ChartType.PIE).addRange(sh.getRange('B12:B61')).addRange(sh.getRange('E12:E61'))
      .setPosition(2, 8, 0, 0).setOption('title', '종목별 비중').build());
  }
}
```

`apps-script/logic.gs` — `routeEdit`의 `if (ev.sheet === '빠른입력' ...` 블록 바로 앞에 추가:

```js
  if (ev.sheet === '증권종목' && ev.row === 3 && ev.col === 2) return ev.value === 'TRUE' ? { type: 'positions' } : null;  // 붙여넣기 반영
  if (ev.sheet === '증권계좌' && ev.col === 1 && ev.row >= 5 && ev.row <= 14) {  // 계좌 이름 → 계좌 탭 생성·이름 변경·숨김
    var accFrom = isBlank(ev.oldValue) ? '' : String(ev.oldValue).trim();
    var accTo = isBlank(ev.value) ? '' : String(ev.value).trim();
    return accFrom === accTo ? null : { type: 'brokerTab', from: accFrom, to: accTo };
  }
```

`apps-script/triggers.gs` — `onEdit` 안 `if (action.type === 'year') ...` 줄 아래에 추가:

```js
  if (action.type === 'positions') importPositions(e.source, range);
  if (action.type === 'brokerTab') syncAccountTab(e.source, action.from, action.to);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)|^not ok"`
Expected: `# fail 0` (기존 134 + 새 테스트 모두 통과)

- [ ] **Step 5: Commit**

```bash
git add apps-script/positions.gs apps-script/logic.gs apps-script/triggers.gs tests/account_tab.test.js
git commit -m "feat: 증권계좌 이름으로 계좌 탭 자동 생성·이름 변경·숨김, onEdit 라우팅

"
```

---

### Task 4: `증권계좌`·`증권종목` 탭 생성 모듈 (Python)

**Files:**
- Modify: `layout.py`, `sigol_tabs.py`, `styling.py`, `deploy_script.py`
- Create: `broker_accounts.py`, `broker_positions.py`
- Test: `tests/test_broker_tabs.py` (+ 기존 탭 수를 세는 테스트 기대값 갱신)

**Interfaces:**
- Consumes: 기존 `sigol_tabs` 모듈 인터페이스 (`S TITLE SECTIONS HEADS TOTALS SUBTOTALS BODIES INPUTS RUNS WIDTHS HIDDEN`, `values() formats() chart_requests()`), `layout.USERS`·`a1_to_grid`·`number_format`·`v`, Task 2·3의 `POS_*`·`ACCT_*` 상수
- Produces: `layout.BROKER_ACCTS == "증권계좌"`(sheetId 2800), `layout.BROKER_POS == "증권종목"`(sheetId 2810), 주소 상수 `layout.POS_*`·`ACCT_*`, 두 모듈이 `sigol_tabs.MODULES`에 등록

- [ ] **Step 1: Write the failing test** — `tests/test_broker_tabs.py`

```python
"""증권계좌·증권종목 탭 (다증권사 A단계). 주소·문구는 Apps Script(positions.gs)와 같아야 한다."""
import re
from pathlib import Path

import broker_accounts
import broker_positions
import layout
import migrate_couple as mc
import sigol_tabs
import styling

GS = (Path(__file__).parent.parent / "apps-script" / "positions.gs").read_text(encoding="utf-8")
ALL = {t for t, *_ in layout.SHEETS}


def _gs(name):
    return re.search(rf"var {name} = '([^']*)';", GS).group(1)


def _state(titles=ALL):
    return mc.State(titles=set(titles), settings_cols=13, asset_cols=12, networth_charts=1, settings=[], budgets_empty=False,
                    invest_charts=2, dash_rows=200, dash_base=46)


def test_addresses_match_the_script():
    for py, gs in [("POS_ACCOUNT", "POS_ACCOUNT"), ("POS_CHECK", "POS_CHECK"), ("POS_RESULT", "POS_RESULT"), ("POS_PASTE", "POS_PASTE"),
                   ("POS_TABLE", "POS_TABLE"), ("ACCT_NAMES", "ACCT_NAMES"), ("ACCT_PASTED", "ACCT_PASTED"),
                   ("ACCOUNT_TAB_PREFIX", "ACCOUNT_TAB_PREFIX")]:
        assert getattr(layout, py) == _gs(gs), py
    assert (layout.BROKER_ACCTS, layout.BROKER_POS) == (_gs("ACCT_TAB"), _gs("POS_TAB")) == ("증권계좌", "증권종목")


def test_tabs_follow_invest_and_have_input_color():
    titles = [t for t, *_ in layout.SHEETS]
    i = titles.index(layout.INVEST)
    assert titles[i + 1:i + 3] == [layout.BROKER_ACCTS, layout.BROKER_POS]
    assert (layout.SHEET_ID[layout.BROKER_ACCTS], layout.SHEET_ID[layout.BROKER_POS]) == (2800, 2810)
    assert broker_accounts in sigol_tabs.MODULES and broker_positions in sigol_tabs.MODULES
    assert styling.TAB_COLORS[layout.BROKER_ACCTS] == styling.INPUT_TAB == styling.TAB_COLORS[layout.BROKER_POS]


def test_account_list_headers_input_cells_and_status_formula():
    vals = {e["range"]: e["values"] for e in broker_accounts.values()}
    assert vals["증권계좌!A4:G4"] == [["이름", "소유자", "증권사", "방식", "예수금", "마지막 붙여넣기", "상태"]]
    assert broker_accounts.INPUTS == ["증권계좌!A5:E14"]
    assert "증권계좌!F5" not in vals and not any(k.startswith("증권계좌!A5") for k in vals)   # 입력·스크립트 칸은 값으로 쓰지 않는다
    assert "붙여넣기 전" in vals["증권계좌!G5"][0][0] and "오래됨" in vals["증권계좌!G5"][0][0]


def test_name_validation_rejects_tab_forbidden_characters_and_duplicates():
    rule = next(r["setDataValidation"]["rule"] for r in broker_accounts.formats()
                if "setDataValidation" in r and r["setDataValidation"]["range"] == layout.a1_to_grid("증권계좌!A5:A14"))
    formula = rule["condition"]["values"][0]["userEnteredValue"]
    assert rule["strict"] is True and rule["condition"]["type"] == "CUSTOM_FORMULA"
    assert "COUNTIF($A$5:$A$14,A5)=1" in formula and "LEN(A5)<=90" in formula
    assert all(ch in formula for ch in r"\[\]*?:/\\")           # 스크립트 validAccountName과 같은 금지 문자


def test_positions_tab_layout_matches_script_cells():
    vals = {e["range"]: e["values"] for e in broker_positions.values()}
    assert vals["증권종목!H5:N5"] == [["계좌", "코드", "종목명", "수량", "매입금액", "평가금액", "통화"]]
    for written in ("증권종목!B2", "증권종목!B3", "증권종목!C3"):
        assert written not in vals                                   # 계좌 선택·체크·결과는 사용자/스크립트 칸
    assert broker_positions.INPUTS == ["증권종목!B2:B3", "증권종목!A6:F205"]
    rules = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]
             for r in broker_positions.formats() if "setDataValidation" in r}
    assert rules[tuple(sorted(layout.a1_to_grid("증권종목!B3").items()))]["condition"]["type"] == "BOOLEAN"
    pick = rules[tuple(sorted(layout.a1_to_grid("증권종목!B2").items()))]
    assert pick["condition"]["type"] == "ONE_OF_RANGE" and pick["condition"]["values"][0]["userEnteredValue"] == "=증권계좌!$A$5:$A$14"


def test_live_migration_adds_both_tabs_once():
    structure, values, _v = mc.plan(_state(ALL - {layout.BROKER_ACCTS, layout.BROKER_POS}))
    added = {r["addSheet"]["properties"]["title"] for r in structure if "addSheet" in r}
    assert {layout.BROKER_ACCTS, layout.BROKER_POS} <= added
    assert {"증권계좌!A4:G4", "증권종목!H5:N5"} <= {e["range"] for e in values}
    again = mc.plan(_state())[0]
    assert not {layout.BROKER_ACCTS, layout.BROKER_POS} & {r["addSheet"]["properties"]["title"] for r in again if "addSheet" in r}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_broker_tabs.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'broker_accounts'`

- [ ] **Step 3: Write minimal implementation**

`layout.py` — 상수(예: `KIS_HOLD = ...` 줄 근처)와 `SHEETS` 두 줄:

```python
# 다증권사(A단계): 계좌 목록·붙여넣기 — 주소는 apps-script/positions.gs와 같아야 한다 (tests/test_broker_tabs.py가 대조)
BROKER_ACCTS, BROKER_POS = "증권계좌", "증권종목"
POS_ACCOUNT, POS_CHECK, POS_RESULT = "B2", "B3", "C3"
POS_PASTE, POS_TABLE = "A6:F205", "H6:N1005"
ACCT_NAMES, ACCT_PASTED = "A5:A14", "F5:F14"
ACCOUNT_TAB_PREFIX = "계좌_"
```
```python
    (INVEST, 1900, 100, 10, False),
    (BROKER_ACCTS, 2800, 40, 9, False),
    (BROKER_POS, 2810, 1010, 14, False),
```

`broker_accounts.py`:

```python
"""[증권계좌] 탭: 증권사와 상관없이 계좌를 적는 목록 (다증권사 A단계).

이름을 적으면 스크립트(positions.gs syncAccountTab)가 '계좌_이름' 탭을 자동으로 만든다. 종목은 [증권종목]에 붙여넣는다.
F(마지막 붙여넣기)는 스크립트가 쓰는 칸이라 값으로 쓰지 않고, G(상태)는 수식이다.
"""
from layout import ACCT_NAMES, BROKER_ACCTS as S, USERS, a1_to_grid, number_format, v

TITLE = f"{S}!A1"
HEAD = 4
FIRST, LAST = 5, 14
HEADERS = ["이름", "소유자", "증권사", "방식", "예수금", "마지막 붙여넣기", "상태"]

SECTIONS: list = []
HEADS = [f"{S}!A{HEAD}:G{HEAD}"]
TOTALS: list = []
SUBTOTALS: list = []
BODIES = [f"{S}!A{FIRST}:G{LAST}"]
INPUTS = [f"{S}!A{FIRST}:E{LAST}"]
RUNS = [("A", FIRST, LAST, "LCLCRCC")]
WIDTHS = [180, 90, 110, 90, 110, 130, 110]
HIDDEN: list = []

# 탭 이름이 되므로 금지 문자 [ ] * ? : / \ 와 중복·90자 초과를 입력 단계에서 막는다 (apps-script validAccountName과 같은 규칙)
NAME_RULE = (f'=OR(A{FIRST}="",AND(COUNTIF($A${FIRST}:$A${LAST},A{FIRST})=1,LEN(A{FIRST})<=90,'
             f'NOT(REGEXMATCH(A{FIRST},"[\\[\\]*?:/\\\\]"))))')


def values() -> list[dict]:
    status = (f'=ARRAYFORMULA(IF(A{FIRST}:A{LAST}="","",IF(F{FIRST}:F{LAST}="","붙여넣기 전",'
              f'IF(TODAY()-F{FIRST}:F{LAST}>14,"오래됨","정상"))))')
    return [v(TITLE, [["증권 계좌"]]),
            v(f"{S}!A2", [["증권사 이름과 상관없이 계좌를 적으세요. 이름을 적으면 '계좌_이름' 탭이 자동으로 만들어집니다. 종목은 [증권종목]에 붙여넣으세요."]]),
            v(f"{S}!A{HEAD}:G{HEAD}", [HEADERS]),
            v(f"{S}!G{FIRST}", [[status]]),
            v(f"{S}!A{LAST + 2}", [["방식은 지금 '붙여넣기'만 쓸 수 있습니다. 예수금은 증권사 앱의 현금(예수금)을 직접 적으세요."]])]


def _rule(a1: str, ctype: str, *values: str, strict: bool = False) -> dict:
    cond = {"type": ctype, **({"values": [{"userEnteredValue": x} for x in values]} if values else {})}
    return {"setDataValidation": {"range": a1_to_grid(f"{S}!{a1}"), "rule": {"condition": cond, "strict": strict, "showCustomUi": True}}}


def formats() -> list[dict]:
    return [number_format(f"{S}!E{FIRST}:E{LAST}", "NUMBER", "#,##0"), number_format(f"{S}!F{FIRST}:F{LAST}", "DATE", "yyyy-mm-dd"),
            _rule(ACCT_NAMES, "CUSTOM_FORMULA", NAME_RULE, strict=True),
            _rule(f"B{FIRST}:B{LAST}", "ONE_OF_RANGE", USERS), _rule(f"D{FIRST}:D{LAST}", "ONE_OF_LIST", "붙여넣기", strict=True),
            _rule(f"E{FIRST}:E{LAST}", "NUMBER_GREATER_THAN_EQ", "0")]


def chart_requests() -> list[dict]:
    return []
```

`broker_positions.py`:

```python
"""[증권종목] 탭: 증권사 앱의 보유종목 표를 붙여넣어 계좌별 종목을 반영 (다증권사 A단계).

B2 계좌 선택, B3 체크(반영), C3 결과(스크립트), A6:F205 붙여넣기 칸, H5:N 정규 종목 표(스크립트가 씀).
사용자 칸과 스크립트가 쓰는 칸은 values()로 쓰지 않는다.
"""
from layout import ACCT_NAMES, BROKER_POS as S, POS_PASTE, a1_to_grid, number_format, v

TITLE = f"{S}!A1"
HEADERS = ["계좌", "코드", "종목명", "수량", "매입금액", "평가금액", "통화"]

SECTIONS = [f"{S}!H4"]
HEADS = [f"{S}!H5:N5"]
TOTALS: list = []
SUBTOTALS: list = []
BODIES = [f"{S}!A2:B3", f"{S}!H6:N205"]
INPUTS = [f"{S}!B2:B3", f"{S}!{POS_PASTE}"]
RUNS = [("A", 2, 3, "LC"), ("H", 6, 205, "LLLRRRC")]
WIDTHS = [190, 270, 110, 110, 110, 110, 20, 140, 90, 200, 80, 120, 120, 60]
HIDDEN: list = []


def values() -> list[dict]:
    return [v(TITLE, [["증권 종목 붙여넣기"]]),
            v(f"{S}!A2:A3", [["계좌"], ["반영 (체크)"]]),
            v(f"{S}!A5", [["↓ 아래 A6부터 증권사 앱·홈페이지의 보유종목 표를 머리글부터 붙여넣고, 위 B3을 체크하세요."]]),
            v(f"{S}!H4", [["반영된 종목 (자동)"]]),
            v(f"{S}!H5:N5", [HEADERS])]


def _rule(a1: str, ctype: str, *values: str) -> dict:
    cond = {"type": ctype, **({"values": [{"userEnteredValue": x} for x in values]} if values else {})}
    return {"setDataValidation": {"range": a1_to_grid(f"{S}!{a1}"), "rule": {"condition": cond, "strict": False, "showCustomUi": True}}}


def formats() -> list[dict]:
    return [number_format(f"{S}!K6:K1005", "NUMBER", "#,##0.####"), number_format(f"{S}!L6:M1005", "NUMBER", "#,##0"),
            _rule("B2", "ONE_OF_RANGE", f"=증권계좌!$A$5:$A$14"), _rule("B3", "BOOLEAN")]


def chart_requests() -> list[dict]:
    return []
```

`sigol_tabs.py` — import 추가와 `MODULES`:

```python
import broker_accounts
import broker_positions
...
MODULES = [checklist, quick_entry, fixed_costs, cards, stock_sectors, savings, broker_accounts, broker_positions]
```

`styling.py` — `TAB_COLORS`에 `BROKER_ACCTS: INPUT_TAB, BROKER_POS: INPUT_TAB` 추가(+ `from layout import ... BROKER_ACCTS, BROKER_POS`).

`deploy_script.py` — `SOURCES = [..., "invest_logic", "positions_logic", "positions"]`.

- [ ] **Step 4: Run test to verify it passes, then the whole suite and fix count-based expectations**

Run: `python3 -m pytest -q tests/test_broker_tabs.py` → PASS (6 passed)
Run: `python3 -m pytest -q 2>&1 | tail -15`
Expected: 이전에 통과하던 테스트 중 **탭 수·탭 순서·`SHEETS` 길이·deploy SOURCES를 세는 것**이 실패할 수 있다. 실패한 각각을 읽고 기대값에 새 두 탭/두 소스만 더한다 (동작 변경 없음). 예: `tests/test_deploy.py`의 소스 목록, 탭 개수를 세는 `test_layout.py`·`test_sigol_sheets.py`. 그 외 실패는 원인을 찾아 고친다 (기대값을 느슨하게 바꾸지 않는다).
Final: `python3 -m pytest -q` → `# failed 0`

- [ ] **Step 5: Commit**

```bash
git add layout.py broker_accounts.py broker_positions.py sigol_tabs.py styling.py deploy_script.py tests/test_broker_tabs.py tests/test_deploy.py
git commit -m "feat: 증권계좌·증권종목 탭 추가(다증권사 A단계)

"
```
(다른 테스트 파일의 기대값을 고쳤다면 그 경로도 `git add`에 지정한다.)

---

### Task 5: 사용법·안내 문서

**Files:**
- Modify: `guide.py`, `README.md`, `docs/USAGE.md`
- Test: `tests/test_broker_tabs.py` (추가), 기존 `tests/test_styling.py::test_guide_covers_every_visible_tab_and_faq`

**Interfaces:**
- Consumes: `guide.CONTENT`, `guide.GUIDE_ROWS`
- Produces: 사용법 탭 `[증권계좌]`·`[증권종목]` 행

- [ ] **Step 1: Write the failing test** — `tests/test_broker_tabs.py`에 추가

```python
def test_guide_explains_paste_flow_and_auto_tab():
    import guide
    rows = {a: b for _k, a, b in guide.CONTENT}
    assert "계좌_" in rows["[증권계좌]"] and "자동" in rows["[증권계좌]"]
    assert "머리글" in rows["[증권종목]"] and "B3" in rows["[증권종목]"] and "교체" in rows["[증권종목]"]
    tab_map = " ".join(b for k, a, b in guide.CONTENT if a == "투자")
    assert "[증권계좌]" in tab_map
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_broker_tabs.py::test_guide_explains_paste_flow_and_auto_tab`
Expected: FAIL — `KeyError: '[증권계좌]'`

- [ ] **Step 3: Write minimal implementation**

`guide.py` — `"투자"` 탭 지도 행을 `("row", "투자", "[투자] 부부 증권 계좌 합산 · [증권계좌] · [증권종목] · [주식_신랑] · [주식_신부]")`로 바꾸고, `[주식_신부]` 행 근처(주식 구역)에 두 행을 추가:

```python
    ("row", "[증권계좌]", "메리츠·한투 말고 다른 증권사도 쓸 수 있어요. 계좌 이름·소유자·증권사를 적고 방식은 '붙여넣기'를 고르세요. 이름을 적으면 '계좌_이름' 탭이 자동으로 만들어지고, 이름을 바꾸면 탭 이름도 바뀌며, 이름을 지우면 탭이 숨겨집니다(삭제하지 않아요). 예수금은 증권사 앱의 현금을 직접 적습니다."),
    ("row", "[증권종목]", "B2에서 계좌를 고르고, 증권사 앱·홈페이지의 보유종목 표를 머리글(종목명·수량·평가금액 등)부터 A6에 붙여넣은 뒤 B3을 체크하세요. 그 계좌의 종목이 통째로 교체됩니다. 엑셀·표 복사와 CSV 글 모두 읽고, 못 읽은 줄은 '인식 실패'로 남습니다. 머리글을 못 찾으면 기존 종목은 그대로 두고 안내만 합니다. 금액은 원화 기준으로 붙여넣으세요."),
```

`README.md` 탭 지도 표의 `투자` 행에 `· 증권계좌 · 증권종목` 추가, `docs/USAGE.md` 5절 '증권 연동' 아래에 소제목 `### 다른 증권사 (붙여넣기)`를 추가:

```markdown
### 다른 증권사 (붙여넣기)

API 키 없이 어느 증권사든 쓸 수 있습니다.

1. `증권계좌`에 계좌 이름·소유자·증권사를 적습니다 → `계좌_이름` 탭이 자동으로 생깁니다.
2. 증권사 앱·홈페이지의 보유종목 표를 복사해 `증권종목` A6에 **머리글부터** 붙여넣습니다.
3. `증권종목` B2에서 계좌를 고르고 B3을 체크합니다. 결과는 C3에 나옵니다.

| 항목 | 설명 |
|---|---|
| 읽는 머리글 | 종목명, 종목코드/티커, 수량, 매입금액(또는 평균단가), 평가금액(또는 현재가), 통화 |
| 숫자 표기 | 쉼표·원·%·+ 와 괄호 음수 `(1,234)` 허용 |
| 합계 줄 | `합계`·`총계` 줄은 건너뜀 |
| 다시 붙여넣기 | 그 계좌의 종목이 교체됩니다 (쌓이지 않음) |
| 못 읽은 줄 | `인식 실패`로 A열에 남고 나머지는 반영 |
| 오래된 값 | 마지막 붙여넣기가 14일 넘으면 상태가 `오래됨` |
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q 2>&1 | tail -3`
Expected: 전부 통과 (`test_guide_covers_every_visible_tab_and_faq`가 `[증권계좌]`·`[증권종목]`을 요구하므로 같이 통과)

- [ ] **Step 5: Commit**

```bash
git add guide.py README.md docs/USAGE.md tests/test_broker_tabs.py
git commit -m "docs: 증권계좌·증권종목 사용법

"
```

---

### Task 6: 배포와 운영 시트 적용·검증

**Files:** 코드 변경 없음 (필요하면 검증 중 발견한 버그만 TDD로 고친다)

**Interfaces:**
- Consumes: Task 1~5 전부
- Produces: 운영 시트에 두 탭 추가, 배포된 Apps Script

- [ ] **Step 1: 전체 테스트**

Run: `python3 -m pytest -q 2>&1 | tail -1; node --test tests/*.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: pytest 전부 통과, node `# fail 0`

- [ ] **Step 2: 백업 사본**

시트 전체 사본을 만든다 (`migrate_couple.py`의 기존 백업 함수/관례와 같은 방식, 이름 `우리집 가계부 백업 (2026-10-21 증권계좌 탭 전)`):

Run: `python3 - <<'EOF'` 로 Drive `files().copy`를 호출해 사본 id를 출력한다 (`split_names.py` 98~100행과 같은 호출).
Expected: 사본 id 출력

- [ ] **Step 3: 배포와 적용**

Run: `python3 deploy_script.py && python3 migrate_couple.py`
Expected: `업로드 완료`, `적용: 구조 N개, 값 M개 범위, ...`. 그 뒤 약 60초 기다린 다음(읽기 쿼터) 아래 확인.

- [ ] **Step 4: 읽기 전용 검증**

Run: 기존 확인 스크립트(`post2.py`)와 아래 읽기를 실행.
Expected:
- 탭 목록에 `증권계좌`·`증권종목`이 `투자` 뒤에 있다.
- `증권계좌!A4:G4`, `증권종목!H5:N5`, `증권종목!A5`가 기대 문구.
- 오류 칸 0개, 1650px 넘는 탭 없음.
- 기존 `투자`·`투자기록` 값이 적용 전과 같다 (이 단계는 건드리지 않음).

- [ ] **Step 5: 사용자 실사용 확인 요청 (스크립트 경로는 이 환경에서 실행 불가)**

사용자에게 안내한다: ① `증권계좌` A5에 `테스트 계좌`를 적으면 `계좌_테스트 계좌` 탭이 생기는지, ② `증권종목`에서 그 계좌를 고르고 아래 샘플을 A6에 붙여넣어 B3 체크하면 H6부터 종목이 들어가는지.
```
종목명	수량	매입금액	평가금액
삼성전자	10	700,000	750,000
```
③ 확인 뒤 `증권계좌` A5를 지우면 탭이 숨겨지는지(테스트 데이터는 H열 표에서 해당 줄을 직접 지워도 됨).

- [ ] **Step 6: 커밋/푸시는 사용자가 요청할 때만**

브랜치 `feature/multi-broker`에 계획·구현 커밋이 남아 있는 상태로 보고한다. 병합·push는 요청 시.

---

## 다음 단계 (이 계획 밖 — A단계가 운영에서 확인된 뒤 별도 계획)

- **B1** `투자` 탭 계좌 행을 목록 길이만큼 늘리고 소유자별 합계를 목록에서 계산, `증권종목`을 읽는 원금·손익.
- **B2** `투자기록`을 `날짜|계좌|평가|원금` 형식으로 변환(백업 → `투자기록_옛` 보존 → 합계 대조 → 롤백 경로).
- **B3** 어댑터 형식(`x_fetch`)으로 메리츠·한투 감싸기, 기존 4계좌를 `증권계좌` 1~4행으로 이전, `주식투자` 소스를 `증권종목`으로.

## Self-Review

1. **Spec coverage (A단계 범위)**: §2 `증권계좌`·`증권종목`·붙여넣기 → Task 1·2·4. §5 파서(헤더 이름, 탭/CSV, 수량×단가, 숫자 표기, 실패 줄, 헤더 없으면 변경 없음, 결과 한 줄, 칸 비우기) → Task 1·2. §6 계좌 탭 자동 생성(생성·이름 변경·지우면 숨김·금지 문자·중복) → Task 3·4(입력 검증). §3.1 열 구성(이름·소유자·증권사·방식·예수금·마지막 붙여넣기·상태) → Task 4. §9 테스트 전략 일부 → 각 Task. **B단계로 미룬 항목**(§3.3, §4, §7, §8, `투자`/`투자기록` 자동 포함)은 위 "다음 단계"에 명시했다. 사용자의 "투자기록 자동 포함"은 B2의 산출물이다.
2. **Placeholder scan**: Task 4 Step 4의 "기대값 갱신"은 실패한 테스트를 열어 두 탭/두 소스만 더하는 구체적 지시이며 코드 변경이 아니다. Task 6 Step 2의 백업 호출은 기존 `split_names.py` 98~100행 패턴을 가리킨다. 그 외 TBD 없음.
3. **Type consistency**: `parsePositions` 반환 `{positions, failed}`/`{error}` ↔ `importPositions` 사용 일치. 정규 표 행 `[계좌,코드,종목명,수량,매입금액,평가금액,통화]` = `replaceAccountRows`/`renameAccountRows`/`H:N` 열 순서/`buildAccountTab_`의 `I:N` FILTER 열(코드·종목명·수량·매입금액·평가금액·통화)과 일치. 주소 상수는 `positions.gs` ↔ `layout.py` 동일 값을 Task 4 테스트가 대조. `routeEdit` 반환 `{type:'brokerTab', from, to}` ↔ `syncAccountTab(ss, from, to)` 일치.
4. **Review Focus 매핑**: 1 → Task 1(`error`만)·Task 2(`못 찾으면 기존 종목 유지`), 2 → Task 1 `replaceAccountRows`·Task 2, 3 → Task 1 테스트들, 4 → Task 1 `validAccountName`·Task 3 `invalid`·Task 4 입력 검사, 5 → Task 3.
