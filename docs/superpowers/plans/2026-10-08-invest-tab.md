# 투자 탭 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 부부 주식 계좌 4개(메리츠 2, 한투 ISA 2)의 평가금액·투자원금을 [투자] 탭 하나에서 합산해 보고, 매일 기록해 월별·최근 30일 추이를 그린다.

**Architecture:** 판단 로직은 순수 함수 파일(`kis_logic.gs`, `invest_logic.gs`, `meritz_logic.gs`의 `principalOf`)에 두고 node로 시험한다. 연결부(`kis.gs`, `meritz.gs`, `triggers.gs`)가 각자 권한으로 자기 계좌를 조회해 숨김 원본 탭에 쓰고, 소유자의 06시 일일 작업이 [투자] 탭 최종 값을 `투자기록`에 하루 한 줄 쓴다. 시트 쪽은 `invest.py`가 수식·서식·차트 요청을 만들고 새 시트는 `build_budget.py`, 운영 시트는 `migrate_couple.py`가 쓴다.

**Tech Stack:** Python 3.12, google-api-python-client, pytest / Google Apps Script V8 / Node 22 (`node --test`)

**Spec:** `docs/superpowers/specs/2026-10-08-invest-tab-design.md`

## Global Constraints

- 작업 폴더 `/mnt/d/budget book`, 브랜치 `feature/budget-sheet`. 모든 명령은 `cd "/mnt/d/budget book" && ...`.
- 커밋 메시지 끝: 빈 줄 + `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- 새 탭: `투자`(sheetId 1900, 보임, 100행×10열), `한투원본`(1950, 숨김, 3행×7열), `투자기록`(2000, 숨김, 1000행×12열).
- `주식_신랑`는 숨김 목록(`layout.TUCKED`)으로 옮긴다. 보이는 탭은 11개: 사용법·내역·대시보드·부부·자산기록·투자·즐겨찾기·반복·문자입력·자산·설정.
- [투자] 탭 계좌 행: 7 신랑 메리츠, 8 신랑 ISA(한투), 9 신랑 합계, 10 신부 메리츠, 11 신부 ISA(한투), 12 신부 합계. 직접입력 칸 H(평가)·I(원금).
- `한투원본`: 1행 머리글, 2행 신랑(슬롯 0), 3행 신부(슬롯 1). 열 A 사람 | B 상태 | C 코드 | D 메시지 | E 마지막 성공 | F 평가금액 | G 원금.
- `투자기록` 열: A 날짜 | B·C 신랑 메리츠 평가·원금 | D·E 신랑 ISA | F·G 신부 메리츠 | H·I 신부 ISA | J 합계 평가 | K 합계 원금 | L 빠진 계좌 수.
- 메리츠 원금(추정)은 `메리츠원본`/`메리츠원본2`의 H9 (G9 머리글 `원금(추정)`).
- [자산] G열 연동 값(정확히): `메리츠_신랑`, `한투ISA_신랑`, `메리츠_신부`, `한투ISA_신부` → [투자] B7·B8·B10·B11, 시각 F7·F8·F10·F11.
- 한투: 토큰 `POST https://openapi.koreainvestment.com:9443/oauth2/tokenP`, 잔고 `GET /uapi/domestic-stock/v1/trading/inquire-balance`, tr_id `TTTC8434R`, 헤더 `custtype: P`. 조회 전용 — 주문 경로(`order`) 금지.
- 키·계좌번호·토큰은 `PropertiesService.getUserProperties()`에만. 시트·로그·오류 메시지·git·대화에 쓰지 않는다.
- 연결부 함수는 예외를 밖으로 던지지 않는다(구글 실패 메일 방지).
- 운영 시트(`.spreadsheet_id`)의 입력 데이터(내역·반복·즐겨찾기·문자입력·자산 A~D·F·I열·설정)는 쓰지 않는다. 시험은 임시 시트에서만.
- 파일 800줄, 함수 50줄 이하. 사용자 보고는 한국어.

## Review Focus

1. **계좌 하나가 키도 직접입력도 없음** → 합계에서 빠지고 상태 '키없음', 06시 기록은 그 칸 빈칸·`빠진 계좌 수` +1 (Task 2 `investLogRow` 시험, Task 5 통합 시험의 신랑 메리츠 외 빈 계좌).
2. **06시 작업이 같은 날 두 번 돎** → 같은 날짜 줄 덮어쓰기, 줄 수 그대로 (Task 2 `dateRowIndex` 시험).
3. **직접입력 평가만 적고 원금은 비움** → 원금·손익 빈칸, 합계 원금에서 그 계좌 제외 (Task 4 수식 시험, Task 5 통합 시험).
4. **한투 토큰 만료 응답(EGW00123)** → 한 번만 재발급 후 재조회, 계속 실패면 상태 '오류'이고 예외 없음 (Task 1 `parseKisBalance` 'expired' 판정, Task 3 `refreshKis_` 코드 경로 시험).
5. **계좌번호 입력 형식**(`12345678-01`, `1234567801`, 공백 섞임, 9자리, 빈 값) → 앞의 셋은 정규화, 나머지는 거절 (Task 1 `splitAccount` 시험).
6. **투자기록이 비었거나 한 달치뿐** → 전일·전월말 대비와 월별 표가 오류 대신 빈칸 (Task 4 수식 시험에 IFERROR 확인, Task 5 통합 시험).

---

### Task 1: 한투 순수 로직 — 계좌번호·토큰·잔고 요청·응답 해석

**Files:**
- Create: `apps-script/kis_logic.gs`
- Create: `tests/kis.test.js`

**Interfaces:**
- Consumes (같은 전역, `meritz_logic.gs`): `toNum(x)`, `num(obj, key, optional)`
- Produces: `KIS_BASE`, `KIS_BALANCE_PATH`, `KIS_RAW_ROW=[2,3]`, `splitAccount(s)->{cano,prdt}|null`, `buildKisToken(key, secret)->{url,options}`, `parseKisToken(text, nowMs)->{token,expiresAt}|{error}`, `buildKisBalance(token, key, secret, acct)->{url,options}`, `parseKisBalance(text)->{kind:'ok'|'throttled'|'expired'|'error', code, msg, value?, principal?}`

- [ ] **Step 1: Write the failing test** — `tests/kis.test.js`

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({ encodeURIComponent });
for (const f of ['meritz_logic.gs', 'kis_logic.gs']) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
}
const plain = (x) => JSON.parse(JSON.stringify(x));

test('splitAccount: 8-2 형식만, 하이픈·공백 허용', () => {
  assert.deepEqual(plain(ctx.splitAccount('12345678-01')), { cano: '12345678', prdt: '01' });
  assert.deepEqual(plain(ctx.splitAccount('1234567801')), { cano: '12345678', prdt: '01' });
  assert.deepEqual(plain(ctx.splitAccount(' 12345678 - 01 ')), { cano: '12345678', prdt: '01' });
  assert.equal(ctx.splitAccount('123456789'), null);
  assert.equal(ctx.splitAccount(''), null);
  assert.equal(ctx.splitAccount(null), null);
});

test('buildKisToken: JSON 본문 client_credentials', () => {
  const r = ctx.buildKisToken('K', 'S');
  assert.equal(r.url, 'https://openapi.koreainvestment.com:9443/oauth2/tokenP');
  assert.equal(r.options.method, 'post');
  assert.equal(r.options.muteHttpExceptions, true);
  assert.deepEqual(JSON.parse(r.options.payload), { grant_type: 'client_credentials', appkey: 'K', appsecret: 'S' });
});

test('parseKisToken: 만료 시각 = 지금 + expires_in, 실패는 코드·설명', () => {
  assert.deepEqual(plain(ctx.parseKisToken('{"access_token":"T","expires_in":86400}', 1000)),
    { token: 'T', expiresAt: 1000 + 86400000 });
  assert.match(ctx.parseKisToken('{"error_code":"EGW00133","error_description":"1분당 1회"}', 0).error, /EGW00133 1분당 1회/);
  assert.equal(ctx.parseKisToken('<html>', 0).error, '토큰 응답이 JSON이 아님');
});

test('buildKisBalance: 잔고 조회 경로·tr_id·필수 파라미터, 주문 경로 없음', () => {
  const r = ctx.buildKisBalance('T', 'K', 'S', { cano: '12345678', prdt: '01' });
  assert.ok(r.url.startsWith('https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/trading/inquire-balance?'));
  for (const kv of ['CANO=12345678', 'ACNT_PRDT_CD=01', 'AFHR_FLPR_YN=N', 'OFL_YN=', 'INQR_DVSN=02', 'UNPR_DVSN=01',
    'FUND_STTL_ICLD_YN=N', 'FNCG_AMT_AUTO_RDPT_YN=N', 'PRCS_DVSN=00', 'CTX_AREA_FK100=', 'CTX_AREA_NK100=']) {
    assert.ok(r.url.includes(kv), kv);
  }
  assert.ok(!/order/i.test(r.url));
  assert.deepEqual(plain(r.options.headers), { authorization: 'Bearer T', appkey: 'K', appsecret: 'S',
    tr_id: 'TTTC8434R', custtype: 'P' });
  assert.equal(r.options.method, 'get');
});

test('parseKisBalance: 정상 → 평가 = 순자산, 원금 = 매입금액 합계 + 예수금 (쉼표 문자열 허용)', () => {
  const ok = JSON.stringify({ rt_cd: '0', msg_cd: 'KIOK0510', msg1: '조회가 완료되었습니다',
    output1: [], output2: [{ nass_amt: '5,300,000', pchs_amt_smtl_amt: '4,800,000', dnca_tot_amt: '200000' }] });
  assert.deepEqual(plain(ctx.parseKisBalance(ok)), { kind: 'ok', code: 'KIOK0510', msg: '', value: 5300000, principal: 5000000 });
});

test('parseKisBalance: 실패 종류 — 호출 제한, 토큰 만료, 그 밖의 오류, 빈 output2, 숫자 아님, JSON 아님', () => {
  const err = (cd, m) => JSON.stringify({ rt_cd: '1', msg_cd: cd, msg1: m });
  assert.equal(ctx.parseKisBalance(err('EGW00201', '초당 거래건수 초과')).kind, 'throttled');
  assert.equal(ctx.parseKisBalance(err('EGW00123', '기간이 만료된 token')).kind, 'expired');
  assert.deepEqual(plain(ctx.parseKisBalance(err('OPSQ0002', '없는 계좌 '))), { kind: 'error', code: 'OPSQ0002', msg: '없는 계좌' });
  assert.equal(ctx.parseKisBalance(JSON.stringify({ rt_cd: '0', output2: [] })).msg, 'output2 없음');
  assert.equal(ctx.parseKisBalance(JSON.stringify({ rt_cd: '0', output2: [{ nass_amt: 'x', pchs_amt_smtl_amt: 1, dnca_tot_amt: 1 }] })).kind, 'error');
  assert.equal(ctx.parseKisBalance('<html>').msg, '응답이 JSON이 아님');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && node --test tests/kis.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)"`
Expected: 파일이 없어 `ENOENT` 또는 6개 모두 `not ok`

- [ ] **Step 3: Write minimal implementation** — `apps-script/kis_logic.gs`

```js
/* 한투(KIS) 순수 로직 — Apps Script 전역에 의존하지 않는다 (node --test 대상).
   조회 전용: 잔고 조회 하나뿐이고 주문 경로는 없다. toNum·num은 meritz_logic.gs(같은 전역)의 것을 쓴다. */

var KIS_BASE = 'https://openapi.koreainvestment.com:9443';
var KIS_BALANCE_PATH = '/uapi/domestic-stock/v1/trading/inquire-balance';
var KIS_RAW_ROW = [2, 3]; // 한투원본: 슬롯(0 소유자, 1 배우자) → 행
var KIS_BALANCE_PARAMS = [['AFHR_FLPR_YN', 'N'], ['OFL_YN', ''], ['INQR_DVSN', '02'], ['UNPR_DVSN', '01'],
  ['FUND_STTL_ICLD_YN', 'N'], ['FNCG_AMT_AUTO_RDPT_YN', 'N'], ['PRCS_DVSN', '00'],
  ['CTX_AREA_FK100', ''], ['CTX_AREA_NK100', '']];

// '12345678-01' → {cano:'12345678', prdt:'01'}. 숫자 10자리가 아니면 null.
function splitAccount(s) {
  var d = String(s === null || s === undefined ? '' : s).replace(/[-\s]/g, '');
  return /^\d{10}$/.test(d) ? { cano: d.slice(0, 8), prdt: d.slice(8) } : null;
}

function buildKisToken(key, secret) {
  return {
    url: KIS_BASE + '/oauth2/tokenP',
    options: {
      method: 'post', muteHttpExceptions: true, contentType: 'application/json; charset=UTF-8',
      payload: JSON.stringify({ grant_type: 'client_credentials', appkey: key, appsecret: secret })
    }
  };
}

function parseKisToken(text, nowMs) {
  var body;
  try {
    body = JSON.parse(text);
  } catch (e) {
    return { error: '토큰 응답이 JSON이 아님' };
  }
  if (!body || !body.access_token) {
    return { error: String((body && (body.error_code || body.msg_cd)) || '') + ' '
      + String((body && (body.error_description || body.msg1)) || '') };
  }
  var sec = toNum(body.expires_in);
  return { token: String(body.access_token), expiresAt: nowMs + (isNaN(sec) ? 0 : sec) * 1000 };
}

function buildKisBalance(token, key, secret, acct) {
  var q = [['CANO', acct.cano], ['ACNT_PRDT_CD', acct.prdt]].concat(KIS_BALANCE_PARAMS)
    .map(function (p) { return p[0] + '=' + encodeURIComponent(p[1]); }).join('&');
  return {
    url: KIS_BASE + KIS_BALANCE_PATH + '?' + q,
    options: {
      method: 'get', muteHttpExceptions: true, contentType: 'application/json; charset=UTF-8',
      headers: { authorization: 'Bearer ' + token, appkey: key, appsecret: secret, tr_id: 'TTTC8434R', custtype: 'P' }
    }
  };
}

// 성공은 rt_cd "0". 평가 = 순자산(nass_amt), 원금 추정 = 매입금액 합계 + 예수금.
function parseKisBalance(text) {
  var body;
  try {
    body = JSON.parse(String(text));
  } catch (e) {
    return { kind: 'error', code: '', msg: '응답이 JSON이 아님' };
  }
  if (!body || typeof body !== 'object') return { kind: 'error', code: '', msg: '응답 형식 오류' };
  var code = String(body.msg_cd || '');
  if (String(body.rt_cd) !== '0') {
    var kind = code === 'EGW00201' ? 'throttled' : code === 'EGW00123' ? 'expired' : 'error';
    return { kind: kind, code: code, msg: String(body.msg1 || '').trim() };
  }
  var o = Array.isArray(body.output2) ? body.output2[0] : null;
  if (!o) return { kind: 'error', code: code, msg: 'output2 없음' };
  try {
    return { kind: 'ok', code: code, msg: '', value: num(o, 'nass_amt'),
      principal: num(o, 'pchs_amt_smtl_amt') + num(o, 'dnca_tot_amt') };
  } catch (e) {
    return { kind: 'error', code: code, msg: e.message };
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && node --test tests/kis.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)"`
Expected: `# pass 6`, `# fail 0`

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add apps-script/kis_logic.gs tests/kis.test.js && git commit -m "feat: 한투 ISA 순수 로직 — 계좌번호·토큰·잔고 요청·응답 해석 (조회 전용)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 투자 기록 순수 로직 + 메리츠 원금

**Files:**
- Create: `apps-script/invest_logic.gs`
- Modify: `apps-script/meritz_logic.gs` (끝에 `principalOf` 추가)
- Create: `tests/invest.test.js`

**Interfaces:**
- Consumes: `nextEmptyRow(colA)` (`logic.gs`), `num` (`meritz_logic.gs`)
- Produces: `INVEST_ACCOUNT_ROWS=[7,8,10,11]`, `INVEST_LOG_COLS=12`, `yesterday(today)->Date`, `investLogRow(date, pairs)->any[12]`, `dateRowIndex(colA, date)->number`, `principalOf(val)->number`

- [ ] **Step 1: Write the failing test** — `tests/invest.test.js`

```js
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const ctx = vm.createContext({});
for (const f of ['logic.gs', 'meritz_logic.gs', 'invest_logic.gs']) {
  vm.runInContext(fs.readFileSync(path.join(__dirname, '..', 'apps-script', f), 'utf8'), ctx);
}
const plain = (x) => JSON.parse(JSON.stringify(x));

test('investLogRow: 계좌 4개 평가·원금, 합계, 빠진 계좌 수', () => {
  const d = new Date(2026, 9, 12);
  const row = ctx.investLogRow(d, [[1000, 900], ['', ''], [500, ''], ['키없음', 3]]);
  assert.equal(row.length, 12);
  assert.equal(row[0], d);
  assert.deepEqual(plain(row.slice(1)), [1000, 900, '', '', 500, '', '', 3, 1500, 900, 2]);
});

test('investLogRow: 평가가 없으면 그 계좌 원금도 합계에서 뺀다', () => {
  const row = ctx.investLogRow(new Date(2026, 9, 12), [['', 700], [10, 5], ['', ''], ['', '']]);
  assert.deepEqual(plain(row.slice(9)), [10, 5, 3]);
});

test('dateRowIndex: 같은 날짜(시각 무시)면 그 행에 덮어쓰고, 없으면 다음 빈 행', () => {
  const col = [['날짜'], [new Date(2026, 9, 10)], [new Date(2026, 9, 11, 6, 3)], ['']];
  assert.equal(ctx.dateRowIndex(col, new Date(2026, 9, 11)), 3);
  assert.equal(ctx.dateRowIndex(col, new Date(2026, 9, 12)), 4);
  assert.equal(ctx.dateRowIndex([['날짜']], new Date(2026, 9, 12)), 2);
});

test('yesterday: 월 첫날이면 전달 말일', () => {
  const y = ctx.yesterday(new Date(2026, 10, 1));
  assert.deepEqual([y.getFullYear(), y.getMonth(), y.getDate()], [2026, 9, 31]);
});

test('principalOf: 매입금액 + 원화 현금 + 외화 현금 − 대출', () => {
  const val = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'meritz_valuation.json'), 'utf8')).data;
  assert.equal(ctx.principalOf(val), 5084000 + 1000000 + 140000 - 300000);
  assert.equal(ctx.principalOf({ byng_amt: 10, tfam: 5 }), 15); // 외화·대출 없음
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && node --test tests/invest.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)"`
Expected: `invest_logic.gs` 없음 → 실패

- [ ] **Step 3: Write minimal implementation**

`apps-script/invest_logic.gs`:

```js
/* 투자 탭 순수 로직 (node --test 대상). 기록은 06시 일일 작업 한 곳에서만 쓴다. */

var INVEST_ACCOUNT_ROWS = [7, 8, 10, 11]; // [투자] 계좌 행: 신랑 메리츠, 신랑 ISA, 신부 메리츠, 신부 ISA
var INVEST_LOG_COLS = 12;

function dayStart(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

function yesterday(today) {
  return new Date(today.getFullYear(), today.getMonth(), today.getDate() - 1);
}

function isNum(x) {
  return typeof x === 'number' && !isNaN(x);
}

// pairs: 계좌 4개 [평가, 원금] → 날짜 | 4×(평가, 원금) | 합계 평가 | 합계 원금 | 빠진 계좌 수
// 평가가 숫자가 아닌 계좌는 빠진 것으로 보고 합계(평가·원금 모두)에서 뺀다.
function investLogRow(date, pairs) {
  var row = [date];
  var value = 0, principal = 0, missing = 0;
  pairs.forEach(function (p) {
    var v = isNum(p[0]) ? p[0] : '';
    var c = isNum(p[1]) ? p[1] : '';
    row.push(v, c);
    if (v === '') { missing++; return; }
    value += v;
    if (c !== '') principal += c;
  });
  return row.concat([value, principal, missing]);
}

// 투자기록 A열 값 → 이 날짜를 쓸 행 번호(1부터). 같은 날짜가 있으면 그 행(덮어쓰기), 없으면 다음 빈 행.
function dateRowIndex(colA, date) {
  var key = dayStart(date).getTime();
  for (var i = 1; i < colA.length; i++) {
    var x = colA[i][0];
    if (Object.prototype.toString.call(x) === '[object Date]' && dayStart(x).getTime() === key) return i + 1;
  }
  return nextEmptyRow(colA);
}
```

`apps-script/meritz_logic.gs` 끝에 추가:

```js

// 투자원금 추정 = 매입금액 + 원화 현금 + 외화 현금 − 대출. 팔아서 남긴 수익 현금도 원금으로 잡히는 한계가 있다.
function principalOf(val) {
  return num(val, 'byng_amt') + num(val, 'tfam') + num(val, 'frcr_tfam', true) - num(val, 'loan_amt', true);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd "/mnt/d/budget book" && node --test tests/invest.test.js 2>&1 | grep -E "^not ok|^# (pass|fail)" && node --test tests/meritz.test.js 2>&1 | grep -E "^# (pass|fail)"`
Expected: invest `# pass 5`, meritz `# pass 18`, 둘 다 `# fail 0`

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add apps-script/invest_logic.gs apps-script/meritz_logic.gs tests/invest.test.js && git commit -m "feat: 투자기록 한 줄·날짜 덮어쓰기 순수 로직, 메리츠 투자원금 추정

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 스크립트 연결 — 한투 조회, 증권 연동 메뉴, 원금 H9, 06시 투자기록

**Files:**
- Create: `apps-script/kis.gs`
- Modify: `apps-script/meritz.gs` (onOpen 메뉴, setMeritzKeys, clearMeritzKeys, onEditMeritz, refreshMeritz, refreshMeritz_ 키없음 문구, writeResults_)
- Modify: `apps-script/triggers.gs` (TUCKED_VIEWS, dailyJob, recordInvest)
- Modify: `deploy_script.py:18` (SOURCES)
- Test: `tests/test_deploy.py`

**Interfaces:**
- Consumes: Task 1·2 함수, `isOwner_()`, `askValue_(ui,label)`, `tokenFresh`, `STATUS_LABEL`, `showTab_(name)`, `todayDate()`
- Produces: `setKisKeys()`, `clearKisKeys_()`, `refreshKis_(ss)` (예외 없음), `recordInvest(ss)`; 메뉴 '증권 연동'

- [ ] **Step 1: Write the failing test** — `tests/test_deploy.py` 끝에 추가

```python


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
    assert "principalOf(" in _fn(files["meritz"], "writeResults_")
    assert "recordInvest(ss);" in _fn(files["triggers"], "dailyJob")
    assert "'주식_신랑'" in files["triggers"] and "'주식_신부'" in files["triggers"]  # 상세 탭은 다시 숨기기 대상
    assert [f["name"] for f in deploy_script.script_files()][1:] == [
        "logic", "triggers", "meritz_logic", "meritz", "kis_logic", "kis", "invest_logic"]
```

또 같은 파일의 기존 시험 한 줄을 바꾼다 (키를 넣으면 이제 [투자] 탭이 열림):

```python
    assert "showTab_('투자')" in _fn(files["meritz"], "setMeritzKeys")  # 키 넣으면 투자 탭이 보이게
```
(기존: `assert "showTab_(slot_().stock)" in _fn(files["meritz"], "setMeritzKeys")  # 키 넣으면 내 주식 탭이 보이게`)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_deploy.py 2>&1 | tail -3`
Expected: 3 failed (`KeyError: 'kis'` 등)

- [ ] **Step 3: Write implementation**

`deploy_script.py`:
```python
SOURCES = ["logic", "triggers", "meritz_logic", "meritz", "kis_logic", "kis", "invest_logic"]
```

`apps-script/kis.gs`:

```js
/* 한투 ISA 연결부 — 판단 로직은 kis_logic.gs. 조회 전용.
   키·계좌번호·토큰은 각자의 사용자 속성에만 두고, 실행자 슬롯의 한투원본 행에만 쓴다. */

var KIS_RAW = '한투원본';
var KPROP = { key: 'KIS_APP_KEY', secret: 'KIS_APP_SECRET', acct: 'KIS_ACCOUNT', token: 'KIS_TOKEN', exp: 'KIS_TOKEN_EXP' };

function setKisKeys() {
  var ui = SpreadsheetApp.getUi();
  var key = askValue_(ui, '한투 App Key');
  if (!key) return;
  var secret = askValue_(ui, '한투 App Secret');
  if (!secret) return;
  var acct = askValue_(ui, 'ISA 계좌번호 10자리 (예: 12345678-01)');
  if (!splitAccount(acct)) {
    ui.alert('계좌번호는 숫자 10자리(앞 8자리-뒤 2자리)로 넣어 주세요.');
    return;
  }
  var p = PropertiesService.getUserProperties();
  p.setProperty(KPROP.key, key);
  p.setProperty(KPROP.secret, secret);
  p.setProperty(KPROP.acct, acct);
  p.deleteProperty(KPROP.token);
  p.deleteProperty(KPROP.exp);
  showTab_('투자');
  ui.alert("저장했습니다. 처음이면 메뉴 증권 연동 > 자동 갱신 켜기를 한 번 누르고, [투자] 탭의 '지금 갱신'을 체크해 확인하세요.");
}

function clearKisKeys_() {
  var p = PropertiesService.getUserProperties();
  [KPROP.key, KPROP.secret, KPROP.acct, KPROP.token, KPROP.exp].forEach(function (k) { p.deleteProperty(k); });
}

function writeKis_(ss, r) {
  var sh = ss.getSheetByName(KIS_RAW);
  if (!sh) return;
  var row = KIS_RAW_ROW[isOwner_() ? 0 : 1];
  sh.getRange(row, 2, 1, 3).setValues([[STATUS_LABEL[r.kind] || '오류', r.code || '', String(r.msg || '').slice(0, 100)]]);
  if (r.kind === 'ok') sh.getRange(row, 5, 1, 3).setValues([[new Date(), r.value, r.principal]]); // 실패면 마지막 성공 값 유지
}

function getKisToken_(p, key, secret, force) {
  var now = Date.now();
  var saved = p.getProperty(KPROP.token);
  if (!force && saved && tokenFresh(Number(p.getProperty(KPROP.exp)), now)) return { token: saved };
  var req = buildKisToken(key, secret);
  var t = parseKisToken(UrlFetchApp.fetch(req.url, req.options).getContentText(), now);
  if (t.token) {
    p.setProperty(KPROP.token, t.token);
    p.setProperty(KPROP.exp, String(t.expiresAt));
  }
  return t;
}

function fetchKis_(token, key, secret, acct) {
  var req = buildKisBalance(token, key, secret, acct);
  for (var attempt = 0; attempt < 3; attempt++) {
    var r = parseKisBalance(UrlFetchApp.fetch(req.url, req.options).getContentText());
    if (r.kind !== 'throttled') return r;
    Utilities.sleep(1000);
  }
  return { kind: 'error', code: 'EGW00201', msg: '초당 호출 제한이 계속됨' };
}

// refreshMeritz 안에서 메리츠 다음에 돈다. 예외를 밖으로 던지지 않는다.
function refreshKis_(ss) {
  var p = PropertiesService.getUserProperties();
  var key = p.getProperty(KPROP.key);
  var secret = p.getProperty(KPROP.secret);
  var acct = splitAccount(p.getProperty(KPROP.acct));
  if (!key || !secret || !acct) {
    writeKis_(ss, { kind: 'nokey', code: '', msg: '메뉴 증권 연동 > 한투 ISA 키 입력' });
    return;
  }
  try {
    var t = getKisToken_(p, key, secret, false);
    if (!t.token) {
      writeKis_(ss, { kind: 'error', code: '', msg: '토큰 발급 실패 ' + t.error });
      return;
    }
    var r = fetchKis_(t.token, key, secret, acct);
    if (r.kind === 'expired') { // 저장된 토큰이 먼저 끊겼다 — 한 번만 새로 받는다
      t = getKisToken_(p, key, secret, true);
      r = t.token ? fetchKis_(t.token, key, secret, acct) : { kind: 'error', code: '', msg: '토큰 재발급 실패 ' + t.error };
    }
    writeKis_(ss, r);
  } catch (err) {
    writeKis_(ss, { kind: 'error', code: '', msg: '예외: ' + String(err.message) });
  }
}
```

`apps-script/meritz.gs` 바꿀 곳 (각각 정확히 한 번 나옴):

```js
// onOpen — 기존 createMenu('메리츠') 묶음 전체를 이것으로
function onOpen() {
  SpreadsheetApp.getUi().createMenu('증권 연동')
    .addItem('메리츠 키 입력 (내 계좌)', 'setMeritzKeys')
    .addItem('한투 ISA 키 입력 (내 계좌)', 'setKisKeys')
    .addItem('자동 갱신 켜기 (내 계좌)', 'setupMeritzTriggers')
    .addItem('내 키 삭제 (메리츠·한투)', 'clearMeritzKeys')
    .addToUi();
  addViewMenu_();
}
```

```js
// setMeritzKeys 끝부분 — showTab_(slot_().stock); 과 ui.alert(...) 두 줄을 이것으로
  showTab_('투자');
  ui.alert("저장했습니다. 처음이면 메뉴 증권 연동 > 자동 갱신 켜기를 한 번 누르고, [투자] 탭의 '지금 갱신'을 체크해 확인하세요.");
```

```js
// clearMeritzKeys 본문 전체
function clearMeritzKeys() {
  var p = PropertiesService.getUserProperties();
  [PROP.key, PROP.secret, PROP.mac, PROP.token, PROP.exp].forEach(function (k) { p.deleteProperty(k); });
  clearKisKeys_();
  SpreadsheetApp.getUi().alert('내 메리츠·한투 키를 지웠습니다.');
}
```

```js
// onEditMeritz 첫 두 줄을 이것으로 — 투자 탭 H1도 갱신 체크박스
function onEditMeritz(e) {
  var r = e.range;
  var name = r.getSheet().getName();
  if ((name !== slot_().stock && name !== '투자') || r.getA1Notation() !== 'H1' || e.value !== 'TRUE') return;
```

```js
// refreshMeritz 의 try/catch/finally 를 이것으로 — 메리츠가 실패해도 한투는 조회
  try {
    try {
      refreshMeritz_(ss);
    } catch (err) {
      writeAllStatus_(ss, { kind: 'error', code: '', msg: '예외: ' + String(err.message).slice(0, 100) });
    }
    refreshKis_(ss);
  } finally {
    lock.releaseLock();
  }
```

```js
// refreshMeritz_ 의 키없음 문구
    writeAllStatus_(ss, { kind: 'nokey', code: '', msg: '메뉴 증권 연동 > 메리츠 키 입력' });
```

```js
// writeResults_ 의 valuation 블록 — H9 원금 추정 추가
  if (res.valuation.kind === 'ok') {
    try {
      var principal = principalOf(res.valuation.data);
      sh.getRange('H1:H7').setValues(summaryValues(res.valuation.data).map(function (x) { return [x]; }));
      sh.getRange('H8').setValue(now);
      sh.getRange('H9').setValue(principal);
    } catch (err) { res.valuation = failed_(res.valuation, err); }
  }
```

`apps-script/triggers.gs`:

```js
// TUCKED_VIEWS 줄과 그 위 주석을 이것으로
// 자주 안 쓰는 보기 탭은 숨겨 두고 PC 메뉴로 꺼낸다 (폰 앱엔 메뉴가 없지만 폰은 내역·대시보드·투자 위주).
var TUCKED_VIEWS = ['추이', '달력', '검색', '주식_신랑', '메리츠_신랑', '주식_신부', '메리츠_신부'];
```

```js
// dailyJob 안 sendMonthlyReport(ss); 다음 줄에
  recordInvest(ss);
```

`function setupTriggers()` 바로 위에 추가:

```js
// 투자기록: 06시에 전날 기준 한 줄(같은 날짜면 덮어씀). 값은 [투자] 탭 계좌 표의 최종 값(직접입력 우선).
function recordInvest(ss) {
  var tab = ss.getSheetByName('투자');
  var log = ss.getSheetByName('투자기록');
  if (!tab || !log) return;
  var vals = tab.getRange(1, 2, 12, 2).getValues(); // B1:C12 — 계좌 행의 평가·원금
  var pairs = INVEST_ACCOUNT_ROWS.map(function (r) { return vals[r - 1]; });
  var date = yesterday(todayDate());
  var row = dateRowIndex(log.getRange(1, 1, log.getMaxRows(), 1).getValues(), date);
  if (row > log.getMaxRows()) log.insertRowsAfter(log.getMaxRows(), 365);
  log.getRange(row, 1, 1, INVEST_LOG_COLS).setValues([investLogRow(date, pairs)]);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_deploy.py 2>&1 | tail -1 && for t in logic meritz couple kis invest; do node --test tests/$t.test.js 2>&1 | grep -E "^# fail"; done && node -e "const fs=require('fs');for(const f of ['logic','triggers','meritz_logic','meritz','kis_logic','kis','invest_logic'])new Function(fs.readFileSync('apps-script/'+f+'.gs','utf8'));console.log('문법 OK')"`
Expected: pytest 전부 통과, node 다섯 파일 모두 `# fail 0`, `문법 OK`

- [ ] **Step 5: Commit** (배포는 Task 6에서 운영 탭이 생긴 뒤)

```bash
cd "/mnt/d/budget book" && git add apps-script deploy_script.py tests/test_deploy.py && git commit -m "feat: 한투 ISA 조회 연결·증권 연동 메뉴·메리츠 원금(H9)·06시 투자기록

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 시트 생성기 — [투자] 탭·숨김 원본/기록 탭·자산 연동 4계좌

**Files:**
- Create: `invest.py`
- Modify: `layout.py` (탭 상수·SHEETS·TUCKED·INVEST_ACCOUNTS·자산 G 검증·보호)
- Modify: `formulas.py` (`asset_values`의 연동 대상)
- Modify: `meritz_sheet.py` (`raw_values`에 G9), `meritz_style.py` (`_formats`에 H9)
- Modify: `styling.py` (열 너비·탭 색·눈금선·머리글), `guide.py` (요약·주식 구역), `build_budget.py` (연결)
- Create: `tests/test_invest.py`
- Modify tests: `tests/test_couple.py`, `tests/test_formulas.py`, `tests/test_layout.py`, `verify_meritz.py`

**Interfaces:**
- Consumes: `layout.v`, `layout.number_format`, `layout.a1_to_grid`, `charts._basic`, `charts._chart`, `meritz_style._sign_rule`, `styling.CHECK_BG`
- Produces: `layout.INVEST="투자"`, `layout.KIS_RAW="한투원본"`, `layout.INVEST_LOG="투자기록"`, `layout.INVEST_ACCOUNTS=[("메리츠_신랑",7),("한투ISA_신랑",8),("메리츠_신부",10),("한투ISA_신부",11)]`, `invest.invest_values()->list[dict]`, `invest.structure_requests()->list[dict]`, `invest.visual_requests()->list[dict]`

- [ ] **Step 1: Write the failing test** — `tests/test_invest.py`

```python
import build_budget
import formulas
import invest
import layout


def _by_range(values):
    return {e["range"]: e["values"] for e in values}


def test_invest_tabs_defined_visible_and_hidden():
    props = {t: (sid, rows, cols, hidden) for t, sid, rows, cols, hidden in layout.SHEETS}
    assert props["투자"] == (1900, 100, 10, False)
    assert props["한투원본"] == (1950, 3, 7, True)
    assert props["투자기록"] == (2000, 1000, 12, True)
    assert "주식_신랑" in layout.TUCKED
    visible = [s["properties"]["title"] for s in layout.create_body("t")["sheets"] if not s["properties"]["hidden"]]
    assert visible == ["사용법", "내역", "대시보드", "부부", "자산기록", "투자", "즐겨찾기", "반복", "문자입력", "자산", "설정"]


def test_account_rows_prefer_manual_then_auto():
    vals = _by_range(invest.invest_values())
    row = vals["투자!A7:G7"][0]
    assert row[0] == "신랑 메리츠"
    assert row[1] == '=IF(ISNUMBER(H7),H7,IF(ISNUMBER(메리츠원본!$H$7),메리츠원본!$H$7,""))'
    assert row[2] == '=IF(ISNUMBER(I7),I7,IF(ISNUMBER(H7),"",IF(ISNUMBER(메리츠원본!$H$9),메리츠원본!$H$9,"")))'
    assert '"직접입력"' in row[6] and '"오래됨"' in row[6] and '"자동"' in row[6]
    isa = vals["투자!A11:G11"][0]
    assert "한투원본!$F$3" in isa[1] and "한투원본!$G$3" in isa[2] and "한투원본!$B$3" in isa[6]


def test_totals_kpi_and_changes_tolerate_empty_log():
    vals = _by_range(invest.invest_values())
    assert vals["투자!A9:G9"][0][1] == '=IF(COUNT(B7,B8)=0,"",SUM(B7,B8))'
    kpi = vals["투자!A4:F4"][0]
    assert kpi[0] == '=IF(COUNT(B7,B8,B10,B11)=0,"",SUM(B7,B8,B10,B11))'
    assert kpi[4].startswith("=IFERROR(") and kpi[5].startswith("=IFERROR(")
    assert "EOMONTH(last,-1)" in kpi[5]


def test_month_end_and_recent_30_tables():
    vals = _by_range(invest.invest_values())
    assert vals["투자!A40:C40"] == [["월", "합계 평가", "합계 원금"]]
    assert vals["투자!A41"][0][0].startswith("=IFERROR(SORT(UNIQUE(FILTER(")
    month = vals["투자!B41:C41"][0]
    assert "EOMONTH(m,0)" in month[0] and ",10,FALSE)" in month[0] and ",11,FALSE)" in month[1]
    assert "MAX(투자기록!A2:A)-29" in vals["투자!E41"][0][0]


def test_raw_and_log_headers():
    vals = _by_range(invest.invest_values())
    assert vals["한투원본!A1:G3"][0] == ["사람", "상태", "코드", "메시지", "마지막 성공", "평가금액", "원금"]
    assert [r[0] for r in vals["한투원본!A1:G3"][1:]] == ["신랑", "신부"]
    assert len(vals["투자기록!A1:L1"][0]) == 12


def test_asset_sync_reads_invest_tab_for_all_four_accounts():
    e2 = _by_range(formulas.asset_values())["자산!E1:E2"][1][0]
    assert '{"메리츠_신랑","한투ISA_신랑","메리츠_신부","한투ISA_신부"}' in e2
    assert "투자!$B$7,투자!$B$8,투자!$B$10,투자!$B$11" in e2
    h2 = _by_range(formulas.asset_values())["자산!H1:H2"][1][0]
    assert "투자!$F$7" in h2 and '"직접입력"' in h2 and '"연동 "&TEXT(at,"mm/dd hh:mm")' in h2
    rules = {tuple(sorted(r["setDataValidation"]["range"].items())): r["setDataValidation"]["rule"]
             for r in layout.validation_requests()}
    g = rules[tuple(sorted(layout.a1_to_grid("자산!G2:G50").items()))]
    assert [x["userEnteredValue"] for x in g["condition"]["values"]] == [n for n, _r in layout.INVEST_ACCOUNTS]


def test_invest_tab_protected_except_refresh_and_manual_cells():
    prs = [r["addProtectedRange"]["protectedRange"] for r in layout.protection_requests()]
    tab = [p for p in prs if p["range"] == {"sheetId": 1900}][0]
    assert tab["unprotectedRanges"] == [layout.a1_to_grid(a) for a in ("투자!H1", "투자!H7:I8", "투자!H10:I11")]


def test_two_charts_and_build_wiring():
    charts = [r["addChart"]["chart"] for r in invest.visual_requests() if "addChart" in r]
    assert [c["spec"]["title"] for c in charts] == ["월별 투자 추이 (월말)", "최근 30일 합산 평가금액"]
    assert all(c["position"]["overlayPosition"]["anchorCell"]["sheetId"] == 1900 for c in charts)
    assert any("투자!A7:G7" == e["range"] for e in build_budget.value_data("a@b.com"))
    assert any("setDataValidation" in r and r["setDataValidation"]["range"] == layout.a1_to_grid("투자!H1")
               for r in build_budget.structure_requests())


def test_meritz_raw_has_principal_row():
    import meritz_sheet as ms
    vals = _by_range(ms.raw_values(layout.MERITZ_SLOTS[1]))
    assert vals["메리츠원본2!G9"] == [["원금(추정)"]]


def test_guide_points_to_invest_tab_and_kis_menu():
    import guide
    text = "\n".join(b for _k, _a, b in guide.CONTENT)
    assert "[투자]" in "\n".join(b for _k, _a, b in guide.CONTENT[2:8])
    assert "증권 연동" in text and "한투 ISA 키 입력" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_invest.py 2>&1 | tail -2`
Expected: `ModuleNotFoundError: No module named 'invest'`

- [ ] **Step 3: Implement**

`layout.py`:

```python
# RAW2, STOCK2, MERITZ2 정의 줄 다음에
INVEST, KIS_RAW, INVEST_LOG = "투자", "한투원본", "투자기록"
```

SHEETS: `(NETWORTH, 1800, 200, 12, False),` 다음 줄에 `(INVEST, 1900, 100, 10, False),`, 맨 끝 `(RAW2, 1450, 110, 14, True),` 다음에 `(KIS_RAW, 1950, 3, 7, True),`, `(INVEST_LOG, 2000, 1000, 12, True),`.

```python
TUCKED = {TREND, CAL, SEARCH, STOCK, MERITZ, STOCK2, MERITZ2}
# [자산] G열 연동 값 → [투자] 탭 그 계좌의 행 (평가 B열, 마지막 갱신 F열)
INVEST_ACCOUNTS = [("메리츠_신랑", 7), ("한투ISA_신랑", 8), ("메리츠_신부", 10), ("한투ISA_신부", 11)]
```

`validation_requests`의 자산 G 줄:
```python
        (f"{ASSETS}!G2:G50", _rule("ONE_OF_LIST", *[n for n, _r in INVEST_ACCOUNTS])),
```

`protection_requests`의 `whole` 첫 줄 끝에 `, (INVEST, ["H1", "H7:I8", "H10:I11"]), (KIS_RAW, []), (INVEST_LOG, [])` 추가 (리스트 안).

`formulas.py` — import에 `INVEST, INVEST_ACCOUNTS` 추가(`MERITZ_SLOTS`는 이 파일에서 더 안 쓰면 import에서 뺀다), `asset_values`의 연동 부분을 교체:

```python
    # 연동(G열)에 고른 계좌의 [투자] 탭 최종 평가금액(직접입력 우선). 값이 없으면 기존 계산으로 되돌림.
    choices = "{" + ",".join(f'"{n}"' for n, _r in INVEST_ACCOUNTS) + "}"
    pick = lambda col: (f'IFERROR(CHOOSE(MATCH(sync,{choices},0),'
                        + ",".join(f"{INVEST}!${col}${r}" for _n, r in INVEST_ACCOUNTS) + '),"")')
    synced = f'LET(net,{pick("B")},IF(AND(sync<>"",ISNUMBER(net)),net,{bal}))'
    status = (f'IF(OR(x="",sync=""),"",LET(net,{pick("B")},at,{pick("F")},IF(NOT(ISNUMBER(net)),"미갱신",'
              f'IF(NOT(ISNUMBER(at)),"직접입력",IF(NOW()-at>3,"오래됨 ("&TEXT(at,"mm/dd")&")",'
              f'"연동 "&TEXT(at,"mm/dd hh:mm"))))))')
```

`meritz_sheet.py` `raw_values` 반환 목록에 `v(f"{r}!G9", [["원금(추정)"]]),` 추가. `meritz_style.py` `_formats`의 `(f"{r}!H1:H7", "NUMBER", "#,##0")` 다음에 `(f"{r}!H9", "NUMBER", "#,##0"),`.

`invest.py`:

```python
"""투자 탭(부부 주식 계좌 4개 합산·증감·추이)과 숨김 탭 한투원본·투자기록의 값·서식·차트."""
from charts import _basic, _chart
from layout import INVEST, INVEST_LOG, KIS_RAW, RAW, RAW2, a1_to_grid, number_format, v
from meritz_style import _sign_rule
from styling import BLUE_TEXT, CHECK_BG, RED_TEXT

L = INVEST_LOG
# (표시 이름, 행, 자동 평가, 자동 원금, 마지막 성공, 상태, 메시지)
ACCOUNT_ROWS = [
    ("신랑 메리츠", 7, f"{RAW}!$H$7", f"{RAW}!$H$9", f"{RAW}!$H$8", f"{RAW}!$B$2", f"{RAW}!$D$2"),
    ("신랑 ISA(한투)", 8, f"{KIS_RAW}!$F$2", f"{KIS_RAW}!$G$2", f"{KIS_RAW}!$E$2", f"{KIS_RAW}!$B$2", f"{KIS_RAW}!$D$2"),
    ("신부 메리츠", 10, f"{RAW2}!$H$7", f"{RAW2}!$H$9", f"{RAW2}!$H$8", f"{RAW2}!$B$2", f"{RAW2}!$D$2"),
    ("신부 ISA(한투)", 11, f"{KIS_RAW}!$F$3", f"{KIS_RAW}!$G$3", f"{KIS_RAW}!$E$3", f"{KIS_RAW}!$B$3", f"{KIS_RAW}!$D$3"),
]
TOTAL_ROWS = [("신랑 합계", 9, 7, 8), ("신부 합계", 12, 10, 11)]
KPI_HEAD = ["부부 합산 평가금액", "투자원금", "평가손익", "수익률", "전일 대비", "전월말 대비"]
TABLE_HEAD = ["계좌", "평가금액", "원금", "손익", "수익률", "마지막 갱신", "상태", "직접입력 평가", "직접입력 원금"]
LOG_HEAD = ["날짜", "신랑 메리츠 평가", "원금", "신랑 ISA 평가", "원금", "신부 메리츠 평가", "원금",
            "신부 ISA 평가", "원금", "합계 평가", "합계 원금", "빠진 계좌 수"]
KIS_HEAD = ["사람", "상태", "코드", "메시지", "마지막 성공", "평가금액", "원금"]


def _pl(r: int) -> list[str]:
    return [f'=IF(AND(ISNUMBER(B{r}),ISNUMBER(C{r})),B{r}-C{r},"")',
            f'=IF(AND(ISNUMBER(D{r}),N(C{r})<>0),D{r}/C{r},"")']


def account_row(name, r, value, principal, at, status, msg) -> list[str]:
    """직접입력(H·I)이 있으면 그 값, 없으면 원본 탭 자동 값. 직접 평가만 있고 원금이 비면 원금은 모름(빈칸)."""
    return ([name,
             f'=IF(ISNUMBER(H{r}),H{r},IF(ISNUMBER({value}),{value},""))',
             f'=IF(ISNUMBER(I{r}),I{r},IF(ISNUMBER(H{r}),"",IF(ISNUMBER({principal}),{principal},"")))']
            + _pl(r)
            + [f'=IF(ISNUMBER(H{r}),"",IF(ISNUMBER({at}),{at},""))',
               (f'=IF(ISNUMBER(H{r}),"직접입력",IF({status}="","아직 갱신 전",IF({status}="성공",'
                f'IF(NOW()-{at}>3,"오래됨","자동"),{status}&IF({msg}="",""," ("&{msg}&")"))))')])


def total_row(name, r, a, b) -> list[str]:
    return ([name, f'=IF(COUNT(B{a},B{b})=0,"",SUM(B{a},B{b}))', f'=IF(COUNT(C{a},C{b})=0,"",SUM(C{a},C{b}))']
            + _pl(r) + ["", ""])


def _kpi() -> list[str]:
    acc = "B7,B8,B10,B11"
    d, t = f"FILTER({L}!A2:A,{L}!A2:A<>\"\")", f"FILTER({L}!J2:J,{L}!A2:A<>\"\")"
    prev_day = f'=IFERROR(LET(t,{t},n,ROWS(t),IF(n<2,"",INDEX(t,n)-INDEX(t,n-1))),"")'
    prev_month = (f'=IFERROR(LET(d,{d},t,{t},last,MAX(d),pe,MAX(FILTER(d,d<=EOMONTH(last,-1))),'
                  f'INDEX(t,MATCH(last,d,0))-INDEX(t,MATCH(pe,d,0))),"")')
    return [f'=IF(COUNT({acc})=0,"",SUM({acc}))', f'=IF(COUNT(C7,C8,C10,C11)=0,"",SUM(C7,C8,C10,C11))',
            '=IF(AND(ISNUMBER(A4),ISNUMBER(B4)),A4-B4,"")', '=IF(AND(ISNUMBER(C4),N(B4)<>0),C4/B4,"")',
            prev_day, prev_month]


def _trend_tables() -> list[dict]:
    months = (f'=IFERROR(SORT(UNIQUE(FILTER(ARRAYFORMULA(DATE(YEAR({L}!A2:A),MONTH({L}!A2:A),1)),'
              f'{L}!A2:A<>""))),"")')
    month_end = lambda col: (f'=MAP(A41:A100,LAMBDA(m,IF(m="","",IFERROR(VLOOKUP(MAX(FILTER({L}!$A$2:$A,'
                             f'{L}!$A$2:$A>=m,{L}!$A$2:$A<=EOMONTH(m,0))),{L}!$A$2:$K,{col},FALSE),""))))')
    recent = f'=IFERROR(SORT(FILTER({{{L}!A2:A,{L}!J2:J}},{L}!A2:A<>"",{L}!A2:A>=MAX({L}!A2:A)-29)),"")'
    return [v(f"{INVEST}!A40:C40", [["월", "합계 평가", "합계 원금"]]), v(f"{INVEST}!A41", [[months]]),
            v(f"{INVEST}!B41:C41", [[month_end(10), month_end(11)]]),
            v(f"{INVEST}!E40:F40", [["날짜", "합계 평가"]]), v(f"{INVEST}!E41", [[recent]])]


def invest_values() -> list[dict]:
    note = "직접입력 칸(H·I)에 숫자를 적으면 그 계좌는 자동 조회 대신 그 값을 씁니다. 원금은 '매입금액+현금' 추정입니다."
    out = [v(f"{INVEST}!A1", [["📈 우리집 투자"]]),
           v(f"{INVEST}!G1:I1", [["지금 갱신", False, "◀ 체크하면 자동 갱신을 켠 사람의 계좌를 바로 갱신"]]),
           v(f"{INVEST}!A2", [[note]]), v(f"{INVEST}!A3:F3", [KPI_HEAD]), v(f"{INVEST}!A4:F4", [_kpi()]),
           v(f"{INVEST}!A6:I6", [TABLE_HEAD])]
    out += [v(f"{INVEST}!A{r[1]}:G{r[1]}", [account_row(*r)]) for r in ACCOUNT_ROWS]
    out += [v(f"{INVEST}!A{r[1]}:G{r[1]}", [total_row(*r)]) for r in TOTAL_ROWS]
    return (out + _trend_tables()
            + [v(f"{KIS_RAW}!A1:G3", [KIS_HEAD, ["신랑", "", "", "", "", "", ""], ["신부", "", "", "", "", "", ""]]),
               v(f"{L}!A1:L1", [LOG_HEAD])])


def structure_requests() -> list[dict]:
    check = {"setDataValidation": {"range": a1_to_grid(f"{INVEST}!H1"), "rule": {
        "condition": {"type": "BOOLEAN"}, "strict": False, "showCustomUi": True}}}
    fmts = [(f"{INVEST}!A4:C4", "NUMBER", "#,##0"), (f"{INVEST}!D4", "PERCENT", "0.0%"),
            (f"{INVEST}!E4:F4", "NUMBER", "+#,##0;-#,##0;0"), (f"{INVEST}!B7:D12", "NUMBER", "#,##0"),
            (f"{INVEST}!E7:E12", "PERCENT", "0.0%"), (f"{INVEST}!F7:F12", "DATE_TIME", "mm/dd hh:mm"),
            (f"{INVEST}!H7:I12", "NUMBER", "#,##0"), (f"{INVEST}!A41:A100", "DATE", "yyyy-mm"),
            (f"{INVEST}!B41:C100", "NUMBER", "#,##0"), (f"{INVEST}!E41:E100", "DATE", "m/d"),
            (f"{INVEST}!F41:F100", "NUMBER", "#,##0"), (f"{KIS_RAW}!E2:E3", "DATE_TIME", "yyyy-mm-dd hh:mm"),
            (f"{KIS_RAW}!F2:G3", "NUMBER", "#,##0"), (f"{L}!A2:A1000", "DATE", "yyyy-mm-dd"),
            (f"{L}!B2:K1000", "NUMBER", "#,##0")]
    return [check] + [number_format(a1, kind, pattern) for a1, kind, pattern in fmts]


def visual_requests() -> list[dict]:
    monthly = _basic("월별 투자 추이 (월말)", "LINE", f"{INVEST}!A40:A100",
                     [(f"{INVEST}!B40:B100", "LINE"), (f"{INVEST}!C40:C100", "LINE")])
    recent = _basic("최근 30일 합산 평가금액", "LINE", f"{INVEST}!E40:E100", [(f"{INVEST}!F40:F100", "LINE")])
    signs = [f"{INVEST}!C4", f"{INVEST}!E4:F4", f"{INVEST}!D7:E12"]
    manual = {"repeatCell": {"range": a1_to_grid(f"{INVEST}!H7:I12"), "cell": {"userEnteredFormat": {
        "backgroundColor": CHECK_BG}}, "fields": "userEnteredFormat.backgroundColor"}}
    return ([_chart(monthly, INVEST, 13), _chart(recent, INVEST, 30), manual]
            + [_sign_rule(a1, "NUMBER_GREATER", RED_TEXT) for a1 in signs]
            + [_sign_rule(a1, "NUMBER_LESS", BLUE_TEXT) for a1 in signs])
```

`styling.py`: import에 `INVEST` 추가. `TAB_COLORS`에 `INVEST: VIEW_TAB`, `COL_WIDTHS`에 `INVEST: [150, 130, 130, 120, 80, 120, 220, 120, 120, 30]`, 눈금선 숨김 목록 `(GUIDE, DASH, TREND, CAL, STOCK, MERITZ, STOCK2, MERITZ2, COUPLE)`에 `INVEST` 추가, `HEADERS`에 `(f"{INVEST}!A3:F3", VIEW_TAB), (f"{INVEST}!A6:I6", VIEW_TAB), (f"{INVEST}!A40:C40", VIEW_TAB), (f"{INVEST}!E40:F40", VIEW_TAB),` 추가.

`guide.py`: '⭐ 이것만 기억하세요'의 '보기' 행 B를 `"[대시보드] 이번 달 살림 · [부부] 사람별 지출과 정산 · [자산기록] 순자산 추이 · [투자] 부부 주식 계좌 합산과 추이."`, '숨긴 탭' 행 B를 `"추이·달력·검색·주식/메리츠 상세는 숨겨 두었습니다. PC에서 메뉴 '가계부'로 열고, 다 보면 '꺼낸 탭 다시 숨기기'. 숨겨도 자동 기능은 그대로 돌아갑니다."`로. '📈 주식 (메리츠증권)' 구역 제목 바로 다음에 두 행 추가:

```python
    ("row", "[투자]", "신랑·신부의 메리츠·한투 ISA 계좌 4개를 합친 평가금액·투자원금·손익과 전일·전월말 대비, 월별·최근 30일 그래프를 봅니다. 매일 아침 6시에 전날 값이 기록됩니다. 어떤 계좌가 자동 조회가 안 되면 H·I열 직접입력 칸에 숫자를 적으세요. 원금은 '매입금액+현금' 추정이라 팔아서 남은 수익 현금도 원금에 들어갑니다."),
    ("row", "한투 ISA 키 입력", "각자 PC에서 메뉴 '증권 연동 → 한투 ISA 키 입력 (내 계좌)'으로 App Key·App Secret·ISA 계좌번호 10자리를 넣고, 처음 한 번 '자동 갱신 켜기 (내 계좌)'를 누릅니다. 키는 넣은 사람 구글 계정에만 저장됩니다."),
```

그리고 기존 '키 입력 (각자)' 행 B의 메뉴 이름 `'메리츠 → 키 입력 (내 계좌)'` → `'증권 연동 → 메리츠 키 입력 (내 계좌)'`, `'메리츠 → 자동 갱신 켜기 (내 계좌)'` → `'증권 연동 → 자동 갱신 켜기 (내 계좌)'`.

`build_budget.py`: `import invest` 추가, `structure_requests()` 끝 `+ layout.protection_requests())` 앞에 `+ invest.structure_requests()`, `value_data` 끝에 `+ invest.invest_values()`, `visual_requests` 끝에 `+ invest.visual_requests()`.

기존 시험 갱신 (의도한 변경):
- `tests/test_couple.py::test_rarely_used_view_tabs_start_hidden_but_keep_styling`: `tucked`에 `"주식_신랑"`, 숨김 집합에 `"한투원본", "투자기록"`, 보이는 집합의 `"주식_신랑"` → `"투자"`.
- `tests/test_couple.py::test_asset_owner_column_and_meritz_sync_choices`: 기대 목록 → `["메리츠_신랑", "한투ISA_신랑", "메리츠_신부", "한투ISA_신부"]`.
- `tests/test_couple.py::test_asset_balance_reads_the_chosen_meritz_slot`: `"투자!$B$7" in e2 and "투자!$B$10" in e2`.
- `tests/test_formulas.py::test_asset_balance_uses_meritz_net_when_linked`: `pick = 'IFERROR(CHOOSE(MATCH(sync,{"메리츠_신랑","한투ISA_신랑","메리츠_신부","한투ISA_신부"},0),투자!$B$7,투자!$B$8,투자!$B$10,투자!$B$11),"")'`.
- `tests/test_formulas.py::test_asset_link_status_shows_time_stale_or_missing`: at 줄 → `투자!$F$7,투자!$F$8,투자!$F$10,투자!$F$11`, 마지막 줄 → `'"연동 "&TEXT(at,"mm/dd hh:mm")'`.
- `tests/test_layout.py::test_asset_link_column_dropdown_and_status_protected`: 기대 values → 위 4개.
- `verify_meritz.py`: `startswith("메리츠 ")` → `startswith("연동 ")`, 오류 문구 `'메리츠 …'` → `'연동 …'`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q 2>&1 | tail -1`
Expected: 모두 통과 (`0 failed`)

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add -A && git commit -m "feat: [투자] 탭 생성기 — 계좌 4개 합산·직접입력·전일/전월말 대비·월말/30일 추이, 자산 연동 4계좌

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 운영 마이그레이션 확장 + 임시 시트 통합 시험

**Files:**
- Modify: `migrate_couple.py` (State·_structure·_values·_visual·_state)
- Modify: `tests/test_migrate_couple.py`
- Create: `verify_invest.py`

**Interfaces:**
- Consumes: Task 4의 `invest.*`, `layout.INVEST/KIS_RAW/INVEST_LOG`
- Produces: `migrate_couple.INVEST_TABS`, `State.invest_charts:int` (기본 0)

- [ ] **Step 1: Write the failing test** — `tests/test_migrate_couple.py` 끝에 추가, 그리고 `DONE` 상태에 `invest_charts=2` 추가 (`DONE = mc.State(..., budgets_empty=False, invest_charts=2)`).
  기존 `test_live_sheet_renames_adds_tabs_and_columns`의 기대 목록도 바꾼다 (운영 첫 적용 상태면 투자 탭 3개도 함께 생김):
  `assert added == sorted(["부부", "자산기록", "주식_신부", "메리츠_신부", "메리츠원본2", "투자", "한투원본", "투자기록"])`

```python


AFTER_COUPLE = mc.State(titles={t for t, *_ in layout.SHEETS} - {"투자", "한투원본", "투자기록"}, settings_cols=13,
                        asset_cols=9, networth_charts=1, settings=[["식비", "지출", 600000]], budgets_empty=False)


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q tests/test_migrate_couple.py 2>&1 | tail -2`
Expected: `invest_charts` 인자 없음 / 기대한 탭 추가 없음으로 실패

- [ ] **Step 3: Implement** — `migrate_couple.py`

```python
# import 에 invest 추가, layout import 에 INVEST, INVEST_LOG, KIS_RAW 추가
INVEST_TABS = (INVEST, KIS_RAW, INVEST_LOG)
```

`State`에 마지막 필드 추가: `invest_charts: int = 0  # [투자] 탭 차트 수 (있으면 투자 보기 서식이 이미 적용된 것)`

`_structure`를 이렇게 바꾼다 (기존 couple 묶음은 그대로, 투자 묶음은 따로 한 번):

```python
def _invest_structure(new_ids: set[int]) -> list[dict]:
    """투자 탭 묶음: 검증·서식·보호(새 탭만) + 자산 G 연동 선택지 4계좌로 갱신. 한 번만."""
    valid = _in(layout.validation_requests(), [f"{ASSETS}!G2:G50"], "setDataValidation")
    return valid + invest.structure_requests() + _only(layout.protection_requests(), new_ids)


def _structure(s: State) -> list[dict]:
    reqs = [_prop({"sheetId": SHEET_ID[new], "title": new}, "title") for old, new in RENAMES.items() if old in s.titles]
    new = [t for t in NEW_TABS if t not in s.titles]
    new_invest = [t for t in INVEST_TABS if t not in s.titles]
    reqs += [_add_sheet(t) for t in new + new_invest]
    for title, have in ((SETTINGS, s.settings_cols), (ASSETS, s.asset_cols)):
        if have < COLS[title]:
            reqs.append({"appendDimension": {"sheetId": SHEET_ID[title], "dimension": "COLUMNS",
                                             "length": COLS[title] - have}})
    reqs += [_prop({"sheetId": sid, "index": i}, "index") for i, (_t, sid, *_r) in enumerate(SHEETS)]
    reqs += [_prop({"sheetId": SHEET_ID[t], "hidden": True}, "hidden") for t in sorted(layout.TUCKED)]
    reqs.append({"unmergeCells": {"range": GUIDE_ALL}})  # 병합 칸 밑으로 쓴 값은 버려지므로 값 쓰기 전에 푼다
    if new:  # 한 batchUpdate는 원자적: 새 탭이 이미 있으면 이 묶음 전체가 이미 적용된 것
        reqs += _new_tab_structure({SHEET_ID[t] for t in new})
    if new_invest:
        reqs += _invest_structure({SHEET_ID[t] for t in new_invest})
    return reqs
```

`_values` 반환식 끝에 `+ invest.invest_values()` 추가.

`_visual`을 이렇게 바꾼다:

```python
def _visual(s: State) -> list[dict]:
    out = []
    if not s.networth_charts:  # 차트도 같은 원자적 묶음 → 있으면 부부 보기 서식이 이미 적용된 것
        new_ids = {SHEET_ID[t] for t in NEW_TABS}
        touched = new_ids | {SHEET_ID[SETTINGS], SHEET_ID[ASSETS]}
        out += (_only(styling.base_requests(), new_ids)
                + _only(styling.layout_requests() + styling.header_requests(), touched)
                + _only(styling.highlight_requests(), {SHEET_ID[COUPLE]}) + styling.couple_title_requests()
                + couple.visual_requests() + meritz_style.visual_requests([MERITZ_SLOTS[1]])
                + [charts.unregistered_payment_rule()])
    if not s.invest_charts:
        ids = {SHEET_ID[INVEST]}
        out += (_only(styling.base_requests() + styling.layout_requests() + styling.header_requests(), ids)
                + invest.visual_requests())
    return out + _guide_format()
```

`_state`: `charts_n` 다음 줄에 `invest_n = len(props.get(SHEET_ID[INVEST], {}).get("charts", []))`, `State(...)` 호출 끝 인자에 `invest_n` 추가 (`pies[0] if pies else None, invest_n`).

`verify_invest.py`:

```python
"""투자 탭 통합 시험 — 임시 시트에 가짜 원본·투자기록을 넣고 합산·증감·월말 표·직접입력·자산 연동을 확인한 뒤 휴지통으로.

운영 시트에는 손대지 않는다. 사용: python3 verify_invest.py  (종료코드 0 = 통과)
"""
import datetime as dt
import sys
from zoneinfo import ZoneInfo

from googleapiclient.discovery import build

import build_budget
import layout
from auth import get_credentials
from verify_meritz import _read, _same, serial


def log_rows() -> list[list]:
    d = lambda m, day: serial(dt.datetime(2026, m, day))
    row = lambda date, total, principal: [date, total, principal, "", "", "", "", "", "", total, principal, 3]
    return [row(d(9, 29), 3000000, 2700000), row(d(9, 30), 3100000, 2700000),
            row(d(10, 7), 3400000, 3000000), row(d(10, 8), 3500000, 3100000)]


def sample(now: float) -> list[dict]:
    return [layout.v("메리츠원본!B2", [["성공"]]), layout.v("메리츠원본!H7:H9", [[1000000], [now], [900000]]),
            layout.v("한투원본!B2:G2", [["성공", "0", "", now, 2000000, 1800000]]),
            layout.v("투자!H10:I10", [[500000, 400000]]), layout.v("투자!H11", [[100000]]),
            layout.v("자산!A5:G5", [["ISA권", "통장", 0, "", "", "", "한투ISA_신랑"]]),
            layout.v("투자기록!A2:L5", log_rows())]


def checks() -> dict:
    return {"투자!B7": 1000000, "투자!C7": 900000, "투자!G7": "자동", "투자!G8": "자동", "투자!G10": "직접입력",
            "투자!B11": 100000, "투자!C11": "", "투자!B9": 3000000, "투자!B12": 600000,
            "투자!A4": 3600000, "투자!B4": 3100000, "투자!C4": 500000,
            "투자!E4": 100000, "투자!F4": 400000,
            "투자!B41": 3100000, "투자!B42": 3500000, "투자!C42": 3100000,
            "자산!E5": 2000000}


def run(sheets, vals, drive) -> list[str]:
    sid = sheets.create(body=layout.create_body("투자 시험 (자동 삭제)"), fields="spreadsheetId").execute()["spreadsheetId"]
    try:
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.structure_requests()}).execute()
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "USER_ENTERED",
                                                  "data": build_budget.value_data("nobody@example.com")}).execute()
        sheets.batchUpdate(spreadsheetId=sid, body={"requests": build_budget.visual_requests()}).execute()
        now = serial(dt.datetime.now(ZoneInfo("Asia/Seoul")))
        vals.batchUpdate(spreadsheetId=sid, body={"valueInputOption": "RAW", "data": sample(now)}).execute()
        return [f"{a1}: 기대 {want!r}, 실제 {_read(vals, sid, a1)!r}"
                for a1, want in checks().items() if not _same(_read(vals, sid, a1) or "", want)]
    finally:
        drive.files().update(fileId=sid, body={"trashed": True}).execute()


def main() -> int:
    creds = get_credentials()
    sheets = build("sheets", "v4", credentials=creds).spreadsheets()
    errors = run(sheets, sheets.values(), build("drive", "v3", credentials=creds))
    print("\n".join(errors) if errors else f"통과: 투자 탭 {len(checks())}개 항목 일치 (임시 시트는 휴지통으로)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
```

(기대값 근거: 계좌 합 1,000,000 + 2,000,000 + 500,000 + 100,000 = 3,600,000. 원금 900,000 + 1,800,000 + 400,000 = 3,100,000 — 신부 ISA는 직접 평가만 있어 원금 빈칸. 투자기록 마지막 두 줄 3,500,000 − 3,400,000 = 100,000. 전월말 3,500,000 − 3,100,000(9/30) = 400,000.)

- [ ] **Step 4: Run tests**

Run: `cd "/mnt/d/budget book" && python3 -m pytest -q 2>&1 | tail -1 && timeout 300 python3 verify_invest.py && timeout 300 python3 verify_couple.py && timeout 300 python3 verify_meritz.py`
Expected: pytest `0 failed`, 세 통합 시험 모두 `통과` (종료코드 0)

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add -A && git commit -m "feat: 운영 마이그레이션에 투자 탭 묶음(한 번만) 추가, 투자 탭 임시 시트 통합 시험

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 운영 적용·확인·문서

**Files:**
- Modify: `README.md`
- Modify: `~/.claude/projects/-home-jack/memory/project_budget_book.md`

- [ ] **Step 1: 적용 전 스냅숏** (사용자 데이터 비교용, 스크래치패드에 저장)

```bash
python3 <<'EOF' > /tmp/claude-1000/-home-jack/49a9863d-50cd-4147-96fb-6b7088fd25f6/scratchpad/invest_before.json
import sys, json; sys.path.insert(0, "/mnt/d/budget book")
from pathlib import Path
from googleapiclient.discovery import build
from auth import get_credentials
sid = Path("/mnt/d/budget book/.spreadsheet_id").read_text().strip()
s = build("sheets", "v4", credentials=get_credentials()).spreadsheets()
rngs = ["내역!A2:J500", "반복!A2:I50", "즐겨찾기!A2:G50", "자산!A2:D50", "자산!F2:F50", "자산!I2:I50", "설정!A2:M60"]
got = s.values().batchGet(spreadsheetId=sid, ranges=rngs, valueRenderOption="UNFORMATTED_VALUE").execute()["valueRanges"]
print(json.dumps({r: g.get("values", []) for r, g in zip(rngs, got)}, ensure_ascii=False))
EOF
```

- [ ] **Step 2: 마이그레이션 → 배포**

Run: `cd "/mnt/d/budget book" && timeout 300 python3 migrate_couple.py && python3 deploy_script.py`
Expected: `적용: …` 출력, `업로드 완료: scriptId=…`

- [ ] **Step 3: 운영 확인**
  - 같은 스냅숏을 `invest_after.json`으로 다시 떠서 `python3 -c "import json;d='/tmp/claude-1000/-home-jack/49a9863d-50cd-4147-96fb-6b7088fd25f6/scratchpad/';print(json.load(open(d+'invest_before.json'))==json.load(open(d+'invest_after.json')))"` → `True`
  - 보이는 탭 11개가 Global Constraints 순서와 같은지, 21+3개 탭 전체 오류 칸(`#REF` `#N/A` `#VALUE` `#ERROR` `#DIV` `#NAME` `#NUM`) 0인지, [투자] 차트 2개인지 (`scratchpad/post.py` 재사용)
  - `투자!G7:G11` 상태가 키 발급 전이므로 '키없음' 또는 '아직 갱신 전'인지
  - 마이그레이션을 한 번 더 돌려 `addSheet`/`addChart`가 없는지 (출력의 서식 요청 수가 사용법 서식만큼인지)

- [ ] **Step 4: 문서**
  - `README.md` 사용법에 한 줄: `- **투자**: \`투자\` 탭 — 메리츠·한투 ISA 계좌 4개 합산(평가·원금·손익·전일/전월말 대비)과 월별·최근 30일 추이. 매일 06시 전날 값 기록(\`투자기록\`, 같은 날짜 덮어씀). 자동 조회가 안 되는 계좌는 H·I열 직접입력. 한투 키는 메뉴 \`증권 연동 > 한투 ISA 키 입력 (내 계좌)\`.`
  - `README.md` 개발에 한 줄: `- 투자 탭 통합 시험(임시 시트): \`python3 verify_invest.py\``
  - 메모리 `project_budget_book.md`에 적용 결과·남은 사용자 몫(한투 앱키 신청 시 ISA 선택 가능 여부 확인, 각자 키 입력·자동 갱신 켜기, 자산 G열 연동 선택) 기록.

- [ ] **Step 5: Commit**

```bash
cd "/mnt/d/budget book" && git add README.md && git commit -m "docs: 투자 탭 사용법·통합 시험 안내

운영 적용 완료: 사용자 입력 데이터 불변, 오류 칸 0.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
